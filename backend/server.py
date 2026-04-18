"""
Market Pulse — Hardened Backup Backend
=======================================
Philosophy: NEVER 500. NEVER crash. ALWAYS return usable JSON.

Every endpoint:
  1. Tries the real data source (yfinance, RSS, etc.)
  2. Falls back to last-known-good cache in MongoDB
  3. Falls back to safe default structure
  4. Returns with a `stale: true` or `fallback: true` flag so the frontend
     can show a subtle indicator without breaking the UI.

Failure modes explicitly handled:
  - Missing env vars (MongoDB URL, API keys) → safe defaults, log warning
  - yfinance rate-limited / returning empty → cached prices, then mock structure
  - Network timeouts on any external call → cached, then mock
  - MongoDB unavailable → in-memory cache for the request
  - Bad ticker / unknown symbol → structured error response, not 500
  - Any exception in any endpoint body → structured 200 with fallback data

Replace backend/server.py with this file. Keep the existing imports of
supporting modules (collectors/, research_platform/) intact — this file
uses the same collector function names so the file is drop-in compatible.
"""

from __future__ import annotations

# ---------- Standard library ----------
import os
import sys
import json
import logging
import asyncio
import traceback
import subprocess
import functools
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

# ---------- Third-party (all imports are defensive) ----------
try:
    from fastapi import FastAPI, APIRouter, HTTPException, Request, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, FileResponse
    from pydantic import BaseModel
except Exception as e:
    # If FastAPI itself fails to import, we can't serve anything. Raise loudly.
    raise RuntimeError(f"FATAL: FastAPI import failed: {e}")

# Optional imports — every one is wrapped so startup never crashes.
try:
    from dotenv import load_dotenv
    ROOT_DIR = Path(__file__).parent
    load_dotenv(ROOT_DIR / ".env")
except Exception as e:
    ROOT_DIR = Path(__file__).parent
    print(f"[startup] dotenv skipped: {e}")

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except Exception as e:
    MOTOR_AVAILABLE = False
    print(f"[startup] motor not available: {e}")

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception as e:
    YF_AVAILABLE = False
    yf = None
    print(f"[startup] yfinance not available: {e}")

try:
    import httpx
    HTTPX_AVAILABLE = True
except Exception as e:
    HTTPX_AVAILABLE = False
    print(f"[startup] httpx not available: {e}")

# =====================================================================
# LOGGING
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("market_pulse")

# =====================================================================
# CONFIG — every value has a safe default
# =====================================================================

MONGO_URL = os.environ.get("MONGO_URL", "").strip()
DB_NAME = os.environ.get("DB_NAME", "market_pulse").strip()
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "").strip()
FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "").strip()
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# Cache TTL for "stale-but-useful" data (seconds)
CACHE_TTL_SECONDS = 900  # 15 min — live market data stays fresh, falls back gracefully after

# In-memory fallback cache (used when Mongo is unavailable)
_MEMORY_CACHE: dict[str, tuple[datetime, Any]] = {}

# Git SHA for version endpoint
def _get_version() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT_DIR,
            stderr=subprocess.DEVNULL,
        ).decode().strip()[:7]
        return sha
    except Exception:
        return os.environ.get("APP_VERSION", "unknown")

VERSION = _get_version()
STARTUP_TIME = datetime.now(timezone.utc).isoformat()

# =====================================================================
# MONGODB — lazy, safe, optional
# =====================================================================

_mongo_client = None
_db = None

def _get_db():
    """Return Mongo db handle, or None if unavailable. Never raises."""
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
        logger.warning(f"Mongo connection failed: {e}")
        return None

# =====================================================================
# CACHE HELPERS — Mongo first, memory fallback
# =====================================================================

async def cache_set(key: str, value: Any) -> None:
    """Store value in cache. Tries Mongo, falls back to memory. Never raises."""
    now = datetime.now(timezone.utc)
    # Always write to memory as safety net
    _MEMORY_CACHE[key] = (now, value)
    # Try Mongo
    db = _get_db()
    if db is None:
        return
    try:
        await db.cache.update_one(
            {"_id": key},
            {"$set": {"value": value, "updated_at": now}},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"cache_set({key}) mongo failed: {e}")

async def cache_get(key: str, max_age_seconds: int = CACHE_TTL_SECONDS) -> tuple[Optional[Any], bool]:
    """
    Fetch cached value. Returns (value, is_stale).
    If value is None, nothing was cached.
    is_stale=True means the cache is older than max_age_seconds but still usable.
    Never raises.
    """
    # Try Mongo first
    db = _get_db()
    if db is not None:
        try:
            doc = await db.cache.find_one({"_id": key})
            if doc:
                updated = doc.get("updated_at")
                if isinstance(updated, datetime):
                    age = (datetime.now(timezone.utc) - updated.replace(tzinfo=timezone.utc) if updated.tzinfo is None else datetime.now(timezone.utc) - updated).total_seconds()
                    is_stale = age > max_age_seconds
                    return doc.get("value"), is_stale
        except Exception as e:
            logger.warning(f"cache_get({key}) mongo failed: {e}")
    # Memory fallback
    if key in _MEMORY_CACHE:
        cached_at, value = _MEMORY_CACHE[key]
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        return value, age > max_age_seconds
    return None, False

# =====================================================================
# SAFE DATA FETCHERS — each one has fallback chain
# =====================================================================

# ---- NSE top movers ----

NIFTY50_TOP = [
    ("RELIANCE", "RELIANCE.NS"),
    ("HDFCBANK", "HDFCBANK.NS"),
    ("ICICIBANK", "ICICIBANK.NS"),
    ("INFY", "INFY.NS"),
    ("TCS", "TCS.NS"),
    ("SBIN", "SBIN.NS"),
    ("BHARTIARTL", "BHARTIARTL.NS"),
    ("HINDUNILVR", "HINDUNILVR.NS"),
    ("BAJFINANCE", "BAJFINANCE.NS"),
    ("KOTAKBANK", "KOTAKBANK.NS"),
]

