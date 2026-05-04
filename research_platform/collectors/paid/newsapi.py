"""
collectors/paid/newsapi.py
───────────────────────────
NewsAPI financial news aggregator.
Requires NEWSAPI_KEY. Disabled by default.
Stores headline events into the event table.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import NEWSAPI_KEY
from database.connection import get_session
from database.models import Event

NEWSAPI_URL = "https://newsapi.org/v2/everything"
TIMEOUT: int = 15
QUERIES = ["NIFTY", "NSE India", "BSE Sensex", "RBI", "SEBI"]


class NewsApiCollector(BaseCollector):
    source_name: str = "newsapi"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not NEWSAPI_KEY:
            logger.warning(f"[{self.source_name}] NEWSAPI_KEY not set. Skipping.")
            return None

        all_events: list[Event] = []

        for query in QUERIES:
            params = {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": NEWSAPI_KEY,
            }
            if target_date:
                params["from"] = target_date.isoformat()
                params["to"] = target_date.isoformat()

            try:
                resp = requests.get(NEWSAPI_URL, params=params, timeout=TIMEOUT)
                resp.raise_for_status()
                articles = resp.json().get("articles", [])
                for art in articles:
                    all_events.append(
                        Event(
                            type="regulatory",
                            title=(art.get("title") or "")[:1000],
                            source_url=(art.get("url") or "")[:500] or None,
                            entity_type="news",
                        )
                    )
            except Exception as exc:
                logger.warning(f"[{self.source_name}] NewsAPI query '{query}' failed: {exc}")

        if not all_events:
            return None

        with get_session() as session:
            for ev in all_events:
                session.add(ev)

        self._store_cache(all_events, target_date=target_date)
        return CollectionResult(
            source_name=self.source_name,
            records=all_events,
            status="ok",
        )
