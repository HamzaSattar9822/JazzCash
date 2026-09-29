"""Additional conversational safety & pipeline cases."""

from __future__ import annotations

import pytest

from agents.intent import TRANSACTION_REFUSAL, detect_intent
from agents.pipeline import run_agent
from models.schemas import Intent


@pytest.mark.asyncio
async def test_execution_refusal_without_llm():
    res = await run_agent("Ali ko 5000 rupees send kar do.")
    assert res.blocked_transaction is True
    assert res.intent == Intent.TRANSACTION_EXECUTION_REQUEST
    assert res.suggested_action and res.suggested_action.route == "/send-money"
    assert "demo" in res.response.lower() or "execute" in res.response.lower() or "لین دین" in res.response


def test_refusal_copy_exists_all_langs():
    for key in ("english", "roman_urdu", "urdu", "mixed"):
        assert key in TRANSACTION_REFUSAL
        assert len(TRANSACTION_REFUSAL[key]) > 20


def test_intent_passport():
    intent, _ = detect_intent("Mujhe passport fee pay karni hai.")
    assert intent in (Intent.SERVICE_DISCOVERY, Intent.HOW_TO, Intent.APP_NAVIGATION)


def test_intent_how_to_bank():
    intent, _ = detect_intent("How do I send money to a bank account?")
    assert intent in (Intent.HOW_TO, Intent.SERVICE_DISCOVERY, Intent.APP_NAVIGATION)
