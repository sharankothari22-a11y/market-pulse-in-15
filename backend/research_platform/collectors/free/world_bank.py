"""
collectors/free/world_bank.py
──────────────────────────────
Fetches World Bank development indicators for key countries.
Uses World Bank REST API v2 — no key required.
Stores into macro_indicators table.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import WORLD_BANK_API_URL
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

INDICATORS = [
    "NY.GDP.MKTP.KD.ZG",   # GDP growth (annual %)
    "FP.CPI.TOTL.ZG",      # Inflation, consumer prices (annual %)
    "SL.UEM.TOTL.ZS",      # Unemployment, total (% of labor force)
]
COUNTRIES = ["IN", "US", "CN", "GB", "DE", "JP"]
TIMEOUT: int = 30
PER_PAGE: int = 1000


class WorldBankCollector(BaseCollector):
    source_name: str = "world_bank"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        all_records: list[MacroIndicator] = []

        for indicator in INDICATORS:
            for country in COUNTRIES:
                url = (
                    f"{WORLD_BANK_API_URL}/country/{country}/indicator/{indicator}"
                )
                params = {
                    "format": "json",
                    "per_page": PER_PAGE,
                    "mrv": 20,          # most recent 20 values
                }
                try:
                    resp = requests.get(url, params=params, timeout=TIMEOUT)
                    resp.raise_for_status()
                    payload = resp.json()
                    if len(payload) < 2 or not payload[1]:
                        continue

                    for obs in payload[1]:
                        value = obs.get("value")
                        if value is None:
                            continue
                        year = obs.get("date")
                        try:
                            obs_date = date(int(year), 12, 31)  # year-end
                        except (TypeError, ValueError):
                            continue

                        all_records.append(
                            MacroIndicator(
                                country_id=None,   # resolved later via entity_resolver
                                indicator=indicator,
                                date=obs_date,
                                value=float(value),
                                source=f"WorldBank/{country}",
                            )
                        )
                except Exception as exc:
                    logger.warning(
                        f"[{self.source_name}] {country}/{indicator} failed: {exc}"
                    )
                    continue

        if not all_records:
            return None

        with get_session() as session:
            for r in all_records:
                upsert_macro_indicator(session, r)

        self._store_cache(all_records, target_date=target_date)
        logger.info(
            f"[{self.source_name}] Stored {len(all_records)} World Bank observations."
        )
        return CollectionResult(
            source_name=self.source_name,
            records=all_records,
            status="ok",
        )
