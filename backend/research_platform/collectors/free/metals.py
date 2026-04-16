"""
collectors/free/metals.py
─────────────────────────
Gold, Silver, Platinum, Steel prices.
Sources: metals-api (free tier) → Yahoo Finance fallback → cache
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import CommodityPrice
from database.queries import upsert_commodity_price

METALS = {
    "XAU": {"name": "Gold",     "type": "metal", "currency": "USD"},
    "XAG": {"name": "Silver",   "type": "metal", "currency": "USD"},
    "XPT": {"name": "Platinum", "type": "metal", "currency": "USD"},
}
YAHOO_TICKERS = {
    "Gold":     "GC=F",
    "Silver":   "SI=F",
    "Platinum": "PL=F",
    "Steel":    "STEEL.L",
}

class MetalsCollector(BaseCollector):
    source_name = "metals"
    fallback_chain = ["api", "scrape", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Try Yahoo Finance for metal prices (free, no key needed)."""
        try:
            import yfinance as yf
        except ImportError:
            return None
        records = []
        today = target_date or date.today()
        for name, ticker in YAHOO_TICKERS.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if hist.empty:
                    continue
                price = float(hist["Close"].iloc[-1])
                rec = CommodityPrice(
                    date=today, price=price, currency="USD", exchange="COMEX",
                    extra_data={"name": name, "symbol": ticker, "source": "yahoo"}
                )
                records.append(rec)
            except Exception as e:
                logger.warning(f"[metals] {name} failed: {e}")
        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_commodity_price(s, r)
        self._store_cache(records, target_date=target_date)
        logger.info(f"[metals] {len(records)} prices stored")
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape kitco.com for metal spot prices as fallback."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get("https://www.kitco.com/market/", timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for tag in soup.select(".price-table tr"):
                cells = tag.find_all("td")
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    price_str = cells[1].get_text(strip=True).replace(",", "").replace("$", "")
                    if name in ("Gold", "Silver", "Platinum") and price_str:
                        try:
                            records.append(CommodityPrice(
                                date=today, price=float(price_str),
                                currency="USD", exchange="SPOT",
                                extra_data={"name": name, "source": "kitco"}
                            ))
                        except ValueError:
                            pass
            if not records:
                return None
            with get_session() as s:
                for r in records:
                    upsert_commodity_price(s, r)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[metals] scrape failed: {e}")
            return None
