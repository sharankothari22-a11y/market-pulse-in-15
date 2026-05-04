"""
collectors/free/pli_schemes.py
────────────────────────────────
PLI (Production Linked Incentive) scheme beneficiary lists.
Source: Ministry websites + PIB press releases
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

PLI_FEEDS = [
    ("MoEF PLI",       "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"),
    ("MeitY PLI",      "https://www.meity.gov.in/rss.xml"),
    ("Pharma PLI",     "https://pharmaceuticals.gov.in/rss.xml"),
    ("Auto PLI",       "https://heavyindustries.gov.in/rss.xml"),
    ("Textile PLI",    "https://texmin.nic.in/rss.xml"),
]
PLI_KEYWORDS = ["pli", "production linked", "beneficiary", "scheme approval",
                "incentive", "approved applicant", "selected company"]

class PliSchemesCollector(BaseCollector):
    source_name = "pli_schemes"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()

        for feed_name, feed_url in PLI_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    if not title:
                        continue
                    if not any(kw in title.lower() for kw in PLI_KEYWORDS):
                        continue
                    pub = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = today
                    records.append(Event(
                        type="policy",
                        title=f"[PLI] {title}"[:1000],
                        date=ed, source_url=link,
                        entity_type="government",
                        impact_score=0.6,
                    ))
            except Exception as e:
                logger.debug(f"[pli_schemes] {feed_name} failed: {e}")

        if not records:
            return self._try_scrape(target_date)

        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)

        logger.info(f"[pli_schemes] {len(records)} PLI items stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(
                "https://www.investindia.gov.in/production-linked-incentive-scheme",
                timeout=15, follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for el in soup.select("h3, h4, .scheme-name, .beneficiary")[:15]:
                text = el.get_text(strip=True)
                if len(text) > 10:
                    records.append(Event(
                        type="policy",
                        title=f"[PLI] {text}"[:1000],
                        date=today,
                        source_url="https://www.investindia.gov.in/production-linked-incentive-scheme",
                        entity_type="government",
                        impact_score=0.5,
                    ))
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[pli_schemes] scrape failed: {e}")
            return None
