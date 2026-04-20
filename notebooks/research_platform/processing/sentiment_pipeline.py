"""
processing/sentiment_pipeline.py
──────────────────────────────────
Sentiment scoring pipeline.
Scores news articles, events, and transcripts using a hybrid approach:
  1. Rule-based (keyword sentiment) — fast, free, deterministic
  2. LLM-based (Claude API) — slower, accurate, cached

Writes scores to NewsSentiment table and updates NewsArticle.sentiment_score.
"""
from __future__ import annotations

import re
from typing import Optional

from loguru import logger

# ── Keyword sentiment lists ───────────────────────────────────────────────────

POSITIVE_KEYWORDS = {
    "strong": 0.6, "beat": 0.7, "upgrade": 0.6, "buy": 0.5, "growth": 0.4,
    "record": 0.5, "profit": 0.4, "expansion": 0.5, "approved": 0.6,
    "win": 0.5, "contract": 0.4, "dividend": 0.4, "acquisition": 0.3,
    "outperform": 0.6, "raised guidance": 0.8, "above estimate": 0.7,
    "new high": 0.6, "inflow": 0.4, "order book": 0.5, "recovery": 0.4,
    "positive outlook": 0.7, "stable": 0.3, "upgrade rating": 0.7,
}
NEGATIVE_KEYWORDS = {
    "miss": -0.7, "downgrade": -0.6, "sell": -0.5, "loss": -0.6,
    "penalty": -0.7, "warning": -0.5, "decline": -0.4, "concern": -0.3,
    "weak": -0.5, "below estimate": -0.7, "outflow": -0.4, "fraud": -0.9,
    "sebi notice": -0.7, "rbi notice": -0.7, "npa": -0.6, "default": -0.8,
    "negative outlook": -0.7, "watch negative": -0.7, "cut guidance": -0.8,
    "profit warning": -0.8, "suspend": -0.7, "delist": -0.8, "ban": -0.7,
    "recall": -0.6, "oai": -0.8, "import alert": -0.8,
}


def score_text_keywords(text: str) -> float:
    """
    Fast keyword-based sentiment score.
    Returns: -1.0 (very negative) to +1.0 (very positive)
    """
    if not text:
        return 0.0

    text_lower = text.lower()
    score = 0.0
    hits  = 0

    for kw, weight in POSITIVE_KEYWORDS.items():
        if kw in text_lower:
            score += weight
            hits  += 1

    for kw, weight in NEGATIVE_KEYWORDS.items():
        if kw in text_lower:
            score += weight  # weight is negative
            hits  += 1

    if hits == 0:
        return 0.0

    # Normalise to -1..+1
    return max(-1.0, min(1.0, score / max(hits, 1)))


def score_text_llm(text: str, ticker: Optional[str] = None) -> Optional[float]:
    """
    LLM-based sentiment scoring using Claude API.
    Returns: -1.0 to +1.0 or None if API unavailable.
    Cached — identical text gets the same score without API call.
    """
    import os, hashlib, json
    from pathlib import Path

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    cache_dir = Path(os.getenv("CACHE_DIR", "/tmp/research_platform_cache")) / "sentiment"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(text[:500].encode()).hexdigest()[:16]
    cache_file = cache_dir / f"{cache_key}.json"

    if cache_file.exists():
        return json.loads(cache_file.read_text()).get("score")

    try:
        import requests as req
        prompt = (
            f"Rate the financial sentiment of this text for {'stock ' + ticker if ticker else 'the market'}.\n"
            f"Return ONLY a number between -1.0 (very negative) and +1.0 (very positive).\n"
            f"0.0 = neutral. No explanation.\n\nText: {text[:500]}"
        )
        resp = req.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 10,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=15,
        )
        resp.raise_for_status()
        score_str = resp.json()["content"][0]["text"].strip()
        score = float(re.findall(r"-?\d+\.?\d*", score_str)[0])
        score = max(-1.0, min(1.0, score))
        cache_file.write_text(json.dumps({"score": score}))
        return score
    except Exception as e:
        logger.debug(f"[sentiment] LLM scoring failed: {e}")
        return None


def score(text: str, ticker: Optional[str] = None,
          use_llm: bool = True) -> dict:
    """
    Score sentiment of a text. Returns dict with score, method, label.
    """
    # Always run keyword scoring (fast, free)
    kw_score = score_text_keywords(text)

    # Try LLM if requested and available
    final_score = kw_score
    method = "keyword"
    if use_llm:
        llm_score = score_text_llm(text, ticker=ticker)
        if llm_score is not None:
            # Blend: 60% LLM, 40% keyword
            final_score = llm_score * 0.6 + kw_score * 0.4
            method = "llm+keyword"

    label = "positive" if final_score > 0.1 else "negative" if final_score < -0.1 else "neutral"
    return {
        "score":    round(final_score, 3),
        "label":    label,
        "method":   method,
        "kw_score": round(kw_score, 3),
    }


def score_and_store(article_id: int, text: str, entity_id: Optional[int] = None,
                    entity_type: str = "company", ticker: Optional[str] = None) -> None:
    """Score a news article and store the result in news_sentiment table."""
    from database.connection import get_session
    from database.models import NewsSentiment, NewsArticle
    from sqlalchemy import select, update

    result = score(text, ticker=ticker)
    try:
        with get_session() as session:
            # Write to news_sentiment
            ns = NewsSentiment(
                article_id=article_id,
                entity_id=entity_id,
                entity_type=entity_type,
                sentiment=result["label"],
                score=result["score"],
                source=result["method"],
            )
            session.add(ns)
            # Update sentiment_score on NewsArticle
            session.execute(
                update(NewsArticle)
                .where(NewsArticle.id == article_id)
                .values(sentiment_score=result["score"])
            )
    except Exception as e:
        logger.warning(f"[sentiment] Store failed for article {article_id}: {e}")


def batch_score_unscored_articles(limit: int = 100) -> int:
    """Score all NewsArticle rows that don't have a sentiment score yet."""
    from database.connection import get_session
    from database.models import NewsArticle
    from sqlalchemy import select

    scored = 0
    try:
        with get_session() as session:
            rows = session.scalars(
                select(NewsArticle)
                .where(NewsArticle.sentiment_score.is_(None), NewsArticle.body.isnot(None))
                .limit(limit)
            ).all()
            article_ids = [r.id for r in rows]
            texts       = [r.body or r.title for r in rows]

        for aid, text in zip(article_ids, texts):
            score_and_store(aid, text)
            scored += 1

    except Exception as e:
        logger.error(f"[sentiment] Batch scoring failed: {e}")

    logger.info(f"[sentiment] Scored {scored} articles")
    return scored
