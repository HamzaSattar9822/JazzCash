"""Application configuration from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_key: str = ""
    llm_model: str = "gemma-3-12b-dpo-apr-merged-aws"
    llm_base_url: str = (
        "https://gemma-3-12b-dpo-apr-merged-aws-teknosys-ai.apps.aiops.jazz.com.pk/v1"
    )
    # Jazz AIOps uses an internal CA / self-signed chain
    llm_verify_ssl: bool = False
    # vLLM/Gemma: prefer prompt-enforced JSON over response_format
    llm_json_mode: bool = False
    llm_max_tokens: int = 1024

    # Separate OpenAI-compatible endpoint for embeddings / STT / TTS (optional)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_enabled: bool = False

    stt_provider: str = "openai"
    stt_api_key: str = ""
    stt_model: str = "whisper-1"

    tts_provider: str = "openai"
    tts_api_key: str = ""
    tts_model: str = "tts-1"
    tts_voice: str = "nova"

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    deepgram_api_key: str = ""

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    dev_mode_default: bool = False
    port: int = 8000

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_stt_key(self) -> str:
        return self.stt_api_key or self.openai_api_key or self.llm_api_key

    @property
    def effective_tts_key(self) -> str:
        return self.tts_api_key or self.openai_api_key or self.llm_api_key

    @property
    def effective_embedding_key(self) -> str:
        return self.openai_api_key or self.llm_api_key

    @property
    def llm_configured(self) -> bool:
        """Jazz/internal vLLM endpoints often need no API key."""
        base = (self.llm_base_url or "").lower()
        is_public_openai = "api.openai.com" in base
        placeholder = self.llm_api_key in (
            "",
            "sk-your-openai-key-here",
            "not-required",
            "none",
        )
        if is_public_openai:
            return not placeholder
        return bool(self.llm_base_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
