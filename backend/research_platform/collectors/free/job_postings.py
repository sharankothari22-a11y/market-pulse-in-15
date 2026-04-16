"""
collectors/free/job_postings.py
─────────────────────────────────
Job posting trends by company — proxy for growth/expansion.
Source: LinkedIn public job count → Naukri RSS → Indeed scrape
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
import feedparser
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

# Naukri RSS feeds by company/sector
NAUKRI_FEEDS = [
    ("Naukri IT",       "https://www.naukri.com/rss/jobs-in-it-sector.rss"),
    ("Naukri Banking",  "https://www.naukri.com/rss/jobs-in-banking-sector.rss"),
    ("Naukri Pharma",   "https://www.naukri.com/rss/jobs-in-pharmaceutical-sector.rss"),
]

# Companies to track hiring sentiment
COMPANIES = {
    "Infosys": "https://www.naukri.com/infosys-jobs",
    "TCS":     "https://www.naukri.com/tcs-jobs",
    "Wipro":   "https://www.naukri.com/wipro-jobs",
}

class JobPostingsCollector(BaseCollector):
    source_name = "job_postings"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()
        for feed_name, feed_url in NAUKRI_FEEDS:
            try:
                try:
                    import requests as _rq
                    _r = _rq.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
                    feed = feedparser.parse(_r.content) if _r.ok else feedparser.FeedParserDict()
                except Exception:
                    feed = feedparser.FeedParserDict()
                count = len(feed.entries)
                if count > 0:
                    # Store job count as a macro indicator
                    sector = feed_name.replace("Naukri ", "").lower()
                    rec = MacroIndicator(
                        indicator=f"JobPostings/{sector}/count",
                        date=today,
                        value=float(count),
                        source="Naukri/RSS",
                    )
                    records.append(rec)
                    logger.debug(f"[job_postings] {feed_name}: {count} active postings")
            except Exception as e:
                logger.debug(f"[job_postings] {feed_name} failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_macro_indicator(s, r)
        logger.info(f"[job_postings] {len(records)} job count indicators stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape Naukri for job count per company."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            records = []
            today = target_date or date.today()
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            for company, url in list(COMPANIES.items())[:3]:
                try:
                    resp = httpx.get(url, timeout=15, headers=headers, follow_redirects=True)
                    soup = BeautifulSoup(resp.text, "lxml")
                    # Find job count text
                    count_el = soup.find(string=lambda t: t and "jobs" in t.lower() and any(c.isdigit() for c in t))
                    if count_el:
                        import re
                        nums = re.findall(r'[\d,]+', str(count_el))
                        if nums:
                            count = int(nums[0].replace(",", ""))
                            rec = MacroIndicator(
                                indicator=f"JobPostings/{company}/count",
                                date=today, value=float(count),
                                source="Naukri/Scrape",
                            )
                            records.append(rec)
                except Exception:
                    continue
            if not records:
                return None
            with get_session() as s:
                for r in records:
                    upsert_macro_indicator(s, r)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[job_postings] scrape failed: {e}")
            return None
