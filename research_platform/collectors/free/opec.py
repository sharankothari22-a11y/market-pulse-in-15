"""
collectors/free/opec.py
───────────────────────
OPEC news, production decisions, supply/demand data.
Sources: OPEC RSS → OPEC website scrape → cache
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

OPEC_FEEDS = [
    "https://www.opec.org/opec_web/en/press_room/rss.htm",
    "https://feeds.feedburner.com/opec-news",
]
OPEC_KEYWORDS = ["production", "quota", "barrel", "supply", "demand", "cut", "increase", "mbpd"]

class OpecCollector(BaseCollector):
    source_name = "opec"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        events = []
        for feed_url in OPEC_FEEDS:
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
                    # Tag high-impact production decisions
                    is_production = any(kw in title.lower() for kw in OPEC_KEYWORDS)
                    impact = 0.8 if is_production else 0.4
                    events.append(Event(
                        type="policy", title=title[:1000], date=ed,
                        source_url=link, entity_type="opec", impact_score=impact
                    ))
                if events:
                    break
            except Exception as e:
                logger.warning(f"[opec] RSS {feed_url} failed: {e}")

        if not events:
            return None
        with get_session() as s:
            for ev in events:
                upsert_event(s, ev)
        self._store_cache(events, target_date=target_date)
        logger.info(f"[opec] {len(events)} events stored")
        return CollectionResult(source_name=self.source_name, records=events, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get("https://www.opec.org/opec_web/en/press_room/news.htm",
                             timeout=20, headers={"User-Agent": "Mozilla/5.0"},
                             follow_redirects=True)
            soup = BeautifulSoup(resp.text, "lxml")
            events = []
            today = target_date or date.today()
            for item in soup.select(".news-item, .pressRelease, article")[:15]:
                title_el = item.find(["h2", "h3", "h4", "a"])
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = item.find("a", href=True)
                link = link_el["href"] if link_el else None
                if link and not link.startswith("http"):
                    link = f"https://www.opec.org{link}"
                if title:
                    events.append(Event(
                        type="policy", title=title[:1000], date=today,
                        source_url=link, entity_type="opec", impact_score=0.5
                    ))
            if not events:
                return None
            with get_session() as s:
                for ev in events:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=events, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[opec] scrape failed: {e}")
            return None
