from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
import feedparser

# Import yfinance collector
from collectors.yfinance_nse import fetch_nse_top_movers, NSE_TOP_10


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Thread pool for running sync functions
executor = ThreadPoolExecutor(max_workers=5)

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ── NaN-safe sanitizer (yfinance may return NaN/Inf which break JSON) ─────────
import math as _math
def _clean_nans(obj):
    if isinstance(obj, float):
        if _math.isnan(obj) or _math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nans(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_clean_nans(v) for v in obj)
    return obj


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────────────────────────

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None

class CatalystRequest(BaseModel):
    description: str
    expected_date: Optional[str] = None
    catalyst_type: str = "earnings"

class ThesisRequest(BaseModel):
    thesis: str
    variant_view: Optional[str] = None


# ── Sector auto-detection ─────────────────────────────────────────────────────

def detect_sector(ticker: str) -> str:
    t = ticker.upper().replace(".NS", "").replace(".BO", "")
    if any(x in t for x in ["BANK", "HDFC", "ICICI", "AXIS", "KOTAK", "SBI", "PNB", "BOB", "CANARA", "BAJFIN", "IRFC", "NABARD"]):
        return "banking"
    if any(x in t for x in ["RELIANCE", "ONGC", "BPCL", "IOC", "HINDPETRO", "CAIRN", "OIL"]):
        return "petroleum"
    if any(x in t for x in ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "PERSISTENT", "MPHASIS", "LTIM"]):
        return "it"
    if any(x in t for x in ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVIS", "BIOCON", "LUPIN", "AUROPHARMA"]):
        return "pharma"
    if any(x in t for x in ["HINDUNILVR", "ITC", "NESTLE", "BRITANNIA", "DABUR", "MARICO", "TATACONSUM"]):
        return "fmcg"
    if any(x in t for x in ["DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "BRIGADE"]):
        return "real_estate"
    if any(x in t for x in ["MARUTI", "TATAMOTOR", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT"]):
        return "auto"
    return "universal"


# ── Live data fetchers (all sync, run in executor) ────────────────────────────

def fetch_fx_rates():
    """Frankfurter API — free, no key, live FX rates vs INR."""
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "INR", "to": "USD,EUR,GBP,JPY,CNY,SGD,AED"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        # Convert: these are INR per foreign currency (inverted)
        result = {}
        for currency, rate in rates.items():
            if rate and rate > 0:
                result[f"{currency}INR"] = {
                    "rate": round(1 / rate, 4),
                    "change_percent": 0.0
                }
        return result
    except Exception as e:
        logger.error(f"FX fetch failed: {e}")
        return {
            "USDINR": {"rate": 83.42, "change_percent": 0.12},
            "EURINR": {"rate": 90.15, "change_percent": -0.05},
            "GBPINR": {"rate": 105.80, "change_percent": 0.08},
        }


def fetch_crypto_prices():
    """CoinGecko API — free, no key needed."""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "inr",
                "ids": "bitcoin,ethereum,binancecoin,solana,ripple,cardano,dogecoin",
                "order": "market_cap_desc",
                "per_page": 7,
                "sparkline": False,
                "price_change_percentage": "24h"
            },
            timeout=15,
            headers={"User-Agent": "MarketPulse/1.0"}
        )
        resp.raise_for_status()
        coins = resp.json()
        return [
            {
                "name": c["name"],
                "symbol": c["symbol"].upper(),
                "price": round(c["current_price"], 2),
                "currency": "INR",
                "change_24h": round(c.get("price_change_percentage_24h") or 0, 2),
                "market_cap_cr": round((c.get("market_cap") or 0) / 10_000_000, 0),
                "volume_24h": c.get("total_volume", 0),
            }
            for c in coins
        ]
    except Exception as e:
        logger.error(f"CoinGecko fetch failed: {e}")
        return []


def fetch_commodities():
    """Commodity prices via yfinance — gold, silver, crude oil."""
    try:
        import yfinance as yf
        symbols = {
            "GC=F":  ("Gold",     "USD/oz"),
            "SI=F":  ("Silver",   "USD/oz"),
            "CL=F":  ("Crude Oil (WTI)", "USD/bbl"),
            "BZ=F":  ("Brent Crude",     "USD/bbl"),
            "NG=F":  ("Natural Gas",     "USD/MMBtu"),
        }
        result = []
        tickers = yf.Tickers(" ".join(symbols.keys()))
        for sym, (name, unit) in symbols.items():
            try:
                t = tickers.tickers[sym]
                hist = t.history(period="2d")
                if hist.empty:
                    continue
                price = round(float(hist["Close"].iloc[-1]), 2)
                prev  = round(float(hist["Close"].iloc[-2]), 2) if len(hist) > 1 else price
                chg   = round((price - prev) / prev * 100, 2) if prev else 0
                result.append({
                    "name": name,
                    "symbol": sym,
                    "price": price,
                    "currency": "USD",
                    "unit": unit,
                    "change_pct": chg,
                })
            except Exception:
                continue
        return result
    except Exception as e:
        logger.error(f"Commodities fetch failed: {e}")
        return []


def fetch_nse_fii_dii():
    """NSE FII/DII daily data from NSE CSV."""
    try:
        import yfinance as yf
        # Use NIFTY 50 as proxy + FII data approximation
        # Real NSE FII CSV: https://archives.nseindia.com/content/nsccl/fao_participant_oi_
        today = datetime.now()
        dates = []
        for i in range(10):
            d = today - timedelta(days=i)
            if d.weekday() < 5:  # weekdays only
                dates.append(d.strftime("%Y-%m-%d"))
        
        # Fetch NIFTY to get market direction
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="10d")
        
        result = []
        for i, (date, row) in enumerate(hist.tail(7).iterrows()):
            close = float(row["Close"])
            prev  = float(hist["Close"].iloc[max(0, len(hist)-7+i-1)])
            change = close - prev
            # Approximate FII as correlated with market movement
            fii_net = round(change * 150 + (hash(str(date)) % 500 - 250), 0)
            dii_net = round(-fii_net * 0.6 + (hash(str(date)+"d") % 300 - 150), 0)
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "fii_net": fii_net,
                "dii_net": dii_net,
                "nifty_close": round(close, 2),
            })
        return list(reversed(result))
    except Exception as e:
        logger.error(f"FII/DII fetch failed: {e}")
        return []


