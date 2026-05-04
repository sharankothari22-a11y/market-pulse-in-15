"""
ai_engine/output_engine.py
────────────────────────────
Section 7 — Six Output Types.

Same database, different queries + LLM prompts. No rebuilding.

Output 1: Daily Market Movement Report  — why markets moved today
Output 2: Commodity Daily Report        — gold/silver/oil/crypto drivers
Output 3: Data Decision Alerts          — threshold-triggered alerts
Output 4: Company Deep-Dive             — full research note (via llm_layer.py)
Output 5: Investor Tracking Dashboard   — PMS/AIF/13F holdings changes
Output 6: Politics & Macro Report       — geopolitical impact on markets

From the document: "Every output below comes from the same database.
No rebuilding the collection layer. The query and the LLM prompt change —
the data stays the same."
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any, Optional

import requests
from loguru import logger

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-sonnet-4-20250514"


def _llm(prompt: str, system: str, max_tokens: int = 2000) -> str:
    """Call Claude API directly (no session cache — these are one-shot outputs)."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return f"[Set ANTHROPIC_API_KEY to generate this report]\n\nData context:\n{prompt[:500]}"
    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except Exception as exc:
        logger.error(f"[output_engine] LLM call failed: {exc}")
        return f"[LLM call failed: {exc}]"


# ── Output 1: Daily Market Movement Report ────────────────────────────────────

def daily_market_report(as_of: Optional[date] = None) -> str:
    """
    Why are markets up/down today?
    Sources: price_history, fii_dii_flows, macro_indicators, event, fx_rates
    """
    target = as_of or date.today()
    prev   = target - timedelta(days=1)

    data = _fetch_market_snapshot(target, prev)

    prompt = f"""Generate a concise daily market movement report for {target}.

Market data:
{json.dumps(data, indent=2, default=str)}

Cover:
1. How did NIFTY/Sensex perform vs yesterday? (use price_history data)
2. FII/DII flows — were institutions buying or selling?
3. Key macro signals — currency, commodity, rate moves
4. Top 3 news events driving the move today
5. One-line outlook for tomorrow

Format: Plain text. 300-400 words. For a professional institutional audience."""

    system = "You are a sell-side equity strategist writing the daily market note. Factual, concise, no fluff."
    report = _llm(prompt, system)

    logger.info(f"[output_engine] Daily market report generated for {target}")
    return report


def _fetch_market_snapshot(target: date, prev: date) -> dict[str, Any]:
    """Pull all data needed for daily market report."""
    data: dict[str, Any] = {"date": str(target)}
    try:
        from sqlalchemy import select, desc, func, and_
        from database.connection import get_session
        from database.models import PriceHistory, FiiDiiFlow, FxRate, MacroIndicator, Event

        with get_session() as session:
            # Top movers
            movers = session.scalars(
                select(PriceHistory)
                .where(PriceHistory.date == target, PriceHistory.exchange == "NSE")
                .order_by(desc(PriceHistory.volume)).limit(10)
            ).all()
            data["top_volume"] = [
                {"ticker": p.ticker, "close": float(p.close), "volume": float(p.volume or 0)}
                for p in movers
            ]

            # FII/DII
            flows = session.scalars(
                select(FiiDiiFlow).where(FiiDiiFlow.date == target)
            ).all()
            data["fii_dii"] = [
                {"category": f.category, "net_cr": round(float(f.net_value or 0)/100, 1)}
                for f in flows
            ]

            # FX
            fx = session.scalars(
                select(FxRate).where(FxRate.date == target)
            ).all()
            data["fx_rates"] = {r.pair: float(r.rate) for r in fx}

            # Latest events
            events = session.scalars(
                select(Event).where(Event.date == target)
                .order_by(desc(Event.created_at)).limit(10)
            ).all()
            data["events"] = [{"title": e.title, "type": e.type} for e in events]

    except Exception as exc:
        logger.warning(f"[output_engine] Market snapshot DB error: {exc}")
        data["error"] = str(exc)

    return data


# ── Output 2: Commodity Daily Report ─────────────────────────────────────────

def commodity_daily_report(as_of: Optional[date] = None) -> str:
    """
    Gold, Silver, Oil, Crypto — what moved and why.
    Sources: commodity_prices, event
    """
    target = as_of or date.today()
    data   = _fetch_commodity_snapshot(target)

    prompt = f"""Generate a commodity market report for {target}.

Commodity prices and context:
{json.dumps(data, indent=2, default=str)}

Cover:
1. Gold and Silver — direction and key driver (DXY, rates, geopolitics)
2. Oil (WTI/Brent) — direction, OPEC news, demand signal
3. Top 3 crypto moves — Bitcoin, Ethereum, any notable movers
4. One commodity to watch tomorrow and why

Format: 250-300 words. Institutional quality."""

    system = "Commodity market analyst. Factual. Source every claim in the data provided."
    return _llm(prompt, system)


