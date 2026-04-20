"""
api_server.py
─────────────
FastAPI backend for the Emergent frontend dashboard.

Run:
    cd research_platform
    uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

All endpoints return JSON. CORS is open for localhost Emergent dev.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Research Platform API",
    description="Unified Financial Intelligence System — Backend API",
    version="1.0.0",
)

# CORS — allow Emergent dev server and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to Emergent URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _db():
    from database.connection import get_session
    return get_session()

def _now_ist() -> str:
    from datetime import timezone as tz
    import pytz
    return datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Simple health check — Emergent pings this to confirm backend is up."""
    from database.connection import check_connection
    return {
        "status":    "ok",
        "db":        check_connection(),
        "timestamp": _now_ist(),
    }


@app.get("/api/status")
def system_status():
    """Full system status — collector health, table row counts, last runs."""
    from sqlalchemy import select, func, desc
    from database.models import (
        CollectionLog, PriceHistory, FiiDiiFlow, CommodityPrice,
        FxRate, MacroIndicator, Event, FundNav,
    )

    result: dict[str, Any] = {"timestamp": _now_ist(), "collectors": [], "tables": {}}

    try:
        with _db() as session:
            # Last run per collector
            subq = (
                select(CollectionLog.source_name,
                       func.max(CollectionLog.timestamp).label("last_ts"))
                .group_by(CollectionLog.source_name)
                .subquery()
            )
            logs = session.scalars(
                select(CollectionLog).join(
                    subq,
                    (CollectionLog.source_name == subq.c.source_name) &
                    (CollectionLog.timestamp == subq.c.last_ts),
                )
            ).all()

            result["collectors"] = [
                {
                    "source":   l.source_name,
                    "status":   l.status,
                    "records":  l.records_collected,
                    "method":   l.method_used,
                    "fallback": l.fallback_used,
                    "last_run": l.timestamp.isoformat() if l.timestamp else None,
                }
                for l in sorted(logs, key=lambda x: x.source_name)
            ]

            # Table counts
            for name, model in [
                ("price_history",    PriceHistory),
                ("fii_dii_flows",    FiiDiiFlow),
                ("commodity_prices", CommodityPrice),
                ("fx_rates",         FxRate),
                ("macro_indicators", MacroIndicator),
                ("fund_nav",         FundNav),
                ("events",           Event),
            ]:
                result["tables"][name] = session.scalar(
                    select(func.count()).select_from(model)
                ) or 0

    except Exception as exc:
        result["error"] = str(exc)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/market/overview")
def market_overview():
    """
    Everything needed for the Market Overview page.
    Returns: indices, top movers, FII/DII, FX, commodities.
    """
    from sqlalchemy import select, desc, func
    from database.models import PriceHistory, FiiDiiFlow, FxRate, CommodityPrice, Event

    result: dict[str, Any] = {}

    try:
        with _db() as session:
            # Latest date in price_history
            latest_date = session.scalar(
                select(PriceHistory.date).order_by(desc(PriceHistory.date)).limit(1)
            )
            prev_date = latest_date - timedelta(days=1) if latest_date else None
            result["data_date"] = str(latest_date) if latest_date else None

            # Top movers by volume (NSE)
            if latest_date:
                today_prices = session.scalars(
                    select(PriceHistory)
                    .where(PriceHistory.date == latest_date, PriceHistory.exchange == "NSE")
                    .order_by(desc(PriceHistory.volume))
                    .limit(20)
                ).all()

                prev_map: dict[str, float] = {}
                if prev_date:
                    prev_rows = session.scalars(
                        select(PriceHistory)
                        .where(PriceHistory.date == prev_date, PriceHistory.exchange == "NSE")
                    ).all()
                    prev_map = {r.ticker: float(r.close) for r in prev_rows}

                movers = []
                for p in today_prices:
                    prev_close = prev_map.get(p.ticker)
                    change_pct = None
                    if prev_close and prev_close > 0:
                        change_pct = round((float(p.close) - prev_close) / prev_close * 100, 2)
                    movers.append({
                        "ticker":     p.ticker,
                        "close":      float(p.close),
                        "open":       float(p.open) if p.open else None,
                        "high":       float(p.high) if p.high else None,
                        "low":        float(p.low) if p.low else None,
                        "volume":     int(p.volume) if p.volume else 0,
                        "change_pct": change_pct,
                    })
                result["top_movers"] = movers

            # FII / DII latest
            fii_rows = session.scalars(
                select(FiiDiiFlow).order_by(desc(FiiDiiFlow.date)).limit(60)
            ).all()
            result["fii_dii"] = [
                {
                    "date":     str(r.date),
                    "category": r.category,
                    "buy_cr":   round(float(r.buy_value or 0) / 100, 2),
                    "sell_cr":  round(float(r.sell_value or 0) / 100, 2),
                    "net_cr":   round(float(r.net_value or 0) / 100, 2),
                }
                for r in fii_rows
            ]

            # FX rates latest
            fx_rows = session.scalars(
                select(FxRate).order_by(desc(FxRate.date)).limit(20)
            ).all()
            result["fx"] = {r.pair: float(r.rate) for r in fx_rows}

            # Commodities latest (crypto + energy)
            comm_rows = session.scalars(
                select(CommodityPrice).order_by(desc(CommodityPrice.date)).limit(30)
            ).all()
            result["commodities"] = [
                {
                    "name":       (r.extra_data or {}).get("name", f"id_{r.commodity_id}"),
                    "symbol":     (r.extra_data or {}).get("symbol", ""),
                    "price":      float(r.price),
                    "currency":   r.currency,
                    "change_24h": (r.extra_data or {}).get("price_change_pct_24h"),
                    "date":       str(r.date),
                }
                for r in comm_rows
            ]

            # Latest news
            news = session.scalars(
                select(Event).order_by(desc(Event.created_at)).limit(20)
            ).all()
            result["news"] = [
                {
                    "title":      n.title,
                    "type":       n.type,
                    "entity":     n.entity_type,
                    "date":       str(n.date) if n.date else None,
                    "impact":     n.impact_score,
                    "source_url": n.source_url,
                }
                for n in news
            ]

    except Exception as exc:
        result["error"] = str(exc)

    return result


