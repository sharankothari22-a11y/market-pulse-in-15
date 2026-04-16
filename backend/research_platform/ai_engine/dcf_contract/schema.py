"""
ai_engine/dcf_contract/schema.py
─────────────────────────────────
The permanent contract between research_platform and the DCF model.

This file defines the EXACT structure of both JSON files.
Neither side should change these field names without bumping SCHEMA_VERSION.

assumptions.json  ← research_platform writes, DCF reads
dcf_output.json   ← DCF writes, research_platform reads

Rule: both systems must tolerate unknown fields gracefully.
New fields can be ADDED at any time without breaking anything.
Existing fields must NEVER be renamed or removed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = "1.0"


# ─────────────────────────────────────────────────────────────────────────────
# ASSUMPTIONS SCHEMA  (research_platform → DCF)
# ─────────────────────────────────────────────────────────────────────────────

def empty_assumptions(
    ticker: str = "",
    sector: str = "other",
    session_id: str = "",
    model_version: str = "base",
) -> dict[str, Any]:
    """
    Returns a fully-structured assumptions dict with all fields set to None.
    research_platform fills these in before writing to disk.
    DCF reads this and falls back to its own defaults for any null field.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "ticker":        ticker,
            "sector":        sector,
            "session_id":    session_id,
            "model_version": model_version,   # "base" | "analyst" | "data_driven"
            "generated_at":  _now(),
            "data_confidence": None,
        },
        # Maps directly to DCF Master Config globals
        "wacc_inputs": {
            "risk_free":             None,   # RISK_FREE (%)
            "equity_risk_premium":   None,   # EQUITY_RISK_PREMIUM (%)
            "beta":                  None,   # BETA
            "cost_of_debt_pretax":   None,   # COST_OF_DEBT_PRETAX (%)
            "tax_rate":              None,   # TAX_RATE (%)
            "target_debt_weight":    None,   # TARGET_DEBT_WEIGHT (%)
            "wacc_direct":           None,   # WACC_DIRECT — set to skip CAPM
        },
        # Maps directly to DCF Master Config globals
        "dcf_parameters": {
            "forecast_years":    None,   # FORECAST_YEARS
            "terminal_growth":   None,   # TERMINAL_GROWTH (%)
            "exit_multiple":     None,   # EXIT_MULTIPLE
            "use_exit_multiple": None,   # USE_EXIT_MULTIPLE
            "mid_year":          None,   # MID_YEAR
            "base_year":         None,   # BASE_YEAR
        },
        # Maps to project_fcff() overrides — null = DCF uses infer_drivers()
        "driver_overrides": {
            "revenue_growth": None,   # fraction e.g. 0.12 = 12%
            "ebit_margin":    None,   # fraction e.g. 0.18 = 18%
            "capex_pct":      None,   # fraction e.g. 0.08 = 8%
            "da_pct":         None,   # fraction e.g. 0.03 = 3%
            "nwc_pct":        None,   # fraction e.g. 0.02 = 2%
        },
        # Per-year overrides — list of 5 dicts (one per forecast year)
        "year_overrides": [],
        # Sensitivity grid config
        "sensitivity": {
            "wacc_grid":       None,   # list of floats e.g. [0.07,0.08,0.09,0.10,0.11]
            "growth_grid":     None,   # list of floats e.g. [0.01,0.02,0.025,0.03]
            "exit_mult_grid":  None,
            "margin_adj":      None,
        },
    }


def validate_assumptions(data: dict[str, Any]) -> list[str]:
    """
    Returns list of validation errors. Empty list = valid.
    Lenient — only fails on clearly broken data.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["assumptions.json is not a dict"]

    meta = data.get("meta", {})
    if not meta.get("ticker"):
        errors.append("meta.ticker is missing")
    if meta.get("model_version") not in ("base", "analyst", "data_driven", None):
        errors.append(f"meta.model_version invalid: {meta.get('model_version')}")

    wi = data.get("wacc_inputs", {})
    for field in ("risk_free", "equity_risk_premium", "beta"):
        v = wi.get(field)
        if v is not None:
            try:
                fv = float(v)
                if fv < 0:
                    errors.append(f"wacc_inputs.{field} cannot be negative: {fv}")
            except (TypeError, ValueError):
                errors.append(f"wacc_inputs.{field} not numeric: {v}")

    dp = data.get("dcf_parameters", {})
    tg = dp.get("terminal_growth")
    if tg is not None:
        try:
            if float(tg) >= 15:
                errors.append(f"dcf_parameters.terminal_growth looks wrong: {tg} (should be %, e.g. 2.0)")
        except (TypeError, ValueError):
            pass

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# DCF OUTPUT SCHEMA  (DCF → research_platform)
# ─────────────────────────────────────────────────────────────────────────────

def empty_output(ticker: str = "", model_version: str = "base") -> dict[str, Any]:
    """
    Returns skeleton of dcf_output.json with all fields None.
    DCF fills this in after running.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "ticker":              ticker,
            "model_version":       model_version,
            "run_at":              _now(),
            "tv_method":           None,   # "Gordon Growth" | "Exit Multiple"
            "wacc_pct":            None,
            "terminal_growth_pct": None,
            "currency":            None,
            "units":               None,
            "forecast_years":      None,
            "status":              "pending",  # "ok" | "error" | "pending"
            "error_message":       None,
        },
        "valuation": {
            "enterprise_value":   None,
            "net_debt":           None,
            "equity_value":       None,
            "shares_outstanding": None,
            "per_share":          None,
            "pv_fcffs":           None,
            "pv_terminal_value":  None,
            "current_price":      None,
            "upside_pct":         None,
        },
        "scenarios": {
            "base": {"per_share": None, "upside_pct": None, "rating": None, "key_assumption": "Base case"},
            "bull": {"per_share": None, "upside_pct": None, "rating": None, "key_assumption": "Bull case"},
            "bear": {"per_share": None, "upside_pct": None, "rating": None, "key_assumption": "Bear case"},
        },
        "sensitivity_table": {
            "wacc_vs_growth": {
                "rows": [],   # WACC labels
                "cols": [],   # growth labels
                "matrix": [], # list of lists
            },
        },
        "forecast": [],   # list of {year, revenue, ebit, fcff, revenue_growth, ebit_margin}
        "checks": {
            "wacc_gt_zero":   None,
            "g_lt_wacc":      None,
            "fcff_present":   None,
        },
    }


def validate_output(data: dict[str, Any]) -> list[str]:
    """Returns list of validation errors."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["dcf_output.json is not a dict"]

    meta = data.get("meta", {})
    if meta.get("status") == "error":
        errors.append(f"DCF reported error: {meta.get('error_message', 'unknown')}")

    val = data.get("valuation", {})
    per_share = val.get("per_share")
    if per_share is not None:
        try:
            if float(per_share) <= 0:
                errors.append(f"valuation.per_share is non-positive: {per_share}")
        except (TypeError, ValueError):
            errors.append(f"valuation.per_share not numeric: {per_share}")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# FILE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return None


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
