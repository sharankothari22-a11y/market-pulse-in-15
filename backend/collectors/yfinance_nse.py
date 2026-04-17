"""
Market Pulse — Hardened NSE Top Movers Collector
=================================================
Drop-in replacement for backend/collectors/yfinance_nse.py.

Philosophy: never raise, never return None, always return a list
of dicts with the expected shape — even if every external call fails.

Fallback chain per symbol:
  1. yfinance history(period="2d")       — live bid/ask
  2. yfinance .info dict                  — market metadata
  3. Twelve Data REST API                 — cloud-friendly backup (if key set)
  4. MongoDB last-known-good cache        — "stale" flag, still usable
  5. Skeleton dict with nulls             — frontend never crashes

Cascade recognition:
  If yfinance returns real data for < 30% of symbols, we assume the IP is
  rate-limited and fall through to Twelve Data / cache for the whole batch.
  This avoids the null-price pattern that was cascading into 500s on
  /api/research/analyze.

Public API (unchanged, drop-in compatible):
  fetch_nse_top_movers()          -> list[dict]   (sync, for legacy imports)
  fetch_nse_top_movers_async()    -> list[dict]   (async, preferred)

Each dict has keys:
  symbol, ticker, ltp, price, prev_close, change, change_percent,
  volume, changeType, _source, _stale
"""

from __future__ import annotations

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# =====================================================================
# DEFENSIVE IMPORTS — never crash at import time
# =====================================================================

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception as e:
    YF_AVAILABLE = False
    yf = None
    logger.warning(f"yfinance import failed: {e}")

try:
    import httpx
    HTTPX_AVAILABLE = True
except Exception as e:
    HTTPX_AVAILABLE = False
    logger.warning(f"httpx import failed: {e}")

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except Exception as e:
    MOTOR_AVAILABLE = False
    logger.warning(f"motor import failed: {e}")

# =====================================================================
# CONFIG
# =====================================================================

TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "").strip()
FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "").strip()
MONGO_URL = os.environ.get("MONGO_URL", "").strip()
DB_NAME = os.environ.get("DB_NAME", "market_pulse").strip()

# Cascade threshold: if we get real prices for fewer than this fraction
# of symbols from yfinance, assume we're rate-limited and use the cache/backup.
MIN_SUCCESS_RATIO = 0.3

# Cache TTL in seconds (stale-but-usable window)
CACHE_TTL_SECONDS = 900  # 15 min

# NSE top 10 by market cap (Nifty 50 leaders). Adjust as needed.
NIFTY_TOP: list[tuple[str, str]] = [
    ("HDFCBANK",   "HDFCBANK.NS"),
    ("ICICIBANK",  "ICICIBANK.NS"),
    ("TCS",        "TCS.NS"),
    ("RELIANCE",   "RELIANCE.NS"),
    ("INFY",       "INFY.NS"),
    ("SBIN",       "SBIN.NS"),
    ("BHARTIARTL", "BHARTIARTL.NS"),
    ("HINDUNILVR", "HINDUNILVR.NS"),
    ("BAJFINANCE", "BAJFINANCE.NS"),
    ("KOTAKBANK",  "KOTAKBANK.NS"),
]

# =====================================================================
# SAFE UTILITIES
# =====================================================================

def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    """Convert anything to float safely. NaN, None, bad strings → default."""
    try:
        if x is None:
            return default
        val = float(x)
        # NaN check (NaN != NaN is the only value where this is true)
        if val != val:
            return default
        # Infinity check
        if val in (float("inf"), float("-inf")):
            return default
        return val
    except (TypeError, ValueError):
        return default


def _skeleton(symbol: str, ticker: str, prev_close: Optional[float] = None) -> dict:
    """Shape-complete skeleton a symbol. Frontend can always render this."""
    return {
        "symbol": symbol,
        "ticker": ticker,
        "ltp": None,
        "price": None,
        "prev_close": prev_close,
        "change": None,
        "change_percent": None,
        "volume": None,
        "changeType": "neutral",
        "_source": "skeleton",
        "_stale": True,
    }


def _build_row(
    symbol: str,
    ticker: str,
    price: Optional[float],
    prev_close: Optional[float],
    volume: Optional[float],
    source: str,
    stale: bool = False,
) -> dict:
    """Build a complete mover row from components. Handles null math safely."""
    change = None
    change_pct = None
    if price is not None and prev_close is not None and prev_close != 0:
        change = price - prev_close
        change_pct = (change / prev_close) * 100

    if change is None:
        change_type = "neutral"
    elif change >= 0:
        change_type = "positive"
    else:
        change_type = "negative"

    return {
        "symbol": symbol,
        "ticker": ticker,
        "ltp": price,
        "price": price,
        "prev_close": prev_close,
        "change": change,
        "change_percent": change_pct,
        "volume": volume,
        "changeType": change_type,
        "_source": source,
        "_stale": stale,
    }


