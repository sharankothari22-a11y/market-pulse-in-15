"""
collectors/free/sec_edgar.py
──────────────────────────────
SEC EDGAR 13F filings — US institutional holdings of Indian ADRs.
Source: SEC EDGAR full-text search API (free, no key needed)
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22India%22&dateRange=custom&startdt={start}&enddt={end}&forms=13F-HR"
EDGAR_BASE   = "https://www.sec.gov"
HEADERS = {"User-Agent": "research_platform financial research contact@research.local"}

class SecEdgarCollector(BaseCollector):
    source_name = "sec_edgar"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        from datetime import timedelta
        today = target_date or date.today()
        start = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        end   = today.strftime("%Y-%m-%d")
        try:
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22India%22+%2213F%22&dateRange=custom&startdt={start}&enddt={end}&forms=13F-HR"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            records = []
            with get_session() as s:
                seen_urls = set()
                for hit in hits[:20]:
                    src = hit.get("_source", {})
                    entity_id = src.get("entity_id", "")
                    file_name = src.get("file_name", "")
                    # Skip records with missing URL components — they'd all share
                    # the same malformed URL and violate the unique constraint
                    if not entity_id or not file_name:
                        logger.debug(f"[sec_edgar] skipping hit with missing entity_id/file_name")
                        continue
                    url_ = f"{EDGAR_BASE}/Archives/edgar/data/{entity_id}/{file_name}"
                    # Deduplicate within this batch before hitting the DB
                    dedup_key = (url_, str(today), "filing")
                    if dedup_key in seen_urls:
                        continue
                    seen_urls.add(dedup_key)
                    title = f"13F Filing: {src.get('entity_name', 'Unknown')} — {src.get('file_date', today)}"
                    ev = Event(
                        type="filing", title=title[:1000],
                        date=today, source_url=url_,
                        entity_type="sec_edgar", impact_score=0.3,
                    )
                    upsert_event(s, ev)
                    records.append(ev)
            logger.info(f"[sec_edgar] {len(records)} 13F filings stored")
            self._store_cache(records, target_date=target_date)
            return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
        except Exception as e:
            logger.warning(f"[sec_edgar] failed: {e}")
            return None
