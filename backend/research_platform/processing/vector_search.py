"""
processing/vector_search.py
────────────────────────────
pgvector semantic search queries.
Embeds text using sentence-transformers (free, local) or OpenAI (paid).
Stores embeddings in NewsArticle.embedding (JSONB until pgvector migration).
Enables: "find all news about RELIANCE GRM" semantic queries.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from loguru import logger

# ── Embedding generation ──────────────────────────────────────────────────────

def embed_text(text: str, model: str = "local") -> Optional[list[float]]:
    """
    Generate a text embedding vector.
    model: "local" (sentence-transformers, free) | "openai" (paid)
    Returns list of floats or None if unavailable.
    """
    if model == "local":
        return _embed_local(text)
    if model == "openai":
        return _embed_openai(text)
    return None


def _embed_local(text: str) -> Optional[list[float]]:
    """sentence-transformers — free, runs locally, no API key."""
    try:
        from sentence_transformers import SentenceTransformer
        # Cache model in memory
        if not hasattr(_embed_local, "_model"):
            logger.info("[vector_search] Loading sentence-transformers model (first run only)...")
            _embed_local._model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = _embed_local._model.encode(text[:512], convert_to_list=True)
        return embedding
    except ImportError:
        logger.debug("[vector_search] sentence-transformers not installed — pip install sentence-transformers")
        return None
    except Exception as e:
        logger.warning(f"[vector_search] Local embedding failed: {e}")
        return None


def _embed_openai(text: str) -> Optional[list[float]]:
    """OpenAI text-embedding-3-small — paid, 1536 dimensions."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        import requests
        resp = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": text[:8000]},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"[vector_search] OpenAI embedding failed: {e}")
        return None


# ── Store embeddings ──────────────────────────────────────────────────────────

def embed_and_store_article(article_id: int, text: str) -> bool:
    """Generate embedding for a news article and store in NewsArticle.embedding."""
    embedding = embed_text(text)
    if not embedding:
        return False
    try:
        from database.connection import get_session
        from database.models import NewsArticle
        from sqlalchemy import update
        with get_session() as session:
            session.execute(
                update(NewsArticle)
                .where(NewsArticle.id == article_id)
                .values(embedding=embedding)
            )
        return True
    except Exception as e:
        logger.warning(f"[vector_search] Store failed for article {article_id}: {e}")
        return False


def batch_embed_unembedded(limit: int = 50) -> int:
    """Embed all NewsArticle rows that don't have embeddings yet."""
    from database.connection import get_session
    from database.models import NewsArticle
    from sqlalchemy import select
    embedded = 0
    try:
        with get_session() as session:
            rows = session.scalars(
                select(NewsArticle)
                .where(NewsArticle.embedding.is_(None),
                       NewsArticle.body.isnot(None))
                .limit(limit)
            ).all()
            ids_texts = [(r.id, r.body or r.title) for r in rows]
        for aid, text in ids_texts:
            if embed_and_store_article(aid, text):
                embedded += 1
    except Exception as e:
        logger.error(f"[vector_search] Batch embed failed: {e}")
    logger.info(f"[vector_search] Embedded {embedded} articles")
    return embedded


# ── Semantic search ───────────────────────────────────────────────────────────

def semantic_search(query: str, limit: int = 10,
                    entity_type: Optional[str] = None) -> list[dict]:
    """
    Find news articles semantically similar to the query.
    Uses cosine similarity on stored embeddings.
    Falls back to keyword search if embeddings unavailable.
    """
    query_embedding = embed_text(query)
    if query_embedding is None:
        logger.info("[vector_search] No embedding available — falling back to keyword search")
        return _keyword_fallback(query, limit, entity_type)

    from database.connection import get_session
    from database.models import NewsArticle
    from sqlalchemy import select
    import math

    try:
        with get_session() as session:
            stmt = select(NewsArticle).where(NewsArticle.embedding.isnot(None))
            if entity_type:
                stmt = stmt.where(NewsArticle.source == entity_type)
            rows = session.scalars(stmt.limit(1000)).all()
            articles = [(r.id, r.title, r.body, r.embedding, r.source_url) for r in rows]

        results = []
        for aid, title, body, emb_json, url in articles:
            if not emb_json:
                continue
            try:
                stored = emb_json if isinstance(emb_json, list) else json.loads(emb_json)
                sim = _cosine_similarity(query_embedding, stored)
                results.append({
                    "id": aid, "title": title, "url": url,
                    "similarity": round(sim, 4),
                    "snippet": (body or "")[:200],
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    except Exception as e:
        logger.warning(f"[vector_search] Search failed: {e}")
        return _keyword_fallback(query, limit, entity_type)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    import math
    if len(a) != len(b):
        return 0.0
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _keyword_fallback(query: str, limit: int, entity_type: Optional[str]) -> list[dict]:
    """Keyword-based search fallback when embeddings unavailable."""
    from database.connection import get_session
    from database.models import NewsArticle
    from sqlalchemy import select, or_
    words = query.lower().split()[:5]
    try:
        with get_session() as session:
            stmt = select(NewsArticle)
            conditions = [NewsArticle.title.ilike(f"%{w}%") for w in words]
            stmt = stmt.where(or_(*conditions)).limit(limit)
            rows = session.scalars(stmt).all()
        return [{"id": r.id, "title": r.title, "url": r.source_url,
                 "similarity": 0.0, "snippet": (r.body or "")[:200]} for r in rows]
    except Exception:
        return []
