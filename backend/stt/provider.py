"""Speech-to-Text provider abstraction."""

from __future__ import annotations

import abc
import io
import logging
import time
from typing import Optional

import httpx
from openai import AsyncOpenAI

from config import get_settings

logger = logging.getLogger(__name__)


class STTProvider(abc.ABC):
    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language_hint: Optional[str] = None,
    ) -> tuple[str, float]:
        """Return (transcript, latency_ms)."""


class OpenAISTTProvider(STTProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.stt_model
        key = settings.effective_stt_key
        # Never point Whisper at the Jazz chat LLM host
        self.client = AsyncOpenAI(
            api_key=key or "missing",
            base_url=settings.openai_base_url.rstrip("/"),
        )
        self.configured = bool(
            key and key not in ("sk-your-openai-key-here", "not-required", "none")
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language_hint: Optional[str] = None,
    ) -> tuple[str, float]:
        if not self.configured:
            raise RuntimeError("STT API key not configured")
        start = time.perf_counter()
        # Whisper language codes: en, ur
        lang = None
        if language_hint in ("en", "english"):
            lang = "en"
        elif language_hint in ("ur", "urdu"):
            lang = "ur"

        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        kwargs: dict = {
            "model": self.model,
            "file": file_obj,
        }
        if lang:
            kwargs["language"] = lang

        resp = await self.client.audio.transcriptions.create(**kwargs)
        text = (resp.text or "").strip()
        latency = (time.perf_counter() - start) * 1000
        return text, latency


class DeepgramSTTProvider(STTProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.deepgram_api_key
        self.configured = bool(self.api_key)

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language_hint: Optional[str] = None,
    ) -> tuple[str, float]:
        if not self.configured:
            raise RuntimeError("DEEPGRAM_API_KEY not configured")
        start = time.perf_counter()
        lang = "en"
        if language_hint in ("ur", "urdu"):
            lang = "ur"
        params = {"model": "nova-2", "smart_format": "true", "language": lang}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen",
                params=params,
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "audio/webm",
                },
                content=audio_bytes,
            )
            resp.raise_for_status()
            data = resp.json()
        text = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        latency = (time.perf_counter() - start) * 1000
        return text.strip(), latency


def get_stt_provider() -> STTProvider:
    settings = get_settings()
    if settings.stt_provider == "deepgram":
        return DeepgramSTTProvider()
    return OpenAISTTProvider()
