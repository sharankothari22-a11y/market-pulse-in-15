"""
collectors/free/earnings_transcripts.py
─────────────────────────────────────────
Earnings call transcripts from company IR pages + Finnhub.
Source: Finnhub transcripts API → company IR page scrape → cache
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from config.settings import FINNHUB_API_KEY
from database.connection import get_session
from database.models import EarningsTranscript
from database.queries import upsert_earnings_transcript

# NSE tickers → Finnhub symbols mapping
TICKER_MAP = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS",
    "INFY": "INFY",            "ICICIBANK": "ICICIBANK.NS", "WIPRO": "WIPRO.NS",
    "SBIN": "SBIN.NS",         "BAJFINANCE": "BAJFINANCE.NS",
    "SUNPHARMA": "SUNPHARMA.NS", "DRREDDY": "RDY",
}
FINNHUB_TRANSCRIPTS = "https://finnhub.io/api/v1/stock/transcripts"
FINNHUB_CALENDAR    = "https://finnhub.io/api/v1/calendar/earnings"

class EarningsTranscriptsCollector(BaseCollector):
    source_name = "earnings_transcripts"
    fallback_chain = ["api", "scrape", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not FINNHUB_API_KEY:
            logger.warning("[earnings_transcripts] FINNHUB_API_KEY not set — skipping API")
            return None

        today = target_date or date.today()
        start = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        records = []

        for nse_ticker, finnhub_symbol in list(TICKER_MAP.items())[:5]:
            try:
                # Get transcript list for the ticker
                resp = requests.get(
                    FINNHUB_TRANSCRIPTS,
                    params={"symbol": finnhub_symbol, "token": FINNHUB_API_KEY},
                    timeout=15,
                )
                if not resp.ok:
                    continue
                data = resp.json()
                transcripts = data.get("transcripts", [])
                for t in transcripts[:2]:
                    transcript_id = t.get("id")
                    if not transcript_id:
                        continue
                    # Fetch full transcript
                    full_resp = requests.get(
                        FINNHUB_TRANSCRIPTS,
                        params={"id": transcript_id, "token": FINNHUB_API_KEY},
                        timeout=15,
                    )
                    if not full_resp.ok:
                        continue
                    full = full_resp.json()
                    transcript_text = " ".join(
                        p.get("speech", "") for p in full.get("transcript", [])
                    )
                    quarter = t.get("quarter", f"{today.year}-Q?")
                    rec = EarningsTranscript(
                        ticker=nse_ticker,
                        quarter=f"{t.get('year', today.year)}-Q{quarter}",
                        transcript_text=transcript_text[:20000],
                        source_url=f"https://finnhub.io/stock/{finnhub_symbol}",
                        call_date=today,
                    )
                    with get_session() as s:
                        upsert_earnings_transcript(s, rec)
                    records.append(rec)
                    logger.info(f"[earnings_transcripts] {nse_ticker} Q{quarter} stored")
            except Exception as e:
                logger.debug(f"[earnings_transcripts] {nse_ticker} failed: {e}")

        if not records:
            return None
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape concall.in for Indian earnings transcripts."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            resp = httpx.get("https://concall.in/", timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "lxml")
            records = []
            today = target_date or date.today()
            for item in soup.select(".transcript-item, .concall-item, .card")[:10]:
                title_el = item.find(["h2", "h3", "a"])
                if title_el:
                    title = title_el.get_text(strip=True)
                    link  = item.find("a", href=True)
                    url   = link["href"] if link else None
                    # Extract ticker from title
                    words = title.upper().split()
                    ticker = words[0] if words else "UNKNOWN"
                    rec = EarningsTranscript(
                        ticker=ticker[:20],
                        quarter=f"{today.year}-Q?",
                        transcript_text=title,
                        source_url=url,
                        call_date=today,
                    )
                    with get_session() as s:
                        upsert_earnings_transcript(s, rec)
                    records.append(rec)
            if not records:
                return None
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[earnings_transcripts] scrape failed: {e}")
            return None
