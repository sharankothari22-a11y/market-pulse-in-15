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


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
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

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


# ============== Market Overview Endpoint ==============

@api_router.get("/market/overview")
async def get_market_overview():
    """
    Get market overview including NSE top movers, FX rates, commodities, and news.
    Uses yfinance for real-time NSE stock data.
    """
    try:
        # Fetch NSE stocks in thread pool (yfinance is sync)
        loop = asyncio.get_event_loop()
        top_movers = await loop.run_in_executor(executor, fetch_nse_top_movers)
        
        # Return market overview data
        return {
            "top_movers": top_movers,
            "indices": [],  # Will be populated with NSE indices later
            "fx": {
                "USDINR": {"rate": 83.42, "change_percent": 0.12},
                "EURINR": {"rate": 90.15, "change_percent": -0.05},
                "GBPINR": {"rate": 105.80, "change_percent": 0.08},
            },
            "commodities": [],  # Can add commodity data later
            "fii_dii": [],  # Can add FII/DII data later
            "news": [],  # Can add news feed later
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        return {
            "top_movers": [],
            "indices": [],
            "fx": {},
            "commodities": [],
            "fii_dii": [],
            "news": [],
            "error": str(e),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============== Research Session Endpoints ==============

@api_router.get("/sessions")
async def get_sessions():
    """Get all research sessions."""
    sessions = await db.research_sessions.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return sessions


@api_router.post("/research/new")
async def create_research_session(data: dict):
    """Create a new research session."""
    ticker = data.get("ticker", "UNKNOWN").upper()
    session_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    session = {
        "session_id": session_id,
        "ticker": ticker,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": {},
        "hypothesis": f"Analysis session for {ticker}",
        "catalysts": [],
        "assumptionChanges": [],
    }
    
    await db.research_sessions.insert_one(session)
    return {"session_id": session_id, "ticker": ticker, "status": "created"}


@api_router.get("/research/{session_id}")
async def get_research_session(session_id: str):
    """Get research session data."""
    session = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not session:
        return {"error": "Session not found", "session_id": session_id}
    return session


@api_router.post("/research/{session_id}/run-scenarios")
async def run_scenarios(session_id: str):
    """Run scenario analysis for a research session."""
    session = await db.research_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}
    
    ticker = session.get("ticker", "UNKNOWN")
    
    # Fetch current price using yfinance
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
    
    # Generate scenarios based on current price
    scenarios = {
        "bull": {
            "price_per_share": round(current_price * 1.25, 2),
            "upside_pct": 25.0,
            "rating": "BUY",
        },
        "base": {
            "price_per_share": round(current_price * 1.05, 2),
            "upside_pct": 5.0,
            "rating": "HOLD",
        },
        "bear": {
            "price_per_share": round(current_price * 0.80, 2),
            "upside_pct": -20.0,
            "rating": "SELL",
        },
    }
    
    # Update session with scenarios
    await db.research_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "scenarios": scenarios,
            "current_price": current_price,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    
    return {"session_id": session_id, "scenarios": scenarios, "current_price": current_price}


# ============== Signals & Alerts Endpoints ==============

@api_router.get("/signals")
async def get_signals():
    """Get market signals."""
    return {
        "signals": [
            {"id": 1, "title": "RELIANCE breaks resistance at ₹2,950", "timestamp": "10:30 AM", "severity": "positive", "sector": "Energy", "signalType": "Technical"},
            {"id": 2, "title": "Banking sector under pressure from NIM concerns", "timestamp": "09:45 AM", "severity": "warning", "sector": "Banking", "signalType": "Fundamental"},
            {"id": 3, "title": "IT stocks rally on strong deal pipeline", "timestamp": "09:15 AM", "severity": "positive", "sector": "IT", "signalType": "News"},
        ]
    }


@api_router.get("/alerts")
async def get_alerts():
    """Get active alerts."""
    return {
        "alerts": [
            {"id": 1, "condition": "NIFTY crosses 24,800", "status": "active", "type": "Price Alert"},
            {"id": 2, "condition": "RELIANCE volume > 15M", "status": "active", "type": "Volume Alert"},
            {"id": 3, "condition": "VIX > 18", "status": "triggered", "type": "Volatility Alert"},
        ]
    }


# ============== Macro Dashboard Endpoints ==============

@api_router.get("/macro")
async def get_macro_data():
    """Get macroeconomic data."""
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


# ============== Chat Endpoint ==============

@api_router.post("/chat")
async def chat(request: ChatRequest):
    """Handle chat messages with optional session context."""
    message = request.message.lower()
    session_id = request.session_id
    
    # Generate contextual response
    if session_id:
        # Fetch session data for context
        session = await db.research_sessions.find_one({"session_id": session_id}, {"_id": 0})
        ticker = session.get("ticker", "the stock") if session else "the stock"
        
        if "scenario" in message or "bull" in message or "bear" in message:
            response = f"Based on the {ticker} analysis, the bull case suggests 25% upside while the bear case shows 20% downside risk. Current valuation appears reasonable."
        elif "price" in message or "target" in message:
            response = f"The {ticker} price targets are: Bull ₹{session.get('scenarios', {}).get('bull', {}).get('price_per_share', 'N/A')}, Base ₹{session.get('scenarios', {}).get('base', {}).get('price_per_share', 'N/A')}, Bear ₹{session.get('scenarios', {}).get('bear', {}).get('price_per_share', 'N/A')}."
        else:
            response = f"I'm analyzing {ticker} in session {session_id}. You can ask about scenarios, price targets, or catalysts."
    else:
        # General market questions
        if "nifty" in message:
            response = "NIFTY is showing bullish momentum with support at 24,200. Key resistance at 24,800. FII flows remain a concern."
        elif "reliance" in message:
            response = "RELIANCE trading near ₹2,945. Sum-of-parts suggests 15% upside. Watch for Jio IPO timeline clarity."
        elif "bank" in message:
            response = "Banking sector facing NIM pressure from rate cut expectations. PSU banks preferred over private for value play."
        elif "it" in message or "infosys" in message or "tcs" in message:
            response = "IT sector headwinds from US slowdown. Infosys and TCS showing resilience. Mid-caps attractive at current valuations."
        else:
            response = "I can help you analyze Indian market trends, stock signals, and macro indicators. Ask me about specific stocks, sectors, or market conditions."
    
    return ChatResponse(response=response, session_id=session_id)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()