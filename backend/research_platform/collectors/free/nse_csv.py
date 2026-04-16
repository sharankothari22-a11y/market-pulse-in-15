"""
collectors/free/nse_csv.py
──────────────────────────
Downloads NSE daily Bhavcopy (equity OHLCV) and FII/DII flows.
Parses both into price_history and fii_dii_flows tables.
Fallback: BSE equivalent if NSE download fails.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime
from typing import Optional

import pandas as pd
import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import BSE_BHAVCOPY_BASE_URL, NSE_BHAVCOPY_BASE_URL, NSE_FIIDII_BASE_URL
from database.connection import get_session
from database.models import FiiDiiFlow, PriceHistory
from database.queries import upsert_fii_dii_flow, upsert_price

# Request headers mimicking a browser — NSE blocks bare urllib
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

TIMEOUT: int = 30


class NseCsvCollector(BaseCollector):
    """NSE daily Bhavcopy + FII/DII flows collector."""

    source_name: str = "nse_csv"
    fallback_chain: list[str] = ["api", "scrape", "cache"]

    # ── Main API path (NSE) ───────────────────────────────────────────────────

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        run_date = target_date or date.today()
        records: list = []

        prices = self._fetch_nse_bhavcopy(run_date)
        flows = self._fetch_nse_fiidii(run_date)

        if prices is None and flows is None:
            return None  # trigger fallback

        if prices:
            records.extend(prices)
        if flows:
            records.extend(flows)

        self._persist(prices or [], flows or [])
        self._store_cache(records, target_date=run_date)

        return CollectionResult(
            source_name=self.source_name,
            records=records,
            status="ok" if records else "partial",
        )

    # ── Fallback: BSE Bhavcopy ────────────────────────────────────────────────

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """BSE Bhavcopy as fallback when NSE is unavailable."""
        run_date = target_date or date.today()
        logger.info(f"[{self.source_name}] Trying BSE Bhavcopy fallback for {run_date}")
        prices = self._fetch_bse_bhavcopy(run_date)
        if not prices:
            return None

        self._persist(prices, [])
        self._store_cache(prices, target_date=run_date)
        return CollectionResult(
            source_name=self.source_name,
            records=prices,
            status="partial",  # no FII/DII from BSE path
        )

    # ── NSE Bhavcopy fetch ────────────────────────────────────────────────────

    def _fetch_nse_bhavcopy(self, run_date: date) -> Optional[list[PriceHistory]]:
        """Download and parse NSE Bhavcopy CSV (zipped)."""
        date_str = run_date.strftime("%d%m%Y")
        url = f"{NSE_BHAVCOPY_BASE_URL}/{run_date.year}/{run_date.strftime('%b').upper()}/cm{date_str}bhav.csv.zip"
        logger.info(f"[{self.source_name}] Fetching NSE Bhavcopy: {url}")

        try:
            resp = requests.get(url, headers=NSE_HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(f"[{self.source_name}] NSE Bhavcopy download failed: {exc}")
            return None

        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csv_name = zf.namelist()[0]
                with zf.open(csv_name) as f:
                    df = pd.read_csv(f)
        except Exception as exc:
            logger.warning(f"[{self.source_name}] NSE Bhavcopy parse failed: {exc}")
            return None

        return self._parse_nse_bhavcopy(df, run_date)

    def _parse_nse_bhavcopy(self, df: pd.DataFrame, run_date: date) -> list[PriceHistory]:
        """Convert NSE Bhavcopy dataframe to PriceHistory records."""
        records: list[PriceHistory] = []
        # NSE columns: SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, LAST, PREVCLOSE, TOTTRDQTY, ...
        df.columns = [c.strip() for c in df.columns]

        # Only EQ series (ordinary equity)
        eq_df = df[df.get("SERIES", df.get("Series", pd.Series(dtype=str))).str.strip() == "EQ"]

        for _, row in eq_df.iterrows():
            try:
                record = PriceHistory(
                    ticker=str(row.get("SYMBOL", row.get("Symbol", ""))).strip(),
                    date=run_date,
                    open=self._safe_float(row.get("OPEN", row.get("Open"))),
                    high=self._safe_float(row.get("HIGH", row.get("High"))),
                    low=self._safe_float(row.get("LOW", row.get("Low"))),
                    close=self._safe_float(row.get("CLOSE", row.get("Close"))) or 0,
                    volume=self._safe_float(row.get("TOTTRDQTY", row.get("TotalTradedQuantity"))),
                    exchange="NSE",
                )
                records.append(record)
            except Exception as exc:
                logger.debug(f"[{self.source_name}] Row skip: {exc}")
                continue

        logger.info(f"[{self.source_name}] Parsed {len(records)} NSE equity prices.")
        return records

    # ── NSE FII/DII ───────────────────────────────────────────────────────────

    def _fetch_nse_fiidii(self, run_date: date) -> Optional[list[FiiDiiFlow]]:
        """Download and parse NSE FII/DII daily data."""
        date_str = run_date.strftime("%d%m%Y")
        url = f"{NSE_FIIDII_BASE_URL}/fao_participant_oi_{date_str}.csv"
        logger.info(f"[{self.source_name}] Fetching NSE FII/DII: {url}")

        try:
            resp = requests.get(url, headers=NSE_HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
        except Exception as exc:
            logger.warning(f"[{self.source_name}] NSE FII/DII download failed: {exc}")
            # Try the cash-market FII/DII file as secondary option
            return self._fetch_nse_fiidii_cash(run_date)

        return self._parse_fiidii(df, run_date)

    def _fetch_nse_fiidii_cash(self, run_date: date) -> Optional[list[FiiDiiFlow]]:
        """Alternate NSE endpoint for FII/DII cash market data."""
        date_str = run_date.strftime("%d-%b-%Y")
        url = f"https://www.nseindia.com/api/fiidiiTradeReact?date={date_str}"
        try:
            resp = requests.get(url, headers=NSE_HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(f"[{self.source_name}] NSE FII/DII cash API failed: {exc}")
            return None

        records: list[FiiDiiFlow] = []
        for item in data:
            try:
                category = item.get("category", "").upper()
                if category not in ("FII", "DII"):
                    continue
                records.append(
                    FiiDiiFlow(
                        date=run_date,
                        category=category,
                        buy_value=self._safe_float(item.get("buyValue")),
                        sell_value=self._safe_float(item.get("sellValue")),
                        net_value=self._safe_float(item.get("netValue")),
                        exchange="NSE",
                    )
                )
            except Exception:
                continue
        return records or None

    def _parse_fiidii(self, df: pd.DataFrame, run_date: date) -> list[FiiDiiFlow]:
        df.columns = [c.strip() for c in df.columns]
        records: list[FiiDiiFlow] = []
        for _, row in df.iterrows():
            try:
                category = str(row.get("Client Type", row.get("Category", ""))).strip().upper()
                if "FII" in category:
                    cat = "FII"
                elif "DII" in category:
                    cat = "DII"
                else:
                    continue

                buy = self._safe_float(row.get("Buy Value", row.get("BuyValue")))
                sell = self._safe_float(row.get("Sell Value", row.get("SellValue")))
                net = (buy or 0) - (sell or 0) if buy is not None or sell is not None else None

                records.append(
                    FiiDiiFlow(
                        date=run_date,
                        category=cat,
                        buy_value=buy,
                        sell_value=sell,
                        net_value=net,
                        exchange="NSE",
                    )
                )
            except Exception:
                continue
        logger.info(f"[{self.source_name}] Parsed {len(records)} FII/DII flow records.")
        return records

    # ── BSE fallback ──────────────────────────────────────────────────────────

    def _fetch_bse_bhavcopy(self, run_date: date) -> Optional[list[PriceHistory]]:
        """Download BSE Bhavcopy CSV as fallback."""
        date_str = run_date.strftime("%d%m%y")
        url = f"{BSE_BHAVCOPY_BASE_URL}/EQ{date_str}_CSV.ZIP"
        logger.info(f"[{self.source_name}] Fetching BSE Bhavcopy: {url}")

        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csv_name = zf.namelist()[0]
                with zf.open(csv_name) as f:
                    df = pd.read_csv(f)
        except Exception as exc:
            logger.warning(f"[{self.source_name}] BSE Bhavcopy download failed: {exc}")
            return None

        df.columns = [c.strip() for c in df.columns]
        records: list[PriceHistory] = []
        for _, row in df.iterrows():
            try:
                records.append(
                    PriceHistory(
                        ticker=str(row.get("SC_CODE", "")).strip(),
                        date=run_date,
                        open=self._safe_float(row.get("OPEN")),
                        high=self._safe_float(row.get("HIGH")),
                        low=self._safe_float(row.get("LOW")),
                        close=self._safe_float(row.get("CLOSE")) or 0,
                        volume=self._safe_float(row.get("NO_OF_SHRS")),
                        exchange="BSE",
                    )
                )
            except Exception:
                continue

        logger.info(f"[{self.source_name}] Parsed {len(records)} BSE equity prices.")
        return records

    # ── Database persist ──────────────────────────────────────────────────────

    def _persist(
        self,
        prices: list[PriceHistory],
        flows: list[FiiDiiFlow],
    ) -> None:
        with get_session() as session:
            for p in prices:
                upsert_price(session, p)
            for f in flows:
                upsert_fii_dii_flow(session, f)
        logger.info(
            f"[{self.source_name}] Persisted {len(prices)} prices, {len(flows)} FII/DII records."
        )

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_float(val: object) -> Optional[float]:
        try:
            return float(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
