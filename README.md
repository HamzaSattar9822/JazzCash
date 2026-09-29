# JazzCash AI Assistant — Concept Demo

Bilingual (English / Urdu / Roman Urdu) mobile AI assistant for the JazzCash ecosystem with real LLM, RAG, STT, and TTS. **No real financial transactions.**

> JazzCash AI — Concept Demo · Understand → Retrieve → Explain → Guide → Navigate

---

## Architecture

```
┌─────────────────────────────┐
│  React (Vite) Mobile UI     │  390×844 phone frame on desktop
│  Chat · Voice · Mock screens│
└──────────────┬──────────────┘
               │ HTTP / multipart / SSE
┌──────────────▼──────────────┐
│  FastAPI Backend            │
│  Language → Intent → RAG    │
│  → LLM Agent → Structured   │
│  Voice: STT → Agent → TTS   │
└───┬──────────┬──────────┬───┘
    │          │          │
 OpenAI*    Embeddings  Whisper/TTS
 (LLM)      (RAG)       (or Deepgram / ElevenLabs)
```

\* Providers are abstracted (`LLMProvider`, `STTProvider`, `TTSProvider`) so they can be swapped without rewriting the agent.

**RAG:** curated JazzCash knowledge docs + OpenAI embeddings (hybrid keyword/vector). Replaceable with pgvector / Qdrant / official docs later.

**Safety:** `TRANSACTION_EXECUTION_REQUEST` intent is blocked — the agent never pretends money moved.

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (20+ recommended)
- An [OpenAI API key](https://platform.openai.com/) (LLM + embeddings + Whisper STT + TTS)

Optional: Deepgram (STT), ElevenLabs (TTS)

---

## LLM configuration (Jazz Gemma)

This prototype is wired to Jazz AIOps Gemma by default:

```
LLM_BASE_URL=https://gemma-3-12b-dpo-apr-merged-aws-teknosys-ai.apps.aiops.jazz.com.pk/v1
LLM_MODEL=gemma-3-12b-dpo-apr-merged-aws
LLM_API_KEY=not-required
LLM_VERIFY_SSL=false
```

Chat goes to `/v1/chat/completions` on that host. STT/TTS stay on a separate OpenAI endpoint (`OPENAI_API_KEY`) if you enable voice.
---

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Health check: http://127.0.0.1:8000/api/health  
API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the app renders in a centered **390×844** phone frame.

Vite proxies `/api` → `http://127.0.0.1:8000`.

---

## Voice permissions

1. Use Chrome/Safari on localhost (or HTTPS).
2. Allow microphone when prompted.
3. Voice flow: **Mic → Whisper STT → Agent/LLM → OpenAI TTS → Speaker**.
4. While the AI is speaking, tap **Interrupt** / **Stop AI** (barge-in).

If STT/TTS fails, check `/api/health` (`stt` / `tts` flags) and your API key billing/quota.

---

## Developer mode

Tap the small **◎** control (top-right inside the phone) to toggle developer mode.

Shows: language, intent, retrieved docs, STT / LLM / TTS / first-audio latency.

---

## Demo scenarios (pitch)

| # | Say / type | Expect |
|---|------------|--------|
| 1 | "Mujhe electricity bill pay karna hai." | Guide + **Open Bill Payment** → `/bills` |
| 2 | "JazzCash mein savings ke kya options hain?" | Explains demo savings |
| 3 | "Meri payment fail kyun hui?" | Troubleshooting (demo failed SSGC txn) |
| 4 | "Where can I find my transaction history?" | Navigate → `/transactions` |
| 5 | "Raast kya hai?" | FAQ explanation |
| 6 | "Any cashback offers?" | Mock offers |
| 7 | "Ali ko 5000 rupees send kar do." | **Refuses execution**, offers Send Money guidance |

Demo user: **Fahem** · mock wallet · labeled *Concept Demo — No real transactions*.

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Coverage includes language detection, intents (incl. transaction safety), RAG retrieval, and mock API endpoints (20+ cases).

---

## Latency notes

Targets (not guarantees):

- UI feedback &lt; 100 ms (local state)
- First meaningful audio often ~0.5–2 s depending on network/provider

Dev mode shows measured STT, LLM first token, TTS, and perceived first-audio times. Optimize by: smaller models, streaming TTS, regional endpoints, and shorter replies for voice.

---

## Project structure

```
backend/
  api/          REST routes
  agents/       language, intent, pipeline
  llm/ stt/ tts/ provider interfaces
  rag/          hybrid retrieval
  knowledge/    curated JazzCash docs
  mock_data/    Fahem, txns, offers, fees
  tests/
frontend/
  src/pages/    Home, AI chat, Voice, mock JazzCash screens
  src/hooks/    chat + voice pipeline
  src/lib/      API client (no secrets)
```

---

## Production migration

| Prototype | Production path |
|-----------|-----------------|
| `mock_data/` | JazzCash account/transaction APIs |
| In-app routes (`/bills`, …) | Official deep links / native navigation |
| `knowledge/documents.py` | Official docs + pgvector/Qdrant |
| Demo session IDs | Production auth + session store (Redis) |
| OpenAI STT/TTS | Enterprise voice stack / on-prem as required |
| No transaction execution | Keep refusal layer; wire guided handoff only |

The agent contract (`language`, `intent`, `response`, `suggested_action.route`) is designed to stay stable across those swaps.

---

## License / disclaimer

Unofficial **concept prototype** for demonstration. Not affiliated with or endorsed as the production JazzCash application. Do not use with real customer funds or production credentials.
