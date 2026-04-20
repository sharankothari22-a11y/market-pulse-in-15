"""
collectors/free/reddit_news.py
────────────────────────────────
Reddit financial subreddits — public JSON, no API key needed.
Subreddits: r/IndiaInvestments, r/DalalStreetTalks, r/stocks, r/investing
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

SUBREDDITS = [
    "IndiaInvestments",
    "DalalStreetTalks",
    "IndianStockMarket",
    "stocks",
    "investing",
]
HEADERS = {"User-Agent": "research_platform:v1.0 (financial research tool)"}

class RedditNewsCollector(BaseCollector):
    source_name = "reddit_news"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()
        for sub in SUBREDDITS:
            try:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code == 429:
                    logger.warning(f"[reddit] rate-limited on r/{sub}")
                    continue
                resp.raise_for_status()
                data = resp.json()
                posts = data.get("data", {}).get("children", [])
                for post in posts:
                    pd_data = post.get("data", {})
                    title   = pd_data.get("title", "").strip()
                    url_    = f"https://reddit.com{pd_data.get('permalink', '')}"
                    score   = pd_data.get("score", 0)
                    created = pd_data.get("created_utc")
                    if created:
                        post_date = datetime.fromtimestamp(created, tz=timezone.utc).date()
                    else:
                        post_date = today
                    if title and score > 10:
                        impact = min(score / 1000, 0.5)
                        records.append(Event(
                            type="regulatory",
                            title=f"[r/{sub}] {title}"[:1000],
                            date=post_date,
                            source_url=url_,
                            entity_type="reddit",
                            impact_score=impact,
                        ))
            except Exception as e:
                logger.debug(f"[reddit] r/{sub} failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)
        logger.info(f"[reddit] {len(records)} posts stored from {len(SUBREDDITS)} subreddits")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
