"""LLM provider abstraction — OpenAI-compatible (incl. Jazz Gemma vLLM)."""

from __future__ import annotations

import abc
import json
import logging
import re
import ssl
import time
from typing import Any, AsyncIterator, Optional

import httpx
from openai import AsyncOpenAI

from config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JazzCash AI — a bilingual (English, Urdu, Roman Urdu) assistant for the JazzCash mobile wallet ecosystem in Pakistan.

ROLE:
- Help users discover services, understand features, navigate the app, learn fees, find offers/products, troubleshoot, and get support guidance.
- You are an assistance and discovery layer. You NEVER execute financial transactions.

CRITICAL SAFETY RULES:
1. NEVER pretend a transfer, bill payment, recharge, or any money movement happened.
2. If the user asks you to send/pay/transfer money (e.g. "Ali ko 5000 bhej do"), refuse execution politely and offer to GUIDE them to the correct screen.
3. Never ask for MPIN, OTP, CNIC full number, or passwords.
4. Clearly this is a Concept Demo — no real transactions.

LANGUAGE (MANDATORY — highest priority):
- If the UI / context sets preferred_language (or a session language lock), that language WINS for every turn in the conversation — even if the user types in a different language.
- Always reply in the SAME language the user used for this turn, unless a UI language lock is active.
- If the user writes in English → the "response" field MUST be English only (unless UI lock = urdu).
- If the user writes in Urdu (Arabic/Nastaliq script, e.g. میری...) → the "response" field MUST be Urdu in Arabic script only (not Roman).
- If the user writes in Roman Urdu (e.g. "Mujhe bill pay karna hai") → the "response" field MUST be Roman Urdu (unless UI lock = urdu, then use Arabic script).
- If mixed Urdu+English → reply in the same mixed style (unless UI lock forces urdu/english).
- NEVER answer an Urdu-locked chat in English mid-conversation.
- Set the JSON "language" field to match the reply language.
- Buttons/labels in suggested_action may stay short English for UI, but "response" and suggested_prompts must follow the reply language.

STYLE:
- Concise, friendly, mobile-friendly (2–4 short sentences unless explaining something complex).
- Offer a clear next step when relevant.

RESPONSE FORMAT:
You MUST respond with ONE valid JSON object only.
Do NOT wrap it in markdown.
Do NOT add any notes, examples, or text before or after the JSON.
Do NOT put JSON inside the "response" string — "response" must be plain natural language.

Example of a correct Urdu reply:
{"language":"urdu","intent":"faq","response":"راست پاکستان کا فوری ادائیگی کا نظام ہے۔ JazzCash میں Send Money سے اسے استعمال کریں۔","suggested_action":{"label":"Open Send Money","route":"/send-money"},"suggested_prompts":["فیس کتنی ہے؟","ٹرانزیکشن ہسٹری کہاں ہے؟"],"blocked_transaction":false}

Example of a correct Roman Urdu reply:
{"language":"roman_urdu","intent":"faq","response":"Raast Pakistan ka instant payment system hai.","suggested_action":{"label":"Open Send Money","route":"/send-money"},"suggested_prompts":["Fee kitni hai?","Transaction history kahan hai?"],"blocked_transaction":false}

Valid routes: /home, /services, /bills, /mobile-recharge, /send-money, /transactions, /savings, /insurance, /offers, /support, /ai, /voice, /loans

For Ready Cash / loan repayment journey (plans, late fees, catch-up, reminders, due dates):
explain using APP CONTEXT ready_cash_loan if present, and set suggested_action to
{"label":"Open Loan Repayment","route":"/loans"}.

CX 4.0 engagement modes you may reference when relevant: Event-Driven Engagement (bills),
Predictive Engagement (top-up expiry), Real-Time Service Recovery (failed payments),
Hyper-Personalized Engagement (offers), Autonomous Self-Healing, Proactive Repayment Journey Management (loans).

