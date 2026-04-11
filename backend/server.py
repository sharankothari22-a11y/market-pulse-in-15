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
from datetime import datetime, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import yfinance collector
from collectors.yfinance_nse import fetch_nse_top_movers, NSE_TOP_10


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Thread pool for running sync functions
executor = ThreadPoolExecutor(max_workers=3)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
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
    _ = await db.status_checks.insert_one(doc)
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


# ── Market Overview ───────────────────────────────────────────────────────────

@api_router.get("/market/overview")
async def get_market_overview():
    try:
        loop = asyncio.get_event_loop()
        top_movers = await loop.run_in_executor(executor, fetch_nse_top_movers)
        return {
            "top_movers": top_movers,
            "indices": [],
            "fx": {
                "USDINR": {"rate": 83.42, "change_percent": 0.12},
                "EURINR": {"rate": 90.15, "change_percent": -0.05},
                "GBPINR": {"rate": 105.80, "change_percent": 0.08},
            },
            "commodities": [],
            "fii_dii": [],
            "news": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        return {
            "top_movers": [], "indices": [], "fx": {},
            "commodities": [], "fii_dii": [], "news": [],
            "error": str(e),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


# ── Price history ─────────────────────────────────────────────────────────────

@api_router.get("/prices/{ticker}")
async def get_prices(ticker: str, days: int = 90):
    """Get price history for a ticker using yfinance."""
    try:
        import yfinance as yf
        from datetime import timedelta
        
        # Add .NS suffix if not present
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
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            return result
        
        data = await loop.run_in_executor(executor, fetch_history)
        return {"ticker": ticker, "data": data}
    except Exception as e:
        logger.error(f"Error fetching prices for {ticker}: {e}")
        return {"ticker": ticker, "data": [], "error": str(e)}


# ── Research Sessions ─────────────────────────────────────────────────────────

@api_router.get("/sessions")
async def get_sessions():
    sessions = await db.research_sessions.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return sessions


@api_router.post("/research/new")
async def create_research_session(data: dict):
    ticker = data.get("ticker", "UNKNOWN").upper().strip()
    hypothesis = data.get("hypothesis", "").strip()
    variant_view = data.get("variant_view", "").strip()
    sector_input = data.get("sector", "auto")
    
    # Auto-detect sector
    sector = sector_input if sector_input not in ("auto", "universal", "") else detect_sector(ticker)
    
    session_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    session = {
        "session_id": session_id,
        "ticker": ticker,
        "sector": sector,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": {},
        "hypothesis": hypothesis or f"Analysis session for {ticker}",
        "variant_view": variant_view,
        "catalysts": [],
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
            executor,
            lambda: fetch_nse_top_movers([f"{ticker}.NS"])
        )
        current_price = stock_data[0]["ltp"] if stock_data else 100.0
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        current_price = 100.0
    
    scenarios = {
        "bull": {
            "price_per_share": round(current_price * 1.25, 2),
            "upside_pct": 25.0,
            "rating": "BUY",
            "key_assumption": "Best-case growth + margin expansion",
        },
        "base": {
            "price_per_share": round(current_price * 1.05, 2),
            "upside_pct": 5.0,
            "rating": "HOLD",
            "key_assumption": "Consensus estimates, no major surprises",
        },
        "bear": {
            "price_per_share": round(current_price * 0.80, 2),
            "upside_pct": -20.0,
            "rating": "SELL",
            "key_assumption": "Macro headwinds + sector pressure",
        },
    }
    
    await db.research_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "scenarios": scenarios,
            "current_price": current_price,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    
    return {"session_id": session_id, "scenarios": scenarios, "current_price": current_price}


@api_router.post("/research/{session_id}/catalyst")
async def add_catalyst(session_id: str, req: CatalystRequest):
    """Add a catalyst to a research session."""
    session = await db.research_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}
    
    catalyst = {
        "description": req.description,
        "expected_date": req.expected_date,
        "type": req.catalyst_type,
        "logged_at": datetime.now(timezone.utc).isoformat(),
        # Map to frontend's expected keys too
        "event": req.description,
        "timeline": req.expected_date or "TBD",
        "impact": "Medium",
    }
    
    await db.research_sessions.update_one(
        {"session_id": session_id},
        {"$push": {"catalysts": catalyst}}
    )
    
    updated = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
    return {"session_id": session_id, "catalysts": updated.get("catalysts", [])}


@api_router.post("/research/{session_id}/thesis")
async def update_thesis(session_id: str, req: ThesisRequest):
    """Update hypothesis and variant view for a session."""
    session = await db.research_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}
    
    update = {"hypothesis": req.thesis}
    if req.variant_view is not None:
        update["variant_view"] = req.variant_view
    
    await db.research_sessions.update_one(
        {"session_id": session_id},
        {"$set": update}
    )
    
    return {
        "session_id": session_id,
        "hypothesis": req.thesis,
        "variant_view": req.variant_view,
    }


