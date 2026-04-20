"""
collectors/free/nse_fno.py
───────────────────────────
NSE F&O (Futures & Options) data — OI, PCR, IV.
Source: NSE official endpoints (unofficial but stable)
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

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}
NSE_OPTION_CHAIN_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
NSE_FNO_PARTICIPANTS = "https://www.nseindia.com/api/fii-dii-data"

class NseFnoCollector(BaseCollector):
    source_name = "nse_fno"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        session = requests.Session()
        try:
            # Need to establish session cookie first
            session.get("https://www.nseindia.com/", headers=NSE_HEADERS, timeout=10)
            resp = session.get(NSE_OPTION_CHAIN_URL, headers=NSE_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            records = []
            today = target_date or date.today()

            # Extract PCR (Put-Call Ratio) and total OI
            if "filtered" in data:
                filtered = data["filtered"]
                total_ce_oi = sum(d.get("CE", {}).get("openInterest", 0) for d in filtered.get("data", []) if d.get("CE"))
                total_pe_oi = sum(d.get("PE", {}).get("openInterest", 0) for d in filtered.get("data", []) if d.get("PE"))
                pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else None
                # Store as event for signal detection
                sentiment = "bearish" if pcr and pcr < 0.7 else "bullish" if pcr and pcr > 1.2 else "neutral"
                title = f"NIFTY F&O: PCR={pcr}, CE OI={total_ce_oi:,}, PE OI={total_pe_oi:,} — {sentiment}"
                ev = Event(type="regulatory", title=title[:1000], date=today,
                           entity_type="nse_fno", impact_score=0.4,
                           extra_data={"pcr": pcr, "ce_oi": total_ce_oi, "pe_oi": total_pe_oi})
                with get_session() as s:
                    upsert_event(s, ev)
                records.append(ev)
                logger.info(f"[nse_fno] NIFTY PCR={pcr} stored")

            self._store_cache(records, target_date=target_date)
            return CollectionResult(source_name=self.source_name, records=records,
                                    status="ok" if records else "partial", method_used="api")
        except Exception as e:
            logger.warning(f"[nse_fno] failed: {e}")
            return None
        finally:
            session.close()
