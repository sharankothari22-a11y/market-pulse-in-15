"""
collectors/free/rss_feeds.py
─────────────────────────────
Parses financial news RSS feeds, stores entries as Event records.

BUG FIX: Uses upsert_event() instead of session.add() directly —
prevents duplicate headlines on every daily run.
"""

from __future__ import annotations

import email.utils
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import feedparser  # type: ignore[import-untyped]
import yaml
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

SOURCES_YAML = Path(__file__).parents[3] / "config" / "sources.yaml"

# Hardcoded fallback in case sources.yaml is unavailable
DEFAULT_FEEDS = [
    ("Economic Times Markets",   "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Moneycontrol News",        "https://www.moneycontrol.com/rss/MCtopnews.xml"),
    ("Reuters Business",         "https://feeds.reuters.com/reuters/businessNews"),
    ("Bloomberg Markets",        "https://feeds.bloomberg.com/markets/news.rss"),
    ("NSE Circulars",            "https://nsearchives.nseindia.com/content/circulars/circulars.xml"),
    ("SEBI Press Releases",      "https://www.sebi.gov.in/sebirss.xml"),
    ("RBI Press Releases",       "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=rss"),
]


class RssFeedsCollector(BaseCollector):
    source_name: str = "rss_feeds"
    fallback_chain: list[str] = ["rss", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        feeds = self._load_feed_list()
        all_events: list[Event] = []
        total_inserted = 0

        for feed_name, feed_url in feeds:
            try:
                parsed = feedparser.parse(feed_url)
                inserted_this_feed = 0

                for entry in parsed.entries[:30]:
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip() or None
                    if not title:
                        continue

                    # Parse publish date
                    pub_raw = entry.get("published", "") or entry.get("updated", "")
                    nav_date: Optional[date] = None
                    if pub_raw:
                        try:
                            nav_date = email.utils.parsedate_to_datetime(pub_raw).date()
                        except Exception:
                            try:
                                nav_date = datetime(*entry.get("published_parsed", [])[:3]).date()
                            except Exception:
                                nav_date = date.today()
                    else:
                        nav_date = date.today()

                    ev = Event(
                        type="regulatory",
                        title=title[:1000],
                        source_url=link,
                        date=nav_date,
                        entity_type="news",
                    )
                    all_events.append(ev)

                logger.debug(f"[{self.source_name}] {feed_name}: {len(parsed.entries)} entries fetched")
            except Exception as exc:
                logger.warning(f"[{self.source_name}] Feed '{feed_name}' failed: {exc}")
                continue

        if not all_events:
            return None

        # Upsert — no duplicates on re-run
        with get_session() as session:
            for ev in all_events:
                upsert_event(session, ev)
                total_inserted += 1

        logger.info(f"[{self.source_name}] Upserted {total_inserted} news events.")
        self._store_cache(
            [{"title": e.title, "url": e.source_url, "date": str(e.date)} for e in all_events[:200]],
            target_date=target_date,
        )

        return CollectionResult(
            source_name=self.source_name,
            records=all_events,
            status="ok",
        )

    def _load_feed_list(self) -> list[tuple[str, str]]:
        try:
            with open(SOURCES_YAML) as f:
                config = yaml.safe_load(f)
            feed_confs = config.get("free", {}).get("rss_feeds", {}).get("feeds", [])
            if feed_confs:
                return [(fc.get("name", "?"), fc.get("url", "")) for fc in feed_confs if fc.get("url")]
        except Exception:
            pass
        return DEFAULT_FEEDS
