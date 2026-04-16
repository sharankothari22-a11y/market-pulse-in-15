"""
collectors/free/industry_associations.py
──────────────────────────────────────────
Industry association directories — CII, FICCI, NASSCOM, SIAM, ACMA.
Source: RSS feeds → website scrape
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import feedparser, email.utils
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event, NewsArticle
from database.queries import upsert_event, upsert_news_article

ASSOCIATION_FEEDS = [
    ("CII",     "https://www.cii.in/rss.aspx"),
    ("FICCI",   "https://ficci.in/rss.asp"),
    ("NASSCOM", "https://nasscom.in/rss.xml"),
    ("SIAM",    "https://www.siam.in/rss.aspx"),
    ("ACMA",    "https://www.acma.in/rss.aspx"),
    ("AMFI",    "https://www.amfiindia.com/rss.xml"),
    ("ASSOCHAM","https://www.assocham.org/rss.xml"),
]
SECTOR_MAP = {
    "CII": "general", "FICCI": "general", "NASSCOM": "it",
    "SIAM": "auto",   "ACMA": "auto",     "AMFI": "banking", "ASSOCHAM": "general"
}

class IndustryAssociationsCollector(BaseCollector):
    source_name = "industry_associations"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()

        for org, feed_url in ASSOCIATION_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    if not title:
                        continue
                    pub = entry.get("published", "")
                    try:
                        ed = email.utils.parsedate_to_datetime(pub).date()
                    except Exception:
                        ed = today
                    art = NewsArticle(
                        title=f"[{org}] {title}"[:1000],
                        source=org,
                        source_url=link,
                    )
                    records.append(art)
                logger.debug(f"[industry_assoc] {org}: {len(feed.entries)} entries")
            except Exception as e:
                logger.debug(f"[industry_assoc] {org} RSS failed: {e}")

        if not records:
            return self._try_scrape(target_date)

        with get_session() as s:
            for art in records:
                upsert_news_article(s, art)

        logger.info(f"[industry_assoc] {len(records)} association items stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import httpx
            from bs4 import BeautifulSoup
            records = []
            today = target_date or date.today()
            for org, _ in ASSOCIATION_FEEDS[:3]:
                urls = {
                    "CII":     "https://www.cii.in/NewsViews.aspx",
                    "FICCI":   "https://ficci.in/pressrelease-list.asp",
                    "NASSCOM": "https://nasscom.in/press-releases",
                }
                url = urls.get(org)
                if not url:
                    continue
                try:
                    resp = httpx.get(url, timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(resp.text, "lxml")
                    for a in soup.find_all("a", href=True)[:10]:
                        text = a.get_text(strip=True)
                        if len(text) > 20:
                            full_url = a["href"] if a["href"].startswith("http") else f"https://{url.split('/')[2]}{a['href']}"
                            records.append(NewsArticle(
                                title=f"[{org}] {text[:200]}", source=org, source_url=full_url,
                            ))
                except Exception:
                    continue
            if not records:
                return None
            with get_session() as s:
                for art in records:
                    upsert_news_article(s, art)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[industry_assoc] scrape failed: {e}")
            return None