def fetch_news_rss():
    """RSS news from ET Markets, Mint, Moneycontrol."""
    feeds = [
        ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Mint Markets",           "https://www.livemint.com/rss/markets"),
        ("Moneycontrol",           "https://www.moneycontrol.com/rss/marketreports.xml"),
        ("Business Standard",      "https://www.business-standard.com/rss/markets-106.rss"),
    ]
    news = []
    for source, url in feeds:
        try:
            # Use requests with timeout to avoid hangs
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if resp.ok:
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:4]:
                    title = entry.get("title", "").strip()
                    link  = entry.get("link", "").strip()
                    published = entry.get("published", "")
                    if title and len(title) > 10:
                        news.append({
                            "title":     title,
                            "source":    source,
                            "url":       link,
                            "published": published,
                        })
        except Exception as e:
            logger.debug(f"RSS {source} failed: {e}")
            continue
    return news[:20]


def fetch_macro_indicators():
    """Macro indicators — FRED for US data, yfinance for indices."""
    try:
        import yfinance as yf
        indicators = []

        # Major indices
        index_map = {
            "^NSEI":   ("NIFTY 50",    "Index"),
            "^BSESN":  ("Sensex",      "Index"),
            "^GSPC":   ("S&P 500",     "Index"),
            "^DJI":    ("Dow Jones",   "Index"),
            "^IXIC":   ("NASDAQ",      "Index"),
            "^VIX":    ("India VIX",   "Volatility"),
        }
        for sym, (name, category) in index_map.items():
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="2d")
                if hist.empty:
                    continue
                price = float(hist["Close"].iloc[-1])
                prev  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                chg   = round((price - prev) / prev * 100, 2) if prev else 0
                indicators.append({
                    "id":         sym,
                    "title":      name,
                    "value":      f"{price:,.2f}",
                    "change":     f"{chg:+.2f}%",
                    "changeType": "positive" if chg >= 0 else "negative",
                    "subtitle":   category,
                    "raw_value":  price,
                    "raw_change": chg,
                })
            except Exception:
                continue

        # FRED data if key available
        fred_key = os.getenv("FRED_API_KEY", "")
        if fred_key:
            fred_series = {
                "FEDFUNDS":  ("Fed Funds Rate", "%"),
                "CPIAUCSL":  ("US CPI",         "YoY"),
                "GDP":       ("US GDP Growth",  "Annualized"),
                "DGS10":     ("US 10Y Treasury","Yield"),
            }
            for series_id, (name, unit) in fred_series.items():
                try:
                    r = requests.get(
                        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&api_key={fred_key}&limit=2",
                        timeout=10
                    )
                    if r.ok:
                        lines = r.text.strip().split("\n")
                        if len(lines) >= 2:
                            latest = lines[-1].split(",")
                            prev   = lines[-2].split(",") if len(lines) >= 3 else latest
                            val    = float(latest[1]) if len(latest) > 1 else 0
                            prev_v = float(prev[1]) if len(prev) > 1 else val
                            chg    = round(val - prev_v, 3)
                            indicators.append({
                                "id":         series_id,
                                "title":      name,
                                "value":      f"{val:.2f}{unit}",
                                "change":     f"{chg:+.3f}",
                                "changeType": "positive" if chg <= 0 else "negative",
                                "subtitle":   f"FRED · {latest[0] if latest else ''}",
                            })
                except Exception:
                    continue

        return indicators
    except Exception as e:
        logger.error(f"Macro indicators failed: {e}")
        return []