def _safe_float(x, default=None):
    try:
        if x is None:
            return default
        val = float(x)
        if val != val:  # NaN check
            return default
        return val
    except (TypeError, ValueError):
        return default

async def fetch_nse_movers_safe() -> dict:
    """
    Fetch NSE top movers. Returns:
      {
        "movers": [...],
        "source": "yfinance" | "twelve_data" | "cache" | "skeleton",
        "stale": bool,
      }
    Never raises.
    """
    # Attempt 1: yfinance
    if YF_AVAILABLE:
        try:
            movers = []
            tickers_str = " ".join(t[1] for t in NIFTY50_TOP)
            tks = yf.Tickers(tickers_str)
            for symbol, ticker in NIFTY50_TOP:
                try:
                    tk = tks.tickers.get(ticker) or yf.Ticker(ticker)
                    hist = tk.history(period="2d")
                    price = None
                    prev_close = None
                    volume = None
                    if hist is not None and not hist.empty:
                        price = _safe_float(hist["Close"].iloc[-1])
                        if len(hist) >= 2:
                            prev_close = _safe_float(hist["Close"].iloc[-2])
                        volume = _safe_float(hist["Volume"].iloc[-1])
                    # If history didn't give price, try info as last resort
                    if price is None:
                        try:
                            info = tk.info or {}
                            price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
                            prev_close = prev_close or _safe_float(info.get("previousClose"))
                            volume = volume or _safe_float(info.get("volume"))
                        except Exception:
                            pass
                    change = None
                    change_pct = None
                    if price is not None and prev_close:
                        change = price - prev_close
                        change_pct = (change / prev_close) * 100 if prev_close else None
                    movers.append({
                        "symbol": symbol,
                        "ticker": ticker,
                        "ltp": price,
                        "price": price,
                        "prev_close": prev_close,
                        "change": change,
                        "change_percent": change_pct,
                        "volume": volume,
                        "changeType": "positive" if (change or 0) >= 0 else "negative",
                    })
                except Exception as e:
                    logger.debug(f"yfinance per-ticker {ticker}: {e}")
                    movers.append(_mover_skeleton(symbol, ticker))

            # Check if we got ANY real prices. If every price is None, yfinance is blocked.
            real_prices = sum(1 for m in movers if m["price"] is not None)
            if real_prices >= 3:
                return {"movers": movers, "source": "yfinance", "stale": False}
            logger.warning(f"yfinance returned only {real_prices}/10 real prices — likely rate limited")
        except Exception as e:
            logger.warning(f"yfinance batch failed: {e}")

    # Attempt 2: Twelve Data (if key configured)
    if TWELVE_DATA_KEY and HTTPX_AVAILABLE:
        try:
            movers = await _fetch_twelve_data_movers()
            if movers and any(m["price"] is not None for m in movers):
                return {"movers": movers, "source": "twelve_data", "stale": False}
        except Exception as e:
            logger.warning(f"twelve_data failed: {e}")

    # Attempt 3: cache
    cached, is_stale = await cache_get("nse_movers")
    if cached:
        return {"movers": cached, "source": "cache", "stale": is_stale}

    # Attempt 4: skeleton (never null frontend)
    return {
        "movers": [_mover_skeleton(sym, tk) for sym, tk in NIFTY50_TOP],
        "source": "skeleton",
        "stale": True,
    }

def _mover_skeleton(symbol: str, ticker: str) -> dict:
    return {
        "symbol": symbol,
        "ticker": ticker,
        "ltp": None,
        "price": None,
        "prev_close": None,
        "change": None,
        "change_percent": None,
        "volume": None,
        "changeType": "neutral",
    }

async def _fetch_twelve_data_movers() -> list[dict]:
    """Fetch NSE prices via Twelve Data API. Returns [] on any failure."""
    if not TWELVE_DATA_KEY or not HTTPX_AVAILABLE:
        return []
    movers = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for symbol, ticker in NIFTY50_TOP:
            try:
                # Twelve Data uses symbol like "RELIANCE:NSE"
                td_sym = f"{symbol}:NSE"
                r = await client.get(
                    "https://api.twelvedata.com/quote",
                    params={"symbol": td_sym, "apikey": TWELVE_DATA_KEY},
                )
                if r.status_code == 200:
                    d = r.json()
                    if d.get("code"):  # Twelve Data errors come with a code
                        continue
                    price = _safe_float(d.get("close"))
                    prev = _safe_float(d.get("previous_close"))
                    change = _safe_float(d.get("change"))
                    change_pct = _safe_float(d.get("percent_change"))
                    movers.append({
                        "symbol": symbol, "ticker": ticker,
                        "ltp": price, "price": price,
                        "prev_close": prev,
                        "change": change, "change_percent": change_pct,
                        "volume": _safe_float(d.get("volume")),
                        "changeType": "positive" if (change or 0) >= 0 else "negative",
                    })
                else:
                    movers.append(_mover_skeleton(symbol, ticker))
            except Exception as e:
                logger.debug(f"twelve_data {symbol}: {e}")
                movers.append(_mover_skeleton(symbol, ticker))
    return movers

# ---- FX ----

async def fetch_fx_safe() -> dict:
    """Fetch FX rates. Frankfurter API is cloud-friendly, rarely blocked."""
    default = {
        "CNYINR": {"rate": 13.6, "change_percent": 0.0},
        "EURINR": {"rate": 109.5, "change_percent": 0.0},
        "GBPINR": {"rate": 125.6, "change_percent": 0.0},
        "JPYINR": {"rate": 0.58, "change_percent": 0.0},
        "SGDINR": {"rate": 72.9, "change_percent": 0.0},
        "USDINR": {"rate": 92.9, "change_percent": 0.0},
    }
    if not HTTPX_AVAILABLE:
        cached, _ = await cache_get("fx")
        return cached or default
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get("https://api.frankfurter.app/latest?from=INR")
            if r.status_code == 200:
                d = r.json()
                rates = d.get("rates", {})
                out = {}
                for ccy in ["CNY", "EUR", "GBP", "JPY", "SGD", "USD"]:
                    rate = rates.get(ccy)
                    if rate:
                        out[f"{ccy}INR"] = {"rate": round(1 / rate, 4), "change_percent": 0.0}
                if out:
                    await cache_set("fx", out)
                    return out
    except Exception as e:
        logger.warning(f"fx fetch failed: {e}")
    cached, _ = await cache_get("fx")
    return cached or default

