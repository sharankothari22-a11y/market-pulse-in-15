"""
collectors/free/twitter_nitter.py
───────────────────────────────────
Twitter/X content via Nitter mirrors (no API key needed).
Tracks key Indian market influencers and institutional accounts.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
import feedparser
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import NewsArticle
from database.queries import upsert_news_article

# Active Nitter instances (updated list — some may be down)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://bird.trom.tf",
]
# High-signal Indian finance Twitter accounts
ACCOUNTS = [
    "NSEIndia",      "BSEIndia",      "RBI",           "SEBI_India",
    "FinMinIndia",   "PIBIndia",      "CEAIndia",
    "Unilazer",      "Zerodha",       "Nithin0dha",
]

class TwitterNitterCollector(BaseCollector):
    source_name = "twitter_nitter"
    fallback_chain = ["rss", "scrape", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Nitter exposes RSS feeds for Twitter accounts — no API key needed."""
        records = []
        today = target_date or date.today()
        working_instance = None

        # Find a working Nitter instance
        for instance in NITTER_INSTANCES:
            try:
                resp = requests.get(f"{instance}/NSEIndia/rss", timeout=8)
                if resp.status_code == 200 and "<rss" in resp.text:
                    working_instance = instance
                    break
            except Exception:
                continue

        if not working_instance:
            logger.warning("[twitter] No working Nitter instance found — all down or blocked")
            return None

        for account in ACCOUNTS:
            try:
                try:
                    import requests as _rq
                    _rss_url = f"{working_instance}/{account}/rss"
                    _r = _rq.get(_rss_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
                    feed = feedparser.parse(_r.content) if _r.ok else feedparser.FeedParserDict()
                except Exception:
                    feed = feedparser.FeedParserDict()
                for entry in feed.entries[:5]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip() or None
                    if not title or len(title) < 10:
                        continue
                    art = NewsArticle(
                        title=f"[@{account}] {title}"[:1000],
                        source=f"Twitter/{account}",
                        source_url=link,
                    )
                    records.append(art)
            except Exception as e:
                logger.debug(f"[twitter] {account} failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for art in records:
                upsert_news_article(s, art)

        logger.info(f"[twitter] {len(records)} tweets stored via {working_instance}")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")
