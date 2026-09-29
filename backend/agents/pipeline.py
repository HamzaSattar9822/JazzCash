"""Conversational agent: language → intent → RAG → LLM → structured response."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, AsyncIterator, Optional

from agents.intent import TRANSACTION_REFUSAL, detect_intent
from agents.language import detect_language, response_matches_language, urdu_script_ratio
from llm.provider import build_messages, get_llm_provider
from mock_data import jazzcash_data as mock
from models.schemas import (
    AgentResponse,
    ChatMessage,
    Intent,
    Language,
    LatencyMetrics,
    SuggestedAction,
)
from rag.store import knowledge_store

logger = logging.getLogger(__name__)

# In-memory sessions (replace with Redis later)
_SESSIONS: dict[str, list[dict[str, str]]] = {}
_SESSION_LANG: dict[str, Language] = {}


def get_or_create_session(session_id: Optional[str] = None) -> str:
    sid = session_id or str(uuid.uuid4())
    _SESSIONS.setdefault(sid, [])
    return sid


def append_history(session_id: str, role: str, content: str) -> None:
    _SESSIONS.setdefault(session_id, []).append({"role": role, "content": content})
    _SESSIONS[session_id] = _SESSIONS[session_id][-20:]


def set_session_language(session_id: str, language: Language) -> None:
    _SESSION_LANG[session_id] = language


def get_session_language(session_id: str) -> Optional[Language]:
    return _SESSION_LANG.get(session_id)


def _extract_first_json_object(text: str) -> Optional[dict[str, Any]]:
    """Pull the first balanced {...} object from model output (Gemma often adds notes after)."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start : i + 1]
                try:
                    data = json.loads(chunk)
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError:
                    return None
    return None


def _unwrap_nested_response(data: dict[str, Any]) -> dict[str, Any]:
    """If response field is itself a JSON object string, unwrap (up to 3 levels)."""
    current = data
    for _ in range(3):
        resp = current.get("response")
        if not isinstance(resp, str):
            break
        stripped = resp.strip()
        if not (stripped.startswith("{") and '"response"' in stripped):
            break
        inner = _extract_first_json_object(stripped)
        if not inner or not isinstance(inner.get("response"), str):
            break
        # Prefer inner object fields; keep outer extras only as fallback
        merged = {**current, **inner}
        current = merged
        if not str(inner["response"]).strip().startswith("{"):
            break
    return current


def _sanitize_response_text(text: str) -> str:
    """Strip accidental JSON wrappers from the user-facing reply."""
    if not isinstance(text, str):
        return str(text)
    stripped = text.strip()
    if stripped.startswith("{") and '"response"' in stripped:
        inner = _extract_first_json_object(stripped)
        if inner and isinstance(inner.get("response"), str):
            return _sanitize_response_text(inner["response"])
    return stripped


def _parse_agent_json(raw: str, fallback_lang: Language, fallback_intent: Intent) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()

    data: Optional[dict[str, Any]] = None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            data = parsed
    except json.JSONDecodeError:
        data = _extract_first_json_object(text)

    if data is None:
        return {
            "language": fallback_lang.value,
            "intent": fallback_intent.value,
            "response": text,
            "suggested_action": None,
            "suggested_prompts": [],
            "blocked_transaction": fallback_intent == Intent.TRANSACTION_EXECUTION_REQUEST,
        }

    data = _unwrap_nested_response(data)
    if isinstance(data.get("response"), str):
        data["response"] = _sanitize_response_text(data["response"])
    return data



def _default_prompts(intent: Intent, language: Language) -> list[str]:
    if language == Language.URDU:
        return [
            "بجلی کا بل کہاں ادا کریں؟",
            "راست کیا ہے؟",
            "قرضہ کی قسط کتنی ہے؟",
            "لین دین کی تاریخ کہاں ہے؟",
        ]
    if language in (Language.ROMAN_URDU, Language.MIXED):
        return [
            "Electricity bill kahan pay karen?",
            "Raast kya hai?",
            "Loan qist kitni hai?",
            "Transaction history kahan hai?",
        ]
    return [
        "Find a service",
        "How do I pay a bill?",
        "What is Raast?",
        "Show my loan plan",
        "Why did my payment fail?",
    ]


