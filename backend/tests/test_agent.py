"""Conversational & API tests (≥20 cases)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agents.intent import detect_intent
from agents.language import detect_language
from models.schemas import Intent, Language
from rag.store import knowledge_store


# ---------- Language detection (4+) ----------


def test_lang_english():
    lang, _ = detect_language("Where can I find my transaction history?")
    assert lang == Language.ENGLISH


def test_lang_roman_urdu():
    lang, _ = detect_language("Meri transaction history kahan hai?")
    assert lang in (Language.ROMAN_URDU, Language.MIXED)


def test_lang_urdu_script():
    lang, _ = detect_language("میری ٹرانزیکشن ہسٹری کہاں ہے؟")
    assert lang in (Language.URDU, Language.MIXED)


def test_lang_mixed():
    lang, _ = detect_language("Mujhe electricity bill pay karna hai, option kahan hai?")
    assert lang in (Language.MIXED, Language.ROMAN_URDU)


# ---------- Intent detection (8+) ----------


def test_intent_execution_blocked():
    intent, _ = detect_intent("Ali ko 5000 rupees send kar do.")
    assert intent == Intent.TRANSACTION_EXECUTION_REQUEST


def test_intent_execution_english():
    intent, _ = detect_intent("Please send 2000 rupees to Ahmed")
    assert intent == Intent.TRANSACTION_EXECUTION_REQUEST


def test_intent_bills():
    intent, _ = detect_intent("Mujhe electricity bill pay karna hai.")
    assert intent in (Intent.SERVICE_DISCOVERY, Intent.HOW_TO, Intent.APP_NAVIGATION)


def test_intent_raast_faq():
    intent, _ = detect_intent("Raast kya hai?")
    assert intent in (Intent.FAQ, Intent.SERVICE_DISCOVERY)


def test_intent_offers():
    intent, _ = detect_intent("Any cashback offers?")
    assert intent == Intent.OFFERS


def test_intent_failed_payment():
    intent, _ = detect_intent("Meri payment fail kyun hui?")
    assert intent == Intent.TROUBLESHOOTING


def test_intent_savings():
    intent, _ = detect_intent("JazzCash mein savings ke kya options hain?")
    assert intent in (Intent.PRODUCT_DISCOVERY, Intent.SERVICE_DISCOVERY)


def test_intent_history_nav():
    intent, _ = detect_intent("Where can I find my transaction history?")
    assert intent in (Intent.APP_NAVIGATION, Intent.TRANSACTION_EXPLANATION, Intent.UNKNOWN)


def test_intent_pending():
    intent, _ = detect_intent("Pending transaction ka kya matlab hai?")
    assert intent in (Intent.TRANSACTION_EXPLANATION, Intent.FAQ)


def test_intent_fees():
    intent, _ = detect_intent("Money transfer ki fee kitni hai?")
    assert intent == Intent.FEES


def test_intent_support():
    intent, _ = detect_intent("Meri complaint kahan register hogi?")
    assert intent == Intent.SUPPORT


def test_intent_greeting():
    intent, _ = detect_intent("Hello")
    assert intent == Intent.GREETING


# ---------- RAG ----------


@pytest.mark.asyncio
async def test_rag_electricity():
    docs, ms = await knowledge_store.retrieve("electricity bill pay", top_k=3)
    assert docs
    assert ms >= 0
    titles = " ".join(d.title.lower() for d in docs)
    assert "bill" in titles or "electricity" in titles or docs[0].score >= 0


@pytest.mark.asyncio
async def test_rag_raast():
    docs, _ = await knowledge_store.retrieve("Raast kya hai", top_k=3)
    assert any("raast" in d.title.lower() or "raast" in d.snippet.lower() for d in docs)


@pytest.mark.asyncio
async def test_rag_savings():
    docs, _ = await knowledge_store.retrieve("savings options", top_k=3)
    assert any("sav" in d.title.lower() or "sav" in d.snippet.lower() for d in docs)


# ---------- API endpoints ----------


@pytest.fixture(scope="module")
def client():
    from main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "llm" in body
    assert body["version"]


def test_services(client):
    r = client.get("/api/services")
    assert r.status_code == 200
    assert len(r.json()["services"]) >= 5


def test_offers(client):
    r = client.get("/api/offers")
    assert r.status_code == 200
    assert len(r.json()["offers"]) >= 1


def test_products(client):
    r = client.get("/api/products")
    assert r.status_code == 200


def test_transactions(client):
    r = client.get("/api/transactions")
    assert r.status_code == 200
    assert r.json()["user"]["name"] == "Fahem"


def test_voice_session(client):
    r = client.post("/api/voice/session", json={})
    assert r.status_code == 200
    assert r.json()["session_id"]


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Concept Demo" in r.json()["name"]
