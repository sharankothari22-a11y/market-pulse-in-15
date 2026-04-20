"""
ai_engine/confidence_scorer.py
────────────────────────────────
Layer 8 — Confidence Scoring.

Every assumption gets tagged: High / Medium / Low.
  High  → auto-update (contract-backed, official announcement)
  Medium → update with note (guidance, analyst estimate)
  Low   → flag for human review (rumour, weak signal)

Confidence = f(source_reliability, recency, corroboration_count)

From the document:
  High = contract-backed
  Medium = guidance
  Low = analyst estimate
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from loguru import logger

# ── Source reliability weights ────────────────────────────────────────────────
# Higher = more reliable. Used in final confidence calculation.

SOURCE_RELIABILITY: dict[str, float] = {
    # Official / primary sources
    "exchange_filing":        1.0,   # NSE/BSE filing
    "sebi":                   1.0,   # SEBI order
    "rbi":                    1.0,   # RBI policy
    "company_announcement":   0.95,  # Company press release
    "earnings_transcript":    0.95,  # Earnings call
    "annual_report":          0.90,  # Annual report
    "credit_rating":          0.85,  # CRISIL/ICRA/CARE rating
    "government_gazette":     0.90,  # Government notification
    "fda":                    1.0,   # FDA order/approval

    # Market data
    "nse_csv":                1.0,   # NSE Bhavcopy
    "bse_csv":                1.0,   # BSE Bhavcopy
    "fred":                   0.95,  # FRED macroeconomic
    "world_bank":             0.90,  # World Bank data
    "amfi":                   0.95,  # AMFI NAVs
    "frankfurter":            0.90,  # ECB FX rates

    # News / media
    "reuters":                0.80,
    "economic_times":         0.75,
    "moneycontrol":           0.70,
    "bloomberg":              0.80,
    "financial_times":        0.80,
    "mint":                   0.75,
    "rss":                    0.65,  # Generic RSS
    "rss_feeds":              0.65,
    "news":                   0.60,

    # Alternative sources
    "gdelt":                  0.55,  # GDELT event database
    "reddit":                 0.40,
    "twitter":                0.40,
    "analyst_estimate":       0.50,
    "unknown":                0.50,
}

# ── Recency decay ─────────────────────────────────────────────────────────────

def recency_score(event_date: Optional[date], as_of: Optional[date] = None) -> float:
    """Recency score 0-1. Decays over time.
    - Same day: 1.0
    - 1 week ago: 0.85
    - 1 month ago: 0.65
    - 3 months ago: 0.40
    - 6 months ago: 0.20
    """
    if event_date is None:
        return 0.5  # unknown recency
    today = as_of or date.today()
    days_ago = (today - event_date).days
    if days_ago <= 0:
        return 1.0
    if days_ago <= 7:
        return 0.85
    if days_ago <= 30:
        return 0.65
    if days_ago <= 90:
        return 0.40
    if days_ago <= 180:
        return 0.20
    return 0.10


# ── Corroboration ─────────────────────────────────────────────────────────────

def corroboration_boost(source_count: int) -> float:
    """Boost score if same signal seen in multiple independent sources.
    1 source: 0, 2 sources: +0.05, 3+: +0.10
    """
    if source_count >= 3:
        return 0.10
    if source_count >= 2:
        return 0.05
    return 0.0


# ── Main scorer ───────────────────────────────────────────────────────────────

@dataclass
class ConfidenceResult:
    score: float                # 0.0 – 1.0
    label: str                  # "high" | "medium" | "low"
    action: str                 # "auto_update" | "update_with_note" | "flag_for_review"
    breakdown: dict             # for audit trail


def score(
    source_name: str,
    event_date: Optional[date] = None,
    corroborating_sources: int = 1,
    signal_magnitude: str = "medium",  # "large" | "medium" | "small"
    as_of: Optional[date] = None,
) -> ConfidenceResult:
    """Compute a confidence score for one signal/assumption change."""

    # Normalise source name
    src_key = source_name.lower().replace(" ", "_").replace("-", "_")

    # Try exact match, then partial match
    reliability = SOURCE_RELIABILITY.get(src_key, 0.0)
    if reliability == 0.0:
        for key, val in SOURCE_RELIABILITY.items():
            if key in src_key or src_key in key:
                reliability = val
                break
        if reliability == 0.0:
            reliability = SOURCE_RELIABILITY["unknown"]

    recency = recency_score(event_date, as_of=as_of)
    corroboration = corroboration_boost(corroborating_sources)

    # Magnitude modifier: large signals get slight boost (more attention = more reliable signal)
    mag_boost = {"large": 0.05, "medium": 0.0, "small": -0.05}.get(signal_magnitude, 0.0)

    # Weighted composite
    raw_score = (reliability * 0.50) + (recency * 0.35) + (corroboration * 0.15) + mag_boost
    final_score = max(0.0, min(1.0, raw_score))

    # Thresholds from validation_rules.json
    if final_score >= 0.75:
        label = "high"
        action = "auto_update"
    elif final_score >= 0.45:
        label = "medium"
        action = "update_with_note"
    else:
        label = "low"
        action = "flag_for_review"

    return ConfidenceResult(
        score=round(final_score, 3),
        label=label,
        action=action,
        breakdown={
            "reliability": round(reliability, 3),
            "recency": round(recency, 3),
            "corroboration": round(corroboration, 3),
            "magnitude_boost": mag_boost,
            "source_name": source_name,
            "event_date": str(event_date) if event_date else None,
        }
    )


def score_delta(
    delta,   # AssumptionDelta from factor_engine
    event_date: Optional[date] = None,
    corroborating_sources: int = 1,
) -> ConfidenceResult:
    """Score an AssumptionDelta from the factor engine."""
    return score(
        source_name=delta.source_event,
        event_date=event_date,
        corroborating_sources=corroborating_sources,
        signal_magnitude=delta.magnitude,
    )
