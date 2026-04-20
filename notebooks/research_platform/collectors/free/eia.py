"""
collectors/free/eia.py
──────────────────────
Fetches EIA oil and energy data.
Requires EIA_API_KEY (free registration at https://www.eia.gov/opendata/).
Stores oil prices into commodity_prices and energy metrics into macro_indicators.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import EIA_API_KEY, EIA_API_URL
from database.connection import get_session
from database.models import Commodity, CommodityPrice, MacroIndicator
from database.queries import upsert_commodity_price, upsert_macro_indicator
from sqlalchemy import select

TIMEOUT: int = 30

# EIA series to fetch
EIA_SERIES = [
    {
        "id": "PET.RWTC.D",
        "name": "WTI Crude Oil Spot Price",
        "type": "commodity",
        "unit": "Dollars per Barrel",
    },
    {
        "id": "PET.RBRTE.D",
        "name": "Brent Crude Oil Spot Price",
        "type": "commodity",
        "unit": "Dollars per Barrel",
    },
    {
        "id": "NG.RNGWHHD.D",
        "name": "Henry Hub Natural Gas Spot Price",
        "type": "commodity",
        "unit": "Dollars per MMBtu",
    },
]


class EiaCollector(BaseCollector):
    source_name: str = "eia"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not EIA_API_KEY:
            logger.warning(f"[{self.source_name}] EIA_API_KEY not set. Skipping.")
            return None

        all_records: list = []

        for series in EIA_SERIES:
            url = f"{EIA_API_URL}/seriesid/{series['id']}"
            params = {"api_key": EIA_API_KEY, "out": "json", "num": 365}
            try:
                resp = requests.get(url, params=params, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                observations = (
                    data.get("response", {}).get("data", [])
                    or data.get("series", [{}])[0].get("data", [])
                )

                commodity_id = self._resolve_commodity(series["name"])

                for obs in observations:
                    if isinstance(obs, list):
                        date_str, value = obs[0], obs[1]
                    elif isinstance(obs, dict):
                        date_str = obs.get("period", obs.get("date", ""))
                        value = obs.get("value")
                    else:
                        continue

                    if value is None or value == "":
                        continue
                    try:
                        obs_date = date.fromisoformat(str(date_str)[:10])
                        record = CommodityPrice(
                            commodity_id=commodity_id,
                            date=obs_date,
                            price=float(value),
                            currency="USD",
                            exchange="EIA",
                        )
                        all_records.append(record)
                    except (ValueError, TypeError):
                        continue

            except Exception as exc:
                logger.warning(f"[{self.source_name}] EIA series {series['id']} failed: {exc}")
                continue

        if not all_records:
            return None

        with get_session() as session:
            for r in all_records:
                upsert_commodity_price(session, r)

        self._store_cache(all_records, target_date=target_date)
        logger.info(f"[{self.source_name}] Stored {len(all_records)} EIA records.")
        return CollectionResult(
            source_name=self.source_name,
            records=all_records,
            status="ok",
        )

    def _resolve_commodity(self, name: str) -> Optional[int]:
        try:
            with get_session() as session:
                commodity = session.scalar(
                    select(Commodity).where(
                        Commodity.name == name,
                        Commodity.type == "energy",
                    )
                )
                if not commodity:
                    commodity = Commodity(name=name, type="energy", base_currency="USD")
                    session.add(commodity)
                    session.flush()
                return commodity.id
        except Exception as exc:
            logger.warning(f"[{self.source_name}] Commodity resolve failed: {exc}")
            return None