# =====================================================================
# MONGO CACHE (lazy, optional, never raises)
# =====================================================================

_mongo_client = None
_db = None


def _get_db():
    """Return Mongo db handle, or None. Never raises."""
    global _mongo_client, _db
    if _db is not None:
        return _db
    if not MOTOR_AVAILABLE or not MONGO_URL:
        return None
    try:
        _mongo_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        _db = _mongo_client[DB_NAME]
        return _db
    except Exception as e:
        logger.warning(f"mongo connect failed: {e}")
        return None


async def _cache_set(key: str, value: Any) -> None:
    db = _get_db()
    if db is None:
        return
    try:
        await db.price_cache.update_one(
            {"_id": key},
            {"$set": {"value": value, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        logger.debug(f"cache_set({key}) failed: {e}")


async def _cache_get(key: str) -> tuple[Optional[Any], bool]:
    """Return (value, is_stale). (None, False) if missing."""
    db = _get_db()
    if db is None:
        return None, False
    try:
        doc = await db.price_cache.find_one({"_id": key})
        if not doc:
            return None, False
        updated = doc.get("updated_at")
        is_stale = True
        if isinstance(updated, datetime):
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - updated).total_seconds()
            is_stale = age > CACHE_TTL_SECONDS
        return doc.get("value"), is_stale
    except Exception as e:
        logger.debug(f"cache_get({key}) failed: {e}")
        return None, False


# =====================================================================
# LAYER 1 — YFINANCE (preferred source)
# =====================================================================

def _fetch_one_yfinance(symbol: str, ticker: str) -> dict:
    """
    Fetch a single ticker from yfinance. Always returns a dict (never None,
    never raises). Source will be 'yfinance' on success, 'skeleton' on failure.
    """
    if not YF_AVAILABLE:
        return _skeleton(symbol, ticker)

    price = None
    prev_close = None
    volume = None

    # Try history() first — most reliable when it works
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d")
        if hist is not None and not hist.empty:
            price = _safe_float(hist["Close"].iloc[-1])
            volume = _safe_float(hist["Volume"].iloc[-1])
            if len(hist) >= 2:
                prev_close = _safe_float(hist["Close"].iloc[-2])
    except Exception as e:
        logger.debug(f"yf history {ticker}: {e}")

    # Fallback to .info if history didn't give us price
    if price is None or prev_close is None:
        try:
            tk = yf.Ticker(ticker)
            info = tk.info or {}
            if price is None:
                price = _safe_float(
                    info.get("currentPrice")
                    or info.get("regularMarketPrice")
                    or info.get("previousClose")
                )
            if prev_close is None:
                prev_close = _safe_float(info.get("previousClose"))
            if volume is None:
                volume = _safe_float(
                    info.get("volume") or info.get("regularMarketVolume")
                )
        except Exception as e:
            logger.debug(f"yf info {ticker}: {e}")

    if price is None and prev_close is None:
        return _skeleton(symbol, ticker)

    return _build_row(
        symbol, ticker,
        price=price, prev_close=prev_close, volume=volume,
        source="yfinance", stale=False,
    )


async def _fetch_yfinance_batch() -> list[dict]:
    """
    Fetch all NIFTY_TOP from yfinance. Runs the blocking calls in a
    threadpool so we don't block the event loop.
    """
    if not YF_AVAILABLE:
        return [_skeleton(s, t) for s, t in NIFTY_TOP]

    loop = asyncio.get_event_loop()
    # Run the blocking yfinance calls in parallel threads
    tasks = [
        loop.run_in_executor(None, _fetch_one_yfinance, sym, tk)
        for sym, tk in NIFTY_TOP
    ]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.warning(f"yf batch gather failed: {e}")
        return [_skeleton(s, t) for s, t in NIFTY_TOP]

    out = []
    for (sym, tk), res in zip(NIFTY_TOP, results):
        if isinstance(res, Exception):
            logger.debug(f"yf per-ticker exception {tk}: {res}")
            out.append(_skeleton(sym, tk))
        elif isinstance(res, dict):
            out.append(res)
        else:
            out.append(_skeleton(sym, tk))
    return out


# =====================================================================
# LAYER 2 — TWELVE DATA (cloud-friendly backup)
# =====================================================================

async def _fetch_twelve_data_batch() -> list[dict]:
    """Fetch NSE quotes from Twelve Data. Returns skeletons on failure."""
    if not TWELVE_DATA_KEY or not HTTPX_AVAILABLE:
        return [_skeleton(s, t) for s, t in NIFTY_TOP]

    out = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for symbol, ticker in NIFTY_TOP:
                try:
                    # Twelve Data symbol format: "RELIANCE:NSE"
                    td_sym = f"{symbol}:NSE"
                    r = await client.get(
                        "https://api.twelvedata.com/quote",
                        params={"symbol": td_sym, "apikey": TWELVE_DATA_KEY},
                    )
                    if r.status_code != 200:
                        out.append(_skeleton(symbol, ticker))
                        continue
                    d = r.json()
                    if isinstance(d, dict) and d.get("code"):
                        # Twelve Data error response
                        logger.debug(f"twelve_data error {symbol}: {d.get('message')}")
                        out.append(_skeleton(symbol, ticker))
                        continue
                    price = _safe_float(d.get("close"))
                    prev = _safe_float(d.get("previous_close"))
                    volume = _safe_float(d.get("volume"))
                    out.append(_build_row(
                        symbol, ticker,
                        price=price, prev_close=prev, volume=volume,
                        source="twelve_data", stale=False,
                    ))
                except Exception as e:
                    logger.debug(f"twelve_data {symbol}: {e}")
                    out.append(_skeleton(symbol, ticker))
    except Exception as e:
        logger.warning(f"twelve_data batch failed: {e}")
        return [_skeleton(s, t) for s, t in NIFTY_TOP]

    return out


# =====================================================================
# LAYER 3 — CACHE (last-known-good from Mongo)
# =====================================================================

async def _fetch_from_cache() -> list[dict]:
    """Return cached movers, marked as stale."""
    cached, is_stale = await _cache_get("nse_movers")
    if not cached or not isinstance(cached, list):
        return [_skeleton(s, t) for s, t in NIFTY_TOP]
    # Mark each as stale + cache-sourced
    for row in cached:
        if isinstance(row, dict):
            row["_source"] = "cache"
            row["_stale"] = True
    return cached


# =====================================================================
# PUBLIC API — main entry points
# =====================================================================

async def fetch_nse_top_movers_async() -> list[dict]:
    """
    Fetch NSE top movers with full fallback chain. ALWAYS returns a list
    of 10 dicts with the correct shape. Never raises.

    Returns one of:
      - Live data from yfinance (_source: "yfinance", _stale: False)
      - Live data from Twelve Data (_source: "twelve_data", _stale: False)
      - Stale data from MongoDB cache (_source: "cache", _stale: True)
      - Skeleton with prev_close metadata (_source: "skeleton", _stale: True)
    """
    # --- Layer 1: yfinance ---
    try:
        movers = await _fetch_yfinance_batch()
        # Did we get real prices for enough symbols?
        real_count = sum(1 for m in movers if m.get("price") is not None)
        success_ratio = real_count / max(len(NIFTY_TOP), 1)

        if success_ratio >= MIN_SUCCESS_RATIO:
            logger.info(f"yfinance OK: {real_count}/{len(NIFTY_TOP)} real prices")
            # Cache the good batch for future stale fallbacks
            await _cache_set("nse_movers", movers)
            return movers
        else:
            logger.warning(
                f"yfinance degraded: {real_count}/{len(NIFTY_TOP)} real prices "
                f"(threshold {MIN_SUCCESS_RATIO:.0%}) — trying fallbacks"
            )
    except Exception as e:
        logger.error(f"yfinance layer failed: {e}")

    # --- Layer 2: Twelve Data ---
    if TWELVE_DATA_KEY:
        try:
            movers = await _fetch_twelve_data_batch()
            real_count = sum(1 for m in movers if m.get("price") is not None)
            if real_count >= 3:
                logger.info(f"twelve_data OK: {real_count}/{len(NIFTY_TOP)}")
                await _cache_set("nse_movers", movers)
                return movers
            logger.warning(f"twelve_data degraded: {real_count}/{len(NIFTY_TOP)}")
        except Exception as e:
            logger.error(f"twelve_data layer failed: {e}")

    # --- Layer 3: Cache ---
    try:
        cached = await _fetch_from_cache()
        real_count = sum(1 for m in cached if m.get("price") is not None)
        if real_count >= 1:
            logger.warning(f"using stale cache: {real_count}/{len(NIFTY_TOP)} cached prices")
            return cached
    except Exception as e:
        logger.error(f"cache layer failed: {e}")

    # --- Layer 4: Skeleton (last resort, always works) ---
    logger.warning("all layers failed — returning skeleton")
    return [_skeleton(s, t) for s, t in NIFTY_TOP]


def fetch_nse_top_movers() -> list[dict]:
    """
    Synchronous wrapper for legacy imports. Prefer the async version.
    Never raises.
    """
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(fetch_nse_top_movers_async())
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"sync wrapper failed: {e}")
        return [_skeleton(s, t) for s, t in NIFTY_TOP]


# =====================================================================
# SELF-TEST (run directly to verify)
# =====================================================================

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("Testing fetch_nse_top_movers_async()...")
    result = asyncio.run(fetch_nse_top_movers_async())
    print(f"\nReturned {len(result)} rows")
    for row in result:
        print(f"  {row['symbol']:12} price={row.get('price')} "
              f"prev={row.get('prev_close')} "
              f"source={row.get('_source')} "
              f"stale={row.get('_stale')}")
    print(f"\nFull first row:\n{json.dumps(result[0], indent=2, default=str)}")
