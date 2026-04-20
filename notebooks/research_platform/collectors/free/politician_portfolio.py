"""
collectors/free/politician_portfolio.py
────────────────────────────────────────
Politician asset disclosures — India (ADR/MyNeta) + US (Capitol Trades).
Source: MyNeta/ADR (affidavit data) + Capitol Trades RSS
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
import feedparser
import email.utils
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

ADR_API = "https://myneta.info/api/candidates.php"
CAPITOL_TRADES_RSS = "https://capitoltrades.com/trades.rss"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

class PoliticianPortfolioCollector(BaseCollector):
    source_name = "politician_portfolio"
    fallback_chain = ["rss", "api", "cache"]

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Capitol Trades RSS — US Congress member stock trades."""
        records = []
        today = target_date or date.today()
        try:
            feed = feedparser.parse(CAPITOL_TRADES_RSS)
            for entry in feed.entries[:25]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "").strip() or None
                pub   = entry.get("published", "")
                try:
                    ed = email.utils.parsedate_to_datetime(pub).date()
                except Exception:
                    ed = today
                if title:
                    records.append(Event(
                        type="filing",
                        title=f"[Capitol Trades] {title}"[:1000],
                        date=ed, source_url=link,
                        entity_type="politician_trade",
                        impact_score=0.3,
                    ))
        except Exception as e:
            logger.debug(f"[politician_portfolio] Capitol Trades failed: {e}")

        # India — MyNeta affidavit search
        try:
            resp = requests.get(
                "https://myneta.info/api/candidates.php?election_type=GE&year=2024&format=json",
                headers=HEADERS, timeout=15
            )
            if resp.ok:
                data = resp.json()
                candidates = data.get("candidates", [])[:20]
                for c in candidates:
                    name = c.get("name", "Unknown")
                    party = c.get("party", "")
                    assets = c.get("total_assets", "")
                    if name and assets:
                        records.append(Event(
                            type="filing",
                            title=f"[MyNeta] {name} ({party}) — Assets: {assets}"[:1000],
                            date=today, source_url="https://myneta.info",
                            entity_type="politician_trade",
                            impact_score=0.2,
                        ))
        except Exception as e:
            logger.debug(f"[politician_portfolio] MyNeta failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)
        logger.info(f"[politician_portfolio] {len(records)} politician disclosures stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="rss")
