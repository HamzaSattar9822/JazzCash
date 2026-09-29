"""Pydantic models for JazzCash AI Assistant API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    ENGLISH = "english"
    URDU = "urdu"
    ROMAN_URDU = "roman_urdu"
    MIXED = "mixed"


class Intent(str, Enum):
    SERVICE_DISCOVERY = "service_discovery"
    APP_NAVIGATION = "app_navigation"
    HOW_TO = "how_to"
    PRODUCT_DISCOVERY = "product_discovery"
    FEES = "fees"
    TROUBLESHOOTING = "troubleshooting"
    TRANSACTION_EXPLANATION = "transaction_explanation"
    OFFERS = "offers"
    FAQ = "faq"
    SUPPORT = "support"
    CONTEXTUAL_ASSISTANCE = "contextual_assistance"
    TRANSACTION_EXECUTION_REQUEST = "transaction_execution_request"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class SuggestedAction(BaseModel):
    label: str
    route: str
    description: Optional[str] = None


class LatencyMetrics(BaseModel):
    language_ms: Optional[float] = None
    intent_ms: Optional[float] = None
    retrieval_ms: Optional[float] = None
    llm_first_token_ms: Optional[float] = None
    llm_total_ms: Optional[float] = None
    stt_ms: Optional[float] = None
    tts_first_audio_ms: Optional[float] = None
    tts_total_ms: Optional[float] = None
    first_audio_perceived_ms: Optional[float] = None
    total_ms: Optional[float] = None


class RetrievedDocument(BaseModel):
    id: str
    title: str
    category: str
    score: float
    snippet: str


class ChatMessage(BaseModel):
    role: str  # user | assistant | system
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: list[ChatMessage] = Field(default_factory=list)
    context: Optional[dict[str, Any]] = None
    stream: bool = True
    # Force reply language: "english" | "urdu" (optional — overrides auto-detect)
    preferred_language: Optional[str] = None


class AgentResponse(BaseModel):
    language: Language
    intent: Intent
    response: str
    suggested_action: Optional[SuggestedAction] = None
    suggested_prompts: list[str] = Field(default_factory=list)
    retrieved: list[RetrievedDocument] = Field(default_factory=list)
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics)
    session_id: str
    blocked_transaction: bool = False


class VoiceSessionRequest(BaseModel):
    session_id: Optional[str] = None
    context: Optional[dict[str, Any]] = None


class VoiceSessionResponse(BaseModel):
    session_id: str
    state: VoiceState = VoiceState.IDLE


class TranscribeRequest(BaseModel):
    session_id: str
    # audio sent as multipart; this is for JSON fallback with base64
    audio_base64: Optional[str] = None
    language_hint: Optional[str] = None


class TranscribeResponse(BaseModel):
    text: str
    language: Optional[Language] = None
    latency_ms: float
    is_final: bool = True


class VoiceRespondRequest(BaseModel):
    session_id: str
    transcript: str
    history: list[ChatMessage] = Field(default_factory=list)
    context: Optional[dict[str, Any]] = None


class SpeakRequest(BaseModel):
    text: str
    language: Optional[Language] = None
    session_id: Optional[str] = None
    voice: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    llm: bool
    stt: bool
    tts: bool
    rag: bool
    version: str = "1.0.0-demo"
