"""FastAPI route modules."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from agents.pipeline import get_or_create_session, run_agent, run_agent_stream
from config import get_settings
from llm.provider import get_llm_provider
from mock_data import jazzcash_data as mock
from models.schemas import (
    AgentResponse,
    ChatRequest,
    HealthResponse,
    SpeakRequest,
    TranscribeResponse,
    VoiceRespondRequest,
    VoiceSessionRequest,
    VoiceSessionResponse,
    VoiceState,
)
from rag.store import knowledge_store
from stt.provider import get_stt_provider
from tts.provider import get_tts_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    llm_ok = settings.llm_configured
    stt = get_stt_provider()
    tts = get_tts_provider()
    stt_ok = getattr(stt, "configured", False)
    tts_ok = getattr(tts, "configured", False)
    if settings.stt_provider == "deepgram":
        stt_ok = bool(settings.deepgram_api_key)
    if settings.tts_provider == "elevenlabs":
        tts_ok = bool(settings.elevenlabs_api_key)
    return HealthResponse(
        status="ok" if llm_ok else "degraded",
        llm=llm_ok,
        stt=stt_ok,
        tts=tts_ok,
        rag=True,
    )


@router.post("/chat", response_model=AgentResponse)
async def chat(req: ChatRequest) -> AgentResponse:
    ctx = dict(req.context or {})
    if req.preferred_language:
        ctx["preferred_language"] = req.preferred_language
    return await run_agent(
        message=req.message,
        session_id=req.session_id,
        history=req.history,
        context=ctx,
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    ctx = dict(req.context or {})
    if req.preferred_language:
        ctx["preferred_language"] = req.preferred_language

    async def event_gen():
        async for evt in run_agent_stream(
            message=req.message,
            session_id=req.session_id,
            history=req.history,
            context=ctx,
        ):
            yield {
                "event": evt["event"],
                "data": json.dumps(evt["data"], ensure_ascii=False),
            }

    return EventSourceResponse(event_gen())


@router.post("/voice/session", response_model=VoiceSessionResponse)
async def voice_session(req: VoiceSessionRequest) -> VoiceSessionResponse:
    sid = get_or_create_session(req.session_id)
    return VoiceSessionResponse(session_id=sid, state=VoiceState.IDLE)


@router.post("/voice/transcribe", response_model=TranscribeResponse)
async def voice_transcribe(
    session_id: str = Form(...),
    language_hint: Optional[str] = Form(None),
    file: UploadFile = File(...),
) -> TranscribeResponse:
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio")
    stt = get_stt_provider()
    try:
        text, latency = await stt.transcribe(
            audio,
            filename=file.filename or "audio.webm",
            language_hint=language_hint,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("STT failed")
        raise HTTPException(502, f"STT failure: {exc}") from exc
    if not text:
        raise HTTPException(422, "No speech detected")
    return TranscribeResponse(text=text, latency_ms=round(latency, 1), is_final=True)


@router.post("/voice/transcribe-base64", response_model=TranscribeResponse)
async def voice_transcribe_b64(payload: dict) -> TranscribeResponse:
    audio_b64 = payload.get("audio_base64")
    if not audio_b64:
        raise HTTPException(400, "audio_base64 required")
    audio = base64.b64decode(audio_b64)
    stt = get_stt_provider()
    try:
        text, latency = await stt.transcribe(
            audio,
            filename=payload.get("filename", "audio.webm"),
            language_hint=payload.get("language_hint"),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"STT failure: {exc}") from exc
    if not text:
        raise HTTPException(422, "No speech detected")
    return TranscribeResponse(text=text, latency_ms=round(latency, 1), is_final=True)


@router.post("/voice/respond", response_model=AgentResponse)
async def voice_respond(req: VoiceRespondRequest) -> AgentResponse:
    return await run_agent(
        message=req.transcript,
        session_id=req.session_id,
        history=req.history,
        context=req.context,
    )


@router.post("/voice/speak")
async def voice_speak(req: SpeakRequest):
    tts = get_tts_provider()
    start = time.perf_counter()

    async def audio_gen():
        first_sent = False
        try:
            async for chunk, first_ms in tts.synthesize_stream(
                req.text,
                voice=req.voice,
                language=req.language,
            ):
                if not first_sent and first_ms is not None:
                    first_sent = True
                    # Client can read X-First-Audio-Ms from headers; also prefix meta is hard in raw stream
                yield chunk
        except Exception as exc:  # noqa: BLE001
            logger.exception("TTS stream failed: %s", exc)
            raise

    try:
        # Prefer streaming response
        return StreamingResponse(
            audio_gen(),
            media_type="audio/mpeg",
            headers={
                "X-TTS-Started": str(round((time.perf_counter() - start) * 1000, 1)),
                "Cache-Control": "no-cache",
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"TTS failure: {exc}") from exc


@router.post("/voice/speak-full")
async def voice_speak_full(req: SpeakRequest):
    tts = get_tts_provider()
    try:
        audio, latency = await tts.synthesize(req.text, voice=req.voice, language=req.language)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"TTS failure: {exc}") from exc
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"X-TTS-Latency-Ms": str(round(latency, 1))},
    )


@router.get("/services")
async def services():
    return {"services": mock.SERVICES, "environment": mock.USER["environment"]}


@router.get("/offers")
async def offers():
    return {"offers": mock.OFFERS, "environment": mock.USER["environment"]}


@router.get("/products")
async def products():
    return {"products": mock.PRODUCTS, "environment": mock.USER["environment"]}


@router.get("/transactions")
async def transactions():
    return {
        "user": mock.USER,
        "transactions": mock.TRANSACTIONS,
        "environment": mock.USER["environment"],
    }


@router.get("/user")
async def user():
    return mock.USER


@router.get("/support")
async def support():
    return {"tickets": mock.SUPPORT_TICKETS, "helpline": "Demo only — 0000"}


@router.get("/fees")
async def fees():
    return {"fees": mock.FEES}
