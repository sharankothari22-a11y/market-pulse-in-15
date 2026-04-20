"""
collectors/free/un_comtrade.py
────────────────────────────────
UN Comtrade + DGFT import/export data by HS code.
Source: UN Comtrade public API (free, 500 calls/hour)
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
# Key HS codes for India trade analysis
HS_CODES = {
    "27":   "Mineral fuels / crude oil",
    "72":   "Iron and steel",
    "29":   "Organic chemicals / pharma API",
    "84":   "Machinery / capital goods",
    "85":   "Electronics / semiconductors",
    "87":   "Vehicles / auto",
    "30":   "Pharmaceutical products",
}
INDIA_CODE = "356"

class UnComtradeCollector(BaseCollector):
    source_name = "un_comtrade"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        today = target_date or date.today()
        year  = today.year - 1  # Comtrade lags ~12 months
        records = []

        for hs_code, description in list(HS_CODES.items())[:4]:  # Rate limit
            try:
                params = {
                    "reporterCode": INDIA_CODE,
                    "period":       str(year),
                    "cmdCode":      hs_code,
                    "flowCode":     "X,M",  # Exports + Imports
                    "partnerCode":  "0",    # World
                }
                resp = requests.get(COMTRADE_URL, params=params, timeout=20,
                                    headers={"User-Agent": "research_platform/1.0"})
                if not resp.ok:
                    continue
                data = resp.json()
                rows = data.get("data", [])
                for row in rows[:5]:
                    flow      = row.get("flowDesc", "")
                    value_usd = row.get("primaryValue", 0)
                    if value_usd:
                        rec = MacroIndicator(
                            indicator=f"Comtrade/India/{hs_code}/{description}/{flow}",
                            date=date(year, 12, 31),
                            value=float(value_usd),
                            source=f"UNComtrade/IN/{year}",
                        )
                        records.append(rec)
            except Exception as e:
                logger.debug(f"[un_comtrade] HS {hs_code} failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for r in records:
                upsert_macro_indicator(s, r)

        logger.info(f"[un_comtrade] {len(records)} trade indicators stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
