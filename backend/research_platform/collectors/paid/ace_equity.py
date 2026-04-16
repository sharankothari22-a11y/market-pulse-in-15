"""
collectors/paid/ace_equity.py
───────────────────────────────
ACE Equity / ProwessIQ — Indian institutional financial database.
Requires ACE_EQUITY_API_KEY in .env.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from config.settings import ACE_EQUITY_API_KEY
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

class AceEquityCollector(BaseCollector):
    source_name = "ace_equity"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not ACE_EQUITY_API_KEY:
            logger.info("[ace_equity] ACE_EQUITY_API_KEY not set — add key to .env to enable")
            return None

        today = target_date or date.today()
        try:
            resp = requests.get(
                "https://api.aceequity.com/v1/financials",
                headers={"Authorization": f"Bearer {ACE_EQUITY_API_KEY}"},
                params={"symbol": "RELIANCE", "type": "quarterly"},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            records = []
            for item in data.get("financials", [])[:10]:
                rec = MacroIndicator(
                    indicator=f"ACE/{item.get('symbol','')}/{item.get('metric','')}",
                    date=today,
                    value=item.get("value"),
                    source="ACEEquity",
                )
                records.append(rec)
            if records:
                with get_session() as s:
                    for r in records:
                        upsert_macro_indicator(s, r)
                return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("[ace_equity] API key invalid")
            else:
                logger.warning(f"[ace_equity] Error: {e}")
        except Exception as e:
            logger.warning(f"[ace_equity] Failed: {e}")
        return None
