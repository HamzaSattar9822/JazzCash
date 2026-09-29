"""Text-to-Speech provider abstraction with streaming support."""

from __future__ import annotations

import abc
import logging
import time
from typing import AsyncIterator, Optional

import httpx
from openai import AsyncOpenAI

from config import get_settings
from models.schemas import Language

logger = logging.getLogger(__name__)


class TTSProvider(abc.ABC):
    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> tuple[bytes, float]:
        """Return (audio_bytes, latency_ms) — full audio."""

    @abc.abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> AsyncIterator[tuple[bytes, Optional[float]]]:
        """Yield (chunk, first_audio_ms_once)."""


class OpenAITTSProvider(TTSProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.tts_model
        self.default_voice = settings.tts_voice
        key = settings.effective_tts_key
        self.client = AsyncOpenAI(
            api_key=key or "missing",
            base_url=settings.openai_base_url.rstrip("/"),
        )
        self.configured = bool(
            key and key not in ("sk-your-openai-key-here", "not-required", "none")
        )

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> tuple[bytes, float]:
        if not self.configured:
            raise RuntimeError("TTS API key not configured")
        start = time.perf_counter()
        resp = await self.client.audio.speech.create(
            model=self.model,
            voice=voice or self.default_voice,
            input=text[:4096],
            response_format="mp3",
        )
        audio = resp.content
        latency = (time.perf_counter() - start) * 1000
        return audio, latency

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> AsyncIterator[tuple[bytes, Optional[float]]]:
        if not self.configured:
            raise RuntimeError("TTS API key not configured")
        start = time.perf_counter()
        first_ms: Optional[float] = None
        async with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=voice or self.default_voice,
            input=text[:4096],
            response_format="mp3",
        ) as resp:
            async for chunk in resp.iter_bytes(1024):
                if chunk:
                    if first_ms is None:
                        first_ms = (time.perf_counter() - start) * 1000
                        yield chunk, first_ms
                    else:
                        yield chunk, None


class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id
        self.configured = bool(self.api_key)

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> tuple[bytes, float]:
        chunks: list[bytes] = []
        first = None
        start = time.perf_counter()
        async for chunk, ft in self.synthesize_stream(text, voice, language):
            chunks.append(chunk)
            if ft is not None:
                first = ft
        return b"".join(chunks), first or (time.perf_counter() - start) * 1000

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> AsyncIterator[tuple[bytes, Optional[float]]]:
        if not self.configured:
            raise RuntimeError("ELEVENLABS_API_KEY not configured")
        start = time.perf_counter()
        first_ms: Optional[float] = None
        voice_id = voice or self.voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "xi-api-key": self.api_key,
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                },
                json={
                    "text": text[:4096],
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
                },
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(1024):
                    if chunk:
                        if first_ms is None:
                            first_ms = (time.perf_counter() - start) * 1000
                            yield chunk, first_ms
                        else:
                            yield chunk, None


def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    if settings.tts_provider == "elevenlabs":
        return ElevenLabsTTSProvider()
    return OpenAITTSProvider()
