"""
collectors/paid/refinitiv.py
──────────────────────────────
Refinitiv Eikon / LSEG data — institutional-grade market data.
Requires REFINITIV_API_KEY in .env.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from config.settings import REFINITIV_API_KEY
from database.connection import get_session
from database.models import MacroIndicator, PriceHistory
from database.queries import upsert_macro_indicator, upsert_price

class RefinitivCollector(BaseCollector):
    source_name = "refinitiv"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not REFINITIV_API_KEY:
            logger.info("[refinitiv] REFINITIV_API_KEY not set — add key to .env to enable")
            return None

        today = target_date or date.today()
        records = []
        headers = {"Authorization": f"Bearer {REFINITIV_API_KEY}", "Accept": "application/json"}

        try:
            # Refinitiv Data Platform API
            resp = requests.post(
                "https://api.refinitiv.com/data/historical-pricing/v1/views/summaries",
                headers={**headers, "Content-Type": "application/json"},
                json={"universe": ["NIFTY50=NS","SENSEX=BOM"], "fields": ["TRDPRC_1","NETCHNG_1","PCTCHNG"]},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("data", []):
                ticker = item.get("universe", "")
                close  = item.get("TRDPRC_1")
                if ticker and close:
                    rec = PriceHistory(
                        ticker=ticker.split("=")[0],
                        date=today,
                        close=float(close),
                        exchange="NSE",
                    )
                    records.append(rec)
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("[refinitiv] API key invalid")
            else:
                logger.warning(f"[refinitiv] API error: {e}")
        except Exception as e:
            logger.warning(f"[refinitiv] Failed: {e}")

        if not records:
            return None

        with get_session() as s:
            for r in records:
                if isinstance(r, PriceHistory):
                    upsert_price(s, r)
                else:
                    upsert_macro_indicator(s, r)

        logger.info(f"[refinitiv] {len(records)} records stored")
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