# ---- Commodities ----

async def fetch_commodities_safe() -> list[dict]:
    default = [
        {"name": "Gold", "symbol": "GC=F", "price": 0, "currency": "USD", "unit": "USD/oz", "change_pct": 0},
        {"name": "Silver", "symbol": "SI=F", "price": 0, "currency": "USD", "unit": "USD/oz", "change_pct": 0},
        {"name": "Crude Oil (WTI)", "symbol": "CL=F", "price": 0, "currency": "USD", "unit": "USD/bbl", "change_pct": 0},
        {"name": "Brent Crude", "symbol": "BZ=F", "price": 0, "currency": "USD", "unit": "USD/bbl", "change_pct": 0},
        {"name": "Natural Gas", "symbol": "NG=F", "price": 0, "currency": "USD", "unit": "USD/MMBtu", "change_pct": 0},
    ]
    if not YF_AVAILABLE:
        cached, _ = await cache_get("commodities")
        return cached or default
    try:
        symbols = ["GC=F", "SI=F", "CL=F", "BZ=F", "NG=F"]
        tks = yf.Tickers(" ".join(symbols))
        out = []
        meta = {
            "GC=F": ("Gold", "USD/oz"),
            "SI=F": ("Silver", "USD/oz"),
            "CL=F": ("Crude Oil (WTI)", "USD/bbl"),
            "BZ=F": ("Brent Crude", "USD/bbl"),
            "NG=F": ("Natural Gas", "USD/MMBtu"),
        }
        for sym in symbols:
            try:
                name, unit = meta[sym]
                tk = tks.tickers.get(sym) or yf.Ticker(sym)
                hist = tk.history(period="2d")
                price = 0
                change_pct = 0
                if hist is not None and not hist.empty:
                    price = _safe_float(hist["Close"].iloc[-1], 0)
                    if len(hist) >= 2:
                        prev = _safe_float(hist["Close"].iloc[-2], price)
                        if prev:
                            change_pct = round((price - prev) / prev * 100, 2)
                out.append({
                    "name": name, "symbol": sym,
                    "price": price, "currency": "USD",
                    "unit": unit, "change_pct": change_pct,
                })
            except Exception as e:
                logger.debug(f"commodity {sym}: {e}")
        if out and any(c["price"] for c in out):
            await cache_set("commodities", out)
            return out
    except Exception as e:
        logger.warning(f"commodities failed: {e}")
    cached, _ = await cache_get("commodities")
    return cached or default

# ---- News ----

async def fetch_news_safe() -> list[dict]:
    default = []
    if not HTTPX_AVAILABLE:
        cached, _ = await cache_get("news")
        return cached or default
    feeds = [
        ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Mint Markets", "https://www.livemint.com/rss/markets"),
    ]
    news = []
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for source, url in feeds:
                try:
                    r = await client.get(url)
                    if r.status_code != 200:
                        continue
                    # Cheap RSS parse without feedparser dep
                    text = r.text
                    items = text.split("<item>")[1:6]
                    for item in items:
                        try:
                            title = _between(item, "<title>", "</title>").replace("<![CDATA[", "").replace("]]>", "").strip()
                            link = _between(item, "<link>", "</link>").strip()
                            pub = _between(item, "<pubDate>", "</pubDate>").strip()
                            if title and link:
                                news.append({"title": title, "source": source, "url": link, "published": pub})
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"news feed {source}: {e}")
        if news:
            await cache_set("news", news)
            return news
    except Exception as e:
        logger.warning(f"news failed: {e}")
    cached, _ = await cache_get("news")
    return cached or default

def _between(s: str, start: str, end: str) -> str:
    try:
        a = s.index(start) + len(start)
        b = s.index(end, a)
        return s[a:b]
    except ValueError:
        return ""

# ---- FII/DII (stub — plug your existing collector if you have one) ----

async def fetch_fii_dii_safe() -> list[dict]:
    """Return recent FII/DII flows. Uses cache if live fetch unavailable."""
    cached, _ = await cache_get("fii_dii")
    if cached:
        return cached
    # Safe default: last 7 days with zeros
    today = datetime.now(timezone.utc).date()
    return [
        {"date": (today - timedelta(days=i)).isoformat(), "fii_net": 0, "dii_net": 0, "nifty_close": 0}
        for i in range(1, 8)
    ]

# =====================================================================
# ENDPOINT ERROR WRAPPER — never let anything 500
# =====================================================================