# ── Signals & Alerts ──────────────────────────────────────────────────────────

@api_router.get("/signals")
async def get_signals():
    return {
        "signals": [
            {"id": 1, "title": "RELIANCE breaks resistance at ₹2,950", "timestamp": "10:30 AM", "severity": "positive", "sector": "Energy", "signalType": "Technical"},
            {"id": 2, "title": "Banking sector under pressure from NIM concerns", "timestamp": "09:45 AM", "severity": "warning", "sector": "Banking", "signalType": "Fundamental"},
            {"id": 3, "title": "IT stocks rally on strong deal pipeline", "timestamp": "09:15 AM", "severity": "positive", "sector": "IT", "signalType": "News"},
        ]
    }

@api_router.get("/alerts")
async def get_alerts():
    return {
        "alerts": [
            {"id": 1, "condition": "NIFTY crosses 24,800", "status": "active", "type": "Price Alert"},
            {"id": 2, "condition": "RELIANCE volume > 15M", "status": "active", "type": "Volume Alert"},
            {"id": 3, "condition": "VIX > 18", "status": "triggered", "type": "Volatility Alert"},
        ]
    }


# ── Macro Dashboard ───────────────────────────────────────────────────────────

@api_router.get("/macro")
async def get_macro_data():
    return {
        "indicators": [
            {"id": "gdp", "title": "GDP Growth", "value": "7.2%", "change": "+0.3%", "changeType": "positive", "subtitle": "Q3 FY25 YoY"},
            {"id": "cpi", "title": "CPI Inflation", "value": "4.8%", "change": "-0.2%", "changeType": "positive", "subtitle": "Jan 2025"},
            {"id": "repo", "title": "Repo Rate", "value": "6.50%", "change": "0.00%", "changeType": "neutral", "subtitle": "RBI Policy"},
            {"id": "fed", "title": "Fed Funds", "value": "4.50%", "change": "-0.25%", "changeType": "positive", "subtitle": "US Federal Reserve"},
        ],
        "globalEvents": [
            {"id": 1, "event": "US Fed signals rate cut pause amid sticky inflation", "impact": "Negative", "region": "Global"},
            {"id": 2, "event": "China stimulus measures boost commodity demand", "impact": "Positive", "region": "Asia"},
            {"id": 3, "event": "ECB maintains dovish stance, Euro weakens", "impact": "Mixed", "region": "Europe"},
        ],
        "macroMicro": [
            {"macro": "Crude Oil Price", "trigger": "> $85/bbl", "sector": "Petroleum", "impact": "OMC margins compress 15-20%"},
            {"macro": "Repo Rate Cut", "trigger": "-25bps", "sector": "Banking", "impact": "NIM pressure, credit growth +"},
            {"macro": "CPI > 6%", "trigger": "Sustained", "sector": "FMCG", "impact": "Volume growth slowdown"},
            {"macro": "DXY Strength", "trigger": "> 105", "sector": "IT", "impact": "Revenue tailwind, margin +"},
        ],
    }


# ── Chat ──────────────────────────────────────────────────────────────────────