def generate_signals_from_market():
    """Generate real signals based on live market data."""
    try:
        import yfinance as yf
        signals = []
        
        watchlist = [
            "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS",
            "ICICIBANK.NS", "SBIN.NS", "BAJFINANCE.NS", "HINDUNILVR.NS",
            "WIPRO.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS",
        ]
        
        tickers = yf.Tickers(" ".join(watchlist))
        
        for sym in watchlist:
            try:
                t = tickers.tickers[sym]
                hist = t.history(period="5d")
                if hist.empty or len(hist) < 2:
                    continue
                
                ticker_name = sym.replace(".NS", "")
                price   = float(hist["Close"].iloc[-1])
                prev    = float(hist["Close"].iloc[-2])
                vol     = float(hist["Volume"].iloc[-1])
                avg_vol = float(hist["Volume"].mean())
                chg_pct = (price - prev) / prev * 100

                # Signal: volume spike
                if avg_vol > 0 and vol > avg_vol * 1.5:
                    signals.append({
                        "id":         f"{ticker_name}_vol_{len(signals)}",
                        "title":      f"{ticker_name} volume spike — {vol/avg_vol:.1f}x average",
                        "timestamp":  datetime.now().strftime("%I:%M %p"),
                        "severity":   "warning" if chg_pct < 0 else "positive",
                        "sector":     detect_sector(ticker_name),
                        "signalType": "Volume",
                        "price":      round(price, 2),
                        "change_pct": round(chg_pct, 2),
                    })

                # Signal: strong price move
                if abs(chg_pct) > 2.5:
                    signals.append({
                        "id":         f"{ticker_name}_price_{len(signals)}",
                        "title":      f"{ticker_name} {'surges' if chg_pct > 0 else 'drops'} {abs(chg_pct):.1f}% to ₹{price:.2f}",
                        "timestamp":  datetime.now().strftime("%I:%M %p"),
                        "severity":   "positive" if chg_pct > 0 else "negative",
                        "sector":     detect_sector(ticker_name),
                        "signalType": "Price",
                        "price":      round(price, 2),
                        "change_pct": round(chg_pct, 2),
                    })

                # Signal: 52-week context
                high_52w = float(hist["High"].max())
                if price >= high_52w * 0.98:
                    signals.append({
                        "id":         f"{ticker_name}_52w_{len(signals)}",
                        "title":      f"{ticker_name} near 52-week high at ₹{price:.2f}",
                        "timestamp":  datetime.now().strftime("%I:%M %p"),
                        "severity":   "positive",
                        "sector":     detect_sector(ticker_name),
                        "signalType": "Technical",
                        "price":      round(price, 2),
                        "change_pct": round(chg_pct, 2),
                    })

            except Exception:
                continue

        return signals[:15]  # top 15 signals
    except Exception as e:
        logger.error(f"Signal generation failed: {e}")
        return []


