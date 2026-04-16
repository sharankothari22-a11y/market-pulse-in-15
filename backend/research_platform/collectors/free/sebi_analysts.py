"""
collectors/free/sebi_analysts.py
──────────────────────────────────
SEBI-registered research analysts registry + published research notes.
Source: SEBI public registry → individual firm RSS feeds
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests, feedparser, email.utils
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event, NewsArticle
from database.queries import upsert_event, upsert_news_article

SEBI_RA_URL  = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=14"
SEBI_RA_RSS  = "https://www.sebi.gov.in/sebirss.xml"
# Known SEBI-registered analyst firm RSS / research feeds
ANALYST_FEEDS = [
    ("Motilal Oswal",    "https://www.motilaloswal.com/rss/research"),
    ("Kotak Securities", "https://www.kotaksecurities.com/rss/research"),
    ("ICICI Direct",     "https://www.icicidirect.com/rss/research"),
    ("Axis Securities",  "https://www.axissecurities.in/rss"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

class SebiAnalystsCollector(BaseCollector):
    source_name = "sebi_analysts"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()

        # SEBI main RSS — filter for analyst-related entries
        try:
            feed = feedparser.parse(SEBI_RA_RSS)
            for entry in feed.entries[:30]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "").strip() or None
                if not title:
                    continue
                if any(kw in title.lower() for kw in ["research analyst","analyst","ra circular","ra registration"]):
                    pub = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = today
                    records.append(Event(
                        type="regulatory",
                        title=f"[SEBI RA] {title}"[:1000],
                        date=ed, source_url=link,
                        entity_type="sebi_analyst", impact_score=0.5,
                    ))
        except Exception as e:
            logger.debug(f"[sebi_analysts] SEBI RSS failed: {e}")

        # Known analyst firm feeds
        for firm, feed_url in ANALYST_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    if not title:
                        continue
                    pub = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = today
                    # Store as NewsArticle for AI signal detection
                    art = NewsArticle(
                        title=f"[{firm}] {title}"[:1000],
                        source=firm, source_url=link,
                        published_at=None, body=None,
                    )
                    records.append(art)
            except Exception as e:
                logger.debug(f"[sebi_analysts] {firm} feed failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for r in records:
                if isinstance(r, Event):
                    upsert_event(s, r)
                elif isinstance(r, NewsArticle):
                    upsert_news_article(s, r)

        logger.info(f"[sebi_analysts] {len(records)} analyst items stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape SEBI RA registry page for registered analyst list."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(SEBI_RA_URL, timeout=20, follow_redirects=True, headers=HEADERS)
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for row in soup.select("table tr")[1:21]:
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cells) >= 3:
                    name = cells[0]
                    reg_no = cells[1] if len(cells) > 1 else ""
                    if name:
                        ev = Event(
                            type="regulatory",
                            title=f"[SEBI RA Registry] {name} — Reg: {reg_no}"[:1000],
                            date=today, source_url=SEBI_RA_URL,
                            entity_type="sebi_analyst", impact_score=0.2,
                        )
                        records.append(ev)
            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[sebi_analysts] scrape failed: {e}")
            return None