@app.get("/api/prices/{ticker}")
def get_prices(ticker: str, days: int = 90):
    """Price history for a ticker. Used for stock charts."""
    from sqlalchemy import select, desc
    from database.models import PriceHistory

    ticker = ticker.upper()
    try:
        with _db() as session:
            rows = session.scalars(
                select(PriceHistory)
                .where(PriceHistory.ticker == ticker)
                .order_by(desc(PriceHistory.date))
                .limit(days)
            ).all()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

        return {
            "ticker": ticker,
            "data": [
                {
                    "date":   str(r.date),
                    "open":   float(r.open) if r.open else None,
                    "high":   float(r.high) if r.high else None,
                    "low":    float(r.low) if r.low else None,
                    "close":  float(r.close),
                    "volume": int(r.volume) if r.volume else 0,
                }
                for r in reversed(rows)
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# MACRO DATA
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/macro")
def macro_data():
    """All macro indicators — India and global. Used for Macro Dashboard page."""
    from sqlalchemy import select, desc
    from database.models import MacroIndicator

    try:
        with _db() as session:
            rows = session.scalars(
                select(MacroIndicator).order_by(desc(MacroIndicator.date)).limit(500)
            ).all()

        # Group by indicator, return latest + history
        from collections import defaultdict
        by_indicator: dict[str, list] = defaultdict(list)
        for r in rows:
            by_indicator[r.indicator].append({
                "date":   str(r.date),
                "value":  r.value,
                "source": r.source,
            })

        return {
            "indicators": {
                k: {"latest": v[0], "history": v[:24]}
                for k, v in by_indicator.items()
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# SIGNALS & ALERTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/signals")
def get_signals(sector: Optional[str] = None, severity: Optional[str] = None, limit: int = 50):
    """Latest signals from the event table. Used for Signals & Alerts page."""
    from sqlalchemy import select, desc
    from database.models import Event

    try:
        with _db() as session:
            stmt = select(Event).order_by(desc(Event.created_at)).limit(limit * 3)
            rows = session.scalars(stmt).all()

        signals = [
            {
                "id":       r.id,
                "title":    r.title,
                "type":     r.type,
                "entity":   r.entity_type,
                "date":     str(r.date) if r.date else None,
                "impact":   r.impact_score,
                "url":      r.source_url,
            }
            for r in rows
        ]
        return {"signals": signals[:limit], "total": len(signals)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/alerts")
def get_alerts():
    """Run threshold alert checks. Returns triggered alerts."""
    from ai_engine.output_engine import check_alerts
    try:
        alerts = check_alerts()
        return {"alerts": alerts, "count": len(alerts), "checked_at": _now_ist()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH SESSION
# ─────────────────────────────────────────────────────────────────────────────

class NewSessionRequest(BaseModel):
    ticker: str
    sector: str = "universal"
    hypothesis: Optional[str] = None
    variant_view: Optional[str] = None

class UpdateAssumptionRequest(BaseModel):
    metric: str
    value: float
    reason: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    ticker: Optional[str] = None


@app.post("/api/research/new")
def new_research_session(req: NewSessionRequest):
    """Start a new research session for a ticker."""
    from ai_engine.session_manager import new_session
    from ai_engine.dcf_bridge import build_full_assumptions
    from ai_engine.assumption_engine import AssumptionEngine

    try:
        ses = new_session(
            req.ticker.upper(),
            hypothesis=req.hypothesis,
            variant_view=req.variant_view,
        )
        base = build_full_assumptions(req.ticker.upper(), sector=req.sector)
        AssumptionEngine(ses).initialize(base)

        return {
            "session_id": ses.session_id,
            "ticker":     ses.ticker,
            "sector":     req.sector,
            "assumptions": {k: v for k, v in base.items() if not k.startswith("_")},
            "created_at": _now_ist(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/research/{session_id}")
def get_session(session_id: str):
    """Get full state of a research session."""
    from ai_engine.session_manager import load_session
    from ai_engine.audit_export import get_assumption_audit, get_guardrail_audit

    try:
        ses = load_session(session_id)
        meta        = ses.meta()
        assumptions = ses.get_assumptions()
        scenarios   = ses.get_scenarios()
        hist        = get_assumption_audit(ses)
        breaches    = get_guardrail_audit(ses)

        return {
            "session_id":  session_id,
            "ticker":      ses.ticker,
            "meta":        meta,
            "assumptions": {k: v for k, v in assumptions.items() if not k.startswith("_")},
            "scenarios":   scenarios,
            "assumption_history": hist[-20:],
            "guardrail_breaches": breaches,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/research/{session_id}/signals")
def session_signals(session_id: str):
    """Scan latest DB events for signals relevant to this session's ticker."""
    from ai_engine.session_manager import load_session
    from ai_engine.signal_detector import scan_events_for_signals, deduplicate_signals
    from sqlalchemy import select, desc
    from database.models import Event

    try:
        ses = load_session(session_id)
        meta = ses.get_meta()
        sector = meta.get("_sector", "universal")

        with _db() as session:
            rows = session.scalars(
                select(Event).order_by(desc(Event.created_at)).limit(100)
            ).all()
            events = [{"title": r.title, "source": r.entity_type or "news"} for r in rows]

        signals = deduplicate_signals(
            scan_events_for_signals(events, ticker=ses.ticker, sector=sector)
        )

        return {
            "ticker":  ses.ticker,
            "signals": [s.to_dict() for s in signals],
            "count":   len(signals),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/research/{session_id}/run-scenarios")
def run_session_scenarios(session_id: str):
    """Run Bull/Base/Bear scenarios for a session."""
    from ai_engine.session_manager import load_session
    from ai_engine.scenario_engine import run_scenarios

    try:
        ses  = load_session(session_id)
        base = ses.get_assumptions()
        run_scenarios(
            ses, base,
            shares_outstanding=float(base.get("shares_outstanding") or 6760),
            base_revenue=float(base.get("base_revenue") or 100),
        )
        return ses.get_scenarios()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/research/{session_id}/assumption")
def update_assumption(session_id: str, req: UpdateAssumptionRequest):
    """Update one assumption in a session."""
    from ai_engine.session_manager import load_session
    from ai_engine.assumption_engine import AssumptionEngine

    try:
        ses = load_session(session_id)
        updated = AssumptionEngine(ses).manual_override(
            req.metric, req.value, reason=req.reason
        )
        return {
            "metric":   req.metric,
            "new_value": req.value,
            "assumptions": {k: v for k, v in updated.items() if not k.startswith("_")},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/research/{session_id}/report")
def get_report(session_id: str):
    """Get or generate the research report for a session."""
    from ai_engine.session_manager import load_session
    from ai_engine.llm_layer import generate_full_report

    try:
        ses = load_session(session_id)
        # Return cached if exists
        if ses.summary_file.exists():
            return {
                "session_id": session_id,
                "ticker":     ses.ticker,
                "report":     ses.summary_file.read_text(),
                "cached":     True,
            }
        meta   = ses.get_meta()
        sector = meta.get("_sector", "universal")
        report = generate_full_report(ses, ses.ticker, sector)
        return {
            "session_id": session_id,
            "ticker":     ses.ticker,
            "report":     report,
            "cached":     False,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/sessions")
def list_sessions(ticker: Optional[str] = None):
    """List all research sessions, optionally filtered by ticker."""
    from ai_engine.session_manager import list_sessions as _list
    return {"sessions": _list(ticker=ticker)}


# ─────────────────────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
def chat(req: ChatRequest):
    """
    Main chat endpoint. Parses intent and executes it.
    This is what the Emergent chat panel calls.
    """
    from ai_engine.intent_parser import parse_intent, describe_intent, ACTION_UNKNOWN
    from ai_engine.session_manager import load_session, latest_session

    # Resolve session
    ses = None
    if req.session_id:
        try:
            ses = load_session(req.session_id)
        except Exception:
            pass
    elif req.ticker:
        ses = latest_session(req.ticker.upper())

    ticker      = ses.ticker if ses else req.ticker
    assumptions = ses.get_assumptions() if ses else {}

    intent = parse_intent(
        req.message,
        current_session_id=ses.session_id if ses else None,
        current_ticker=ticker,
        current_assumptions=assumptions,
    )

    # Execute intent and return response
    response = _execute_chat_intent(intent, ses)

    return {
        "message":    req.message,
        "response":   response,
        "action":     intent.action,
        "session_id": ses.session_id if ses else None,
        "timestamp":  _now_ist(),
    }


def _execute_chat_intent(intent, ses) -> str:
    """Execute a parsed chat intent and return a text response."""
    from ai_engine.intent_parser import (
        ACTION_NEW_SESSION, ACTION_SHOW_ASSUMPTIONS, ACTION_UPDATE_ASSUMPTION,
        ACTION_RUN_SCENARIOS, ACTION_SHOW_SCENARIOS, ACTION_SCAN_NEWS,
        ACTION_GENERATE_REPORT, ACTION_SHOW_HISTORY, ACTION_SHOW_CATALYSTS,
        ACTION_SHOW_THESIS, ACTION_REVERSE_DCF, ACTION_MARKET_REPORT,
        ACTION_COMMODITY_REPORT, ACTION_CHECK_ALERTS, ACTION_MACRO_MICRO,
        ACTION_UNKNOWN,
    )

    a = intent.action

    if a == ACTION_MARKET_REPORT:
        from ai_engine.output_engine import daily_market_report
        return daily_market_report()

    if a == ACTION_COMMODITY_REPORT:
        from ai_engine.output_engine import commodity_daily_report
        return commodity_daily_report()

    if a == ACTION_CHECK_ALERTS:
        from ai_engine.output_engine import check_alerts, format_alerts_report
        return format_alerts_report(check_alerts())

    if not ses:
        return (
            f"No active session. To start: POST /api/research/new with a ticker. "
            f"Or say 'research RELIANCE' in your message."
        )

    if a == ACTION_SHOW_ASSUMPTIONS:
        a = ses.get_assumptions()
        lines = [f"{k}: {v}" for k, v in a.items() if not k.startswith("_")]
        return "Current assumptions:\n" + "\n".join(lines)

    if a == ACTION_SHOW_THESIS:
        return f"Thesis: {ses.get_thesis() or 'Not set'}\nVariant view: {ses.get_variant_view() or 'Not set'}"

    if a == ACTION_SHOW_CATALYSTS:
        cats = ses.get_catalysts()
        if not cats:
            return "No catalysts logged yet."
        return "\n".join(f"• {c['description']} ({c.get('expected_date','TBD')})" for c in cats)

    if a == ACTION_RUN_SCENARIOS:
        from ai_engine.scenario_engine import run_scenarios
        base = ses.get_assumptions()
        run_scenarios(ses, base,
                      shares_outstanding=float(base.get("shares_outstanding") or 6760),
                      base_revenue=float(base.get("base_revenue") or 100))
        sc = ses.get_scenarios()
        lines = []
        for label in ("bull", "base", "bear"):
            s = sc.get("scenarios", {}).get(label, {})
            if s:
                up = s.get("upside_pct")
                up_str = f"{up:+.1f}%" if up is not None else "N/A"
                lines.append(f"{label.upper()}: ₹{s.get('price_per_share')} ({up_str}) [{s.get('rating','?').upper()}]")
        rdcf = sc.get("reverse_dcf") or {}
        if rdcf.get("implied_growth_rate"):
            lines.append(f"Reverse DCF: market implies {rdcf['implied_growth_rate']}% growth")
        return "\n".join(lines)

    if a == ACTION_SHOW_SCENARIOS:
        sc = ses.get_scenarios()
        if not sc:
            return "No scenarios yet. Say 'run scenarios' to generate."
        lines = []
        for label in ("bull", "base", "bear"):
            s = sc.get("scenarios", {}).get(label, {})
            if s:
                up = s.get("upside_pct")
                up_str = f"{up:+.1f}%" if up is not None else "N/A"
                lines.append(f"{label.upper()}: ₹{s.get('price_per_share')} ({up_str})")
        return "\n".join(lines) if lines else "No scenarios generated yet."

    if a == ACTION_SCAN_NEWS:
        from sqlalchemy import select, desc
        from database.models import Event
        from ai_engine.signal_detector import scan_events_for_signals, deduplicate_signals
        from ai_engine.factor_engine import signals_to_factors
        from ai_engine.assumption_engine import AssumptionEngine
        from datetime import date

        meta   = ses.get_meta()
        sector = meta.get("_sector", "universal")

        with _db() as session:
            rows = session.scalars(
                select(Event).order_by(desc(Event.created_at)).limit(50)
            ).all()
            events = [{"title": r.title, "source": r.entity_type or "news"} for r in rows]

        signals = deduplicate_signals(
            scan_events_for_signals(events, ticker=ses.ticker, sector=sector)
        )
        if not signals:
            return f"No signals detected in latest events for {ses.ticker}."

        for s in signals:
            ses.log_insight(signal_type=s.signal_id, description=s.signal_name,
                            source_name=s.source_name, severity=s.severity,
                            factor=", ".join(s.factors))

        deltas = signals_to_factors(signals, ses.get_assumptions())
        if deltas:
            AssumptionEngine(ses).process_deltas(deltas, event_date=date.today())

        lines = [f"• [{s.severity.upper()}] {s.signal_name}: {s.transmission[:80]}" for s in signals]
        return f"Detected {len(signals)} signals:\n" + "\n".join(lines)

    if a == ACTION_GENERATE_REPORT:
        from ai_engine.llm_layer import generate_full_report
        meta   = ses.get_meta()
        sector = meta.get("_sector", "universal")
        return generate_full_report(ses, ses.ticker, sector)

    if a == ACTION_REVERSE_DCF:
        from ai_engine.dcf_bridge import reverse_dcf
        a_c    = ses.get_assumptions()
        price  = a_c.get("current_price_inr")
        shares = a_c.get("shares_outstanding")
        if not price or not shares:
            return "Need current_price_inr and shares_outstanding in assumptions first."
        result = reverse_dcf(
            market_cap=float(price) * float(shares),
            base_ebit=float(a_c.get("base_revenue", 100)) * float(a_c.get("ebitda_margin", 18)) / 100 * 0.85,
            tax_rate=float(a_c.get("tax_rate", 25)) / 100,
            wacc=float(a_c.get("wacc", 12)) / 100,
            net_debt=float(a_c.get("net_debt") or 0),
        )
        return result.get("interpretation", "Reverse DCF calculation complete.")

    if a == ACTION_MACRO_MICRO:
        from ai_engine.output_engine import macro_micro_linkage
        meta   = ses.get_meta()
        sector = meta.get("_sector", "universal")
        result = macro_micro_linkage(ses.ticker, sector)
        drivers = result.get("drivers", [])
        if not drivers:
            return f"No macro drivers found for {ses.ticker}. Collect macro data first."
        lines = [
            f"• {d['macro_indicator']} → {d['signal']}: {d['transmission'][:80]}"
            for d in drivers[:5]
        ]
        return f"Macro drivers for {ses.ticker}:\n" + "\n".join(lines)

    if a == ACTION_UNKNOWN:
        return (
            f"I can help with: market overview, signals, scenarios, assumptions, "
            f"report generation, reverse DCF, macro analysis. "
            f"Try: 'scan news', 'run scenarios', 'show assumptions', 'generate report'."
        )

    return f"Executing: {intent.action}"


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT REPORTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/reports/market")
def market_report():
    from ai_engine.output_engine import daily_market_report
    return {"report": daily_market_report(), "generated_at": _now_ist()}

@app.get("/api/reports/commodity")
def commodity_report():
    from ai_engine.output_engine import commodity_daily_report
    return {"report": commodity_daily_report(), "generated_at": _now_ist()}

@app.get("/api/reports/macro")
def macro_report():
    from ai_engine.output_engine import politics_macro_report
    return {"report": politics_macro_report(), "generated_at": _now_ist()}

@app.get("/api/reports/investor")
def investor_report():
    from ai_engine.output_engine import investor_tracking_report
    return {"report": investor_tracking_report(), "generated_at": _now_ist()}


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
