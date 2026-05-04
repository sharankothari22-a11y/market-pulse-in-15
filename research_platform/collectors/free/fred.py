"""
collectors/free/fred.py
───────────────────────
Fetches US and India macro indicators from FRED:
  - US Federal Funds Rate (FEDFUNDS)
  - US CPI (CPIAUCSL)
  - US Real GDP Growth (A191RL1Q225SBEA)
  - India Lending Rate (INDIRLTLT01STM)
  - DXY Dollar Index (DTWEXBGS)

Uses fredapi library. Falls back to direct FRED REST API if library fails.
Stores into macro_indicators table.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import FRED_API_KEY
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

FRED_REST_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Series → (display name, country ISO)
SERIES_MAP: dict[str, tuple[str, str]] = {
    "FEDFUNDS": ("US Federal Funds Rate", "US"),
    "CPIAUCSL": ("US CPI (All Urban Consumers)", "US"),
    "A191RL1Q225SBEA": ("US Real GDP Growth Rate", "US"),
    "INDIRLTLT01STM": ("India Long-Term Lending Rate", "IN"),
    "DTWEXBGS": ("DXY Broad Dollar Index", "US"),
}

# Country ISO → country_id placeholder (resolved at runtime from DB)
_COUNTRY_CACHE: dict[str, Optional[int]] = {}

TIMEOUT: int = 30


class FredCollector(BaseCollector):
    """FRED macro indicators collector."""

    source_name: str = "fred"
    fallback_chain: list[str] = ["api", "cache"]

    # ── Primary: fredapi library ──────────────────────────────────────────────

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not FRED_API_KEY:
            logger.warning(
                f"[{self.source_name}] FRED_API_KEY not set — "
                "trying unauthenticated REST fallback."
            )
            return self._fetch_via_rest(target_date)

        try:
            from fredapi import Fred  # type: ignore[import-untyped]
        except ImportError:
            logger.error(f"[{self.source_name}] fredapi not installed. Falling back to REST.")
            return self._fetch_via_rest(target_date)

        fred = Fred(api_key=FRED_API_KEY)
        all_records: list[MacroIndicator] = []

        # Fetch last 5 years by default; or just around target_date if provided
        start_date = (
            datetime(target_date.year - 1, 1, 1) if target_date
            else datetime.utcnow() - timedelta(days=5 * 365)
        )

        for series_id, (series_name, country_iso) in SERIES_MAP.items():
            try:
                series = fred.get_series(series_id, observation_start=start_date)
                country_id = self._resolve_country_id(country_iso)

                for obs_date, value in series.items():
                    if value != value:  # NaN check
                        continue
                    all_records.append(
                        MacroIndicator(
                            country_id=country_id,
                            indicator=series_id,
                            date=obs_date.date() if hasattr(obs_date, "date") else obs_date,
                            value=float(value),
                            source="FRED",
                        )
                    )
                logger.info(
                    f"[{self.source_name}] {series_id} ({series_name}): "
                    f"{len(series)} observations fetched."
                )
            except Exception as exc:
                logger.warning(
                    f"[{self.source_name}] Failed to fetch {series_id}: {exc}"
                )
                continue

        if not all_records:
            return None

        self._persist(all_records)
        self._store_cache(all_records, target_date=target_date)
        return CollectionResult(
            source_name=self.source_name,
            records=all_records,
            status="ok",
        )

    # ── Fallback: direct FRED REST API ────────────────────────────────────────

    def _fetch_via_rest(
        self, target_date: Optional[date] = None
    ) -> Optional[CollectionResult]:
        """Call FRED REST API directly without the fredapi library."""
        if not FRED_API_KEY:
            logger.error(
                f"[{self.source_name}] Cannot call FRED REST without FRED_API_KEY."
            )
            return None

        start_date = (
            date(target_date.year - 1, 1, 1) if target_date
            else date(datetime.utcnow().year - 5, 1, 1)
        )
        all_records: list[MacroIndicator] = []

        for series_id, (series_name, country_iso) in SERIES_MAP.items():
            params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "observation_start": start_date.isoformat(),
            }
            try:
                resp = requests.get(FRED_REST_BASE, params=params, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                observations = data.get("observations", [])
                country_id = self._resolve_country_id(country_iso)

                for obs in observations:
                    value_str = obs.get("value", ".")
                    if value_str == ".":  # FRED missing value sentinel
                        continue
                    all_records.append(
                        MacroIndicator(
                            country_id=country_id,
                            indicator=series_id,
                            date=date.fromisoformat(obs["date"]),
                            value=float(value_str),
                            source="FRED",
                        )
                    )
                logger.info(
                    f"[{self.source_name}] REST: {series_id}: {len(observations)} obs."
                )
            except Exception as exc:
                logger.warning(
                    f"[{self.source_name}] REST fetch failed for {series_id}: {exc}"
                )
                continue

        if not all_records:
            return None

        self._persist(all_records)
        self._store_cache(all_records, target_date=target_date)
        return CollectionResult(
            source_name=self.source_name,
            records=all_records,
            status="ok",
        )

    # ── Database ──────────────────────────────────────────────────────────────

    def _persist(self, records: list[MacroIndicator]) -> None:
        with get_session() as session:
            for r in records:
                upsert_macro_indicator(session, r)
        logger.info(
            f"[{self.source_name}] Persisted {len(records)} macro indicator records."
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _resolve_country_id(self, iso_code: str) -> Optional[int]:
        """Look up country_id from country table; cache in memory."""
        if iso_code in _COUNTRY_CACHE:
            return _COUNTRY_CACHE[iso_code]
        try:
            from sqlalchemy import select
            from database.models import Country
            with get_session() as session:
                result = session.scalar(
                    select(Country).where(Country.iso_code == iso_code)
                )
                cid = result.id if result else None
                _COUNTRY_CACHE[iso_code] = cid
                return cid
        except Exception:
            _COUNTRY_CACHE[iso_code] = None
            return None