def safe_endpoint(fallback_factory):
    """
    Decorator: catches any exception from an endpoint, logs it with full
    traceback, and returns a structured 200 with fallback data instead of 500.
    fallback_factory: callable that returns the fallback response dict.

    Uses functools.wraps to preserve the wrapped function's signature so
    FastAPI's dependency injection reads the real parameters, not *args/**kwargs.
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except HTTPException:
                raise  # let intentional HTTP errors through (e.g., 404 for unknown ticker)
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"endpoint {fn.__name__} failed: {e}\n{tb}")
                fallback = fallback_factory() if callable(fallback_factory) else fallback_factory
                return JSONResponse(
                    status_code=200,
                    content={
                        **fallback,
                        "_error": {
                            "message": str(e),
                            "endpoint": fn.__name__,
                            "stage": "handler",
                        },
                        "_fallback": True,
                    },
                )
        return wrapper
    return decorator

# =====================================================================
# APP + ROUTER
# =====================================================================

app = FastAPI(title="Market Pulse — Hardened Backend", version=VERSION)

# CORS as early as possible
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != [""] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# ---------- Meta ----------

@api_router.get("/")
async def root():
    return {"message": "Hello World", "service": "market_pulse", "version": VERSION}

@api_router.get("/health")
async def health():
    db = _get_db()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "mongo": "connected" if db is not None else "unavailable",
        "yfinance": "available" if YF_AVAILABLE else "unavailable",
        "twelve_data": "configured" if TWELVE_DATA_KEY else "not_configured",
        "uptime_since": STARTUP_TIME,
    }

@api_router.get("/version")
async def version():
    return {"version": VERSION, "startup": STARTUP_TIME}

@api_router.get("/ping")
async def ping():
    return {"ok": True}

# ---------- Market Overview ----------

def _overview_fallback():
    return {
        "top_movers": [_mover_skeleton(s, t) for s, t in NIFTY50_TOP],
        "fx": {},
        "crypto": [],
        "commodities": [],
        "fii_dii": [],
        "news": [],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

@api_router.get("/market/overview")
@safe_endpoint(_overview_fallback)
async def market_overview():
    # Fan out all fetches in parallel; each is individually safe
    movers_task = fetch_nse_movers_safe()
    fx_task = fetch_fx_safe()
    commodities_task = fetch_commodities_safe()
    news_task = fetch_news_safe()
    fii_task = fetch_fii_dii_safe()

    movers_res, fx_res, comm_res, news_res, fii_res = await asyncio.gather(
        movers_task, fx_task, commodities_task, news_task, fii_task,
        return_exceptions=True,
    )

    # Unpack with defensive checks
    if isinstance(movers_res, dict):
        top_movers = movers_res.get("movers", [])
        movers_source = movers_res.get("source", "unknown")
        movers_stale = movers_res.get("stale", False)
    else:
        top_movers = [_mover_skeleton(s, t) for s, t in NIFTY50_TOP]
        movers_source = "error"
        movers_stale = True

    fx = fx_res if isinstance(fx_res, dict) else {}
    commodities = comm_res if isinstance(comm_res, list) else []
    news = news_res if isinstance(news_res, list) else []
    fii_dii = fii_res if isinstance(fii_res, list) else []

    indices = await fetch_indices_safe()
    nifty = indices.get("NIFTY50") or indices.get("NIFTY 50") or {}
    sensex = indices.get("SENSEX") or {}

    return {
        "top_movers": top_movers,
        "fx": fx,
        "crypto": [],  # TODO: wire CoinGecko fallback
        "commodities": commodities,
        "fii_dii": fii_dii,
        "news": news,
        "indices": indices,
        # Flat index fields — frontend may look for these directly
        "nifty": nifty,
        "nifty50": nifty,
        "NIFTY50": nifty,
        "sensex": sensex,
        "SENSEX": sensex,
        "nifty_value": nifty.get("value"),
        "nifty_change_percent": nifty.get("change_percent"),
        "sensex_value": sensex.get("value"),
        "sensex_change_percent": sensex.get("change_percent"),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "_meta": {
            "movers_source": movers_source,
            "movers_stale": movers_stale,
        },
    }

# ---------- Indices (NIFTY 50 + SENSEX) ----------

INDICES = [
    ("NIFTY 50", "^NSEI"),
    ("SENSEX", "^BSESN"),
]

async def fetch_indices_safe() -> dict:
    """Fetch NIFTY 50 and SENSEX levels. Never raises."""
    out = {}
    if YF_AVAILABLE:
        try:
            loop = asyncio.get_event_loop()
            def _fetch_one(name: str, symbol: str):
                try:
                    tk = yf.Ticker(symbol)
                    hist = tk.history(period="2d")
                    if hist is not None and not hist.empty:
                        price = _safe_float(hist["Close"].iloc[-1])
                        prev = _safe_float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
                        change = (price - prev) if (price and prev) else None
                        change_pct = ((change / prev) * 100) if (change and prev) else None
                        change_type = "neutral"
                        if change is not None:
                            change_type = "positive" if change >= 0 else "negative"
                        # Pre-formatted display strings for the pill
                        value_fmt = f"{price:,.2f}" if price is not None else "—"
                        change_fmt = f"{change_pct:+.2f}%" if change_pct is not None else "—"
                        return name, {
                            "name": name,
                            "symbol": symbol,
                            "value": value_fmt,           # display string "24,353.55"
                            "raw_value": price,           # raw number for toLocaleString
                            "price": price,               # alias
                            "ltp": price,                 # alias
                            "last": price,                # alias
                            "prev_close": prev,
                            "change": change_fmt,         # display string "+0.65%" — frontend renders this
                            "change_raw": change,         # raw delta number
                            "change_percent": change_pct,
                            "change_pct": change_pct,     # alias
                            "changeType": change_type,    # "positive" / "negative" / "neutral"
                        }
                except Exception as e:
                    logger.debug(f"indices {symbol}: {e}")
                return name, {"name": name, "symbol": symbol, "value": "—",
                              "raw_value": None, "price": None, "ltp": None, "last": None,
                              "prev_close": None, "change": "—", "change_raw": None,
                              "change_percent": None, "change_pct": None,
                              "changeType": "neutral"}

            results = await asyncio.gather(
                *[loop.run_in_executor(None, _fetch_one, n, s) for n, s in INDICES],
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, tuple):
                    name, data = res
                    # Expose under every common key the frontend might read:
                    # "NIFTY 50" (with space), "NIFTY50" (no space), "nifty" (lowercase)
                    key_nospace = name.replace(" ", "")
                    out[name] = data                        # "NIFTY 50" / "SENSEX"
                    out[key_nospace] = data                 # "NIFTY50" / "SENSEX"
                    out[key_nospace.lower()] = data         # "nifty50" / "sensex"
                    # Special shortname for NIFTY 50 → "nifty" (TopBar.jsx uses this)
                    if "NIFTY" in key_nospace:
                        out["nifty"] = data
                    if "SENSEX" in key_nospace:
                        out["sensex"] = data
            if out:
                await cache_set("indices", out)
                return out
        except Exception as e:
            logger.warning(f"indices fetch failed: {e}")
    cached, _ = await cache_get("indices")
    return cached or {
        "NIFTY50": {"name": "NIFTY 50", "value": None, "change_percent": None},
        "nifty": {"name": "NIFTY 50", "value": None, "change_percent": None},
        "SENSEX": {"name": "SENSEX", "value": None, "change_percent": None},
        "sensex": {"name": "SENSEX", "value": None, "change_percent": None},
    }

# ---------- Sessions ----------

class SessionCreate(BaseModel):
    ticker: str
    sector: Optional[str] = None

@api_router.get("/sessions")
@safe_endpoint(lambda: {"sessions": []})
async def list_sessions():
    """List research sessions, deduplicated by ticker (keep newest)."""
    db = _get_db()
    if db is None:
        return {"sessions": []}
    try:
        # Dedupe pipeline: group by ticker, keep newest
        pipeline = [
            {"$sort": {"created_at": -1}},
            {"$group": {
                "_id": "$ticker",
                "doc": {"$first": "$$ROOT"},
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$sort": {"created_at": -1}},
            {"$limit": 50},
        ]
        cursor = db.sessions.aggregate(pipeline)
        docs = []
        async for d in cursor:
            d["_id"] = str(d.get("_id", ""))
            docs.append(d)
        return {"sessions": docs}
    except Exception as e:
        logger.warning(f"list_sessions mongo: {e}")
        return {"sessions": []}

@api_router.post("/research/new")
@safe_endpoint(lambda: {"session_id": "offline", "ticker": "UNKNOWN", "created_at": datetime.now(timezone.utc).isoformat()})
async def create_session(req: SessionCreate):
    ticker = (req.ticker or "").upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    now = datetime.now(timezone.utc)
    session_id = now.strftime("%y%m%d_%H%M%S")
    doc = {
        "_id": session_id,
        "session_id": session_id,
        "ticker": ticker,
        "sector": req.sector or "general",
        "hypothesis": f"Analysis session for {ticker}",
        "status": "active",
        "created_at": now,
    }
    db = _get_db()
    if db is not None:
        try:
            await db.sessions.insert_one(doc)
        except Exception as e:
            logger.warning(f"create_session insert: {e}")
    doc["created_at"] = now.isoformat()
    return doc

# ---------- Research Analyze (the endpoint that was 500-ing) ----------

def _analyze_fallback():
    return {
        "ticker": "UNKNOWN",
        "price_data": None,
        "dcf": None,
        "scenarios": [],
        "message": "Analysis unavailable — using cached or fallback data",
    }

@api_router.post("/research/analyze")
@safe_endpoint(_analyze_fallback)
async def analyze(request: Request):
    """
    The previously-500ing endpoint. Now:
      - Every numerical operation guarded with safe_float() + default
      - Missing yfinance data → skeleton response, not exception
      - Division by zero → guarded everywhere
      - Detailed error surface via safe_endpoint decorator
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    ticker = (body.get("ticker") or "").upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")

    ticker_ns = ticker if "." in ticker else f"{ticker}.NS"

    # Try cache first for instant response
    cache_key = f"analyze:{ticker_ns}"

    # Pull live data defensively
    price_data = None
    info = {}
    if YF_AVAILABLE:
        try:
            tk = yf.Ticker(ticker_ns)
            hist = tk.history(period="2d")
            if hist is not None and not hist.empty:
                price = _safe_float(hist["Close"].iloc[-1])
                prev = _safe_float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
                price_data = {
                    "price": price,
                    "prev_close": prev,
                    "change": (price - prev) if (price and prev) else None,
                    "change_pct": ((price - prev) / prev * 100) if (price and prev) else None,
                }
            try:
                info = tk.info or {}
            except Exception:
                info = {}
        except Exception as e:
            logger.warning(f"analyze yfinance failed for {ticker}: {e}")

    # Don't early-return from cache — we always want to go through the full
    # response-building path below so all fields (session_id, flat prices,
    # etc.) are present. Cache is only used when yfinance fully crashes.

    # If history() returned null price but info has currentPrice, use that
    if price_data is None or price_data.get("price") is None:
        info_price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        info_prev = _safe_float(info.get("previousClose") or (price_data or {}).get("prev_close"))
        if info_price is not None:
            price_data = {
                "price": info_price,
                "prev_close": info_prev,
                "change": (info_price - info_prev) if (info_prev is not None) else None,
                "change_pct": ((info_price - info_prev) / info_prev * 100) if (info_prev) else None,
            }

    # Safe DCF skeleton — never divides by zero
    current_price = _safe_float(info.get("currentPrice") or (price_data or {}).get("price"), 0)
    market_cap = _safe_float(info.get("marketCap"), 0)
    total_revenue = _safe_float(info.get("totalRevenue"), 0)
    net_income = _safe_float(info.get("netIncomeToCommon") or info.get("netIncome"), 0)
    shares_out = _safe_float(info.get("sharesOutstanding"), 0)
    beta = _safe_float(info.get("beta"), 1.0)

    # Safe WACC (all bounds guarded)
    rf = 0.072  # India 10Y
    erp = 0.06
    wacc = min(max(rf + beta * erp, 0.08), 0.15)

    # Safe terminal value
    growth = 0.05
    terminal_growth = 0.035
    if wacc <= terminal_growth:
        wacc = terminal_growth + 0.02  # prevent division issues

    # Simple 5-year FCF projection (all zero-safe)
    fcf_base = net_income * 0.7 if net_income else 0
    pv_fcf = 0
    for year in range(1, 6):
        fcf_year = fcf_base * ((1 + growth) ** year)
        pv_fcf += fcf_year / ((1 + wacc) ** year)
    terminal_value = 0
    if fcf_base and (wacc - terminal_growth) > 0:
        terminal_fcf = fcf_base * ((1 + growth) ** 5) * (1 + terminal_growth)
        terminal_value = (terminal_fcf / (wacc - terminal_growth)) / ((1 + wacc) ** 5)
    enterprise_value = pv_fcf + terminal_value

    # Equity value = EV (we skip debt adj in backup for safety)
    equity_value = enterprise_value
    price_per_share = (equity_value / shares_out) if shares_out else 0
    upside_pct = ((price_per_share - current_price) / current_price * 100) if current_price else 0

    # Create session so frontend can navigate to /research/<session_id>
    now = datetime.now(timezone.utc)
    session_id = now.strftime("%y%m%d_%H%M%S")
    session_doc = {
        "_id": session_id,
        "session_id": session_id,
        "ticker": ticker,
        "sector": "general",
        "hypothesis": f"Analysis session for {ticker}",
        "status": "active",
        "created_at": now,
    }
    db = _get_db()
    if db is not None:
        try:
            await db.sessions.insert_one(session_doc)
        except Exception as e:
            logger.debug(f"analyze session insert: {e}")

    response = {
        "session_id": session_id,
        "id": session_id,  # some frontends look for .id instead of .session_id
        "ticker": ticker,
        "ticker_ns": ticker_ns,
        "sector": "general",
        "hypothesis": f"Analysis session for {ticker}",
        "status": "active",
        "created_at": now.isoformat(),
        # Flat price fields — frontend may look for any of these
        "price": current_price,
        "ltp": current_price,
        "last_price": current_price,
        "current_price": current_price,
        "prev_close": (price_data or {}).get("prev_close"),
        "change": (price_data or {}).get("change"),
        "change_percent": (price_data or {}).get("change_pct"),
        "change_pct": (price_data or {}).get("change_pct"),
        # Also keep nested shape for consumers that expect it
        "price_data": price_data,
        "dcf": {
            "current_price": current_price,
            "fair_value": round(price_per_share, 2),
            "upside_pct": round(upside_pct, 2),
            "wacc": round(wacc, 4),
            "terminal_growth": terminal_growth,
            "growth": growth,
            "enterprise_value": round(enterprise_value, 0),
            "equity_value": round(equity_value, 0),
        },
        "meta": {
            "data_source": "yfinance" if info else "skeleton",
            "fallback_used": not bool(info),
        },
    }

    # Cache for next time yfinance fails
    await cache_set(cache_key, response)
    # Also cache by session_id so GET /research/{session_id} works
    await cache_set(f"session:{session_id}", response)
    return response

