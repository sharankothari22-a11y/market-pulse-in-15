"""
collectors/free/wikipedia_signals.py
──────────────────────────────────────
Wikipedia edit frequency — leading signal for major news.
Edit spikes on company/sector pages often precede announcements.
Source: Wikipedia API (free, no key needed)
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

WIKI_API = "https://en.wikipedia.org/w/api.php"
WATCH_PAGES = [
    "Reliance_Industries", "Tata_Consultancy_Services", "HDFC_Bank",
    "Infosys", "ICICI_Bank", "State_Bank_of_India", "Wipro",
    "Adani_Group", "Nifty_50", "Bombay_Stock_Exchange",
    "Reserve_Bank_of_India", "Securities_and_Exchange_Board_of_India",
]
HEADERS = {"User-Agent": "research_platform/1.0 (financial research; contact@research.local)"}

class WikipediaSignalsCollector(BaseCollector):
    source_name = "wikipedia_signals"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()
        yesterday = today - timedelta(days=1)

        for page in WATCH_PAGES:
            try:
                params = {
                    "action": "query", "format": "json",
                    "titles": page, "prop": "revisions",
                    "rvprop": "timestamp|user|comment",
                    "rvstart": f"{yesterday}T00:00:00Z",
                    "rvend":   f"{today}T23:59:59Z",
                    "rvlimit": "50",
                }
                resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_data in pages.values():
                    revisions = page_data.get("revisions", [])
                    edit_count = len(revisions)
                    if edit_count >= 3:  # Spike threshold
                        page_name = page_data.get("title", page)
                        impact = min(edit_count / 20, 0.8)
                        title = f"Wikipedia spike: '{page_name}' had {edit_count} edits in 24h — potential news signal"
                        records.append(Event(
                            type="regulatory",
                            title=title[:1000],
                            date=today,
                            source_url=f"https://en.wikipedia.org/wiki/{page}",
                            entity_type="wikipedia",
                            impact_score=impact,
                        ))
                        logger.info(f"[wikipedia] Spike: {page_name} — {edit_count} edits")
            except Exception as e:
                logger.debug(f"[wikipedia] {page} failed: {e}")

        if not records:
            logger.info("[wikipedia] No edit spikes detected today")
            return None

        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
