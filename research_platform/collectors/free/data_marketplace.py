"""
collectors/free/data_marketplace.py
─────────────────────────────────────
Data marketplace integrations — free tiers / unofficial wrappers.

Covered:
  Quandl / Nasdaq Data Link — macro + commodity datasets (free tier: 50 API calls/day)
  yfinance (unofficial Yahoo Finance wrapper) — global prices + financials
  STOOQ — free historical OHLCV (no API key needed)
  Kite Connect unofficial data — NSE tick data via community wrappers

GitHub unofficial wrapper pattern:
  Search "<site name> python api" on GitHub.
  Many sites have community-maintained wrappers that reverse-engineer
  the backend. These are often more reliable than scraping HTML.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import MacroIndicator, CommodityPrice
from database.queries import upsert_macro_indicator, upsert_commodity_price

# ── Quandl / Nasdaq Data Link ─────────────────────────────────────────────────
QUANDL_BASE = "https://data.nasdaq.com/api/v3/datasets"


def fetch_quandl(dataset_code: str, api_key: str = "",
                 rows: int = 252) -> list[dict]:
    """
    Fetch a Quandl/Nasdaq Data Link time series.
    Free tier: WIKI datasets + many premium datasets with 50 calls/day.
    api_key: optional — many datasets are free without a key.

    Common free datasets:
        LBMA/GOLD  — gold price in USD
        LBMA/SILVER — silver price in USD
        EIA/PET_RWTC_D — WTI crude spot price
        FRED/GDP   — US GDP
        CHRIS/CME_GC1 — COMEX gold futures
    """
    parts = dataset_code.split("/", 1)
    if len(parts) != 2:
        logger.error(f"[quandl] Invalid dataset code: {dataset_code}")
        return []
    db_code, ds_code = parts
    url = f"{QUANDL_BASE}/{db_code}/{ds_code}.json"
    params: dict = {"rows": rows}
    if api_key:
        params["api_key"] = api_key
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json().get("dataset", {})
        col_names = [c.lower().replace(" ", "_") for c in data.get("column_names", [])]
        rows_data  = data.get("data", [])
        return [dict(zip(col_names, row)) for row in rows_data]
    except Exception as e:
        logger.warning(f"[quandl] {dataset_code} failed: {e}")
        return []


def fetch_stooq(ticker: str, days: int = 30) -> list[dict]:
    """
    STOOQ — free OHLCV for global stocks (no API key, no rate limit docs).
    Works for NSE tickers with .NS suffix, US tickers, indices.
    """
    end   = date.today()
    start = end - timedelta(days=days)
    url   = (
        f"https://stooq.com/q/d/l/?s={ticker.lower()}"
        f"&d1={start.strftime('%Y%m%d')}&d2={end.strftime('%Y%m%d')}&i=d"
    )
    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            return []
        headers = [h.lower() for h in lines[0].split(",")]
        result  = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) == len(headers):
                result.append(dict(zip(headers, parts)))
        return result
    except Exception as e:
        logger.debug(f"[stooq] {ticker} failed: {e}")
        return []


class DataMarketplaceCollector(BaseCollector):
    """
    Pulls select free datasets from Quandl (Baltic Dry supplement, gold fix).
    """
    source_name    = "data_marketplace"
    fallback_chain = ["api", "cache"]

    # Free datasets — no API key required
    FREE_DATASETS = [
        ("LBMA/GOLD",    "LBMA_Gold_USD",      "CommodityPrice"),
        ("LBMA/SILVER",  "LBMA_Silver_USD",     "CommodityPrice"),
    ]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        import os
        api_key = os.getenv("QUANDL_API_KEY", "")
        today   = target_date or date.today()
        records = []

        for dataset_code, indicator_name, record_type in self.FREE_DATASETS:
            rows = fetch_quandl(dataset_code, api_key=api_key, rows=5)
            for row in rows:
                try:
                    row_date = date.fromisoformat(str(row.get("date", today)))
                    if record_type == "CommodityPrice":
                        price_val = float(
                            row.get("usd_am") or row.get("usd_pm") or
                            row.get("value") or row.get("price") or 0
                        )
                        if price_val <= 0:
                            continue
                        rec = CommodityPrice(
                            date=row_date,
                            price=price_val,
                            currency="USD",
                            exchange="Quandl/LBMA",
                            extra_data={"dataset": dataset_code, "row": row},
                        )
                        records.append(rec)
                except Exception as e:
                    logger.debug(f"[data_marketplace] {dataset_code} row parse failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_commodity_price(s, r)
        logger.info(f"[data_marketplace] {len(records)} records from Quandl")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(
            source_name=self.source_name, records=records, status="ok", method_used="api"
        )
