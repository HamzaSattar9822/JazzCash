"""JazzCash AI Assistant — FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from config import get_settings
from rag.store import knowledge_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jazzcash_ai")

ROOT = Path(__file__).resolve().parent.parent
PROTOTYPE_HTML = ROOT / "frontend" / "JazzCash_CX4_Agentic_Prototype.html"
LEGACY_PROTOTYPE_HTML = ROOT / "frontend" / "JazzCash_Agentic_Assistant_Prototype.html"
FRONTEND_DIR = ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting JazzCash AI backend (LLM configured=%s)", settings.llm_configured)
    await knowledge_store.initialize()
    yield
    logger.info("Shutting down JazzCash AI backend")


app = FastAPI(
    title="JazzCash AI Assistant",
    description="Concept Demo — No real transactions. Bilingual AI + voice for JazzCash.",
    version="1.0.0-demo",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-TTS-Latency-Ms", "X-TTS-Started", "X-First-Audio-Ms"],
)

app.include_router(router)


@app.get("/")
async def root():
    if PROTOTYPE_HTML.exists():
        return FileResponse(PROTOTYPE_HTML, media_type="text/html; charset=utf-8")
    return {
        "name": "JazzCash AI — Concept Demo",
        "docs": "/docs",
        "health": "/api/health",
        "note": "Prototype HTML missing",
    }


@app.get("/prototype")
async def prototype():
    return FileResponse(PROTOTYPE_HTML, media_type="text/html; charset=utf-8")


@app.get("/prototype/legacy")
async def prototype_legacy():
    target = LEGACY_PROTOTYPE_HTML if LEGACY_PROTOTYPE_HTML.exists() else PROTOTYPE_HTML
    return FileResponse(target, media_type="text/html; charset=utf-8")


if FRONTEND_DIR.exists():
    app.mount("/assets-static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")