Use retrieved knowledge and mock context when provided. If knowledge is missing, say so honestly and suggest Support.
"""


def _build_http_client(verify_ssl: bool) -> httpx.AsyncClient:
    if verify_ssl:
        return httpx.AsyncClient(timeout=120.0)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return httpx.AsyncClient(verify=False, timeout=120.0)


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, float, Optional[float]]:
        """Return (content, total_ms, first_token_ms)."""

    @abc.abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[tuple[str, Optional[float]]]:
        """Yield (delta, first_token_ms_once)."""


class OpenAILLMProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.llm_model
        self.json_mode = settings.llm_json_mode
        self.max_tokens = settings.llm_max_tokens
        # OpenAI SDK requires a non-empty api_key string even if the server ignores it
        api_key = settings.llm_api_key or "not-required"
        if api_key in ("sk-your-openai-key-here", "none", ""):
            api_key = "not-required"
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.llm_base_url.rstrip("/"),
            http_client=_build_http_client(settings.llm_verify_ssl),
        )
        self.configured = settings.llm_configured

    def _create_kwargs(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.4),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, float, Optional[float]]:
        if not self.configured:
            raise RuntimeError("LLM not configured — set LLM_BASE_URL / LLM_MODEL")

        start = time.perf_counter()
        resp = await self.client.chat.completions.create(**self._create_kwargs(messages, **kwargs))
        total_ms = (time.perf_counter() - start) * 1000
        content = resp.choices[0].message.content or "{}"
        return content, total_ms, total_ms

    async def stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[tuple[str, Optional[float]]]:
        if not self.configured:
            raise RuntimeError("LLM not configured — set LLM_BASE_URL / LLM_MODEL")

        start = time.perf_counter()
        first_token_ms: Optional[float] = None
        payload = self._create_kwargs(messages, **kwargs)
        payload["stream"] = True
        stream = await self.client.chat.completions.create(**payload)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                if first_token_ms is None:
                    first_token_ms = (time.perf_counter() - start) * 1000
                    yield delta, first_token_ms
                else:
                    yield delta, None


def get_llm_provider() -> LLMProvider:
    return OpenAILLMProvider()


def _language_instruction(detected: Optional[str]) -> str:
    if not detected:
        return ""
    mapping = {
        "english": (
            "DETECTED USER LANGUAGE: English.\n"
            'You MUST write the "response" value in clear English only. '
            "Do NOT use Urdu Arabic script. Do NOT use Roman Urdu. "
            'Set "language" to "english".'
        ),
        "urdu": (
            "DETECTED USER LANGUAGE: Urdu (Arabic script).\n"
            "CRITICAL: The entire conversational answer in the JSON field \"response\" "
            "MUST be written in Urdu Arabic/Nastaliq script (اردو).\n"
            "You may keep product names like JazzCash, Raast, LESCO in Latin, "
            "but every sentence must be Urdu script — not English, not Roman Urdu.\n"
            "Paraphrase any English knowledge into Urdu. "
            "Example response value: "
            "\"راست پاکستان کا فوری ادائیگی کا نظام ہے۔ JazzCash میں Send Money سے استعمال کریں۔\"\n"
            'Set "language" to "urdu".'
        ),
        "roman_urdu": (
            "DETECTED USER LANGUAGE: Roman Urdu.\n"
            'You MUST write the "response" value in Roman Urdu '
            '(e.g. "Bilkul, electricity bill JazzCash mein pay kar sakte hain."). '
            "Do NOT reply in English-only prose. "
            'Set "language" to "roman_urdu".'
        ),
        "mixed": (
            "DETECTED USER LANGUAGE: Mixed Urdu-English.\n"
            'Reply in the same mixed style. Set "language" to "mixed".'
        ),
    }
    return mapping.get(detected, "")


def _history_matches_language(content: str, detected_language: Optional[str]) -> bool:
    """Drop prior turns that would pull the model into the wrong script."""
    if not detected_language or not content:
        return True
    urdu_chars = len(re.findall(r"[\u0600-\u06FF]", content))
    latin_chars = len(re.findall(r"[A-Za-z]", content))
    total = urdu_chars + latin_chars
    ratio = (urdu_chars / total) if total else 0.0
    if detected_language == "urdu":
        return ratio >= 0.35 or len(content) < 40
    if detected_language == "english":
        return ratio < 0.2
    return True


def build_messages(
    user_query: str,
    history: list[dict[str, str]],
    knowledge: str,
    app_context: Optional[dict] = None,
    detected_language: Optional[str] = None,
    language_locked: bool = False,
) -> list[dict[str, str]]:
    # When UI locks language, strip noisy English context that pulls Gemma off-script
    ctx_payload = dict(app_context or {})
    if language_locked and detected_language == "urdu":
        # Keep numbers/facts; drop long English notes
        ctx_payload.pop("note", None)
        if isinstance(ctx_payload.get("ready_cash_loan"), dict):
            loan = ctx_payload["ready_cash_loan"]
            ctx_payload["ready_cash_loan"] = {
                k: loan[k]
                for k in (
                    "product",
                    "status",
                    "outstanding",
                    "installment",
                    "remaining_payments",
                    "overdue_days",
                    "late_fee",
                    "due_text",
                    "selected_plan",
                )
                if k in loan
            }
    ctx = json.dumps(ctx_payload, ensure_ascii=False)
    lang_block = _language_instruction(detected_language)
    if language_locked and detected_language == "urdu":
        lang_block += (
            "\nUI LANGUAGE LOCK (HIGHEST PRIORITY): The app toggle is URDU. "
            "Every reply turn MUST stay in Urdu Arabic script for the whole conversation, "
            "even if the user types English or Roman Urdu. Do NOT switch to English mid-chat."
        )

    # Keep knowledge short so English docs don't dominate Urdu replies
    knowledge_block = knowledge
    if detected_language == "urdu":
        # Truncate English KB — model must paraphrase, not copy
        clipped = knowledge[:900] + ("…" if len(knowledge) > 900 else "")
        knowledge_block = (
            "حقائق (انگریزی میں ہیں — جواب صرف اردو رسم الخط میں لکھیں، جملے کاپی نہ کریں):\n"
            + clipped
        )
    elif detected_language == "english":
        knowledge_block = (
            "Use the facts below and answer in English only "
            "(do not insert Urdu script):\n" + knowledge
        )

    system = (
        SYSTEM_PROMPT
        + (f"\n\n{lang_block}" if lang_block else "")
        + f"\n\nRETRIEVED KNOWLEDGE:\n{knowledge_block}\n\nAPP CONTEXT:\n{ctx}"
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]

    # When locked Urdu: keep almost no history so earlier English turns can't pull the model
    if language_locked and detected_language == "urdu":
        window = 2
    elif detected_language in ("urdu", "english"):
        window = 3
    else:
        window = 8
    hist_window = history[-window:]
    for h in hist_window:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role not in ("user", "assistant"):
            continue
        if language_locked and detected_language == "urdu":
            # Drop English assistant turns entirely; keep short user turns only
            if role == "assistant" and not _history_matches_language(content, "urdu"):
                continue
            if role == "user" and len(content) > 200:
                content = content[:200]
        elif role == "assistant" and not _history_matches_language(content, detected_language):
            continue
        messages.append({"role": role, "content": content})

    # Sticky language lock AFTER history (wins over prior mismatched assistant turns)
    if detected_language == "urdu":
        messages.append(
            {
                "role": "user",
                "content": (
                    "LANGUAGE LOCK: Reply language is URDU Arabic script for this entire chat. "
                    "Your next JSON \"response\" must be Urdu Arabic script only — "
                    "even if the user wrote in English. "
                    "Ignore any earlier English assistant messages. "
                    "The response field must be plain Urdu text — never nested JSON."
                ),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": '{"language":"urdu","intent":"faq","response":"جی بالکل، میں پوری بات چیت اردو میں ہی جاری رکھوں گا۔","suggested_action":null,"suggested_prompts":["قسط کتنی ہے؟","بل کیسے ادا کریں؟"],"blocked_transaction":false}',
            }
        )
    elif detected_language == "english":
        messages.append(
            {
                "role": "user",
                "content": (
                    "LANGUAGE LOCK: The user selected / is writing in English. "
                    "Your next JSON \"response\" must be English only — no Urdu script, no Roman Urdu. "
                    "The response field must be plain English text — never nested JSON."
                ),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": '{"language":"english","intent":"faq","response":"Sure — I can help in English.","suggested_action":null,"suggested_prompts":[],"blocked_transaction":false}',
            }
        )

    lang_reminder = ""
    if detected_language == "english":
        lang_reminder = " Reply in English only. No Urdu script."
    elif detected_language == "urdu":
        lang_reminder = (
            " اہم: \"response\" صرف اردو رسم الخط میں لکھیں۔ "
            "انگریزی جملے بالکل منع ہیں۔ Roman Urdu منع ہے۔ Nested JSON مت لکھیں۔"
        )
        if language_locked:
            lang_reminder += " UI lock فعال ہے — پوری گفتگو اردو میں رکھیں۔"
    elif detected_language == "roman_urdu":
        lang_reminder = " Jawab sirf Roman Urdu mein dein."
    elif detected_language == "mixed":
        lang_reminder = " Reply in the same mixed Urdu-English style."

    messages.append(
        {
            "role": "user",
            "content": (
                user_query
                + f"\n\nOutput exactly one JSON object now. No commentary after it.{lang_reminder}"
            ),
        }
    )
    return messages
