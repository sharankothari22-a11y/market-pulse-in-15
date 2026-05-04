"""
collectors/free/vc_funding.py
───────────────────────────────
Angel/VC funding rounds — India (Entrackr) + Global (Crunchbase).
Source: Entrackr RSS + public Crunchbase news + VCCircle RSS
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import feedparser, email.utils
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

VC_FEEDS = [
    ("Entrackr",   "https://entrackr.com/feed/"),
    ("VCCircle",   "https://www.vccircle.com/feed/"),
    ("Inc42",      "https://inc42.com/feed/"),
    ("YourStory",  "https://yourstory.com/feed"),
    ("TechCrunch India", "https://techcrunch.com/tag/india/feed/"),
]
FUNDING_KEYWORDS = ["funding", "raises", "series a", "series b", "series c",
                    "seed round", "ipo", "unicorn", "pre-ipo", "crore", "million"]

class VcFundingCollector(BaseCollector):
    source_name = "vc_funding"
    fallback_chain = ["rss", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()

        for source_name, feed_url in VC_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    if not title:
                        continue
                    if not any(kw in title.lower() for kw in FUNDING_KEYWORDS):
                        continue
                    pub = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = today
                    # Estimate impact from funding size mentioned in title
                    impact = 0.6 if any(kw in title.lower() for kw in ["series b","series c","unicorn","ipo"]) else 0.4
                    records.append(Event(
                        type="deal",
                        title=f"[{source_name}] {title}"[:1000],
                        date=ed, source_url=link,
                        entity_type="vc_funding",
                        impact_score=impact,
                    ))
            except Exception as e:
                logger.debug(f"[vc_funding] {source_name} failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)

        logger.info(f"[vc_funding] {len(records)} funding events stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")
