#!/usr/bin/env bash
# Quick start helper — run from repo root.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$ROOT/backend/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/backend/.env"
  echo "Created backend/.env — add your LLM_API_KEY before using chat/voice."
fi

echo "Start backend:  cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000"
echo "Start frontend: cd frontend && npm run dev"
echo "Then open http://127.0.0.1:5173"
