"""
collectors/free/aif_data.py
─────────────────────────────
SEBI AIF (Alternative Investment Fund) category data.
Source: SEBI quarterly AIF download
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests, feedparser, email.utils
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event, Fund
from database.queries import upsert_event

SEBI_AIF_URL = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doAifFund=yes"
SEBI_AIF_RSS = "https://www.sebi.gov.in/sebirss.xml"
AIF_KEYWORDS = ["aif", "alternative investment", "category i", "category ii", "category iii",
                "venture capital", "private equity", "hedge fund"]

class AifDataCollector(BaseCollector):
    source_name = "aif_data"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()
        try:
            feed = feedparser.parse(SEBI_AIF_RSS)
            for entry in feed.entries[:40]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "").strip() or None
                if not title:
                    continue
                if not any(kw in title.lower() for kw in AIF_KEYWORDS):
                    continue
                pub = entry.get("published", "")
                try:
                    ed = email.utils.parsedate_to_datetime(pub).date()
                except Exception:
                    ed = today
                records.append(Event(
                    type="filing",
                    title=f"[SEBI AIF] {title}"[:1000],
                    date=ed, source_url=link,
                    entity_type="aif", impact_score=0.4,
                ))
        except Exception as e:
            logger.warning(f"[aif_data] RSS failed: {e}")

        if not records:
            return self._try_scrape(target_date)

        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)
        logger.info(f"[aif_data] {len(records)} AIF items stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(SEBI_AIF_URL, timeout=20, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for row in soup.select("table tr")[1:21]:
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cells) >= 2 and cells[0]:
                    records.append(Event(
                        type="filing",
                        title=f"[SEBI AIF] {cells[0]}"[:1000],
                        date=today, source_url=SEBI_AIF_URL,
                        entity_type="aif",
                    ))
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[aif_data] scrape failed: {e}")
            return None
