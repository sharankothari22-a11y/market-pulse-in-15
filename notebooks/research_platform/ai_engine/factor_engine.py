"""
ai_engine/factor_engine.py
───────────────────────────
Layer 7 — Factor Engine.

Signal → Factor → Assumption mapping with full source traceability.

The document example:
  Signal: "Oil +15%"
  Factor: "margin compression, high severity"
  Assumption change: EBITDA -2%

Every assumption change must have a traceable chain:
  source_event → detected_signal → factor → assumption_delta
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.signal_detector import DetectedSignal

RULES_FILE = Path(__file__).parent / "assumption_rules.json"


@dataclass
class AssumptionDelta:
    """A proposed change to one DCF assumption metric."""
    metric: str
    delta: float                # change amount (not absolute value)
    direction: str              # "increase" | "decrease" | "neutral"
    magnitude: str              # "large" | "medium" | "small"
    confidence: str             # "high" | "medium" | "low"
    reason: str                 # human-readable explanation
    source_signal_id: str
    source_event: str
    transmission_chain: str     # signal → factor → assumption


@dataclass
class Factor:
    """Intermediate layer between signal and assumption change."""
    factor_id: str
    description: str
    affected_metrics: list[str]
    deltas: list[AssumptionDelta] = field(default_factory=list)


# ── Factor mapping rules ──────────────────────────────────────────────────────
# These rules encode the transmission chain from signal to assumption change.
# Format: signal_id → list of (metric, delta_fn, confidence, magnitude)
# delta_fn takes the signal and returns a float delta.

SIGNAL_TO_FACTORS: dict[str, list[dict[str, Any]]] = {
    # Universal signals
    "guidance_change": [
        {"metric": "revenue_growth",  "delta": +2.0,  "direction": "increase", "magnitude": "medium", "confidence": "high",   "reason": "Upward guidance revision signals management confidence in revenue acceleration"},
        {"metric": "ebitda_margin",   "delta": +0.5,  "direction": "increase", "magnitude": "small",  "confidence": "medium", "reason": "Positive guidance often implies operating leverage"},
    ],
    "guidance_downgrade": [
        {"metric": "revenue_growth",  "delta": -3.0,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Downward guidance signals demand weakness or execution risk"},
        {"metric": "ebitda_margin",   "delta": -1.0,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Guidance cut often includes margin outlook deterioration"},
    ],
    "management_change": [
        {"metric": "equity_risk_premium", "delta": +0.5, "direction": "increase", "magnitude": "small", "confidence": "low", "reason": "Leadership uncertainty increases risk premium by 50-75 bps temporarily"},
    ],
    "regulatory_action": [
        {"metric": "equity_risk_premium", "delta": +1.0, "direction": "increase", "magnitude": "medium", "confidence": "high", "reason": "Regulatory penalty signals governance risk"},
        {"metric": "revenue_growth",      "delta": -2.0, "direction": "decrease", "magnitude": "medium", "confidence": "medium", "reason": "Regulatory constraints may limit operations"},
    ],
    "margin_pressure": [
        {"metric": "ebitda_margin",   "delta": -1.5,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Input cost spike compresses EBITDA margin with 1-2 quarter lag"},
        {"metric": "gross_margin",    "delta": -2.0,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Gross margin contracts before EBITDA, reflecting direct cost impact"},
    ],
    "capex_announcement": [
        {"metric": "capex_pct_revenue",   "delta": +3.0,  "direction": "increase", "magnitude": "medium", "confidence": "high",   "reason": "Expansion capex increases near-term capex intensity"},
        {"metric": "revenue_growth",      "delta": +1.5,  "direction": "increase", "magnitude": "small",  "confidence": "low",    "reason": "Capacity addition supports medium-term revenue growth"},
    ],
    "debt_rating_change": [
        {"metric": "cost_of_debt",    "delta": +0.5,  "direction": "increase", "magnitude": "small",  "confidence": "high",   "reason": "Rating downgrade directly raises cost of new debt"},
        {"metric": "wacc",            "delta": +0.3,  "direction": "increase", "magnitude": "small",  "confidence": "high",   "reason": "Higher cost of debt flows into WACC"},
    ],
    "insider_activity": [
        {"metric": "equity_risk_premium", "delta": +0.5, "direction": "increase", "magnitude": "small", "confidence": "medium", "reason": "Promoter pledging or selling signals financial stress"},
    ],
    "earnings_surprise": [
        {"metric": "revenue_growth",  "delta": +1.5,  "direction": "increase", "magnitude": "small",  "confidence": "medium", "reason": "Positive earnings surprise updates base period for growth"},
        {"metric": "ebitda_margin",   "delta": +0.5,  "direction": "increase", "magnitude": "small",  "confidence": "medium", "reason": "Beat suggests operating leverage better than modelled"},
    ],

    # Sector signals — petroleum
    "crude_price_move": [
        {"metric": "ebitda_margin",   "delta": -1.5,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Crude +10% → feedstock cost +8-10% for refiners (GRM compression)"},
        {"metric": "revenue_growth",  "delta": +2.0,  "direction": "increase", "magnitude": "medium", "confidence": "high",   "reason": "Higher crude prices inflate E&P revenue directly"},
    ],
    "grm_change": [
        {"metric": "ebitda_margin",   "delta": +2.0,  "direction": "increase", "magnitude": "large",  "confidence": "high",   "reason": "GRM improvement flows almost directly into refiner EBITDA per barrel"},
    ],
    "opec_production": [
        {"metric": "revenue_growth",  "delta": +1.0,  "direction": "increase", "magnitude": "small",  "confidence": "low",    "reason": "OPEC supply cuts support crude price in 1-3 months"},
    ],

    # Sector signals — banking
    "rbi_rate_change": [
        {"metric": "nim_pct",         "delta": +0.1,  "direction": "increase", "magnitude": "small",  "confidence": "high",   "reason": "Rate hike improves NIM for CASA-heavy banks (5-15 bps per 25 bps)"},
    ],
    "npl_movement": [
        {"metric": "ebitda_margin",   "delta": -1.0,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "NPA increase → higher provisioning → lower net profit margin"},
    ],
    "credit_growth": [
        {"metric": "revenue_growth",  "delta": +1.5,  "direction": "increase", "magnitude": "medium", "confidence": "high",   "reason": "Loan book growth drives NII growth with ~1 quarter lag"},
    ],

    # Sector signals — pharma
    "fda_action": [
        {"metric": "revenue_growth",  "delta": +5.0,  "direction": "increase", "magnitude": "large",  "confidence": "high",   "reason": "ANDA approval opens US generic market — binary step-change in revenue"},
        {"metric": "equity_risk_premium", "delta": -0.5, "direction": "decrease", "magnitude": "small", "confidence": "medium", "reason": "Clean FDA status reduces regulatory overhang"},
    ],
    "api_price_move": [
        {"metric": "gross_margin",    "delta": -3.0,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "API 30-50% of COGS; +10% API price → gross margin -3-5%"},
    ],
    "plant_inspection": [
        {"metric": "revenue_growth",  "delta": -3.0,  "direction": "decrease", "magnitude": "large",  "confidence": "high",   "reason": "OAI status blocks all US approvals from that plant"},
        {"metric": "equity_risk_premium", "delta": +1.0, "direction": "increase", "magnitude": "medium", "confidence": "high", "reason": "Import alert raises tail risk premium"},
    ],

    # Sector signals — IT
    "large_deal_win": [
        {"metric": "revenue_growth",  "delta": +2.0,  "direction": "increase", "magnitude": "medium", "confidence": "high",   "reason": "TCV increases revenue visibility; ramp contributes in 2-4 quarters"},
    ],
    "attrition_change": [
        {"metric": "ebitda_margin",   "delta": -0.5,  "direction": "decrease", "magnitude": "small",  "confidence": "medium", "reason": "Attrition +2% → replacement cost → wage cost +50-100 bps on margin"},
    ],
    "currency_move": [
        {"metric": "revenue_growth",  "delta": +1.5,  "direction": "increase", "magnitude": "medium", "confidence": "high",   "reason": "INR depreciation: USD revenue translates to higher INR at constant billing"},
    ],

    # Sector signals — auto
    "monthly_volume": [
        {"metric": "revenue_growth",  "delta": +1.0,  "direction": "increase", "magnitude": "small",  "confidence": "medium", "reason": "Strong volume momentum supports near-term revenue upgrade"},
    ],
    "commodity_cost": [
        {"metric": "ebitda_margin",   "delta": -1.5,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Steel +10% → EBITDA margin -150-200 bps with 2-quarter lag"},
        {"metric": "gross_margin",    "delta": -2.0,  "direction": "decrease", "magnitude": "medium", "confidence": "high",   "reason": "Commodity is 60-70% of auto COGS"},
    ],
}


def _load_rules() -> dict[str, Any]:
    if RULES_FILE.exists():
        return json.loads(RULES_FILE.read_text())
    return {"rules": {}}


def signals_to_factors(
    signals: list[DetectedSignal],
    current_assumptions: dict[str, float],
) -> list[AssumptionDelta]:
    """
    Convert detected signals into proposed assumption deltas.

    This is Brain 1 logic — pure Python, deterministic, no LLM.
    For each signal, look up the factor mapping and produce delta objects.
    The confidence scoring layer (Layer 8) then weight-adjusts these deltas.
    """
    rules = _load_rules()
    all_deltas: list[AssumptionDelta] = []

    for signal in signals:
        # Adjust signal_id based on direction where needed
        effective_id = signal.signal_id
        if signal.signal_id == "guidance_change" and signal.direction == "negative":
            effective_id = "guidance_downgrade"
        if signal.signal_id == "earnings_surprise" and signal.direction == "negative":
            # Flip deltas for miss
            pass

        factor_mappings = SIGNAL_TO_FACTORS.get(effective_id, [])
        if not factor_mappings:
            logger.debug(f"[factor_engine] No factor mapping for signal: {effective_id}")
            continue

        for fm in factor_mappings:
            metric = fm["metric"]
            raw_delta = fm["delta"]

            # Flip delta sign for negative-direction signals if not already specified
            if signal.direction == "negative" and raw_delta > 0:
                raw_delta = -raw_delta
            elif signal.direction == "positive" and raw_delta < 0:
                raw_delta = -raw_delta

            # Validate against guardrail rules
            current_val = current_assumptions.get(metric, 0.0)
            proposed_val = current_val + raw_delta
            rule = rules.get("rules", {}).get(metric, {})

            min_val = rule.get("min")
            max_val = rule.get("max")
            if min_val is not None:
                proposed_val = max(proposed_val, min_val)
            if max_val is not None:
                proposed_val = min(proposed_val, max_val)

            clamped_delta = proposed_val - current_val

            all_deltas.append(AssumptionDelta(
                metric=metric,
                delta=round(clamped_delta, 4),
                direction=fm.get("direction", "neutral"),
                magnitude=fm.get("magnitude", "medium"),
                confidence=fm.get("confidence", "medium"),
                reason=fm.get("reason", ""),
                source_signal_id=signal.signal_id,
                source_event=signal.source_name,
                transmission_chain=(
                    f"Event: '{signal.source_text[:80]}' → "
                    f"Signal: {signal.signal_name} → "
                    f"Factor: {signal.matched_keywords} → "
                    f"Assumption: {metric} {'+' if clamped_delta >= 0 else ''}{clamped_delta:.2f}"
                ),
            ))

    logger.info(f"[factor_engine] Produced {len(all_deltas)} assumption deltas from {len(signals)} signals")
    return all_deltas


def consolidate_deltas(
    deltas: list[AssumptionDelta],
) -> dict[str, AssumptionDelta]:
    """
    When multiple signals affect the same metric, consolidate into one delta.
    Strategy: weighted average by confidence (high=1.0, medium=0.6, low=0.3).
    Returns one AssumptionDelta per metric.
    """
    conf_weights = {"high": 1.0, "medium": 0.6, "low": 0.3}

    by_metric: dict[str, list[AssumptionDelta]] = {}
    for d in deltas:
        by_metric.setdefault(d.metric, []).append(d)

    consolidated: dict[str, AssumptionDelta] = {}
    for metric, ds in by_metric.items():
        if len(ds) == 1:
            consolidated[metric] = ds[0]
            continue

        # Weighted average
        total_weight = sum(conf_weights.get(d.confidence, 0.5) for d in ds)
        weighted_delta = sum(
            d.delta * conf_weights.get(d.confidence, 0.5) for d in ds
        ) / total_weight if total_weight > 0 else 0

        # Use the highest-confidence delta as the base
        best = max(ds, key=lambda d: conf_weights.get(d.confidence, 0.5))
        reasons = "; ".join(d.reason for d in ds[:3])

        consolidated[metric] = AssumptionDelta(
            metric=metric,
            delta=round(weighted_delta, 4),
            direction="increase" if weighted_delta > 0 else "decrease",
            magnitude=best.magnitude,
            confidence=best.confidence,
            reason=f"Consolidated from {len(ds)} signals: {reasons}",
            source_signal_id=best.source_signal_id,
            source_event=best.source_event,
            transmission_chain=best.transmission_chain,
        )

    return consolidated
