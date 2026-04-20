"""
collectors/free/insider_trades.py
───────────────────────────────────
Insider trading / bulk deals / block deals from NSE & BSE.
Source: NSE bulk deal CSV → BSE bulk deal CSV → scrape
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import io
import requests
import pandas as pd
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

NSE_BULK_URL = "https://archives.nseindia.com/content/equities/bulk.csv"
BSE_BULK_URL = "https://www.bseindia.com/markets/equity/EQReports/bulk_deals.aspx"

class InsiderTradesCollector(BaseCollector):
    source_name = "insider_trades"
    fallback_chain = ["api", "scrape", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        today = target_date or date.today()
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            resp = requests.get(NSE_BULK_URL, headers=headers, timeout=15)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            if df.empty:
                return None
            records = []
            with get_session() as s:
                for _, row in df.head(50).iterrows():
                    try:
                        ticker = str(row.get("Symbol", row.get("SYMBOL", ""))).strip().upper()
                        client = str(row.get("Client Name", row.get("CLIENT NAME", "Unknown"))).strip()
                        buy_sell = str(row.get("Buy/Sell", row.get("BUY/SELL", ""))).strip()
                        qty = row.get("Quantity Traded", row.get("QUANTITY", 0))
                        price = row.get("Trade Price / Wght. Avg. Price", row.get("PRICE", 0))
                        value_cr = round(float(qty or 0) * float(price or 0) / 1e7, 2)
                        title = f"Bulk Deal: {ticker} — {client} {buy_sell} {qty:,} @ ₹{price} (₹{value_cr}Cr)"
                        ev = Event(
                            type="filing",
                            title=title[:1000],
                            date=today,
                            entity_type="insider_trade",
                            impact_score=min(value_cr / 100, 1.0),
                            source_url=NSE_BULK_URL,
                        )
                        upsert_event(s, ev)
                        records.append(ev)
                    except Exception:
                        continue
            logger.info(f"[insider_trades] {len(records)} bulk deals stored")
            self._store_cache(records, target_date=target_date)
            return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
        except Exception as e:
            logger.warning(f"[insider_trades] NSE bulk CSV failed: {e}")
            return None

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """BSE bulk deals page as fallback."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get(BSE_BULK_URL, timeout=20, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            table = soup.find("table", {"id": "ContentPlaceHolder1_GridViewbulk"})
            if not table:
                return None
            with get_session() as s:
                for row in table.find_all("tr")[1:21]:
                    cells = [c.get_text(strip=True) for c in row.find_all("td")]
                    if len(cells) >= 5:
                        title = f"BSE Bulk Deal: {cells[1]} — {cells[2]} {cells[3]} @ {cells[4]}"
                        ev = Event(type="filing", title=title[:1000], date=today,
                                   entity_type="insider_trade", source_url=BSE_BULK_URL)
                        upsert_event(s, ev)
                        records.append(ev)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[insider_trades] BSE scrape failed: {e}")
            return None
