"""
collectors/free/screener.py
────────────────────────────
Screener.in — peer comparison, financial ratios, sector data.
Source: Screener.in JSON API (unofficial but stable)
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Company, MacroIndicator
from database.queries import upsert_macro_indicator

SCREENER_BASE = "https://www.screener.in"
SCREENER_COMPANY_URL = "https://www.screener.in/api/company/{ticker}/?format=json"

class ScreenerCollector(BaseCollector):
    source_name = "screener"
    fallback_chain = ["api", "scrape", "cache"]

    # Top 50 Nifty50 tickers to collect
    TICKERS = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
        "AXISBANK", "LT", "BAJFINANCE", "ASIANPAINT", "MARUTI",
        "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND",
        "HCLTECH", "POWERGRID", "NTPC", "TECHM", "BAJAJFINSV",
    ]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Referer": "https://www.screener.in",
            "Accept": "application/json",
        }
        records = []
        today = target_date or date.today()
        session = requests.Session()
        # Establish session
        try:
            session.get(SCREENER_BASE, headers=headers, timeout=10)
        except Exception:
            pass

        for ticker in self.TICKERS[:10]:  # Rate-limit: 10 per run
            try:
                url = SCREENER_COMPANY_URL.format(ticker=ticker)
                resp = session.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                # Extract key ratios
                ratios = data.get("ratios", {})
                for metric_name, value in ratios.items():
                    if value is None:
                        continue
                    try:
                        rec = MacroIndicator(
                            indicator=f"SCREENER/{ticker}/{metric_name}",
                            date=today,
                            value=float(str(value).replace(",", "").replace("%", "")),
                            source=f"Screener/{ticker}",
                        )
                        records.append(rec)
                    except (ValueError, TypeError):
                        continue
            except Exception as e:
                logger.debug(f"[screener] {ticker} failed: {e}")
                continue

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_macro_indicator(s, r)
        logger.info(f"[screener] {len(records)} ratios stored for {len(self.TICKERS[:10])} tickers")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape Screener.in HTML for ratios when JSON API fails."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            records = []
            today = target_date or date.today()
            for ticker in self.TICKERS[:5]:
                try:
                    resp = httpx.get(f"{SCREENER_BASE}/company/{ticker}/consolidated/",
                                     timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(resp.text, "lxml")
                    for li in soup.select("#top-ratios li"):
                        name_el = li.find("span", class_="name")
                        val_el  = li.find("span", class_="value") or li.find("span", class_="number")
                        if name_el and val_el:
                            name = name_el.get_text(strip=True)
                            val_str = val_el.get_text(strip=True).replace(",","").replace("%","").replace("₹","")
                            try:
                                rec = MacroIndicator(
                                    indicator=f"SCREENER/{ticker}/{name}",
                                    date=today, value=float(val_str),
                                    source=f"Screener/{ticker}"
                                )
                                records.append(rec)
                            except (ValueError, TypeError):
                                pass
                except Exception:
                    continue
            if not records:
                return None
            with get_session() as s:
                for r in records:
                    upsert_macro_indicator(s, r)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[screener] scrape failed: {e}")
            return None
