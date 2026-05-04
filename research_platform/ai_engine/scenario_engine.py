"""
ai_engine/scenario_engine.py
──────────────────────────────
Layer 12 — Scenario Engine.

Auto-runs Bull / Base / Bear — bear case CANNOT be skipped.
Generates sensitivity table (WACC vs terminal growth rate grid).
Writes structured JSON to scenarios.json in session folder.

From the document:
  "Auto-runs Bull / Base / Bear · Sensitivity table (WACC vs growth) ·
   Valuation range not just one number"
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.session_manager import ResearchSession


@dataclass
class ScenarioResult:
    """One DCF scenario output."""
    label:              str            # "bull" | "base" | "bear"
    revenue_growth:     float
    ebitda_margin:      float
    wacc:               float
    terminal_growth:    float
    enterprise_value:   float
    equity_value:       float
    price_per_share:    Optional[float]
    upside_pct:         Optional[float]
    rating:             str            # "buy" | "hold" | "sell" | "avoid"
    key_assumption:     str            # one-line summary of the key bet in this scenario


@dataclass
class ScenarioSet:
    """Bull + Base + Bear together with sensitivity table."""
    ticker:             str
    current_price:      Optional[float]
    shares_outstanding: Optional[float]
    net_debt:           float
    bull:               Optional[ScenarioResult]  = None
    base:               Optional[ScenarioResult]  = None
    bear:               Optional[ScenarioResult]  = None
    sensitivity:        dict[str, Any]            = field(default_factory=dict)
    reverse_dcf:        Optional[dict[str, Any]]  = None
    generated_at:       str                       = ""


def _simple_dcf(
    base_revenue: float,
    revenue_growth: float,
    ebitda_margin: float,
    capex_pct: float,
    tax_rate: float,
    wacc: float,
    terminal_growth: float,
    projection_years: int = 10,
    da_pct: float = 0.03,
    wc_change_pct: float = 0.01,
) -> float:
    """
    Simple DCF returning Enterprise Value.
    FCFF-based. Revenue drives EBITDA → EBIT → NOPAT → FCFF.
    """
    if wacc <= terminal_growth:
        # Protect against division-by-zero / negative terminal value
        terminal_growth = wacc - 0.01

    total_pv = 0.0
    rev = base_revenue
    for yr in range(1, projection_years + 1):
        rev       = rev * (1 + revenue_growth / 100)
        ebitda    = rev * ebitda_margin / 100
        ebit      = ebitda - rev * da_pct
        nopat     = ebit * (1 - tax_rate / 100)
        capex     = rev * capex_pct / 100
        da        = rev * da_pct
        wc_chg    = rev * wc_change_pct
        fcff      = nopat + da - capex - wc_chg
        pv        = fcff / ((1 + wacc / 100) ** yr)
        total_pv += pv

    # Terminal value
    last_fcff     = base_revenue * ((1 + revenue_growth / 100) ** projection_years)
    last_fcff     = last_fcff * ebitda_margin / 100 * (1 - da_pct / ebitda_margin) * (1 - tax_rate / 100)
    last_fcff    *= (1 + terminal_growth / 100)
    tv            = last_fcff / ((wacc - terminal_growth) / 100)
    tv_pv         = tv / ((1 + wacc / 100) ** projection_years)

    return max(total_pv + tv_pv, 0)


def run_scenarios(
    session: ResearchSession,
    base_assumptions: dict[str, Any],
    shares_outstanding: Optional[float] = None,
    base_revenue: float = 100.0,          # use actual revenue if available
    bull_adj: Optional[dict[str, float]] = None,
    bear_adj: Optional[dict[str, float]] = None,
) -> ScenarioSet:
    """
    Auto-generate Bull / Base / Bear scenarios.

    Bear case CANNOT be skipped — it is always generated.

    Bull/Bear adjustments are applied as deltas from Base.
    Default adjustments if not provided:
      Bull: revenue_growth +3%, ebitda_margin +2%, wacc -0.5%, terminal_growth +0.5%
      Bear: revenue_growth -4%, ebitda_margin -3%, wacc +1.0%, terminal_growth -1.0%
    """
    from datetime import datetime, timezone

    ticker        = session.ticker
    current_price = base_assumptions.get("current_price_inr")
    net_debt      = float(base_assumptions.get("net_debt", 0) or 0)

    # Base assumptions
    base_rev_g    = float(base_assumptions.get("revenue_growth",      8.0))
    base_ebm      = float(base_assumptions.get("ebitda_margin",       18.0))
    base_wacc     = float(base_assumptions.get("wacc",                12.0))
    base_tg       = float(base_assumptions.get("terminal_growth_rate", 4.5))
    base_capex    = float(base_assumptions.get("capex_pct_revenue",    5.0))
    base_tax      = float(base_assumptions.get("tax_rate",             25.0))

    # Scenario adjustments
    bull_adj = bull_adj or {"revenue_growth": +3.0, "ebitda_margin": +2.0, "wacc": -0.5, "terminal_growth": +0.5}
    bear_adj = bear_adj or {"revenue_growth": -4.0, "ebitda_margin": -3.0, "wacc": +1.0, "terminal_growth": -1.0}

    def _make_scenario(label: str, adj: dict[str, float]) -> ScenarioResult:
        rg  = base_rev_g  + adj.get("revenue_growth",    0)
        ebm = base_ebm    + adj.get("ebitda_margin",     0)
        w   = base_wacc   + adj.get("wacc",              0)
        tg  = base_tg     + adj.get("terminal_growth",   0)

        # Clamp
        rg  = max(-20.0,  min(50.0, rg))
        ebm = max(-10.0,  min(60.0, ebm))
        w   = max(7.0,    min(20.0, w))
        tg  = max(0.5,    min(6.0,  tg))

        ev = _simple_dcf(
            base_revenue=base_revenue,
            revenue_growth=rg,
            ebitda_margin=ebm,
            capex_pct=base_capex,
            tax_rate=base_tax,
            wacc=w,
            terminal_growth=tg,
        )
        eq_val = max(ev - net_debt, 0)
        price  = round(eq_val / shares_outstanding, 2) if shares_outstanding else None
        upside = round((price / current_price - 1) * 100, 1) if (price and current_price) else None

        if upside is not None:
            rating = "buy" if upside > 15 else "hold" if upside > -10 else "sell"
        else:
            rating = "hold"

        key_assumption = {
            "bull": f"{rg:.1f}% revenue growth + {ebm:.1f}% EBITDA margin driving value",
            "base": f"Base case: {rg:.1f}% growth, {ebm:.1f}% margin, {w:.1f}% WACC",
            "bear": f"Downside risk: {rg:.1f}% growth, {ebm:.1f}% margin, {w:.1f}% WACC",
        }[label]

        return ScenarioResult(
            label=label,
            revenue_growth=round(rg, 2),
            ebitda_margin=round(ebm, 2),
            wacc=round(w, 2),
            terminal_growth=round(tg, 2),
            enterprise_value=round(ev, 2),
            equity_value=round(eq_val, 2),
            price_per_share=price,
            upside_pct=upside,
            rating=rating,
            key_assumption=key_assumption,
        )

    bull = _make_scenario("bull", bull_adj)
    base = _make_scenario("base", {})
    bear = _make_scenario("bear", bear_adj)   # CANNOT be skipped

    # Sensitivity table: WACC (rows) vs Terminal Growth (cols)
    wacc_range   = [round(base_wacc - 1.5 + i * 0.5, 1) for i in range(7)]
    tg_range     = [round(base_tg   - 1.5 + i * 0.5, 1) for i in range(7)]
    sensitivity  = _build_sensitivity(
        base_revenue, base_rev_g, base_ebm, base_capex, base_tax,
        wacc_range, tg_range, net_debt, shares_outstanding, current_price,
    )

    # Reverse DCF
    rdcf = None
    if current_price and shares_outstanding:
        mktcap = current_price * shares_outstanding
        from ai_engine.dcf_bridge import reverse_dcf
        rdcf = reverse_dcf(
            market_cap  = mktcap,
            base_ebit   = base_revenue * base_ebm / 100 * 0.85,  # approx EBIT
            tax_rate    = base_tax / 100,
            capex_pct   = base_capex / 100,
            wacc        = base_wacc / 100,
            net_debt    = net_debt,
        )

    result = ScenarioSet(
        ticker             = ticker,
        current_price      = current_price,
        shares_outstanding = shares_outstanding,
        net_debt           = net_debt,
        bull               = bull,
        base               = base,
        bear               = bear,
        sensitivity        = sensitivity,
        reverse_dcf        = rdcf,
        generated_at       = datetime.now(timezone.utc).isoformat(),
    )

    # Write to session
    _write_scenarios(session, result)
    return result


def _build_sensitivity(
    base_revenue, rev_g, ebm, capex, tax,
    wacc_range, tg_range,
    net_debt, shares, current_price,
) -> dict[str, Any]:
    """Build WACC × terminal_growth sensitivity grid."""
    grid: list[list[Optional[float]]] = []
    for w in wacc_range:
        row: list[Optional[float]] = []
        for tg in tg_range:
            if w <= tg:
                row.append(None)
                continue
            ev    = _simple_dcf(base_revenue, rev_g, ebm, capex, tax, w, tg)
            eq    = max(ev - net_debt, 0)
            price = round(eq / shares, 1) if shares else None
            if price and current_price:
                row.append(round((price / current_price - 1) * 100, 1))
            else:
                row.append(round(eq, 1))
        grid.append(row)

    return {
        "wacc_range":           wacc_range,
        "terminal_growth_range": tg_range,
        "metric":               "upside_pct" if (shares and current_price) else "equity_value",
        "grid":                 grid,
    }


def _write_scenarios(session: ResearchSession, result: ScenarioSet) -> None:
    """Persist ScenarioSet to scenarios.json as structured JSON."""
    def _s(sc: Optional[ScenarioResult]) -> Optional[dict]:
        if sc is None:
            return None
        return {
            "label":            sc.label,
            "revenue_growth":   sc.revenue_growth,
            "ebitda_margin":    sc.ebitda_margin,
            "wacc":             sc.wacc,
            "terminal_growth":  sc.terminal_growth,
            "enterprise_value": sc.enterprise_value,
            "equity_value":     sc.equity_value,
            "price_per_share":  sc.price_per_share,
            "upside_pct":       sc.upside_pct,
            "rating":           sc.rating,
            "key_assumption":   sc.key_assumption,
        }

    data = {
        "ticker":             result.ticker,
        "current_price":      result.current_price,
        "shares_outstanding": result.shares_outstanding,
        "net_debt":           result.net_debt,
        "scenarios": {
            "bull": _s(result.bull),
            "base": _s(result.base),
            "bear": _s(result.bear),
        },
        "sensitivity":  result.sensitivity,
        "reverse_dcf":  result.reverse_dcf,
        "generated_at": result.generated_at,
    }
    session.write_scenarios(data)
    logger.info(
        f"[scenario_engine] {result.ticker}: "
        f"bull={result.bull.price_per_share} base={result.base.price_per_share} "
        f"bear={result.bear.price_per_share if result.bear else 'N/A'}"
    )