def _resolve_language(
    message: str,
    context: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> tuple[Language, float, bool]:
    """Auto-detect, then honor UI preferred_language + sticky session lock."""
    language, lang_ms = detect_language(message)
    preferred = None
    if context and isinstance(context, dict):
        preferred = (
            context.get("preferred_language")
            or context.get("reply_language")
            or context.get("ui_language")
        )
    if isinstance(preferred, str):
        pref = preferred.strip().lower()
        if pref in ("urdu", "ur", "اردو"):
            if session_id:
                set_session_language(session_id, Language.URDU)
            return Language.URDU, lang_ms, True
        if pref in ("english", "en", "eng"):
            if session_id:
                set_session_language(session_id, Language.ENGLISH)
            return Language.ENGLISH, lang_ms, True
        if pref in ("roman_urdu", "roman-urdu"):
            if session_id:
                set_session_language(session_id, Language.ROMAN_URDU)
            return Language.ROMAN_URDU, lang_ms, True

    # Sticky session lock so later turns stay in the chosen language
    if session_id:
        sticky = get_session_language(session_id)
        if sticky is not None:
            return sticky, lang_ms, True
    return language, lang_ms, False


def _mock_context() -> dict[str, Any]:
    return {
        "user": mock.USER,
        "recent_transactions": mock.TRANSACTIONS[:3],
        "active_offers": mock.OFFERS[:2],
        "fees": mock.FEES,
        "note": "Concept Demo — No real transactions",
    }


async def _force_language_rewrite(
    llm: Any,
    *,
    response_text: str,
    language: Language,
    intent: Intent,
    suggested_action: Any,
    suggested_prompts: list,
    blocked: bool,
) -> tuple[str, float, Optional[float]]:
    """Clean rewrite WITHOUT chat history — stops English/Urdu drift."""
    action_json = json.dumps(suggested_action, ensure_ascii=False) if suggested_action else "null"
    prompts_json = json.dumps(suggested_prompts[:3], ensure_ascii=False)

    if language == Language.URDU:
        instruction = (
            "Rewrite the assistant reply as NATURAL spoken Urdu in Arabic/Nastaliq script ONLY. "
            "Every sentence must be Urdu script — translate any English fully. "
            "Latin allowed ONLY for: JazzCash, Ready Cash, Raast, LESCO, SSGC, CNIC, MPIN, IBAN, QR, Rs. "
            "Forbidden: English sentences, Roman Urdu, mixed English prose."
        )
        lang_val = "urdu"
    elif language == Language.ENGLISH:
        instruction = (
            "Rewrite the assistant reply in CLEAR ENGLISH only. "
            "Do NOT use Urdu Arabic script. Do NOT use Roman Urdu."
        )
        lang_val = "english"
    else:
        instruction = (
            "Rewrite the assistant reply in Roman Urdu (Urdu in Latin letters). "
            "Do NOT use formal English-only prose."
        )
        lang_val = "roman_urdu"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict language rewriter for JazzCash AI. "
                "Output ONE JSON object only with keys: "
                "language, intent, response, suggested_action, suggested_prompts, blocked_transaction. "
                "The response field must be plain user-facing text in the target language — "
                "never nest another JSON object inside response."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{instruction}\n\n"
                f'Target language field: "{lang_val}"\n'
                f'intent: "{intent.value}"\n'
                f"suggested_action: {action_json}\n"
                f"suggested_prompts: {prompts_json}\n"
                f"blocked_transaction: {str(blocked).lower()}\n\n"
                f"Original reply to rewrite:\n{_sanitize_response_text(str(response_text))}\n\n"
                "Return JSON only. The response field MUST be plain text matching the target language."
            ),
        },
    ]
    return await llm.complete(messages, temperature=0.05)


