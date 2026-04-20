"""
collectors/free/sebi_pms.py
────────────────────────────
SEBI PMS quarterly disclosures — portfolio management scheme holdings.
Source: SEBI website direct download
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

SEBI_PMS_URL = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doDisclosurePMS=yes"
SEBI_PMS_RSS = "https://www.sebi.gov.in/sebirss.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

class SebiPmsCollector(BaseCollector):
    source_name = "sebi_pms"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        import feedparser, email.utils
        try:
            feed = feedparser.parse(SEBI_PMS_RSS)
            records = []
            today = target_date or date.today()
            for entry in feed.entries[:30]:
                title = entry.get("title", "").strip()
                if "pms" not in title.lower() and "portfolio" not in title.lower():
                    continue
                link = entry.get("link", "").strip() or None
                pub  = entry.get("published", "")
                try:
                    ed = email.utils.parsedate_to_datetime(pub).date()
                except Exception:
                    ed = today
                records.append(Event(
                    type="filing", title=f"[SEBI PMS] {title}"[:1000],
                    date=ed, source_url=link,
                    entity_type="sebi_pms", impact_score=0.4,
                ))
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            logger.info(f"[sebi_pms] {len(records)} PMS disclosures stored")
            self._store_cache(records, target_date=target_date)
            return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")
        except Exception as e:
            logger.warning(f"[sebi_pms] RSS failed: {e}")
            return None

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(SEBI_PMS_URL, timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for link in soup.find_all("a", href=True)[:20]:
                href = link["href"]
                text = link.get_text(strip=True)
                if ".pdf" in href.lower() or "pms" in text.lower():
                    full_url = href if href.startswith("http") else f"https://www.sebi.gov.in{href}"
                    records.append(Event(
                        type="filing", title=f"[SEBI PMS] {text or href}"[:1000],
                        date=today, source_url=full_url,
                        entity_type="sebi_pms",
                    ))
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[sebi_pms] scrape failed: {e}")
            return None
