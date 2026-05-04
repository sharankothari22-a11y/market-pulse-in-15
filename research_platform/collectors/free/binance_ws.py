"""
collectors/free/binance_ws.py
──────────────────────────────
Binance WebSocket — real-time crypto prices.
No API key needed for public streams.
Falls back to REST snapshot if WebSocket unavailable.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import json
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import CommodityPrice
from database.queries import upsert_commodity_price

# Top 10 crypto pairs by INR volume on Binance
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT", "DOTUSDT",
]

BINANCE_REST  = "https://api.binance.com/api/v3/ticker/price"
BINANCE_24HR  = "https://api.binance.com/api/v3/ticker/24hr"


class BinanceWsCollector(BaseCollector):
    """
    Real-time crypto via Binance REST snapshot (no key needed).
    WS stream is handled separately by binance_ws_stream.py for
    live dashboards — this collector runs on the scheduler for
    daily OHLCV snapshots.
    """
    source_name   = "binance_ws"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        today  = target_date or date.today()
        records = []
        try:
            # Batch request: all symbols in one call
            params = [("symbol", s) for s in SYMBOLS]
            resp = requests.get(BINANCE_24HR, timeout=15)
            resp.raise_for_status()
            tickers = {t["symbol"]: t for t in resp.json()}

            for sym in SYMBOLS:
                t = tickers.get(sym)
                if not t:
                    continue
                try:
                    rec = CommodityPrice(
                        date=today,
                        price=float(t["lastPrice"]),
                        currency="USD",
                        exchange="Binance",
                        extra_data={
                            "symbol":   sym,
                            "open":     float(t.get("openPrice", 0)),
                            "high":     float(t.get("highPrice", 0)),
                            "low":      float(t.get("lowPrice", 0)),
                            "volume":   float(t.get("volume", 0)),
                            "change_pct": float(t.get("priceChangePercent", 0)),
                        },
                    )
                    records.append(rec)
                except Exception as e:
                    logger.debug(f"[binance_ws] {sym} parse failed: {e}")

            if not records:
                return None
            with get_session() as s:
                for r in records:
                    upsert_commodity_price(s, r)
            logger.info(f"[binance_ws] {len(records)} crypto prices stored")
            self._store_cache(records, target_date=target_date)
            return CollectionResult(
                source_name=self.source_name, records=records, status="ok", method_used="api"
            )
        except Exception as e:
            logger.warning(f"[binance_ws] REST failed: {e}")
            return None