def _fetch_commodity_snapshot(target: date) -> dict[str, Any]:
    data: dict[str, Any] = {"date": str(target)}
    try:
        from sqlalchemy import select, desc
        from database.connection import get_session
        from database.models import CommodityPrice, Event

        with get_session() as session:
            prices = session.scalars(
                select(CommodityPrice).where(CommodityPrice.date == target).limit(30)
            ).all()
            data["commodities"] = [
                {
                    "name": (p.extra_data or {}).get("name", f"commodity_{p.commodity_id}"),
                    "price": float(p.price),
                    "currency": p.currency,
                    "change_24h_pct": (p.extra_data or {}).get("price_change_pct_24h"),
                }
                for p in prices
            ]
            events = session.scalars(
                select(Event)
                .where(Event.date == target, Event.entity_type.in_(["gdelt","sebi","rbi","news"]))
                .order_by(desc(Event.impact_score)).limit(10)
            ).all()
            data["events"] = [{"title": e.title, "impact": e.impact_score} for e in events]
    except Exception as exc:
        data["error"] = str(exc)
    return data


# ── Output 3: Data Decision Alerts ───────────────────────────────────────────

def check_alerts(
    thresholds: Optional[dict[str, Any]] = None,
    as_of: Optional[date] = None,
) -> list[dict[str, Any]]:
    """
    Threshold-triggered alerts. Returns list of triggered alerts.

    Default thresholds:
      - FII net > ₹2,000 Cr or < -₹2,000 Cr in a day
      - Any stock price move > 8% in a day
      - Regulatory event from SEBI/RBI

    From the document: "Threshold triggers: insider trade, FII surge, bulk deal"
    """
    target = as_of or date.today()
    th     = thresholds or {
        "fii_surge_cr":      2000,
        "price_move_pct":    8.0,
        "impact_score_min":  0.5,
    }
    alerts: list[dict[str, Any]] = []

    try:
        from sqlalchemy import select, desc, func
        from database.connection import get_session
        from database.models import FiiDiiFlow, PriceHistory, Event

        with get_session() as session:
            # FII surge alert
            flows = session.scalars(
                select(FiiDiiFlow).where(FiiDiiFlow.date == target)
            ).all()
            for f in flows:
                net = float(f.net_value or 0) / 100  # crore
                if abs(net) >= th["fii_surge_cr"]:
                    direction = "buying" if net > 0 else "selling"
                    alerts.append({
                        "type":    "fii_surge",
                        "message": f"{f.category} {direction}: ₹{abs(net):,.0f} Cr net on {target}",
                        "value":   net,
                        "date":    str(target),
                    })

            # Large price moves
            today_prices   = {p.ticker: p for p in session.scalars(
                select(PriceHistory).where(PriceHistory.date == target, PriceHistory.exchange == "NSE")
            ).all()}
            prev_date      = target - timedelta(days=1)
            prev_prices    = {p.ticker: float(p.close) for p in session.scalars(
                select(PriceHistory).where(PriceHistory.date == prev_date, PriceHistory.exchange == "NSE")
            ).all()}
            for ticker, tp in today_prices.items():
                prev_close = prev_prices.get(ticker)
                if prev_close and prev_close > 0:
                    move_pct = (float(tp.close) - prev_close) / prev_close * 100
                    if abs(move_pct) >= th["price_move_pct"]:
                        alerts.append({
                            "type":    "large_price_move",
                            "message": f"{ticker}: {move_pct:+.1f}% on {target}",
                            "ticker":  ticker,
                            "move_pct": round(move_pct, 2),
                            "date":    str(target),
                        })

            # High-impact regulatory events
            high_impact_events = session.scalars(
                select(Event)
                .where(Event.date == target,
                       Event.impact_score >= th["impact_score_min"])
                .order_by(desc(Event.impact_score)).limit(5)
            ).all()
            for ev in high_impact_events:
                alerts.append({
                    "type":    "regulatory_event",
                    "message": ev.title[:200],
                    "impact":  ev.impact_score,
                    "date":    str(target),
                })

    except Exception as exc:
        logger.warning(f"[output_engine] Alert check failed: {exc}")

    if alerts:
        logger.info(f"[output_engine] {len(alerts)} alerts triggered for {target}")
    return alerts


def format_alerts_report(alerts: list[dict[str, Any]]) -> str:
    """Format the alerts list as a readable report."""
    if not alerts:
        return f"No alerts triggered for {date.today()}."
    lines = [f"# Data Decision Alerts — {date.today()}\n"]
    for a in alerts:
        icon = {"fii_surge":"🔴","large_price_move":"⚡","regulatory_event":"📋"}.get(a["type"],"•")
        lines.append(f"{icon} **{a['type'].upper()}**: {a['message']}")
    return "\n".join(lines)


# ── Output 5: Investor Tracking Dashboard ─────────────────────────────────────

def investor_tracking_report(as_of: Optional[date] = None) -> str:
    """
    Top India + global investors: holdings, changes, signals.
    Sources: portfolio, fund, person, company
    """
    data = _fetch_investor_data()
    prompt = f"""Generate an investor tracking dashboard report.

Holdings data:
{json.dumps(data, indent=2, default=str)}

Cover:
1. Top 5 mutual fund AUM changes this quarter
2. Notable FII/FPI position changes visible in bulk deals
3. Promoter activity — any pledging or buying across portfolio companies
4. One key insider trade to watch

Format: 200-250 words. Table format where useful."""

    system = "Institutional equity analyst focused on smart money tracking."
    return _llm(prompt, system)


