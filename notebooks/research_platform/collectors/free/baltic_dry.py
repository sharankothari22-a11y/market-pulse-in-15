"""
collectors/free/baltic_dry.py
──────────────────────────────
Baltic Dry Index — leading global trade indicator.
Source: Yahoo Finance ^BDI → Quandl/FRED fallback
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

class BalticDryCollector(BaseCollector):
    source_name = "baltic_dry"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            import yfinance as yf
            ticker = yf.Ticker("^BDI")
            hist = ticker.history(period="30d")
            if hist.empty:
                logger.warning("[baltic_dry] ^BDI returned empty — trying BDI=F")
                ticker = yf.Ticker("BDI=F")
                hist = ticker.history(period="30d")
            if hist.empty:
                return None
            records = []
            with get_session() as s:
                for idx_date, row in hist.iterrows():
                    d = idx_date.date() if hasattr(idx_date, 'date') else idx_date
                    rec = MacroIndicator(
                        indicator="Baltic Dry Index",
                        date=d,
                        value=round(float(row["Close"]), 2),
                        source="YahooFinance/BDI"
                    )
                    upsert_macro_indicator(s, rec)
                    records.append(rec)
            logger.info(f"[baltic_dry] {len(records)} BDI values stored")
            self._store_cache(records, target_date=target_date)
            return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
        except Exception as e:
            logger.warning(f"[baltic_dry] failed: {e}")
            return None
