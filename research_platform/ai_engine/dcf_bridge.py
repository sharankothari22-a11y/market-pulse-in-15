"""
ai_engine/dcf_bridge.py
─────────────────────────
Layer 11 — DCF Engine Connection.

Three responsibilities:
  1. Build live assumption inputs from the database (replaces manual Excel)
  2. Write assumptions.json bridge file that the DCF engine reads
  3. Read DCF results back from session folder and store in scenarios.json

The document spec:
  "Reads assumptions.json (bridge file) · Runs existing DCF model ·
   Writes results back to session folder"
  "Zero rebuild required — your existing engine reads the bridge file"

DCF improvement checklist (Section 15.3):
  [x] Read from assumptions.json
  [x] Write results back to session folder
  [x] Sector-specific default assumptions from framework files
  [x] Reverse DCF function (given market cap → implied growth rate)
  [x] Scenario output schema (JSON not just Excel tabs)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

from loguru import logger

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"


# ── Sector-specific default assumptions ──────────────────────────────────────

def get_sector_defaults(sector: str) -> dict[str, Any]:
    """
    Load default assumptions from the sector framework file.
    Falls back to universal defaults if sector file missing.
    """
    sector_file = FRAMEWORKS_DIR / sector / "signals.json"
    if sector_file.exists():
        data = json.loads(sector_file.read_text())
        defaults = data.get("default_assumptions", {})
        if defaults:
            return defaults

    # Universal fallbacks
    return {
        "revenue_growth":       8.0,
        "ebitda_margin":        18.0,
        "gross_margin":         35.0,
        "capex_pct_revenue":    5.0,
        "wacc":                 12.0,
        "terminal_growth_rate": 4.5,
        "cost_of_debt":         8.5,
        "equity_risk_premium":  7.5,
        "tax_rate":             25.0,
        "working_capital_days": 45.0,
        "debt_equity_ratio":    0.5,
    }


# ── Live data pulls from database ─────────────────────────────────────────────

def pull_live_inputs(ticker: str, exchange: str = "NSE") -> dict[str, Any]:
    """
    Pull live market data from the Research Data Platform database.
    These replace manually typed Excel cells in the DCF model.
    """
    from sqlalchemy import select, desc
    from database.connection import get_session
    from database.models import PriceHistory, FxRate, MacroIndicator, FiiDiiFlow

    inputs: dict[str, Any] = {
        "ticker":    ticker,
        "exchange":  exchange,
        "data_date": str(date.today()),
    }

    try:
        with get_session() as session:
            # Current share price
            price_row = session.scalar(
                select(PriceHistory)
                .where(PriceHistory.ticker == ticker, PriceHistory.exchange == exchange)
                .order_by(desc(PriceHistory.date)).limit(1)
            )
            inputs["current_price_inr"] = float(price_row.close) if price_row else None
            inputs["price_date"] = str(price_row.date) if price_row else None

            # USD/INR
            fx_row = session.scalar(
                select(FxRate).where(FxRate.pair == "USD/INR")
                .order_by(desc(FxRate.date)).limit(1)
            )
            inputs["usd_inr"] = float(fx_row.rate) if fx_row else 84.0

            # India GDP growth (World Bank)
            gdp_row = session.scalar(
                select(MacroIndicator)
                .where(MacroIndicator.indicator == "NY.GDP.MKTP.KD.ZG",
                       MacroIndicator.source.like("WorldBank%"))
                .order_by(desc(MacroIndicator.date)).limit(1)
            )
            inputs["india_gdp_growth"] = float(gdp_row.value) if gdp_row else 6.5

            # India CPI (World Bank)
            cpi_row = session.scalar(
                select(MacroIndicator)
                .where(MacroIndicator.indicator == "FP.CPI.TOTL.ZG",
                       MacroIndicator.source.like("WorldBank%"))
                .order_by(desc(MacroIndicator.date)).limit(1)
            )
            inputs["india_cpi"] = float(cpi_row.value) if cpi_row else 5.0

            # US Fed Funds Rate
            fed_row = session.scalar(
                select(MacroIndicator)
                .where(MacroIndicator.indicator == "FEDFUNDS",
                       MacroIndicator.source == "FRED")
                .order_by(desc(MacroIndicator.date)).limit(1)
            )
            inputs["us_fed_funds"] = float(fed_row.value) if fed_row else 5.0

            # Latest FII net flow (sentiment signal)
            fii_row = session.scalar(
                select(FiiDiiFlow).where(FiiDiiFlow.category == "FII")
                .order_by(desc(FiiDiiFlow.date)).limit(1)
            )
            if fii_row and fii_row.net_value:
                inputs["fii_net_flow_cr"]   = round(float(fii_row.net_value) / 100, 2)
                inputs["fii_sentiment"]     = "positive" if fii_row.net_value > 0 else "negative"

    except Exception as exc:
        logger.warning(f"[dcf_bridge] DB pull partial — {exc}")

    # Derived assumptions
    cpi  = inputs.get("india_cpi", 5.0) or 5.0
    gdp  = inputs.get("india_gdp_growth", 6.5) or 6.5
    inputs["risk_free_rate"]       = round(max(cpi, 4.0), 2)
    inputs["terminal_growth_rate"] = round(min((gdp + cpi) * 0.40, 5.0), 1)

    return inputs


def build_full_assumptions(
    ticker: str,
    sector: str = "universal",
    exchange: str = "NSE",
    overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Build a complete assumptions dict:
      sector defaults → live DB inputs → session overrides (if any)

    This is the function the AI research pipeline calls at session start.
    """
    assumptions = get_sector_defaults(sector)
    live        = pull_live_inputs(ticker, exchange)

    # Merge live inputs into assumptions
    for key, val in live.items():
        if val is not None:
            assumptions[key] = val

    # Apply manual overrides last (highest priority)
    if overrides:
        assumptions.update(overrides)

    assumptions["_sector"]  = sector
    assumptions["_built_at"] = str(date.today())

    return assumptions


