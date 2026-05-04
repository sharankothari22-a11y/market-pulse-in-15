"""
ai_engine/swot.py
──────────────────
SWOT generator ported from the company_research notebook.
Works entirely from session JSON files.

Every item is tagged:
  [FACT]           — derived from actual financial data
  [ASSUMPTION]     — derived from model assumptions
  [INTERPRETATION] — derived from signal analysis

Never fails — returns empty lists if data is missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        logger.debug(f"[swot] could not load {path}: {exc}")
    return None


def _get_sector_defaults(sector: str) -> dict[str, Any]:
    folder_map = {
        "petroleum_energy": "petroleum",
        "banking_nbfc":     "banking",
        "fmcg_retail":      "fmcg",
        "it_tech":          "it",
        "pharma":           "pharma",
        "real_estate":      "real_estate",
        "auto":             "auto",
    }
    folder = folder_map.get(sector, sector)
    try:
        f = FRAMEWORKS_DIR / folder / "signals.json"
        if f.exists():
            data = json.loads(f.read_text())
            return data.get("default_assumptions", {})
    except Exception:
        pass
    return {}


def _tag(label: str) -> str:
    return f"[{label}]"


# ── SWOT builders ─────────────────────────────────────────────────────────────

def _build_strengths(
    assumptions: dict[str, Any],
    sector_defaults: dict[str, Any],
) -> list[str]:
    items: list[str] = []

    ebitda_margin = assumptions.get("ebitda_margin")
    sector_ebitda = (
        sector_defaults.get("ebitda_margin_default") or
        sector_defaults.get("ebitda_margin") or 18.0
    )

    try:
        em = float(ebitda_margin) if ebitda_margin is not None else None
        se = float(sector_ebitda)
        if em is not None:
            if em > se + 5:
                items.append(
                    f"{_tag('FACT')} EBITDA margin {em:.1f}% significantly above "
                    f"sector average ({se:.1f}%) — indicates strong pricing power"
                )
            elif em > se:
                items.append(
                    f"{_tag('FACT')} EBITDA margin {em:.1f}% ahead of sector average "
                    f"({se:.1f}%) — operational efficiency advantage"
                )
    except (TypeError, ValueError):
        pass

    net_debt = assumptions.get("net_debt")
    try:
        nd = float(net_debt) if net_debt is not None else None
        if nd is not None and nd < 0:
            items.append(
                f"{_tag('FACT')} Net cash position (net debt = {nd:,.0f}) — "
                "strong balance sheet with financial flexibility"
            )
    except (TypeError, ValueError):
        pass

    growths = []
    for yr in range(1, 4):
        v = assumptions.get(f"revenue_growth_y{yr}")
        if v is not None:
            try:
                growths.append(float(v))
            except (TypeError, ValueError):
                pass
    if growths and all(g > 8 for g in growths):
        items.append(
            f"{_tag('ASSUMPTION')} Consistent revenue growth projected "
            f"({growths[0]:.1f}% → {growths[-1]:.1f}%) — "
            "business momentum across forecast horizon"
        )

    conf_tags = assumptions.get("_confidence_tags") or assumptions.get("confidence_tags") or {}
    if isinstance(conf_tags, dict):
        high_tags = [k for k, v in conf_tags.items() if v == "high"]
        if high_tags:
            items.append(
                f"{_tag('FACT')} High-confidence data on: "
                f"{', '.join(high_tags)} — derived directly from filings"
            )

    capex_pct = assumptions.get("capex_pct_revenue")
    try:
        cp = float(capex_pct) if capex_pct is not None else None
        if cp is not None and cp < 5:
            items.append(
                f"{_tag('FACT')} Low capex intensity ({cp:.1f}% of revenue) — "
                "asset-light model generates strong free cash flow"
            )
    except (TypeError, ValueError):
        pass

    return items[:5]


def _build_weaknesses(
    assumptions: dict[str, Any],
    sector_defaults: dict[str, Any],
) -> list[str]:
    items: list[str] = []

    ebitda_margin = assumptions.get("ebitda_margin")
    sector_ebitda = (
        sector_defaults.get("ebitda_margin_default") or
        sector_defaults.get("ebitda_margin") or 18.0
    )

    try:
        em = float(ebitda_margin) if ebitda_margin is not None else None
        se = float(sector_ebitda)
        if em is not None and em < se:
            items.append(
                f"{_tag('FACT')} EBITDA margin {em:.1f}% below sector average "
                f"({se:.1f}%) — cost pressure or pricing weakness"
            )
    except (TypeError, ValueError):
        pass

    net_debt = assumptions.get("net_debt")
    try:
        nd = float(net_debt) if net_debt is not None else None
        base_rev = float(assumptions.get("base_revenue") or 1)
        em_val   = float(ebitda_margin or 18) / 100
        ebitda   = base_rev * em_val
        if nd is not None and nd > 0 and ebitda > 0 and nd > 2 * ebitda:
            items.append(
                f"{_tag('FACT')} Net debt {nd:,.0f} > 2× EBITDA — "
                "elevated leverage constrains financial flexibility"
            )
    except (TypeError, ValueError):
        pass

    growths = []
    for yr in range(1, 6):
        v = assumptions.get(f"revenue_growth_y{yr}")
        if v is not None:
            try:
                growths.append(float(v))
            except (TypeError, ValueError):
                pass
    if len(growths) >= 3 and growths[0] < growths[2]:
        items.append(
            f"{_tag('ASSUMPTION')} Revenue growth decelerating "
            f"(Y1: {growths[0]:.1f}% → Y3: {growths[2]:.1f}%) — "
            "business momentum losing steam"
        )

    conf_tags = assumptions.get("_confidence_tags") or assumptions.get("confidence_tags") or {}
    if isinstance(conf_tags, dict):
        low_tags = [k for k, v in conf_tags.items() if v == "low"]
        if low_tags:
            items.append(
                f"{_tag('ASSUMPTION')} Low-confidence assumptions on: "
                f"{', '.join(low_tags)} — model uncertainty is higher than usual"
            )

    # Fallback item if list is too short
    if len(items) < 2:
        items.append(
            f"{_tag('ASSUMPTION')} Limited public data available — "
            "key financial metrics rely on estimated assumptions"
        )

    return items[:5]


def _build_opportunities(
    assumptions: dict[str, Any],
    scenarios: dict[str, Any],
    insights: list[dict],
    sector: str,
) -> list[str]:
    items: list[str] = []

    # Bull case upside
    bull = scenarios.get("scenarios", {}).get("bull") or {}
    bull_upside = bull.get("upside_pct")
    try:
        up = float(bull_upside) if bull_upside is not None else None
        if up is not None and up > 30:
            items.append(
                f"{_tag('ASSUMPTION')} Bull case upside {up:.1f}% — "
                "significant re-rating potential if key assumptions play out"
            )
    except (TypeError, ValueError):
        pass

    # Positive signals from insights
    positive_signals = [
        s for s in insights
        if (s.get("sentiment") or s.get("direction") or "").lower() in ("positive", "bullish", "up")
    ]
    for sig in positive_signals[:2]:
        name = sig.get("signal_name") or sig.get("name") or sig.get("title") or "Signal"
        items.append(
            f"{_tag('INTERPRETATION')} {name} — positive catalyst detected in recent data"
        )

    # Sector tailwind signals
    folder_map = {
        "petroleum_energy": "petroleum",
        "banking_nbfc":     "banking",
        "fmcg_retail":      "fmcg",
        "it_tech":          "it",
        "pharma":           "pharma",
        "real_estate":      "real_estate",
        "auto":             "auto",
    }
    folder = folder_map.get(sector, sector)
    try:
        sig_file = FRAMEWORKS_DIR / folder / "signals.json"
        if sig_file.exists():
            data = json.loads(sig_file.read_text())
            key_drivers = data.get("key_drivers", [])
            if key_drivers:
                items.append(
                    f"{_tag('INTERPRETATION')} Sector key drivers — "
                    f"{', '.join(str(d) for d in key_drivers[:3])} — "
                    "monitor for positive shifts"
                )
    except Exception:
        pass

    # Reverse DCF opportunity
    rdcf = scenarios.get("reverse_dcf") or {}
    if (rdcf.get("assessment") or "").lower().replace(" ", "_") == "priced_for_pessimism":
        items.append(
            f"{_tag('ASSUMPTION')} Market currently pricing pessimistic scenario — "
            "any positive newsflow could trigger re-rating"
        )

    # Fallback
    if len(items) < 2:
        items.append(
            f"{_tag('INTERPRETATION')} Sector growth tailwinds may benefit the company "
            "as macro conditions normalise"
        )

    return items[:5]


def _build_threats(
    guardrails: list[dict],
    insights:   list[dict],
    scenarios:  dict[str, Any],
) -> list[str]:
    items: list[str] = []

    # Negative / high severity signals
    neg_signals = [
        s for s in insights
        if (s.get("severity") or "").lower() == "high" or
           (s.get("sentiment") or s.get("direction") or "").lower() in ("negative", "bearish", "down")
    ]
    for sig in neg_signals[:2]:
        name = sig.get("signal_name") or sig.get("name") or sig.get("title") or "Risk signal"
        items.append(
            f"{_tag('INTERPRETATION')} {name} — negative signal flagged; may impact assumptions"
        )

    # Bear case downside
    bear = scenarios.get("scenarios", {}).get("bear") or {}
    bear_upside = bear.get("upside_pct")
    try:
        down = float(bear_upside) if bear_upside is not None else None
        if down is not None and down < -20:
            items.append(
                f"{_tag('ASSUMPTION')} Bear case downside {down:.1f}% — "
                "meaningful capital loss risk if bear scenario materialises"
            )
    except (TypeError, ValueError):
        pass

    # Guardrail breaches
    if len(guardrails) > 0:
        metrics = list({g.get("metric", "unknown") for g in guardrails})[:3]
        items.append(
            f"{_tag('ASSUMPTION')} Guardrail breach(es) on "
            f"{', '.join(str(m) for m in metrics)} — "
            "model at boundary conditions; assumptions need review"
        )

    # Fallback items
    if len(items) < 2:
        items.append(
            f"{_tag('INTERPRETATION')} Macro headwinds (rates, inflation, FX) "
            "could compress valuations across the sector"
        )
    if len(items) < 2:
        items.append(
            f"{_tag('INTERPRETATION')} Competitive intensity may pressure margins "
            "if peers gain market share"
        )

    return items[:5]


# ── Main public function ──────────────────────────────────────────────────────

def generate_swot(
    session: Any,            # ResearchSession
    scoring: Any,            # ScoringResult
    sector:  str = "other",
) -> dict[str, list[str]]:
    """
    Generate SWOT analysis from session data.
    Each item is tagged [FACT], [ASSUMPTION], or [INTERPRETATION].
    Never fails — returns empty lists if all data is missing.

    Args:
        session: ResearchSession instance
        scoring: ScoringResult from score_session()
        sector:  sector string

    Returns:
        dict with keys: strengths, weaknesses, opportunities, threats
    """
    empty: dict[str, list[str]] = {
        "strengths":     [],
        "weaknesses":    [],
        "opportunities": [],
        "threats":       [],
    }

    try:
        assumptions: dict[str, Any] = {}
        try:
            assumptions = session.get_assumptions() or {}
        except Exception:
            pass

        scenarios: dict[str, Any] = {}
        try:
            scenarios = session.get_scenarios() or {}
        except Exception:
            pass

        guardrails: list[dict] = []
        gl = _load_json(session.guardrail_log_file)
        if isinstance(gl, list):
            guardrails = gl

        insights: list[dict] = []
        ins = _load_json(session.insights_file)
        if isinstance(ins, list):
            insights = ins

        sector_defaults = _get_sector_defaults(sector)

        return {
            "strengths":     _build_strengths(assumptions, sector_defaults),
            "weaknesses":    _build_weaknesses(assumptions, sector_defaults),
            "opportunities": _build_opportunities(assumptions, scenarios, insights, sector),
            "threats":       _build_threats(guardrails, insights, scenarios),
        }

    except Exception as exc:
        logger.error(f"[swot] generate_swot failed: {exc}")
        return empty
