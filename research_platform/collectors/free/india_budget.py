"""
collectors/free/india_budget.py
────────────────────────────────
India Budget documents, government notifications, gazette.
Source: indiabudget.gov.in + PIB RSS + Gazette RSS
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import feedparser
import email.utils
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import BudgetDocument, Event
from database.queries import upsert_event

GOV_FEEDS = [
    ("PIB India",        "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"),
    ("India Budget",     "https://www.indiabudget.gov.in/rss.xml"),
    ("Ministry Finance", "https://finmin.nic.in/rss.xml"),
    ("MoF Press",        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=rss"),
]

class IndiaBudgetCollector(BaseCollector):
    source_name = "india_budget"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()
        for feed_name, feed_url in GOV_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    pub   = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = today
                    if title:
                        # High-impact keywords
                        is_budget = any(kw in title.lower() for kw in
                            ["budget", "fiscal", "tax", "gst", "pli", "tariff", "duty", "subsidy"])
                        impact = 0.8 if is_budget else 0.4
                        records.append(Event(
                            type="policy",
                            title=f"[{feed_name}] {title}"[:1000],
                            date=ed, source_url=link,
                            entity_type="government",
                            impact_score=impact,
                        ))
            except Exception as e:
                logger.debug(f"[india_budget] {feed_name} failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)
        logger.info(f"[india_budget] {len(records)} government notices stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get("https://www.indiabudget.gov.in/", timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for a in soup.find_all("a", href=True)[:20]:
                href = a["href"]
                text = a.get_text(strip=True)
                if ".pdf" in href.lower() and len(text) > 5:
                    full = href if href.startswith("http") else f"https://www.indiabudget.gov.in{href}"
                    records.append(Event(
                        type="policy", title=f"[Budget PDF] {text}"[:1000],
                        date=today, source_url=full,
                        entity_type="government", impact_score=0.7,
                    ))
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[india_budget] scrape failed: {e}")
            return None
