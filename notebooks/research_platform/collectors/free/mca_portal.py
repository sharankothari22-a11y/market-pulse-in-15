"""
collectors/free/mca_portal.py
──────────────────────────────
Fetches company master data and filing events from MCA21 portal.
MCA provides a public API for company master data.
Stores into company and event tables.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import MCA_PORTAL_BASE_URL
from database.connection import get_session
from database.models import Company, Event
from database.queries import get_or_create_company

TIMEOUT: int = 30
MCA_API_BASE = "https://www.mca.gov.in/MCAGovPortal/dca/company"


class McaPortalCollector(BaseCollector):
    source_name: str = "mca_portal"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """
        MCA21 v3 REST API for company master data.
        Endpoint: GET /MCAGovPortal/dca/company/companyMasterData
        Note: MCA API requires registration; this implements the public endpoint.
        """
        # MCA provides search by CIN prefix for bulk pulls
        # For demo: pull recently incorporated companies
        url = f"{MCA_API_BASE}/companyMasterData"
        params = {
            "companyCategory": "COMPANY LIMITED BY SHARES",
            "companySubCategory": "Non-govt company",
            "activeCompany": "Active",
        }
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            companies_raw = data.get("companyMasterData", data if isinstance(data, list) else [])
        except Exception as exc:
            logger.warning(f"[{self.source_name}] MCA API call failed: {exc}")
            return None

        records: list[Company] = []
        with get_session() as session:
            for item in companies_raw[:500]:  # cap per run
                try:
                    cin = item.get("CIN", item.get("cin", ""))
                    name = item.get("COMPANY_NAME", item.get("companyName", ""))
                    if not name:
                        continue
                    company = get_or_create_company(
                        session,
                        ticker=cin,  # CIN as identifier until ticker resolved
                        name=name,
                    )
                    company.cin = cin or None
                    company.country = "IN"
                    company.is_listed = False  # updated by NSE/BSE collector
                    records.append(company)
                except Exception as exc:
                    logger.debug(f"[{self.source_name}] Company parse error: {exc}")
                    continue

        self._store_cache(records, target_date=target_date)
        logger.info(f"[{self.source_name}] Processed {len(records)} MCA company records.")
        return CollectionResult(
            source_name=self.source_name,
            records=records,
            status="ok" if records else "partial",
        )
