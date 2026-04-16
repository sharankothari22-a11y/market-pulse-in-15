"""
collectors/paid/bloomberg.py
──────────────────────────────
Bloomberg Intelligence analyst database.
Requires Bloomberg API key (BLOOMBERG_API_KEY in .env).
Add key when available — all logic is ready.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from config.settings import BLOOMBERG_API_KEY
from database.connection import get_session
from database.models import NewsArticle, MacroIndicator
from database.queries import upsert_news_article, upsert_macro_indicator

BLOOMBERG_BASE = "https://api.bloomberg.com/eap/catalogs/bbg/fields"
BLOOMBERG_DATA = "https://api.bloomberg.com/eap/catalogs/bbg/universes"

class BloombergCollector(BaseCollector):
    source_name = "bloomberg"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not BLOOMBERG_API_KEY:
            logger.info("[bloomberg] BLOOMBERG_API_KEY not set — add key to .env to enable")
            return None

        today = target_date or date.today()
        records = []
        headers = {
            "Authorization": f"Bearer {BLOOMBERG_API_KEY}",
            "Accept": "application/json",
        }
        # Bloomberg Intelligence analyst reports
        try:
            resp = requests.get(
                f"{BLOOMBERG_BASE}/intelligence/reports",
                headers=headers,
                params={"regions": "India", "limit": 20},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("reports", []):
                title   = item.get("title", "")
                analyst = item.get("analyst", "")
                sector  = item.get("sector", "")
                art = NewsArticle(
                    title=f"[Bloomberg Intelligence/{analyst}] {title} — {sector}"[:1000],
                    source="Bloomberg Intelligence",
                    source_url=item.get("url"),
                )
                records.append(art)
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("[bloomberg] API key invalid or expired")
            else:
                logger.warning(f"[bloomberg] API error: {e}")
        except Exception as e:
            logger.warning(f"[bloomberg] Failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for art in records:
                upsert_news_article(s, art)

        logger.info(f"[bloomberg] {len(records)} Bloomberg Intelligence items stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
