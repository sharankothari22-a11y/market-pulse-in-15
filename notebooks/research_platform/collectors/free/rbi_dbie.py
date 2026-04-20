"""
collectors/free/rbi_dbie.py
────────────────────────────
RBI DBIE macro/banking statistics + RBI press release RSS.

BUG FIX: RSS fallback now uses upsert_event + upsert_regulatory_order.
Also fixes source field so MacroIndicator dedup works correctly.
"""

from __future__ import annotations

import email.utils
from datetime import date
from typing import Optional

import requests
import feedparser  # type: ignore[import-untyped]
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import RBI_DBIE_BASE_URL
from database.connection import get_session
from database.models import Event, MacroIndicator, RegulatoryOrder
from database.queries import upsert_event, upsert_macro_indicator, upsert_regulatory_order

TIMEOUT: int = 30

RBI_SERIES = [
    {"code": "RBIQ0001", "name": "Repo Rate",         "country_iso": "IN"},
    {"code": "RBIQ0002", "name": "Reverse Repo Rate", "country_iso": "IN"},
    {"code": "RBIQ0003", "name": "CRR",               "country_iso": "IN"},
    {"code": "RBIQ0004", "name": "SLR",               "country_iso": "IN"},
]

RBI_RSS_FEEDS = [
    ("RBI Press Releases", "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=rss"),
    ("RBI Notifications",  "https://www.rbi.org.in/Scripts/NotificationUser.aspx?rss=1"),
]

RATE_KEYWORDS = ["repo", "rate", "monetary", "policy", "crr", "slr", "inflation", "gdp"]


class RbiDbieCollector(BaseCollector):
    source_name: str = "rbi_dbie"
    fallback_chain: list[str] = ["api", "rss", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        all_records: list[MacroIndicator] = []

        for series in RBI_SERIES:
            url = f"{RBI_DBIE_BASE_URL}/DBIE/dbie.rbi"
            params = {"site": "DBIE", "type": "statement", "param": series["code"]}
            try:
                resp = requests.get(url, params=params, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                observations = (
                    data if isinstance(data, list)
                    else data.get("data", data.get("observations", []))
                )
                for obs in observations:
                    try:
                        date_str = obs.get("TIME_PERIOD", obs.get("date", ""))
                        value = obs.get("OBS_VALUE", obs.get("value"))
                        if not date_str or value is None:
                            continue
                        obs_date = date.fromisoformat(str(date_str)[:10])
                        # Source includes country so dedup works correctly
                        source = f"RBI_DBIE/{series['country_iso']}"
                        all_records.append(MacroIndicator(
                            country_id=None,
                            indicator=series["name"],
                            date=obs_date,
                            value=float(value),
                            source=source,
                        ))
                    except Exception:
                        continue
            except Exception as exc:
                logger.warning(f"[{self.source_name}] Series {series['code']} failed: {exc}")
                continue

        if not all_records:
            logger.warning(f"[{self.source_name}] RBI DBIE API returned no data — trying RSS.")
            return None

        with get_session() as session:
            for r in all_records:
                upsert_macro_indicator(session, r)

        self._store_cache(all_records, target_date=target_date)
        logger.info(f"[{self.source_name}] Stored {len(all_records)} RBI DBIE records.")
        return CollectionResult(
            source_name=self.source_name,
            records=all_records,
            status="ok",
        )

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Mine RBI press releases for rate decisions and policy events.

        BUG FIX: Was returning a list of dicts and never persisting to DB.
        Now uses upsert_event + upsert_regulatory_order.
        """
        all_events: list[Event] = []
        all_orders: list[RegulatoryOrder] = []

        for feed_name, feed_url in RBI_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:30]:
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

                    is_policy = any(kw in title.lower() for kw in RATE_KEYWORDS)

                    all_events.append(Event(
                        type="policy" if is_policy else "regulatory",
                        title=title[:1000],
                        source_url=link,
                        date=entry_date,
                        entity_type="rbi",
                    ))
                    all_orders.append(RegulatoryOrder(
                        regulator="RBI",
                        order_type="monetary_policy" if is_policy else "press_release",
                        title=title[:1000],
                        order_date=entry_date,
                        source_url=link,
                    ))

                logger.info(f"[{self.source_name}] {feed_name}: {len(feed.entries)} entries")
            except Exception as exc:
                logger.warning(f"[{self.source_name}] Feed '{feed_name}' failed: {exc}")

        if not all_events:
            return None

        with get_session() as session:
            for ev in all_events:
                upsert_event(session, ev)
            for order in all_orders:
                upsert_regulatory_order(session, order)

        logger.info(f"[{self.source_name}] Upserted {len(all_events)} RBI events.")
        cache_data = [{"title": e.title, "url": e.source_url} for e in all_events[:100]]
        self._store_cache(cache_data, target_date=target_date)

        return CollectionResult(
            source_name=self.source_name,
            records=all_events,
            status="partial",  # partial because RSS != structured rate data
        )
