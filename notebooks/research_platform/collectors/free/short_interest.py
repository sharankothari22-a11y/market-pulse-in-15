"""
collectors/free/short_interest.py
───────────────────────────────────
Short interest data — who bets against which stock.
Source: NSE Securities Lending & Borrowing (SLB) data + F&O Put/Call ratio
Phase 3: True short interest not cleanly available in India.
This collector uses F&O data as a proxy.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import MacroIndicator, Event
from database.queries import upsert_macro_indicator, upsert_event

NSE_SLB_URL = "https://www.nseindia.com/api/slbm-summary-data"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Referer": "https://www.nseindia.com/",
    "Accept": "application/json",
}

class ShortInterestCollector(BaseCollector):
    source_name = "short_interest"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """
        NSE Securities Lending & Borrowing (SLB) as short interest proxy.
        True short selling data in India is limited — SLB + high put OI are best proxies.
        """
        today = target_date or date.today()
        records = []
        session = requests.Session()
        try:
            # Establish NSE session cookie
            session.get("https://www.nseindia.com/", headers=NSE_HEADERS, timeout=10)
            resp = session.get(NSE_SLB_URL, headers=NSE_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            for item in items[:30]:
                symbol     = item.get("symbol", "")
                total_fees = item.get("totalFees", 0)
                total_qty  = item.get("totalQty", 0)
                if symbol and total_qty:
                    rec = MacroIndicator(
                        indicator=f"ShortInterest/{symbol}/SLBQty",
                        date=today,
                        value=float(total_qty),
                        source="NSE/SLB",
                    )
                    records.append(rec)
                    # High SLB = bearish signal
                    if float(total_qty) > 100000:
                        ev = Event(
                            type="regulatory",
                            title=f"High SLB activity: {symbol} — {total_qty:,} shares borrowed",
                            date=today,
                            entity_type="short_interest",
                            impact_score=0.5,
                        )
                        records.append(ev)
        except Exception as e:
            logger.warning(f"[short_interest] NSE SLB failed: {e}")
        finally:
            session.close()

        if not records:
            logger.info("[short_interest] No SLB data — market may be closed or data unavailable")
            return None

        with get_session() as s:
            for r in records:
                if isinstance(r, MacroIndicator):
                    upsert_macro_indicator(s, r)
                elif isinstance(r, Event):
                    upsert_event(s, r)

        logger.info(f"[short_interest] {len(records)} short interest records stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
