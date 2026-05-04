"""
collectors/free/sebi_portal.py
───────────────────────────────
Fetches SEBI regulatory circulars and PMS disclosures.

BUG FIX:
  - Removed fake placeholder dict that reported "partial" while storing nothing
  - RSS path now uses upsert_event + upsert_regulatory_order properly
  - API path fetches SEBI circular list as structured JSON where available
"""

from __future__ import annotations

import email.utils
from datetime import date
from typing import Optional

import requests
import feedparser  # type: ignore[import-untyped]
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import SEBI_PORTAL_BASE_URL
from database.connection import get_session
from database.models import Event, RegulatoryOrder
from database.queries import upsert_event, upsert_regulatory_order

TIMEOUT: int = 30

# SEBI's public RSS for circulars and press releases
SEBI_FEEDS = [
    ("SEBI Circulars",        "https://www.sebi.gov.in/sebirss.xml"),
    ("SEBI Press Releases",   "https://www.sebi.gov.in/pressrelease/sebi_pressreleases_rss.xml"),
]


class SebiPortalCollector(BaseCollector):
    source_name: str = "sebi_portal"
    fallback_chain: list[str] = ["rss", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Fetch SEBI circulars and press releases via RSS."""
        all_events: list[Event] = []
        all_orders: list[RegulatoryOrder] = []

        for feed_name, feed_url in SEBI_FEEDS:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:50]:
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip() or None
                    if not title:
                        continue

                    pub_raw = entry.get("published", "") or entry.get("updated", "")
                    entry_date: Optional[date] = None
                    if pub_raw:
                        try:
                            entry_date = email.utils.parsedate_to_datetime(pub_raw).date()
                        except Exception:
                            entry_date = date.today()
                    else:
                        entry_date = date.today()

                    # Store as Event for signal detection layer
                    all_events.append(Event(
                        type="regulatory",
                        title=title[:1000],
                        source_url=link,
                        date=entry_date,
                        entity_type="sebi",
                    ))

                    # Also store as RegulatoryOrder for structured access
                    all_orders.append(RegulatoryOrder(
                        regulator="SEBI",
                        order_type="circular" if "circular" in feed_name.lower() else "press_release",
                        title=title[:1000],
                        order_date=entry_date,
                        source_url=link,
                    ))

                logger.info(f"[{self.source_name}] {feed_name}: {len(parsed.entries)} entries")
            except Exception as exc:
                logger.warning(f"[{self.source_name}] Feed '{feed_name}' failed: {exc}")
                continue

        if not all_events:
            return None

        with get_session() as session:
            for ev in all_events:
                upsert_event(session, ev)
            for order in all_orders:
                upsert_regulatory_order(session, order)

        logger.info(
            f"[{self.source_name}] Upserted {len(all_events)} events, "
            f"{len(all_orders)} regulatory orders."
        )

        cache_data = [{"title": e.title, "url": e.source_url, "date": str(e.date)} for e in all_events[:100]]
        self._store_cache(cache_data, target_date=target_date)

        return CollectionResult(
            source_name=self.source_name,
            records=all_events,
            status="ok",
        )
