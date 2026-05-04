"""
ai_engine/scoring.py
─────────────────────
5-dimension scoring system ported from the company_research notebook.
Works entirely from session JSON files — never requires the database.

Dimensions:
  financial_strength        (0-100)
  growth_quality            (0-100)
  valuation_attractiveness  (0-100)
  risk_score                (0-100)  ← inverted; higher = less risk
  market_positioning        (0-100)
  composite_score           (weighted average)

All functions fail gracefully — never crash the pipeline.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ScoringResult:
    financial_strength:       float = 50.0   # 0-100
    growth_quality:           float = 50.0   # 0-100
    valuation_attractiveness: float = 50.0   # 0-100
    risk_score:               float = 50.0   # 0-100 (higher = safer)
    market_positioning:       float = 50.0   # 0-100
    composite_score:          float = 50.0   # weighted average
    recommendation:           str   = "Insufficient Data"
    business_quality:         str   = "C"
    rationale:                list  = field(default_factory=list)
    caveats:                  list  = field(default_factory=list)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _load_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        logger.debug(f"[scoring] could not load {path}: {exc}")
    return None


def _get_sector_defaults(sector: str) -> dict[str, Any]:
    """Load EBITDA margin default and other sector benchmarks."""
    try:
        # Normalise sector name to folder name
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
        signals_file = FRAMEWORKS_DIR / folder / "signals.json"
        if signals_file.exists():
            data = json.loads(signals_file.read_text())
            return data.get("default_assumptions", {})
    except Exception:
        pass
    return {}


def _competitive_signals(sector: str) -> tuple[int, int]:
    """
    Return (positive_count, negative_count) from the sector signals file.
    Positive signals: id / name does NOT contain negative keywords.
    Negative signals: contain risk / threat / pressure / downside / cut.
    """
    neg_kw = {"risk", "threat", "pressure", "downside", "cut", "decline", "loss"}
    pos, neg = 0, 0
    try:
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
        signals_file = FRAMEWORKS_DIR / folder / "signals.json"
        if signals_file.exists():
            data = json.loads(signals_file.read_text())
            for sig in data.get("signals", []):
                name = (sig.get("name", "") + sig.get("id", "")).lower()
                if any(k in name for k in neg_kw):
                    neg += 1
                else:
                    pos += 1
    except Exception:
        pass
    return pos, neg


# ── Individual dimension scorers ──────────────────────────────────────────────

def _score_financial_strength(
    assumptions: dict[str, Any],
    sector_defaults: dict[str, Any],
    rationale: list[str],
    caveats: list[str],
) -> float:
    score = 50.0

    ebitda_margin   = assumptions.get("ebitda_margin")
    net_debt        = assumptions.get("net_debt")
    capex_pct       = assumptions.get("capex_pct_revenue")
    base_revenue    = assumptions.get("base_revenue") or 1
    sector_ebitda   = sector_defaults.get("ebitda_margin_default") or \
                      sector_defaults.get("ebitda_margin") or 18.0

    if ebitda_margin is not None:
        try:
            em = float(ebitda_margin)
            sd = float(sector_ebitda)
            if em > sd + 5:
                score += 20
                rationale.append(f"EBITDA margin {em:.1f}% is well above sector avg {sd:.1f}% → strong pricing power")
            elif em > sd:
                score += 10
                rationale.append(f"EBITDA margin {em:.1f}% ahead of sector avg {sd:.1f}%")
            else:
                score -= 5
                caveats.append(f"EBITDA margin {em:.1f}% trails sector avg {sd:.1f}%")
        except (TypeError, ValueError):
            caveats.append("EBITDA margin data not numeric")
    else:
        caveats.append("EBITDA margin not available")

    if net_debt is not None:
        try:
            nd = float(net_debt)
            ebitda = (float(ebitda_margin or 18) / 100) * float(base_revenue)
            if nd < 0:
                score += 15
                rationale.append("Net cash position — strong balance sheet")
            elif ebitda > 0 and nd < 2 * ebitda:
                score += 10
                rationale.append(f"Net debt / EBITDA < 2× — manageable leverage")
            else:
                score -= 5
                caveats.append("High net debt relative to EBITDA")
        except (TypeError, ValueError):
            pass

    if capex_pct is not None:
        try:
            if float(capex_pct) < 10:
                score += 10
                rationale.append(f"Capex {capex_pct:.1f}% of revenue — asset-light model")
        except (TypeError, ValueError):
            pass

    return _clamp(score)


def _score_growth_quality(
    assumptions: dict[str, Any],
    rationale: list[str],
    caveats: list[str],
) -> float:
    score = 50.0

    growths = []
    for yr in range(1, 6):
        v = assumptions.get(f"revenue_growth_y{yr}")
        if v is not None:
            try:
                growths.append(float(v))
            except (TypeError, ValueError):
                pass

    if not growths:
        caveats.append("No revenue growth assumptions found")
        return score

    g1 = growths[0]
    if g1 > 15:
        score += 20
        rationale.append(f"Y1 revenue growth {g1:.1f}% — high growth profile")
    elif g1 > 10:
        score += 10
        rationale.append(f"Y1 revenue growth {g1:.1f}% — solid growth")
    elif g1 < 5:
        score -= 5
        caveats.append(f"Y1 revenue growth {g1:.1f}% — modest")

    if len(growths) >= 5:
        std_dev = (sum((g - sum(growths) / len(growths)) ** 2 for g in growths) / len(growths)) ** 0.5
        if std_dev < 3:
            score += 15
            rationale.append("Revenue growth consistent across Y1–Y5 (low variance)")
        else:
            caveats.append(f"Revenue growth volatile across years (σ={std_dev:.1f}%)")

    if len(growths) >= 3 and growths[0] > growths[2]:
        score += 10
        rationale.append("Growth accelerating — Y1 > Y3")

    return _clamp(score)


def _score_valuation_attractiveness(
    scenarios: dict[str, Any],
    rationale: list[str],
    caveats: list[str],
) -> float:
    score = 50.0

    base = scenarios.get("scenarios", {}).get("base") or {}
    upside = base.get("upside_pct")

    if upside is not None:
        try:
            up = float(upside)
            if up > 30:
                score += 25
                rationale.append(f"Base case upside {up:.1f}% — significant undervaluation")
            elif up > 15:
                score += 15
                rationale.append(f"Base case upside {up:.1f}% — attractive valuation")
            elif up < 0:
                score -= 15
                caveats.append(f"Base case shows {up:.1f}% downside at current price")
        except (TypeError, ValueError):
            caveats.append("Upside % is not numeric")
    else:
        caveats.append("Scenarios not run yet — valuation score is neutral")

    rdcf = scenarios.get("reverse_dcf") or {}
    assessment = (rdcf.get("assessment") or "").lower().replace(" ", "_")
    if assessment == "priced_for_pessimism":
        score += 20
        rationale.append("Reverse DCF: market pricing in pessimism — asymmetric upside")
    elif assessment in ("fairly_valued", "fair_value"):
        score += 10
        rationale.append("Reverse DCF: market pricing fairly")
    elif assessment == "priced_for_perfection":
        score -= 10
        caveats.append("Reverse DCF: market pricing in high growth — limited margin of safety")

    return _clamp(score)


def _score_risk(
    guardrails: list[dict],
    assumptions: dict[str, Any],
    scenarios: dict[str, Any],
    insights: list[dict],
    rationale: list[str],
    caveats: list[str],
) -> float:
    score = 50.0

    breach_count = len(guardrails)
    if breach_count == 0:
        score += 20
        rationale.append("No guardrail breaches — all assumptions within bounds")
    elif breach_count <= 2:
        score -= 5
        caveats.append(f"{breach_count} guardrail breach(es) — some assumptions at limits")
    else:
        score -= 15
        caveats.append(f"{breach_count} guardrail breaches — model under stress")

    # Confidence tags
    conf_data = assumptions.get("_confidence_tags") or assumptions.get("confidence_tags") or {}
    if isinstance(conf_data, dict):
        tags = list(conf_data.values())
        if tags and all(t == "high" for t in tags):
            score += 15
            rationale.append("All assumption confidence tags: HIGH (from filings)")
        elif any(t == "low" for t in tags):
            score -= 10
            caveats.append("Some assumptions tagged LOW confidence — verify manually")

    # Bear case downside
    bear = scenarios.get("scenarios", {}).get("bear") or {}
    bear_upside = bear.get("upside_pct")
    if bear_upside is not None:
        try:
            if float(bear_upside) > -15:
                score += 15
                rationale.append("Bear case downside < 15% — limited downside risk")
            elif float(bear_upside) < -30:
                score -= 10
                caveats.append(f"Bear case downside {bear_upside:.1f}% — significant tail risk")
        except (TypeError, ValueError):
            pass

    # High severity signals
    high_sev = [s for s in insights if (s.get("severity") or "").lower() == "high"]
    if not high_sev:
        score += 10
        rationale.append("No high-severity signals detected")
    else:
        score -= len(high_sev) * 5
        caveats.append(f"{len(high_sev)} high-severity signal(s) detected")

    return _clamp(score)


def _score_market_positioning(
    sector: str,
    rationale: list[str],
    caveats: list[str],
) -> float:
    score = 50.0
    pos, neg = _competitive_signals(sector)
    total = pos + neg
    if total == 0:
        caveats.append("No sector framework signals — market positioning score is neutral")
        return score

    net = pos - neg
    adjustment = _clamp(net / max(total, 1) * 30, -30, 30)
    score += adjustment
    if net > 0:
        rationale.append(f"Sector framework: {pos} positive vs {neg} negative competitive signals")
    else:
        caveats.append(f"Sector framework: {neg} negative vs {pos} positive competitive signals")

    return _clamp(score)


# ── Main public function ──────────────────────────────────────────────────────

def score_session(
    session: Any,  # ResearchSession — avoid circular import
    sector: str = "other",
) -> ScoringResult:
    """
    Calculate all 5 scoring dimensions from session JSON files.
    Never raises — returns neutral ScoringResult if data is missing.

    Args:
        session: ResearchSession instance
        sector:  sector string (e.g. "petroleum_energy", "it_tech")

    Returns:
        ScoringResult with all dimensions populated
    """
    result = ScoringResult()
    rationale: list[str] = []
    caveats:   list[str] = []

    try:
        # ── Load all session data ────────────────────────────────────────────
        assumptions = {}
        try:
            assumptions = session.get_assumptions() or {}
        except Exception:
            caveats.append("Could not load assumptions")

        scenarios = {}
        try:
            scenarios = session.get_scenarios() or {}
        except Exception:
            caveats.append("Could not load scenarios")

        guardrails: list[dict] = []
        try:
            gl = _load_json(session.guardrail_log_file)
            guardrails = gl if isinstance(gl, list) else []
        except Exception:
            pass

        insights: list[dict] = []
        try:
            ins = _load_json(session.insights_file)
            insights = ins if isinstance(ins, list) else []
        except Exception:
            pass

        sector_defaults = _get_sector_defaults(sector)

        # ── Score each dimension ─────────────────────────────────────────────
        result.financial_strength       = _score_financial_strength(assumptions, sector_defaults, rationale, caveats)
        result.growth_quality           = _score_growth_quality(assumptions, rationale, caveats)
        result.valuation_attractiveness = _score_valuation_attractiveness(scenarios, rationale, caveats)
        result.risk_score               = _score_risk(guardrails, assumptions, scenarios, insights, rationale, caveats)
        result.market_positioning       = _score_market_positioning(sector, rationale, caveats)

        # ── Composite ────────────────────────────────────────────────────────
        result.composite_score = (
            result.financial_strength       * 0.25 +
            result.growth_quality           * 0.25 +
            result.valuation_attractiveness * 0.25 +
            result.risk_score               * 0.15 +
            result.market_positioning       * 0.10
        )

        # ── Recommendation ───────────────────────────────────────────────────
        cs = result.composite_score
        has_data = bool(assumptions) and bool(scenarios.get("scenarios"))
        if not has_data:
            result.recommendation = "Insufficient Data"
        elif cs > 65:
            result.recommendation = "Buy"
        elif cs > 45:
            result.recommendation = "Hold"
        else:
            result.recommendation = "Avoid"

        # ── Business quality ─────────────────────────────────────────────────
        fs = result.financial_strength
        if fs > 70:
            result.business_quality = "A"
        elif fs > 55:
            result.business_quality = "B"
        elif fs > 40:
            result.business_quality = "C"
        else:
            result.business_quality = "D"

        result.rationale = rationale[:8]
        result.caveats   = caveats[:5]

        logger.info(
            f"[scoring] {session.ticker} — composite={result.composite_score:.1f} "
            f"rec={result.recommendation} quality={result.business_quality}"
        )

    except Exception as exc:
        logger.error(f"[scoring] score_session failed: {exc}")
        result.caveats = [f"Scoring error: {exc}"]

    return result
