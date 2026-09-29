"""Rule-based intent detection (LLM may refine)."""

from __future__ import annotations

import re
import time

from models.schemas import Intent

# Explicit "do it for me" execution asks — not how-to / discovery
EXECUTION_PATTERNS = [
    r"\b(bhej\s*do|bhej\s*den|send\s+kar\s+do|transfer\s+kar\s+do|pay\s+kar\s+do)\b",
    r"\b(send|transfer|pay)\s+(\d[\d,]*)\s*(rupees|rs\.?|pkr|rupay)?\s+(to|ko)\b",
    r"\b\w+\s+ko\s+\d[\d,]*\s*(rupees|rs\.?|pkr|rupay)?\s*(bhej|send|transfer)",
    r"\b(please\s+)?(send|transfer)\s+\d[\d,]*\s*(rupees|rs\.?|pkr)?\s+to\s+\w+",
]

HOWTO_MARKERS = (
    "how do i",
    "how to",
    "kaise",
    "kis tarah",
    "where",
    "kahan",
    "kya hai",
    "what is",
    "explain",
    "options",
    "guide",
)

INTENT_RULES: list[tuple[Intent, list[str]]] = [
    (Intent.GREETING, ["hello", "hi", "salam", "assalam", "hey", "aoa", "good morning"]),
    (Intent.OFFERS, ["offer", "cashback", "reward", "promo", "discount", "deal"]),
    (Intent.FEES, ["fee", "charge", "charges", "kitni fee", "cost of", "pricing"]),
    (
        Intent.TROUBLESHOOTING,
        ["fail", "failed", "error", "problem", "issue", "nahi hui", "kyun hui", "stuck"],
    ),
    (
        Intent.TRANSACTION_EXPLANATION,
        ["pending", "transaction status", "txn", "matlab", "what does pending"],
    ),
    (Intent.SUPPORT, ["complaint", "support", "helpline", "help desk", "register complaint"]),
    (
        Intent.PRODUCT_DISCOVERY,
        [
            "saving",
            "savings",
            "loan",
            "ready cash",
            "qarz",
            "installment",
            "repay",
            "repayment",
            "late fee",
            "payment plan",
            "insurance",
            "product",
            "invest",
            "قرضہ",
            "قسط",
        ],
    ),
    (Intent.HOW_TO, ["how do i", "how to", "kaise", "kis tarah", "steps"]),
    (
        Intent.APP_NAVIGATION,
        ["kahan", "where", "open", "navigate", "section", "find my", "history kahan"],
    ),
    (
        Intent.SERVICE_DISCOVERY,
        [
            "bill",
            "electricity",
            "passport",
            "recharge",
            "raast",
            "m-tag",
            "mtag",
            "qr",
            "service",
            "pay karna",
            "fee pay",
        ],
    ),
    (Intent.FAQ, ["what is", "kya hai", "explain", "matlab kya"]),
]


def detect_intent(text: str) -> tuple[Intent, float]:
    start = time.perf_counter()
    lower = text.lower().strip()

    is_howto = any(m in lower for m in HOWTO_MARKERS)

    if not is_howto:
        for pattern in EXECUTION_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                return Intent.TRANSACTION_EXECUTION_REQUEST, (time.perf_counter() - start) * 1000

        # Amount + person + imperative send verbs (not "pay karna hai" discovery)
        if re.search(r"\b\d{3,}\b", lower) and any(
            v in lower for v in ("bhej do", "send kar do", "transfer kar do", "send to", "bhej den")
        ):
            return Intent.TRANSACTION_EXECUTION_REQUEST, (time.perf_counter() - start) * 1000

    scores: dict[Intent, int] = {}
    for intent, keywords in INTENT_RULES:
        score = sum(1 for kw in keywords if kw in lower)
        if score:
            scores[intent] = score

    if not scores:
        return Intent.UNKNOWN, (time.perf_counter() - start) * 1000

    best = max(scores.items(), key=lambda x: x[1])[0]
    return best, (time.perf_counter() - start) * 1000


TRANSACTION_REFUSAL = {
    "english": (
        "I can guide you through the transfer process, but in this demo I cannot execute "
        "real transactions. Open Send Money to continue yourself — your funds stay safe."
    ),
    "roman_urdu": (
        "Main aapko transfer process mein guide kar sakta hoon, lekin is demo mein real "
        "transactions execute nahi ki ja sakti. Send Money section khol kar aap khud complete kar sakte hain."
    ),
    "urdu": (
        "میں آپ کو ٹرانسفر کے عمل میں رہنمائی دے سکتا ہوں، لیکن اس ڈیمو میں حقیقی لین دین "
        "انجام نہیں دیا جا سکتا۔ Send Money سیکشن کھولیں۔"
    ),
    "mixed": (
        "Main aapko transfer process mein guide kar sakta hoon, lekin is demo mein real "
        "transactions execute nahi ki ja sakti. Send Money khol kar continue karein."
    ),
}
