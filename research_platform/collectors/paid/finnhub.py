"""
collectors/paid/finnhub.py
───────────────────────────
Finnhub real-time quotes, company fundamentals, and news.
Requires FINNHUB_API_KEY. Disabled by default in sources.yaml.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import FINNHUB_API_KEY

FINNHUB_BASE = "https://finnhub.io/api/v1"
TIMEOUT: int = 15


class FinnhubCollector(BaseCollector):
    source_name: str = "finnhub"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not FINNHUB_API_KEY:
            logger.warning(f"[{self.source_name}] FINNHUB_API_KEY not set. Skipping.")
            return None

        headers = {"X-Finnhub-Token": FINNHUB_API_KEY}
        url = f"{FINNHUB_BASE}/quote"
        # Example: fetch NIFTY50 constituents (extend for full list)
        test_symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
        records: list[dict] = []

        for symbol in test_symbols:
            try:
                resp = requests.get(url, params={"symbol": symbol}, headers=headers, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                records.append({"symbol": symbol, **data})
            except Exception as exc:
                logger.warning(f"[{self.source_name}] {symbol} failed: {exc}")

        if not records:
            return None

        self._store_cache(records, target_date=target_date)
        return CollectionResult(
            source_name=self.source_name,
            records=records,
            status="ok",
        )
