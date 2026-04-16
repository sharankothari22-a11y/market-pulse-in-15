"""
collectors/free/beneficial_ownership.py
─────────────────────────────────────────
Hedge fund / PE beneficial ownership — shell company mapping.
Phase 3: No single clean source. This collector assembles from:
  - MCA charge holder data
  - SEBI SAST (bulk shareholding) disclosures
  - Panama/Pandora Papers ICIJ database (public)
  - OpenCorporates API (free tier)
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

ICIJ_OFFSHORE_API  = "https://offshoreleaks.icij.org/api/v1/search"
OPENCORP_API       = "https://api.opencorporates.com/v0.4/companies/search"
SEBI_SAST_URL      = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doSastAnonymous=yes"

class BeneficialOwnershipCollector(BaseCollector):
    source_name = "beneficial_ownership"
    fallback_chain = ["api", "scrape", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """
        ICIJ Offshore Leaks database — Panama Papers, Pandora Papers (public).
        Search for Indian entities.
        """
        today = target_date or date.today()
        records = []
        try:
            resp = requests.get(
                ICIJ_OFFSHORE_API,
                params={"q": "India", "c": "IND", "includes": "entities,officers"},
                timeout=15,
                headers={"User-Agent": "research_platform/1.0 financial research"}
            )
            if resp.ok:
                data = resp.json()
                nodes = data.get("nodes", [])
                for node in nodes[:20]:
                    name    = node.get("name", "")
                    source_ = node.get("sourceID", "")
                    country = node.get("countries", "")
                    if name:
                        ev = Event(
                            type="filing",
                            title=f"[ICIJ Offshore] {name} — Source: {source_} | Country: {country}"[:1000],
                            date=today,
                            source_url=f"https://offshoreleaks.icij.org/nodes/{node.get('id','')}",
                            entity_type="beneficial_ownership",
                            impact_score=0.7,
                        )
                        records.append(ev)
        except Exception as e:
            logger.debug(f"[beneficial_ownership] ICIJ API failed: {e}")

        # OpenCorporates — free tier (limited)
        try:
            resp = requests.get(
                OPENCORP_API,
                params={"q": "India", "jurisdiction_code": "in", "per_page": 10},
                timeout=15,
                headers={"User-Agent": "research_platform/1.0"}
            )
            if resp.ok:
                data = resp.json()
                companies = data.get("results", {}).get("companies", [])
                for item in companies[:5]:
                    c = item.get("company", {})
                    name = c.get("name", "")
                    if name:
                        ev = Event(
                            type="filing",
                            title=f"[OpenCorporates] {name} — {c.get('company_type','')} | {c.get('current_status','')}",
                            date=today,
                            source_url=c.get("opencorporates_url"),
                            entity_type="beneficial_ownership",
                            impact_score=0.3,
                        )
                        records.append(ev)
        except Exception as e:
            logger.debug(f"[beneficial_ownership] OpenCorporates failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for ev in records:
                upsert_event(s, ev)

        logger.info(f"[beneficial_ownership] {len(records)} ownership records stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
