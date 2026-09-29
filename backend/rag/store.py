"""RAG retrieval layer with embedding + keyword hybrid search."""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

import numpy as np
from openai import AsyncOpenAI

from config import get_settings
from knowledge.documents import KNOWLEDGE_DOCUMENTS
from models.schemas import RetrievedDocument

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """In-memory vector + keyword store. Replaceable with pgvector/Qdrant later."""

    def __init__(self) -> None:
        self.documents = KNOWLEDGE_DOCUMENTS
        self._embeddings: Optional[np.ndarray] = None
        self._ready = False
        self._client: Optional[AsyncOpenAI] = None

    async def initialize(self) -> None:
        settings = get_settings()
        if settings.embedding_enabled and settings.effective_embedding_key:
            self._client = AsyncOpenAI(
                api_key=settings.effective_embedding_key,
                base_url=settings.openai_base_url.rstrip("/"),
            )
            try:
                await self._build_embeddings()
                self._ready = True
                logger.info("RAG embeddings built for %d documents", len(self.documents))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Embedding build failed, keyword-only RAG: %s", exc)
                self._ready = False
        else:
            logger.info("Embeddings disabled — using keyword-only RAG (Jazz Gemma chat LLM)")
            self._ready = False

    async def _build_embeddings(self) -> None:
        assert self._client is not None
        settings = get_settings()
        texts = [
            f"{d['title']}. {d['content']} Keywords: {', '.join(d.get('keywords', []))}"
            for d in self.documents
        ]
        # Batch embed
        resp = await self._client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        vectors = [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
        self._embeddings = np.array(vectors, dtype=np.float32)
        # Normalize for cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-9
        self._embeddings = self._embeddings / norms

    def _keyword_scores(self, query: str) -> np.ndarray:
        q = query.lower()
        tokens = set(re.findall(r"[\w\u0600-\u06FF]+", q))
        scores = np.zeros(len(self.documents), dtype=np.float32)
        for i, doc in enumerate(self.documents):
            hay = " ".join(
                [
                    doc["title"].lower(),
                    doc["content"].lower(),
                    " ".join(doc.get("keywords", [])).lower(),
                    doc.get("category", "").lower(),
                ]
            )
            hits = sum(1 for t in tokens if t in hay and len(t) > 2)
            # Bonus for phrase matches
            for kw in doc.get("keywords", []):
                if kw.lower() in q:
                    hits += 2
            scores[i] = float(hits)
        if scores.max() > 0:
            scores = scores / (scores.max() + 1e-9)
        return scores

    async def retrieve(self, query: str, top_k: int = 4) -> tuple[list[RetrievedDocument], float]:
        start = time.perf_counter()
        keyword = self._keyword_scores(query)
        vector_scores = np.zeros(len(self.documents), dtype=np.float32)

        if self._ready and self._client is not None and self._embeddings is not None:
            try:
                settings = get_settings()
                resp = await self._client.embeddings.create(
                    model=settings.embedding_model,
                    input=[query],
                )
                qvec = np.array(resp.data[0].embedding, dtype=np.float32)
                qvec = qvec / (np.linalg.norm(qvec) + 1e-9)
                vector_scores = self._embeddings @ qvec
            except Exception as exc:  # noqa: BLE001
                logger.warning("Query embedding failed: %s", exc)

        # Hybrid: 0.65 vector + 0.35 keyword
        if vector_scores.max() > 0:
            combined = 0.65 * vector_scores + 0.35 * keyword
        else:
            combined = keyword

        top_idx = np.argsort(-combined)[:top_k]
        results: list[RetrievedDocument] = []
        for idx in top_idx:
            score = float(combined[idx])
            if score <= 0 and vector_scores.max() <= 0:
                continue
            doc = self.documents[int(idx)]
            results.append(
                RetrievedDocument(
                    id=doc["id"],
                    title=doc["title"],
                    category=doc["category"],
                    score=round(score, 4),
                    snippet=doc["content"][:220] + ("..." if len(doc["content"]) > 220 else ""),
                )
            )

        # Always return at least something useful for common intents
        if not results:
            results = [
                RetrievedDocument(
                    id=self.documents[0]["id"],
                    title=self.documents[0]["title"],
                    category=self.documents[0]["category"],
                    score=0.0,
                    snippet=self.documents[0]["content"][:220],
                )
            ]

        elapsed = (time.perf_counter() - start) * 1000
        return results, elapsed

    def get_full_content(self, doc_ids: list[str]) -> str:
        by_id = {d["id"]: d for d in self.documents}
        parts = []
        for did in doc_ids:
            d = by_id.get(did)
            if d:
                parts.append(
                    f"### {d['title']} (route: {d.get('route', 'n/a')})\n{d['content']}"
                )
        return "\n\n".join(parts)


# Singleton
knowledge_store = KnowledgeStore()
