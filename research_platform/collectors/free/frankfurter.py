"""
collectors/free/frankfurter.py
───────────────────────────────
Fetches daily FX rates from Frankfurter API (ECB sourced, free, no key).
Stores into fx_rates table.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import FRANKFURTER_API_URL
from database.connection import get_session
from database.models import FxRate
from database.queries import upsert_fx_rate

BASE_CURRENCY = "USD"
SYMBOLS = ["EUR", "GBP", "JPY", "INR", "CNY", "AUD", "CAD", "CHF", "SGD", "HKD"]
TIMEOUT: int = 15


class FrankfurterCollector(BaseCollector):
    source_name: str = "frankfurter"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        date_str = target_date.isoformat() if target_date else "latest"
        url = f"{FRANKFURTER_API_URL}/{date_str}"
        params = {"from": BASE_CURRENCY, "to": ",".join(SYMBOLS)}

        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(f"[{self.source_name}] Frankfurter request failed: {exc}")
            return None

        obs_date = date.fromisoformat(data.get("date", date.today().isoformat()))
        rates = data.get("rates", {})
        records: list[FxRate] = []

        for symbol, rate in rates.items():
            records.append(
                FxRate(
                    pair=f"{BASE_CURRENCY}/{symbol}",
                    date=obs_date,
                    rate=float(rate),
                    source="Frankfurter/ECB",
                )
            )

        with get_session() as session:
            for r in records:
                upsert_fx_rate(session, r)

        self._store_cache(records, target_date=obs_date)
        logger.info(f"[{self.source_name}] Stored {len(records)} FX rates for {obs_date}.")
        return CollectionResult(
            source_name=self.source_name,
            records=records,
            status="ok" if records else "partial",
        )
