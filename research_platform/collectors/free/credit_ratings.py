"""
collectors/free/credit_ratings.py
───────────────────────────────────
Credit rating actions from CRISIL, ICRA, CARE, India Ratings.
Source: RSS feeds from each agency
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import email.utils
import feedparser
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

RATING_FEEDS = [
    ("CRISIL",         "https://www.crisil.com/content/dam/crisil/rss/ratings-news.xml"),
    ("ICRA",           "https://www.icra.in/RSS/Ratings/RatingsRSS"),
    ("CARE Ratings",   "https://www.careratings.com/rss/rating-actions-rss.xml"),
    ("India Ratings",  "https://www.indiaratings.co.in/rss/news.rss"),
]
DOWNGRADE_WORDS = ["downgrade", "watch negative", "review negative", "negative outlook", "default"]
UPGRADE_WORDS   = ["upgrade", "positive outlook", "watch positive", "stable"]

class CreditRatingsCollector(BaseCollector):
    source_name = "credit_ratings"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        for agency, feed_url in RATING_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    if not title:
                        continue
                    pub = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = date.today()
                    tl = title.lower()
                    is_downgrade = any(w in tl for w in DOWNGRADE_WORDS)
                    is_upgrade   = any(w in tl for w in UPGRADE_WORDS)
                    impact = 0.9 if is_downgrade else 0.6 if is_upgrade else 0.4
                    records.append(Event(
                        type="regulatory",
                        title=f"[{agency}] {title}"[:1000],
                        date=ed, source_url=link,
                        entity_type="credit_rating",
                        impact_score=impact,
                    ))
            except Exception as e:
                logger.debug(f"[credit_ratings] {agency} RSS failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)
        logger.info(f"[credit_ratings] {len(records)} rating actions stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape CRISIL rating actions page as fallback."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get("https://www.crisil.com/en/home/our-businesses/ratings/corporate-ratings/rating-actions.html",
                             timeout=20, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for item in soup.select(".rating-action-item, .news-item, tr")[:20]:
                text = item.get_text(strip=True)
                if len(text) > 20 and any(w in text.lower() for w in DOWNGRADE_WORDS + UPGRADE_WORDS):
                    records.append(Event(
                        type="regulatory", title=f"[CRISIL] {text[:200]}",
                        date=today, entity_type="credit_rating", impact_score=0.6
                    ))
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[credit_ratings] scrape failed: {e}")
            return None