@api_router.post("/chat")
async def chat(request: ChatRequest):
    message = request.message.lower()
    session_id = request.session_id

    if session_id:
        session = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
        if not session:
            return ChatResponse(response="Session not found. Please start a new session.", session_id=session_id)

        ticker = session.get("ticker", "the stock")
        sector = session.get("sector", "universal")
        hypothesis = session.get("hypothesis", "")
        variant = session.get("variant_view", "")
        scenarios = session.get("scenarios", {})
        catalysts = session.get("catalysts", [])
        current_price = session.get("current_price")

        # Handle catalyst logging via chat
        if "add catalyst" in message or "catalyst" in message and any(w in message for w in ["add", "log", "track"]):
            parts = request.message.replace("add catalyst", "").replace("log catalyst", "").strip()
            if parts:
                catalyst = {
                    "description": parts,
                    "event": parts,
                    "timeline": "TBD",
                    "impact": "Medium",
                    "type": "general",
                    "logged_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.research_sessions.update_one(
                    {"session_id": session_id},
                    {"$push": {"catalysts": catalyst}}
                )
                return ChatResponse(response=f"Catalyst logged: '{parts}'. You can view it in the Catalysts section.", session_id=session_id)

        # Handle thesis update via chat
        if any(w in message for w in ["my thesis is", "thesis:", "hypothesis is", "hypothesis:"]):
            thesis_text = request.message
            for prefix in ["my thesis is", "thesis:", "hypothesis is", "hypothesis:"]:
                thesis_text = thesis_text.lower().replace(prefix, "").strip()
            if thesis_text:
                await db.research_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"hypothesis": thesis_text}}
                )
                return ChatResponse(response=f"Thesis updated: '{thesis_text}'", session_id=session_id)

        # Scenario questions
        if any(w in message for w in ["scenario", "bull", "bear", "base", "price target", "target"]):
            bull = scenarios.get("bull", {})
            base = scenarios.get("base", {})
            bear = scenarios.get("bear", {})
            if bull:
                response = (
                    f"{ticker} price targets — "
                    f"Bull: ₹{bull.get('price_per_share', 'N/A')} (+{bull.get('upside_pct', 0):.0f}%) | "
                    f"Base: ₹{base.get('price_per_share', 'N/A')} (+{base.get('upside_pct', 0):.0f}%) | "
                    f"Bear: ₹{bear.get('price_per_share', 'N/A')} ({bear.get('upside_pct', 0):.0f}%). "
                    f"Bull case assumes best-case growth. Bear case reflects macro headwinds."
                )
            else:
                response = f"No scenarios run yet for {ticker}. Click 'Run Scenarios' to generate price targets."

        # Hypothesis / thesis
        elif any(w in message for w in ["hypothesis", "thesis", "variant", "view"]):
            response = f"Thesis: {hypothesis or 'Not set'}. Variant view: {variant or 'Not set'}."

        # Catalyst questions
        elif "catalyst" in message:
            if catalysts:
                cat_list = ", ".join([c.get("description", c.get("event", "")) for c in catalysts[:3]])
                response = f"Catalysts for {ticker}: {cat_list}."
            else:
                response = f"No catalysts logged for {ticker} yet. Use the + Add Catalyst button or say 'add catalyst [description]'."

        # Current price
        elif any(w in message for w in ["price", "ltp", "current", "trading"]):
            if current_price:
                response = f"{ticker} is currently at ₹{current_price:.2f}. Sector: {sector}."
            else:
                response = f"Click 'Run Scenarios' to fetch live price for {ticker}."

        # Sector / macro
        elif any(w in message for w in ["sector", "macro", "moving", "why"]):
            sector_notes = {
                "banking": "Banking sector driven by NIM trends, RBI rate decisions, and credit growth.",
                "petroleum": "Petroleum sector tied to crude oil prices and GRM (gross refining margins).",
                "it": "IT sector driven by US deal flow, attrition, and USD/INR movement.",
                "pharma": "Pharma driven by FDA approvals, R&D pipeline, and API prices.",
                "fmcg": "FMCG driven by volume growth, rural demand, and input cost inflation.",
            }
            note = sector_notes.get(sector, f"{ticker} is in the {sector} sector.")
            response = f"{note} Current thesis: {hypothesis or 'not set'}."

        else:
            response = (
                f"I'm analysing {ticker} (session: {session_id[-8:]}). "
                f"Sector: {sector}. "
                f"You can ask about: scenarios, price targets, hypothesis, catalysts, or why {ticker} is moving."
            )
    else:
        # No session — general market questions
        if "nifty" in message:
            response = "NIFTY showing bullish momentum with support at 24,200. Key resistance at 24,800. FII flows remain a concern."
        elif "reliance" in message:
            response = "RELIANCE near ₹2,945. Sum-of-parts suggests 15% upside. Watch for Jio IPO clarity."
        elif "bank" in message:
            response = "Banking sector facing NIM pressure from rate cut expectations. PSU banks preferred for value."
        elif any(w in message for w in ["it", "infosys", "tcs", "wipro"]):
            response = "IT sector headwinds from US slowdown. TCS and Infosys showing resilience. Mid-caps attractive."
        else:
            response = "I can help with Indian market trends, stock signals, and macro indicators. Start a research session by entering a ticker and clicking Analyze."

    return ChatResponse(response=response, session_id=session_id)


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