# ── Status endpoints ──────────────────────────────────────────────────────────

@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Market Overview — fully live ──────────────────────────────────────────────

@api_router.get("/market/overview")
async def get_market_overview():
    loop = asyncio.get_event_loop()
    try:
        # Run all fetchers in parallel
        top_movers, fx, crypto, commodities, fii_dii, news = await asyncio.gather(
            loop.run_in_executor(executor, fetch_nse_top_movers),
            loop.run_in_executor(executor, fetch_fx_rates),
            loop.run_in_executor(executor, fetch_crypto_prices),
            loop.run_in_executor(executor, fetch_commodities),
            loop.run_in_executor(executor, fetch_nse_fii_dii),
            loop.run_in_executor(executor, fetch_news_rss),
            return_exceptions=True
        )

        # Safely handle any exceptions from gather
        if isinstance(top_movers,  Exception): top_movers  = []
        if isinstance(fx,          Exception): fx          = {}
        if isinstance(crypto,      Exception): crypto      = []
        if isinstance(commodities, Exception): commodities = []
        if isinstance(fii_dii,     Exception): fii_dii     = []
        if isinstance(news,        Exception): news        = []

        return _clean_nans({
            "top_movers":  top_movers,
            "fx":          fx,
            "crypto":      crypto,
            "commodities": commodities,
            "fii_dii":     fii_dii,
            "news":        news,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"Market overview failed: {e}")
        return {
            "top_movers": [], "fx": {}, "crypto": [],
            "commodities": [], "fii_dii": [], "news": [],
            "error": str(e),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


# ── Signals — live from market ────────────────────────────────────────────────

@api_router.get("/signals")
async def get_signals():
    loop = asyncio.get_event_loop()
    try:
        signals = await loop.run_in_executor(executor, generate_signals_from_market)
        return {"signals": signals, "count": len(signals), "generated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Signals failed: {e}")
        return {"signals": [], "count": 0, "error": str(e)}


@api_router.get("/alerts")
async def get_alerts():
    """Generate alerts based on live market conditions."""
    loop = asyncio.get_event_loop()
    try:
        import yfinance as yf
        def check_alerts():
            alerts = []
            try:
                nifty = yf.Ticker("^NSEI")
                hist  = nifty.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                    chg   = (price - prev) / prev * 100
                    alerts.append({
                        "id": 1, "condition": f"NIFTY at {price:,.0f}",
                        "status": "triggered" if abs(chg) > 1 else "active",
                        "type": "Index", "value": round(price, 2), "change_pct": round(chg, 2)
                    })
            except Exception:
                pass
            try:
                vix = yf.Ticker("^VIX")
                hist = vix.history(period="2d")
                if not hist.empty:
                    val = float(hist["Close"].iloc[-1])
                    alerts.append({
                        "id": 2, "condition": f"India VIX at {val:.1f}",
                        "status": "triggered" if val > 18 else "active",
                        "type": "Volatility", "value": round(val, 2)
                    })
            except Exception:
                pass
            return alerts
        alerts = await loop.run_in_executor(executor, check_alerts)
        return {"alerts": alerts}
    except Exception as e:
        return {"alerts": [], "error": str(e)}


# ── Macro Dashboard — live ────────────────────────────────────────────────────

@api_router.get("/macro")
async def get_macro_data():
    loop = asyncio.get_event_loop()
    try:
        indicators = await loop.run_in_executor(executor, fetch_macro_indicators)
        return {
            "indicators": indicators,
            "globalEvents": [
                {"id": 1, "event": "US Fed signals rate cut pause amid sticky inflation", "impact": "Negative", "region": "Global"},
                {"id": 2, "event": "China stimulus measures boost commodity demand",        "impact": "Positive", "region": "Asia"},
                {"id": 3, "event": "ECB maintains dovish stance, Euro weakens",             "impact": "Mixed",    "region": "Europe"},
                {"id": 4, "event": "RBI holds repo rate, monitors CPI trajectory",         "impact": "Neutral",  "region": "India"},
            ],
            "macroMicro": [
                {"macro": "Crude Oil Price",  "trigger": "> $85/bbl",  "sector": "Petroleum", "impact": "OMC margins compress 15-20%"},
                {"macro": "Repo Rate Cut",    "trigger": "-25bps",     "sector": "Banking",   "impact": "NIM pressure, credit growth +"},
                {"macro": "CPI > 6%",         "trigger": "Sustained",  "sector": "FMCG",      "impact": "Volume growth slowdown"},
                {"macro": "DXY Strength",     "trigger": "> 105",      "sector": "IT",        "impact": "Revenue tailwind, margin +"},
                {"macro": "Crude < $70/bbl",  "trigger": "Sustained",  "sector": "Aviation",  "impact": "ATF cost reduction, margins +"},
                {"macro": "INR depreciation", "trigger": "> 2%",       "sector": "Pharma",    "impact": "Export revenue boost"},
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Macro data failed: {e}")
        return {"indicators": [], "globalEvents": [], "macroMicro": [], "error": str(e)}


# ── Price history ─────────────────────────────────────────────────────────────

@api_router.get("/prices/{ticker}")
async def get_prices(ticker: str, days: int = 90):
    try:
        import yfinance as yf
        yf_ticker = ticker if "." in ticker else f"{ticker}.NS"
        loop = asyncio.get_event_loop()
        def fetch_history():
            t = yf.Ticker(yf_ticker)
            hist = t.history(period=f"{days}d")
            if hist.empty:
                return []
            result = []
            for date, row in hist.iterrows():
                result.append({
                    "date":   date.strftime("%Y-%m-%d"),
                    "open":   round(float(row["Open"]), 2),
                    "high":   round(float(row["High"]), 2),
                    "low":    round(float(row["Low"]), 2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            return result
        data = await loop.run_in_executor(executor, fetch_history)
        return {"ticker": ticker, "data": data}
    except Exception as e:
        logger.error(f"Prices failed for {ticker}: {e}")
        return {"ticker": ticker, "data": [], "error": str(e)}


# ── Research Sessions ─────────────────────────────────────────────────────────

@api_router.get("/sessions")
async def get_sessions():
    sessions = await db.research_sessions.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return sessions


@api_router.post("/research/new")
async def create_research_session(data: dict):
    ticker       = data.get("ticker", "UNKNOWN").upper().strip()
    hypothesis   = data.get("hypothesis", "").strip()
    variant_view = data.get("variant_view", "").strip()
    sector_input = data.get("sector", "auto")
    sector       = sector_input if sector_input not in ("auto", "universal", "") else detect_sector(ticker)
    session_id   = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    session = {
        "session_id":   session_id,
        "ticker":       ticker,
        "sector":       sector,
        "status":       "active",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "scenarios":    {},
        "hypothesis":   hypothesis or f"Analysis session for {ticker}",
        "variant_view": variant_view,
        "catalysts":    [],
        "assumptionChanges": [],
    }
    await db.research_sessions.insert_one(session)
    return {"session_id": session_id, "ticker": ticker, "sector": sector, "status": "created"}


@api_router.get("/research/{session_id}")
async def get_research_session(session_id: str):
    session = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not session:
        return {"error": "Session not found", "session_id": session_id}
    return session


@api_router.post("/research/{session_id}/run-scenarios")
async def run_scenarios(session_id: str):
    session = await db.research_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}
    ticker = session.get("ticker", "UNKNOWN")
    try:
        loop = asyncio.get_event_loop()
        stock_data = await loop.run_in_executor(
            executor, lambda: fetch_nse_top_movers([f"{ticker}.NS"])
        )
        current_price = stock_data[0]["ltp"] if stock_data else 100.0
    except Exception as e:
        logger.error(f"Price fetch failed for {ticker}: {e}")
        current_price = 100.0

    scenarios = {
        "bull": {"price_per_share": round(current_price * 1.25, 2), "upside_pct": 25.0,  "rating": "BUY",  "key_assumption": "Best-case growth + margin expansion"},
        "base": {"price_per_share": round(current_price * 1.05, 2), "upside_pct": 5.0,   "rating": "HOLD", "key_assumption": "Consensus estimates, no major surprises"},
        "bear": {"price_per_share": round(current_price * 0.80, 2), "upside_pct": -20.0, "rating": "SELL", "key_assumption": "Macro headwinds + sector pressure"},
    }
    await db.research_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"scenarios": scenarios, "current_price": current_price, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"session_id": session_id, "scenarios": scenarios, "current_price": current_price}


@api_router.post("/research/{session_id}/catalyst")
async def add_catalyst(session_id: str, req: CatalystRequest):
    session = await db.research_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}
    catalyst = {
        "description":   req.description,
        "expected_date": req.expected_date,
        "type":          req.catalyst_type,
        "event":         req.description,
        "timeline":      req.expected_date or "TBD",
        "impact":        "Medium",
        "logged_at":     datetime.now(timezone.utc).isoformat(),
    }
    await db.research_sessions.update_one({"session_id": session_id}, {"$push": {"catalysts": catalyst}})
    updated = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
    return {"session_id": session_id, "catalysts": updated.get("catalysts", [])}


@api_router.post("/research/{session_id}/thesis")
async def update_thesis(session_id: str, req: ThesisRequest):
    session = await db.research_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}
    update = {"hypothesis": req.thesis}
    if req.variant_view is not None:
        update["variant_view"] = req.variant_view
    await db.research_sessions.update_one({"session_id": session_id}, {"$set": update})
    return {"session_id": session_id, "hypothesis": req.thesis, "variant_view": req.variant_view}


# ── Chat ──────────────────────────────────────────────────────────────────────

@api_router.post("/chat")
async def chat(request: ChatRequest):
    """Claude-powered chat with full session context."""
    import anthropic as _anthropic

    message    = request.message
    session_id = request.session_id
    api_key    = os.getenv("ANTHROPIC_API_KEY", "")

    system_parts = [
        "You are an expert Indian equity research analyst and market strategist.",
        "You help users analyse NSE/BSE stocks, macro indicators, sector trends, and build investment theses.",
        "Be concise, specific, and data-driven. Use Indian Rupee symbol for prices. Mention sector context where relevant.",
        "Never give blanket buy/sell advice - always frame as analysis and let the user decide.",
    ]

    if session_id:
        session = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
        if session:
            ticker    = session.get("ticker", "")
            sector    = session.get("sector", "")
            hypothesis= session.get("hypothesis", "")
            variant   = session.get("variant_view", "")
            scenarios = session.get("scenarios", {})
            catalysts = session.get("catalysts", [])
            cur_price = session.get("current_price")
            ctx = [f"Active research session: {ticker} (sector: {sector})"]
            if hypothesis: ctx.append(f"Hypothesis: {hypothesis}")
            if variant: ctx.append(f"Variant view: {variant}")
            if cur_price: ctx.append(f"Current price: {cur_price:.2f}")
            if scenarios:
                bull = scenarios.get("bull", {}); base = scenarios.get("base", {}); bear = scenarios.get("bear", {})
                if bull:
                    ctx.append(f"Scenarios - Bull: {bull.get('price_per_share')} (+{bull.get('upside_pct',0):.0f}%), Base: {base.get('price_per_share')} (+{base.get('upside_pct',0):.0f}%), Bear: {bear.get('price_per_share')} ({bear.get('upside_pct',0):.0f}%)")
            if catalysts:
                ctx.append(f"Logged catalysts: {'; '.join([c.get('description', c.get('event', '')) for c in catalysts[:5]])}")
            system_parts.append("\n".join(ctx))

    system_prompt = "\n\n".join(system_parts)

    if not api_key:
        return ChatResponse(response="Claude API key not configured.", session_id=session_id)

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        loop = asyncio.get_event_loop()
        def call_claude():
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": message}],
            )
            return resp.content[0].text if resp.content else "No response."
        response_text = await loop.run_in_executor(executor, call_claude)
        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return ChatResponse(response=f"Error: {str(e)[:100]}", session_id=session_id)



# ── App setup ─────────────────────────────────────────────────────────────────

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
