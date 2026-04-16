"""
collectors/free/patents.py
───────────────────────────
Patent filings from IPO (India) and PatentsView (USPTO).
Critical for pharma and tech research.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

# PatentsView REST API — stable, free
PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"
# IPO India patent search
IPO_URL = "https://ipindiaservices.gov.in/PatentSearch/PatentSearch/ViewApplicationStatus"
PHARMA_TERMS = ["pharmaceutical", "drug", "compound", "molecule", "formulation", "API", "inhibitor"]
IT_TERMS     = ["software", "algorithm", "neural network", "machine learning", "semiconductor"]
HEADERS = {"User-Agent": "research_platform/1.0 (financial research)"}

class PatentsCollector(BaseCollector):
    source_name = "patents"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        today = target_date or date.today()
        start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        # Indian pharma / tech companies to watch
        companies = ["Sun Pharmaceutical", "Dr Reddy", "Cipla", "Infosys", "TCS", "Wipro"]
        records = []
        try:
            for company in companies[:3]:  # Rate limit
                params = {
                    "q": f'(assignee_organization:"{company}") AND (patent_date:[{start} TO {today}])',
                    "f": '["patent_id","patent_title","patent_date","assignee_organization"]',
                    "s": '[{"patent_date":"desc"}]',
                    "o": '{"per_page":5}',
                }
                resp = requests.get(PATENTSVIEW_URL, params=params, headers=HEADERS, timeout=15)
                if not resp.ok:
                    continue
                data = resp.json()
                patents = data.get("patents", [])
                for p in patents:
                    title = p.get("patent_title", "")
                    pid   = p.get("patent_id", "")
                    pdate = p.get("patent_date", str(today))
                    try:
                        pd = date.fromisoformat(pdate[:10])
                    except Exception:
                        pd = today
                    # Classify sector
                    sector_tag = "pharma" if any(t in title.lower() for t in PHARMA_TERMS) else \
                                 "it" if any(t in title.lower() for t in IT_TERMS) else "general"
                    ev = Event(
                        type="filing",
                        title=f"[Patent] {company}: {title}"[:1000],
                        date=pd,
                        source_url=f"https://patents.google.com/patent/US{pid}",
                        entity_type=f"patent_{sector_tag}",
                        impact_score=0.5,
                    )
                    records.append(ev)

            if not records:
                return None
            with get_session() as s:
                for ev in records:
                    upsert_event(s, ev)
            logger.info(f"[patents] {len(records)} patent filings stored")
            self._store_cache(records, target_date=target_date)
            return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
        except Exception as e:
            logger.warning(f"[patents] failed: {e}")
            return None