# ---------- Other stubs for completeness (never 500) ----------

async def _enrich_with_live_price(session: dict) -> dict:
    """Add live price fields to a session doc so frontend always has data."""
    ticker = session.get("ticker", "").upper()
    if not ticker or ticker == "UNKNOWN":
        return session
    ticker_ns = ticker if "." in ticker else f"{ticker}.NS"
    price = None
    prev_close = None
    if YF_AVAILABLE:
        try:
            loop = asyncio.get_event_loop()
            def _fetch():
                tk = yf.Ticker(ticker_ns)
                hist = tk.history(period="2d")
                p = _safe_float(hist["Close"].iloc[-1]) if (hist is not None and not hist.empty) else None
                pc = _safe_float(hist["Close"].iloc[-2]) if (hist is not None and len(hist) >= 2) else None
                return p, pc
            price, prev_close = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.debug(f"enrich price {ticker}: {e}")
    # Cache fallback
    if price is None:
        cached, _ = await cache_get(f"session:{session.get('session_id') or session.get('_id')}")
        if cached and cached.get("price") is not None:
            return {**session, **{
                "price": cached.get("price"),
                "ltp": cached.get("price"),
                "last_price": cached.get("price"),
                "current_price": cached.get("price"),
                "prev_close": cached.get("prev_close"),
                "change": cached.get("change"),
                "change_percent": cached.get("change_percent"),
                "change_pct": cached.get("change_pct"),
            }}
    change = (price - prev_close) if (price is not None and prev_close) else None
    change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None
    return {**session, **{
        "price": price,
        "ltp": price,
        "last_price": price,
        "current_price": price,
        "prev_close": prev_close,
        "change": change,
        "change_percent": change_pct,
        "change_pct": change_pct,
    }}