def write_bridge_file(assumptions: dict[str, Any], bridge_path: Path) -> None:
    """Write assumptions.json that the DCF engine reads."""
    bridge_path.write_text(json.dumps(assumptions, indent=2, default=str))
    logger.info(f"[dcf_bridge] Bridge file written: {bridge_path}")


def read_dcf_results(results_path: Path) -> Optional[dict[str, Any]]:
    """Read results written back by the DCF engine."""
    if not results_path.exists():
        return None
    return json.loads(results_path.read_text())


# ── Reverse DCF ───────────────────────────────────────────────────────────────

def reverse_dcf(
    market_cap: float,
    base_ebit: float,
    tax_rate: float = 0.25,
    capex_pct: float = 0.05,
    da_pct: float = 0.03,
    wc_change_pct: float = 0.01,
    wacc: float = 0.12,
    projection_years: int = 10,
    shares_outstanding: Optional[float] = None,
    net_debt: float = 0.0,
) -> dict[str, Any]:
    """
    Reverse DCF: given the current market cap, solve for the implied
    revenue growth rate the market is pricing in.

    From the document: "Core equity research tool — currently missing"

    Algorithm: binary search over growth_rate until NPV of FCFs + terminal
    value equals (market_cap + net_debt) = Enterprise Value.
    """
    enterprise_value = market_cap + net_debt

    def dcf_value(growth_rate: float) -> float:
        """Calculate DCF enterprise value for a given annual growth rate."""
        fcf = base_ebit * (1 - tax_rate) * (1 - capex_pct + da_pct - wc_change_pct)
        total_pv = 0.0
        for yr in range(1, projection_years + 1):
            fcf_yr = fcf * ((1 + growth_rate) ** yr)
            pv     = fcf_yr / ((1 + wacc) ** yr)
            total_pv += pv

        # Terminal value (Gordon Growth Model, terminal g = 3.5%)
        terminal_g    = min(growth_rate * 0.5, 0.035)
        terminal_fcf  = fcf * ((1 + growth_rate) ** projection_years) * (1 + terminal_g)
        terminal_val  = terminal_fcf / (wacc - terminal_g)
        terminal_pv   = terminal_val / ((1 + wacc) ** projection_years)
        return total_pv + terminal_pv

    # Binary search for implied growth rate
    low, high = -0.10, 0.50
    implied_growth = None
    for _ in range(60):    # ~60 iterations → converges to 6 decimal places
        mid = (low + high) / 2
        if dcf_value(mid) < enterprise_value:
            low = mid
        else:
            high = mid
        if abs(high - low) < 1e-6:
            implied_growth = mid
            break

    if implied_growth is None:
        implied_growth = (low + high) / 2

    implied_pct = round(implied_growth * 100, 2)

    return {
        "market_cap":          market_cap,
        "enterprise_value":    enterprise_value,
        "implied_growth_rate": implied_pct,
        "implied_wacc":        round(wacc * 100, 2),
        "interpretation": (
            f"The market is pricing in {implied_pct:.1f}% annual revenue/FCFF growth "
            f"over {projection_years} years at a {wacc*100:.1f}% WACC. "
            + ("This appears reasonable." if 5 <= implied_pct <= 20
               else "This appears stretched — verify assumptions." if implied_pct > 20
               else "This implies distress or deep value scenario.")
        ),
    }