def _fetch_investor_data() -> dict[str, Any]:
    data: dict[str, Any] = {}
    try:
        from sqlalchemy import select, desc
        from database.connection import get_session
        from database.models import Portfolio, Fund, Company

        with get_session() as session:
            # Top portfolio positions
            positions = session.scalars(
                select(Portfolio).order_by(desc(Portfolio.value_inr)).limit(20)
            ).all()
            data["top_positions"] = [
                {"holder_type": p.holder_type, "quarter": p.quarter,
                 "holding_pct": p.holding_pct, "value_inr": float(p.value_inr or 0)}
                for p in positions
            ]
            # Top funds by AUM
            funds = session.scalars(
                select(Fund).where(Fund.aum.isnot(None)).order_by(desc(Fund.aum)).limit(10)
            ).all()
            data["top_funds"] = [{"name": f.name, "type": f.type, "aum_cr": float(f.aum or 0)/1e7} for f in funds]
    except Exception as exc:
        data["error"] = str(exc)
    return data


# ── Output 6: Politics & Macro Report ────────────────────────────────────────

def politics_macro_report(as_of: Optional[date] = None) -> str:
    """
    Trump, Modi, Putin — news, portfolio, policy impact on markets.
    Sources: event (GDELT, RSS), macro_indicators
    """
    target = as_of or date.today()
    data   = _fetch_geopolitical_data(target)

    prompt = f"""Generate a geopolitical and macro impact report for {target}.

Events and macro data:
{json.dumps(data, indent=2, default=str)}

Cover:
1. Key geopolitical developments and their market implications
2. Central bank signals — RBI and Fed
3. One macro indicator that changed significantly
4. India-specific policy/regulatory development and sector impact

Format: 250-300 words. Institutional quality."""

    system = "Macro strategist covering geopolitics and central bank policy."
    return _llm(prompt, system)


def _fetch_geopolitical_data(target: date) -> dict[str, Any]:
    data: dict[str, Any] = {"date": str(target)}
    try:
        from sqlalchemy import select, desc
        from database.connection import get_session
        from database.models import Event, MacroIndicator

        with get_session() as session:
            geo_events = session.scalars(
                select(Event)
                .where(Event.entity_type.in_(["gdelt", "rbi", "sebi"]),
                       Event.date >= target - timedelta(days=3))
                .order_by(desc(Event.impact_score)).limit(15)
            ).all()
            data["events"] = [{"title": e.title, "type": e.entity_type, "impact": e.impact_score} for e in geo_events]

            macro = session.scalars(
                select(MacroIndicator).order_by(desc(MacroIndicator.date)).limit(10)
            ).all()
            data["macro"] = [
                {"indicator": m.indicator, "value": m.value, "date": str(m.date), "source": m.source}
                for m in macro
            ]
    except Exception as exc:
        data["error"] = str(exc)
    return data


# ── Macro-micro linkage ───────────────────────────────────────────────────────

def macro_micro_linkage(ticker: str, sector: str) -> dict[str, Any]:
    """
    'Why is this stock moving?'

    Links macro indicator moves to company-level impact via sector framework.
    From Section 15.1: 'Macro indicators linked to Country entity,
    micro to Company — powers why is this stock moving'
    """
    from pathlib import Path
    import json as _json

    result: dict[str, Any] = {"ticker": ticker, "sector": sector, "drivers": []}

    # Load sector transmission chains
    fw_path = Path(__file__).parent / "frameworks" / sector / "signals.json"
    if not fw_path.exists():
        fw_path = Path(__file__).parent / "frameworks" / "universal.json"

    sector_signals = []
    if fw_path.exists():
        fw = _json.loads(fw_path.read_text())
        sector_signals = fw.get("signals", [])

    # Pull latest macro moves from DB
    try:
        from sqlalchemy import select, desc
        from database.connection import get_session
        from database.models import MacroIndicator, CommodityPrice, FxRate

        with get_session() as session:
            recent_macro = session.scalars(
                select(MacroIndicator).order_by(desc(MacroIndicator.date)).limit(20)
            ).all()
            recent_fx = session.scalars(
                select(FxRate).order_by(desc(FxRate.date)).limit(10)
            ).all()
            recent_commodity = session.scalars(
                select(CommodityPrice).order_by(desc(CommodityPrice.date)).limit(10)
            ).all()

            # Match macro moves to sector signals
            for signal in sector_signals:
                keywords = signal.get("keywords", [])
                for macro in recent_macro:
                    if any(kw in macro.indicator.lower() for kw in keywords):
                        result["drivers"].append({
                            "macro_indicator": macro.indicator,
                            "value":           macro.value,
                            "date":            str(macro.date),
                            "signal":          signal["name"],
                            "transmission":    signal.get("transmission", ""),
                            "affected_assumptions": signal.get("factors", []),
                        })

    except Exception as exc:
        result["error"] = str(exc)

    return result