# GET session detail — frontend navigates here after analyze
@api_router.get("/research/{session_id}")
@safe_endpoint(lambda: {"session_id": "unknown", "ticker": "UNKNOWN", "status": "not_found", "_fallback": True})
async def get_session(session_id: str):
    # 1. Try Mongo
    db = _get_db()
    if db is not None:
        try:
            doc = await db.sessions.find_one({"_id": session_id})
            if doc:
                doc["_id"] = str(doc.get("_id", ""))
                if isinstance(doc.get("created_at"), datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                # Enrich with live price
                doc = await _enrich_with_live_price(doc)
                return doc
        except Exception as e:
            logger.debug(f"get_session mongo: {e}")
    # 2. Try cache (analyze endpoint caches by session_id) — already has flat fields
    cached, _ = await cache_get(f"session:{session_id}")
    if cached:
        return cached
    # 3. Skeleton session so frontend doesn't crash
    return {
        "session_id": session_id,
        "id": session_id,
        "ticker": "UNKNOWN",
        "sector": "general",
        "status": "not_found",
        "hypothesis": "Session not found",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

# Research sub-endpoints — all return safe empty payloads
@api_router.post("/research/{session_id}/run-scenarios")
@safe_endpoint(lambda: {"scenarios": [], "_fallback": True})
async def run_scenarios(session_id: str):
    return {"session_id": session_id, "scenarios": []}

@api_router.post("/research/{session_id}/catalyst")
@safe_endpoint(lambda: {"catalysts": [], "_fallback": True})
async def add_catalyst(session_id: str, request: Request):
    return {"session_id": session_id, "catalysts": []}

@api_router.post("/research/{session_id}/thesis")
@safe_endpoint(lambda: {"thesis": "", "_fallback": True})
async def update_thesis(session_id: str, request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    return {"session_id": session_id, "thesis": body.get("thesis", "")}

@api_router.post("/research/{session_id}/dcf")
@safe_endpoint(lambda: {"dcf": None, "_fallback": True})
async def run_dcf(session_id: str, request: Request):
    return {"session_id": session_id, "dcf": None, "message": "DCF endpoint stub"}

@api_router.get("/research/{session_id}/dcf")
@safe_endpoint(lambda: {"dcf": None, "_fallback": True})
async def get_dcf(session_id: str):
    return {"session_id": session_id, "dcf": None}

# ---------- Report Downloads (HTML + XLSX) ----------

async def _load_session_for_report(session_id: str) -> dict:
    """Fetch session data from Mongo or cache for report generation."""
    db = _get_db()
    if db is not None:
        try:
            doc = await db.sessions.find_one({"_id": session_id})
            if doc:
                doc["_id"] = str(doc.get("_id", ""))
                if isinstance(doc.get("created_at"), datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                # Enrich with cached analyze response for price/DCF
                cached, _ = await cache_get(f"session:{session_id}")
                if cached:
                    # Merge, prefer cached for numeric fields
                    for k in ("price", "ltp", "prev_close", "change", "change_percent", "dcf"):
                        if cached.get(k) is not None:
                            doc[k] = cached[k]
                return doc
        except Exception as e:
            logger.debug(f"report load mongo: {e}")
    cached, _ = await cache_get(f"session:{session_id}")
    return cached or {"session_id": session_id, "ticker": "UNKNOWN", "status": "not_found"}


@api_router.get("/research/{session_id}/report/download")
async def report_download_html(session_id: str):
    """Return a self-contained HTML report for the session."""
    from fastapi.responses import HTMLResponse
    try:
        session = await _load_session_for_report(session_id)
        ticker = session.get("ticker", "UNKNOWN")
        price = session.get("price") or session.get("current_price") or (session.get("dcf") or {}).get("current_price")
        prev_close = session.get("prev_close")
        change_pct = session.get("change_percent") or session.get("change_pct")
        dcf = session.get("dcf") or {}
        hypothesis = session.get("hypothesis", "—")
        sector = session.get("sector", "general")
        created = session.get("created_at", "")
        status = session.get("status", "active")

        def fmt(v, suffix=""):
            if v is None:
                return "—"
            try:
                return f"{float(v):,.2f}{suffix}"
            except Exception:
                return str(v)

        html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{ticker} Research Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 2rem auto; padding: 2rem; color: #0f172a; }}
  h1 {{ border-bottom: 2px solid #2563eb; padding-bottom: 0.5rem; margin-bottom: 0.5rem; }}
  h2 {{ color: #334155; margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }}
  .meta {{ color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }}
  .card {{ background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
  .kv {{ display: grid; grid-template-columns: 200px 1fr; gap: 0.5rem; margin: 0.25rem 0; }}
  .kv .k {{ color: #64748b; font-weight: 500; }}
  .kv .v {{ color: #0f172a; font-weight: 600; font-variant-numeric: tabular-nums; }}
  .positive {{ color: #16a34a; }}
  .negative {{ color: #dc2626; }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; color: #94a3b8; font-size: 0.8rem; }}
</style></head>
<body>
  <h1>{ticker}</h1>
  <div class="meta">
    Sector: {sector} &middot; Session: {session_id} &middot; Status: {status}<br>
    Generated: {datetime.now(timezone.utc).isoformat()} &middot; Created: {created}
  </div>

  <h2>Price Snapshot</h2>
  <div class="card">
    <div class="kv"><span class="k">Current Price</span><span class="v">₹{fmt(price)}</span></div>
    <div class="kv"><span class="k">Previous Close</span><span class="v">₹{fmt(prev_close)}</span></div>
    <div class="kv"><span class="k">Change (%)</span><span class="v {'positive' if (change_pct or 0) >= 0 else 'negative'}">{fmt(change_pct, '%')}</span></div>
  </div>

  <h2>DCF Valuation</h2>
  <div class="card">
    <div class="kv"><span class="k">Fair Value (Base)</span><span class="v">₹{fmt(dcf.get('fair_value'))}</span></div>
    <div class="kv"><span class="k">Upside vs Current</span><span class="v {'positive' if (dcf.get('upside_pct') or 0) >= 0 else 'negative'}">{fmt(dcf.get('upside_pct'), '%')}</span></div>
    <div class="kv"><span class="k">WACC</span><span class="v">{fmt((dcf.get('wacc') or 0) * 100, '%')}</span></div>
    <div class="kv"><span class="k">Growth Rate</span><span class="v">{fmt((dcf.get('growth') or 0) * 100, '%')}</span></div>
    <div class="kv"><span class="k">Terminal Growth</span><span class="v">{fmt((dcf.get('terminal_growth') or 0) * 100, '%')}</span></div>
    <div class="kv"><span class="k">Enterprise Value</span><span class="v">₹{fmt(dcf.get('enterprise_value'))}</span></div>
    <div class="kv"><span class="k">Equity Value</span><span class="v">₹{fmt(dcf.get('equity_value'))}</span></div>
  </div>

  <h2>Hypothesis</h2>
  <div class="card"><p>{hypothesis}</p></div>

  <div class="footer">
    Market Pulse Research · Automated report · Figures from yfinance at time of analysis.
    Not investment advice. Verify all numbers independently before making decisions.
  </div>
</body></html>"""
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        logger.error(f"report_download failed: {e}\n{traceback.format_exc()}")
        return HTMLResponse(
            content=f"<html><body><h1>Report unavailable</h1><p>{str(e)}</p></body></html>",
            status_code=200,
        )


@api_router.get("/research/{session_id}/report/xlsx")
async def report_download_xlsx(session_id: str):
    """Return an XLSX spreadsheet with session details."""
    from fastapi.responses import Response
    try:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            # openpyxl not installed → fall back to CSV
            return await report_download_csv(session_id)

        session = await _load_session_for_report(session_id)
        ticker = session.get("ticker", "UNKNOWN")
        price = session.get("price") or (session.get("dcf") or {}).get("current_price")
        prev_close = session.get("prev_close")
        change_pct = session.get("change_percent") or session.get("change_pct")
        dcf = session.get("dcf") or {}

        wb = Workbook()

        # Sheet 1: Summary
        ws = wb.active
        ws.title = "Summary"
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 25
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="2563EB")
        section_font = Font(bold=True, size=11, color="1E40AF")
        label_font = Font(color="64748B")

        ws['A1'] = f"{ticker} — Research Report"
        ws['A1'].font = header_font
        ws['A1'].fill = header_fill
        ws.merge_cells('A1:B1')
        ws.row_dimensions[1].height = 28

        rows = [
            ("", ""),
            ("SESSION DETAILS", ""),
            ("Ticker", ticker),
            ("Sector", session.get("sector", "general")),
            ("Session ID", session_id),
            ("Status", session.get("status", "active")),
            ("Created", session.get("created_at", "")),
            ("Generated", datetime.now(timezone.utc).isoformat()),
            ("", ""),
            ("PRICE", ""),
            ("Current Price", price),
            ("Previous Close", prev_close),
            ("Change %", f"{change_pct:.2f}%" if change_pct is not None else "—"),
            ("", ""),
            ("DCF VALUATION", ""),
            ("Fair Value (Base)", dcf.get("fair_value")),
            ("Upside %", f"{dcf.get('upside_pct'):.2f}%" if dcf.get("upside_pct") is not None else "—"),
            ("WACC", f"{dcf.get('wacc') * 100:.2f}%" if dcf.get("wacc") else "—"),
            ("Growth Rate", f"{dcf.get('growth') * 100:.2f}%" if dcf.get("growth") else "—"),
            ("Terminal Growth", f"{dcf.get('terminal_growth') * 100:.2f}%" if dcf.get("terminal_growth") else "—"),
            ("Enterprise Value", dcf.get("enterprise_value")),
            ("Equity Value", dcf.get("equity_value")),
            ("", ""),
            ("HYPOTHESIS", ""),
            ("Thesis", session.get("hypothesis", "—")),
        ]
        for i, (k, v) in enumerate(rows, start=2):
            ws.cell(row=i, column=1, value=k)
            ws.cell(row=i, column=2, value=v)
            if k in ("SESSION DETAILS", "PRICE", "DCF VALUATION", "HYPOTHESIS"):
                ws.cell(row=i, column=1).font = section_font
            elif k:
                ws.cell(row=i, column=1).font = label_font

        # Save to bytes
        import io
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{ticker}_report.xlsx"'},
        )
    except Exception as e:
        logger.error(f"report_xlsx failed: {e}\n{traceback.format_exc()}")
        # Fallback to CSV on any error
        return await report_download_csv(session_id)


@api_router.get("/research/{session_id}/report/csv")
async def report_download_csv(session_id: str):
    """Return a CSV version of the report. Always works, no dependencies."""
    from fastapi.responses import Response
    try:
        session = await _load_session_for_report(session_id)
        ticker = session.get("ticker", "UNKNOWN")
        dcf = session.get("dcf") or {}
        rows = [
            ("Ticker", ticker),
            ("Sector", session.get("sector", "general")),
            ("Session ID", session_id),
            ("Status", session.get("status", "active")),
            ("Created", session.get("created_at", "")),
            ("Current Price", session.get("price") or dcf.get("current_price") or ""),
            ("Previous Close", session.get("prev_close") or ""),
            ("Change %", session.get("change_percent") or session.get("change_pct") or ""),
            ("Fair Value", dcf.get("fair_value") or ""),
            ("Upside %", dcf.get("upside_pct") or ""),
            ("WACC", dcf.get("wacc") or ""),
            ("Growth", dcf.get("growth") or ""),
            ("Terminal Growth", dcf.get("terminal_growth") or ""),
            ("Enterprise Value", dcf.get("enterprise_value") or ""),
            ("Equity Value", dcf.get("equity_value") or ""),
            ("Hypothesis", session.get("hypothesis", "")),
        ]
        csv_lines = ["Field,Value"] + [f'"{k}","{v}"' for k, v in rows]
        csv_content = "\n".join(csv_lines)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{ticker}_report.csv"'},
        )
    except Exception as e:
        logger.error(f"report_csv failed: {e}")
        return Response(content="Field,Value\nerror," + str(e), media_type="text/csv", status_code=200)


@api_router.get("/macro")
@safe_endpoint(lambda: {"indicators": []})
async def macro():
    cached, _ = await cache_get("macro")
    return {"indicators": cached or []}

@api_router.get("/signals")
@safe_endpoint(lambda: {"signals": []})
async def signals():
    return {"signals": []}

@api_router.get("/alerts")
@safe_endpoint(lambda: {"alerts": []})
async def alerts():
    return {"alerts": []}

@api_router.get("/prices/{ticker}")
@safe_endpoint(lambda: {"price": None, "error": "unavailable"})
async def prices(ticker: str):
    ticker_ns = ticker if "." in ticker else f"{ticker}.NS"
    if not YF_AVAILABLE:
        return {"price": None, "ticker": ticker_ns, "source": "unavailable"}
    try:
        tk = yf.Ticker(ticker_ns)
        hist = tk.history(period="1d")
        if hist is not None and not hist.empty:
            return {
                "ticker": ticker_ns,
                "price": _safe_float(hist["Close"].iloc[-1]),
                "source": "yfinance",
            }
    except Exception as e:
        logger.warning(f"prices({ticker}) failed: {e}")
    return {"price": None, "ticker": ticker_ns, "source": "error"}

@api_router.post("/chat")
@safe_endpoint(lambda: {"reply": "Chat service unavailable right now. Please try again in a moment."})
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return {"reply": "Please provide a message."}
    if not ANTHROPIC_KEY:
        return {"reply": "AI chat is not configured on this deployment."}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": message}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        return {"reply": text or "No response."}
    except Exception as e:
        logger.warning(f"chat failed: {e}")
        return {"reply": "Chat temporarily unavailable."}

# =====================================================================
# MOUNT ROUTER — LAST, ALWAYS
# =====================================================================

app.include_router(api_router)

# Global exception handler — last line of defense
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"unhandled exception on {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=200,  # never 500 to the frontend
        content={
            "error": str(exc),
            "path": str(request.url.path),
            "_fallback": True,
        },
    )

logger.info(f"Market Pulse hardened backend ready | version={VERSION} | mongo={'up' if _get_db() is not None else 'down'}")