async def run_agent(
    message: str,
    session_id: Optional[str] = None,
    history: Optional[list[ChatMessage]] = None,
    context: Optional[dict[str, Any]] = None,
) -> AgentResponse:
    total_start = time.perf_counter()
    sid = get_or_create_session(session_id)

    language, lang_ms, lang_locked = _resolve_language(message, context, session_id=sid)
    intent, intent_ms = detect_intent(message)

    retrieved, retrieval_ms = await knowledge_store.retrieve(message, top_k=4)
    knowledge = knowledge_store.get_full_content([d.id for d in retrieved])

    app_ctx = {**_mock_context(), **(context or {})}

    # Hard safety for transaction execution
    if intent == Intent.TRANSACTION_EXECUTION_REQUEST:
        refusal = TRANSACTION_REFUSAL.get(language.value, TRANSACTION_REFUSAL["roman_urdu"])
        action = SuggestedAction(label="Open Send Money", route="/send-money")
        append_history(sid, "user", message)
        append_history(sid, "assistant", refusal)
        return AgentResponse(
            language=language,
            intent=intent,
            response=refusal,
            suggested_action=action,
            suggested_prompts=_default_prompts(intent, language),
            retrieved=retrieved,
            latency=LatencyMetrics(
                language_ms=round(lang_ms, 1),
                intent_ms=round(intent_ms, 1),
                retrieval_ms=round(retrieval_ms, 1),
                llm_total_ms=0,
                total_ms=round((time.perf_counter() - total_start) * 1000, 1),
            ),
            session_id=sid,
            blocked_transaction=True,
        )

    hist = [{"role": h.role, "content": h.content} for h in (history or [])]
    if not hist:
        hist = list(_SESSIONS.get(sid, []))

    messages = build_messages(
        message,
        hist,
        knowledge,
        app_ctx,
        detected_language=language.value,
        language_locked=lang_locked,
    )
    llm = get_llm_provider()

    try:
        raw, llm_ms, first_ms = await llm.complete(
            messages,
            temperature=0.1 if lang_locked else 0.4,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM error")
        err = (
            "AI service temporarily unavailable. Please try again."
            if language == Language.ENGLISH
            else "AI سروس فی الحال دستیاب نہیں۔ براہ کرم دوبارہ کوشش کریں۔"
            if language == Language.URDU
            else "AI service abhi available nahi. Dobara try karein."
        )
        return AgentResponse(
            language=language,
            intent=intent,
            response=err,
            suggested_prompts=_default_prompts(intent, language),
            retrieved=retrieved,
            latency=LatencyMetrics(
                language_ms=round(lang_ms, 1),
                intent_ms=round(intent_ms, 1),
                retrieval_ms=round(retrieval_ms, 1),
                total_ms=round((time.perf_counter() - total_start) * 1000, 1),
            ),
            session_id=sid,
        )

    parsed = _parse_agent_json(raw, language, intent)
    response_text = parsed.get("response") or raw

    # Enforce language every turn. UI/session lock is strict for EN + URDU.
    needs_rewrite = not response_matches_language(
        str(response_text), language, strict=lang_locked
    )
    if language == Language.ENGLISH and lang_locked:
        needs_rewrite = needs_rewrite or (urdu_script_ratio(str(response_text)) >= 0.05)
    if language in (Language.URDU, Language.ROMAN_URDU, Language.ENGLISH) and needs_rewrite:
        for _attempt in range(3 if lang_locked else 1):
            try:
                raw2, llm_ms2, first_ms2 = await _force_language_rewrite(
                    llm,
                    response_text=str(response_text),
                    language=language,
                    intent=intent if isinstance(intent, Intent) else Intent.UNKNOWN,
                    suggested_action=parsed.get("suggested_action"),
                    suggested_prompts=parsed.get("suggested_prompts") or [],
                    blocked=bool(parsed.get("blocked_transaction")),
                )
                llm_ms = (llm_ms or 0) + (llm_ms2 or 0)
                if first_ms is None:
                    first_ms = first_ms2
                parsed2 = _parse_agent_json(raw2, language, intent)
                cand = _sanitize_response_text(str(parsed2.get("response") or raw2))
                improved = response_matches_language(cand, language, strict=lang_locked) or (
                    language == Language.URDU
                    and urdu_script_ratio(cand) > urdu_script_ratio(str(response_text))
                ) or (
                    language == Language.ENGLISH
                    and urdu_script_ratio(cand) < urdu_script_ratio(str(response_text))
                )
                if improved:
                    parsed = parsed2
                    response_text = cand
                if response_matches_language(str(response_text), language, strict=lang_locked):
                    break
            except Exception:  # noqa: BLE001
                logger.warning("Language rewrite pass failed; using original reply")
                break

    response_text = _sanitize_response_text(str(response_text))
    # Final hard gate for locked Urdu: only replace clearly English replies
    if lang_locked and language == Language.URDU:
        if urdu_script_ratio(response_text) < 0.4:
            response_text = (
                "معذرت — میں اس سوال کا جواب اردو میں دیتا/دیتی ہوں۔ "
                "براہ کرم دوبارہ پوچھیں، یا نیچے شارٹ کٹ استعمال کریں۔"
            )
            parsed["suggested_prompts"] = _default_prompts(intent, Language.URDU)

    # Always trust detector for language tag (keeps UI/dev mode accurate)
    out_lang = language
    try:
        out_intent = Intent(parsed.get("intent", intent.value))
    except ValueError:
        out_intent = intent

    # Enforce safety even if LLM slips
    blocked = bool(parsed.get("blocked_transaction")) or out_intent == Intent.TRANSACTION_EXECUTION_REQUEST
    if blocked and out_intent != Intent.TRANSACTION_EXECUTION_REQUEST:
        out_intent = Intent.TRANSACTION_EXECUTION_REQUEST
    if out_intent == Intent.TRANSACTION_EXECUTION_REQUEST:
        response_text = TRANSACTION_REFUSAL.get(out_lang.value, TRANSACTION_REFUSAL["roman_urdu"])
        blocked = True

    action = None
    sa = parsed.get("suggested_action")
    if isinstance(sa, dict) and sa.get("route") and sa.get("label"):
        action = SuggestedAction(label=sa["label"], route=sa["route"], description=sa.get("description"))
    elif blocked:
        action = SuggestedAction(label="Open Send Money", route="/send-money")

    prompts = parsed.get("suggested_prompts") or _default_prompts(out_intent, out_lang)
    if not isinstance(prompts, list):
        prompts = _default_prompts(out_intent, out_lang)
    # Keep follow-up chips in the locked language
    if lang_locked and out_lang == Language.URDU:
        prompts = [
            p for p in prompts
            if isinstance(p, str) and urdu_script_ratio(p) >= 0.4
        ] or _default_prompts(out_intent, Language.URDU)

    append_history(sid, "user", message)
    append_history(sid, "assistant", response_text)

    return AgentResponse(
        language=out_lang,
        intent=out_intent,
        response=response_text,
        suggested_action=action,
        suggested_prompts=prompts[:5],
        retrieved=retrieved,
        latency=LatencyMetrics(
            language_ms=round(lang_ms, 1),
            intent_ms=round(intent_ms, 1),
            retrieval_ms=round(retrieval_ms, 1),
            llm_first_token_ms=round(first_ms, 1) if first_ms else None,
            llm_total_ms=round(llm_ms, 1),
            total_ms=round((time.perf_counter() - total_start) * 1000, 1),
        ),
        session_id=sid,
        blocked_transaction=blocked,
    )


async def run_agent_stream(
    message: str,
    session_id: Optional[str] = None,
    history: Optional[list[ChatMessage]] = None,
    context: Optional[dict[str, Any]] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE-friendly events: meta, token, final, error."""
    total_start = time.perf_counter()
    sid = get_or_create_session(session_id)
    language, lang_ms, lang_locked = _resolve_language(message, context, session_id=sid)
    intent, intent_ms = detect_intent(message)
    retrieved, retrieval_ms = await knowledge_store.retrieve(message, top_k=4)
    knowledge = knowledge_store.get_full_content([d.id for d in retrieved])

    yield {
        "event": "meta",
        "data": {
            "session_id": sid,
            "language": language.value,
            "language_locked": lang_locked,
            "intent": intent.value,
            "retrieved": [r.model_dump() for r in retrieved],
            "latency": {
                "language_ms": round(lang_ms, 1),
                "intent_ms": round(intent_ms, 1),
                "retrieval_ms": round(retrieval_ms, 1),
            },
        },
    }

    if intent == Intent.TRANSACTION_EXECUTION_REQUEST:
        refusal = TRANSACTION_REFUSAL.get(language.value, TRANSACTION_REFUSAL["roman_urdu"])
        append_history(sid, "user", message)
        append_history(sid, "assistant", refusal)
        yield {
            "event": "final",
            "data": AgentResponse(
                language=language,
                intent=intent,
                response=refusal,
                suggested_action=SuggestedAction(label="Open Send Money", route="/send-money"),
                suggested_prompts=_default_prompts(intent, language),
                retrieved=retrieved,
                latency=LatencyMetrics(
                    language_ms=round(lang_ms, 1),
                    intent_ms=round(intent_ms, 1),
                    retrieval_ms=round(retrieval_ms, 1),
                    total_ms=round((time.perf_counter() - total_start) * 1000, 1),
                ),
                session_id=sid,
                blocked_transaction=True,
            ).model_dump(),
        }
        return

    hist = [{"role": h.role, "content": h.content} for h in (history or [])]
    if not hist:
        hist = list(_SESSIONS.get(sid, []))
    messages = build_messages(
        message,
        hist,
        knowledge,
        {**_mock_context(), **(context or {})},
        detected_language=language.value,
        language_locked=lang_locked,
    )
    llm = get_llm_provider()

    buffer = ""
    first_ms: Optional[float] = None
    try:
        async for delta, ft in llm.stream(messages, temperature=0.1 if lang_locked else 0.4):
            buffer += delta
            if ft is not None:
                first_ms = ft
            # Stream partial "response" field if visible; else stream raw tokens for UX
            yield {"event": "token", "data": {"delta": delta, "first_token_ms": first_ms}}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stream LLM error")
        yield {"event": "error", "data": {"message": str(exc)}}
        return

    parsed = _parse_agent_json(buffer, language, intent)
    out_lang = language
    try:
        out_intent = Intent(parsed.get("intent", intent.value))
    except ValueError:
        out_intent = intent

    blocked = bool(parsed.get("blocked_transaction")) or out_intent == Intent.TRANSACTION_EXECUTION_REQUEST
    response_text = _sanitize_response_text(str(parsed.get("response") or buffer))
    if lang_locked and language == Language.URDU and not response_matches_language(
        response_text, Language.URDU, strict=True
    ):
        # One rewrite pass on stream final
        try:
            llm2 = get_llm_provider()
            raw2, _, _ = await _force_language_rewrite(
                llm2,
                response_text=response_text,
                language=Language.URDU,
                intent=out_intent,
                suggested_action=parsed.get("suggested_action"),
                suggested_prompts=parsed.get("suggested_prompts") or [],
                blocked=blocked,
            )
            parsed2 = _parse_agent_json(raw2, Language.URDU, out_intent)
            cand = _sanitize_response_text(str(parsed2.get("response") or raw2))
            if response_matches_language(cand, Language.URDU, strict=True) or urdu_script_ratio(cand) > urdu_script_ratio(response_text):
                response_text = cand
                parsed = parsed2
        except Exception:  # noqa: BLE001
            pass
        if not response_matches_language(response_text, Language.URDU, strict=True):
            if urdu_script_ratio(response_text) < 0.4:
                response_text = (
                    "معذرت — میں اس سوال کا جواب اردو میں دیتا/دیتی ہوں۔ "
                    "براہ کرم دوبارہ پوچھیں، یا نیچے شارٹ کٹ استعمال کریں۔"
                )
    if out_intent == Intent.TRANSACTION_EXECUTION_REQUEST:
        response_text = TRANSACTION_REFUSAL.get(out_lang.value, TRANSACTION_REFUSAL["roman_urdu"])
        blocked = True

    action = None
    sa = parsed.get("suggested_action")
    if isinstance(sa, dict) and sa.get("route") and sa.get("label"):
        action = SuggestedAction(label=sa["label"], route=sa["route"])
    elif blocked:
        action = SuggestedAction(label="Open Send Money", route="/send-money")

    prompts = parsed.get("suggested_prompts") or _default_prompts(out_intent, out_lang)
    append_history(sid, "user", message)
    append_history(sid, "assistant", response_text)

    llm_total = round((time.perf_counter() - total_start) * 1000 - lang_ms - intent_ms - retrieval_ms, 1)

    yield {
        "event": "final",
        "data": AgentResponse(
            language=out_lang,
            intent=out_intent,
            response=response_text,
            suggested_action=action,
            suggested_prompts=(prompts if isinstance(prompts, list) else [])[:5],
            retrieved=retrieved,
            latency=LatencyMetrics(
                language_ms=round(lang_ms, 1),
                intent_ms=round(intent_ms, 1),
                retrieval_ms=round(retrieval_ms, 1),
                llm_first_token_ms=round(first_ms, 1) if first_ms else None,
                llm_total_ms=llm_total,
                total_ms=round((time.perf_counter() - total_start) * 1000, 1),
            ),
            session_id=sid,
            blocked_transaction=blocked,
        ).model_dump(),
    }
