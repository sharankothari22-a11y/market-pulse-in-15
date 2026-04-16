"""
collectors/free/imf.py
───────────────────────
IMF World Economic Outlook data.
Source: IMF Data API (free, no key needed)
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

IMF_API = "https://www.imf.org/external/datamapper/api/v1"
IMF_INDICATORS = {
    "NGDP_RPCH": "IMF/GDP Growth Rate",
    "PCPIPCH":   "IMF/CPI Inflation",
    "LUR":       "IMF/Unemployment Rate",
    "BCA_NGDPD": "IMF/Current Account % GDP",
}
COUNTRIES = {"IN": "India", "US": "United States", "CN": "China", "GB": "United Kingdom"}

class ImfCollector(BaseCollector):
    source_name = "imf"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        records = []
        today = target_date or date.today()
        current_year = today.year
        for imf_code, indicator_name in IMF_INDICATORS.items():
            try:
                url = f"{IMF_API}/{imf_code}"
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                values = data.get("values", {}).get(imf_code, {})
                for iso_code, country_name in COUNTRIES.items():
                    country_data = values.get(iso_code, {})
                    # Get latest available year
                    for year in [str(current_year), str(current_year-1), str(current_year-2)]:
                        if year in country_data and country_data[year] is not None:
                            try:
                                rec = MacroIndicator(
                                    indicator=f"{indicator_name}/{iso_code}",
                                    date=date(int(year), 12, 31),
                                    value=float(country_data[year]),
                                    source=f"IMF/{iso_code}",
                                )
                                records.append(rec)
                            except (ValueError, TypeError):
                                pass
                            break
            except Exception as e:
                logger.debug(f"[imf] {imf_code} failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_macro_indicator(s, r)
        logger.info(f"[imf] {len(records)} IMF indicators stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
