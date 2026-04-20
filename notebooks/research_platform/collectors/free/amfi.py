"""
collectors/free/amfi.py
───────────────────────
Downloads AMFI daily NAV file for all mutual fund schemes.
URL: https://www.amfiindia.com/spages/NAVAll.txt
Format: semicolon-delimited text.

BUG FIX: Previously had a TODO comment and never wrote to the DB.
Now persists to fund_nav table using upsert_fund_nav.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import AMFI_NAV_URL
from database.connection import get_session
from database.models import FundNav
from database.queries import upsert_fund_nav
from processing.normalizer import normalise_date

TIMEOUT: int = 30


class AmfiCollector(BaseCollector):
    source_name: str = "amfi"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            resp = requests.get(AMFI_NAV_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
        except Exception as exc:
            logger.warning(f"[{self.source_name}] AMFI NAV download failed: {exc}")
            return None

        records: list[FundNav] = []
        skipped = 0

        for line in lines:
            line = line.strip()
            # Skip header lines and blank lines
            if not line or line.startswith("Scheme Code") or ";" not in line:
                continue
            parts = line.split(";")
            if len(parts) < 6:
                continue
            try:
                scheme_code = parts[0].strip()
                isin_payout = parts[1].strip() or None
                isin_reinvest = parts[2].strip() or None
                scheme_name = parts[3].strip()
                nav_str = parts[4].strip()
                date_str = parts[5].strip()

                if not scheme_code or not scheme_name:
                    skipped += 1
                    continue

                nav_val = float(nav_str)
                if nav_val <= 0:
                    skipped += 1
                    continue

                nav_date = normalise_date(date_str) or (target_date or date.today())

                records.append(FundNav(
                    scheme_code=scheme_code,
                    scheme_name=scheme_name[:500],
                    isin_div_payout=isin_payout,
                    isin_div_reinvest=isin_reinvest,
                    nav=nav_val,
                    date=nav_date,
                ))
            except (ValueError, IndexError):
                skipped += 1
                continue

        if not records:
            logger.warning(f"[{self.source_name}] No valid NAV records parsed.")
            return None

        # Persist to DB
        persisted = 0
        with get_session() as session:
            for r in records:
                upsert_fund_nav(session, r)
                persisted += 1

        logger.info(
            f"[{self.source_name}] Parsed {len(records)} NAVs, "
            f"persisted {persisted}, skipped {skipped}."
        )

        # Cache a lightweight summary (not full ORM objects)
        cache_data = [
            {"scheme_code": r.scheme_code, "scheme_name": r.scheme_name,
             "nav": float(r.nav), "date": str(r.date)}
            for r in records[:500]  # cap cache size
        ]
        self._store_cache(cache_data, target_date=target_date)

        return CollectionResult(
            source_name=self.source_name,
            records=records,
            status="ok",
        )
