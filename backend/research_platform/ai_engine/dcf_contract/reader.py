"""
ai_engine/dcf_contract/reader.py
─────────────────────────────────
research_platform side of the contract.
Reads dcf_output.json written by the DCF model.
Converts it into structures the platform can use for display,
PDF reports, AI chat, and API responses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.dcf_contract.schema import validate_output, read_json


def read_dcf_output(session_dir, ticker: str = "") -> Optional[dict[str, Any]]:
    """
    Read dcf_output.json from a session folder.
    Returns None if file doesn't exist or is invalid.
    """
    session_dir = Path(session_dir)

    # Try session-specific path first, then generic
    candidates = [
        session_dir / "dcf_output.json",
        session_dir / f"dcf_output_{ticker}.json" if ticker else None,
    ]

    data = None
    for p in candidates:
        if p and p.exists():
            data = read_json(p)
            if data:
                break

    if data is None:
        logger.debug(f"[dcf_contract.reader] dcf_output.json not found in {session_dir}")
        return None

    errors = validate_output(data)
    if errors:
        logger.warning(f"[dcf_contract.reader] output validation issues: {errors}")

    return data


def get_valuation_summary(dcf_output: dict[str, Any]) -> dict[str, Any]:
    """
    Extract clean valuation summary for API responses and UI display.
    All fields safe — never raises.
    """
    if not dcf_output:
        return {"status": "not_run"}

    meta = dcf_output.get("meta", {})
    val  = dcf_output.get("valuation", {})
    sc   = dcf_output.get("scenarios", {})

    def _safe(d, key, fmt=None):
        v = d.get(key)
        if v is None:
            return None
        try:
            fv = float(v)
            if fmt == "pct":
                return round(fv, 2)
            if fmt == "price":
                return round(fv, 2)
            return fv
        except (TypeError, ValueError):
            return v

    # Build per-scenario dicts
    scenarios_out = {}
    for label in ("base", "bull", "bear"):
        s = sc.get(label, {})
        ps = _safe(s, "per_share", "price")
        cp = _safe(val, "current_price", "price")
        upside = _safe(s, "upside_pct", "pct")
        if upside is None and ps and cp and cp > 0:
            upside = round((ps - cp) / cp * 100, 2)
        scenarios_out[label] = {
            "per_share":      ps,
            "upside_pct":     upside,
            "rating":         s.get("rating"),
            "key_assumption": s.get("key_assumption", f"{label.title()} case"),
        }

    return {
        "status":            meta.get("status", "ok"),
        "model_version":     meta.get("model_version"),
        "ticker":            meta.get("ticker"),
        "run_at":            meta.get("run_at"),
        "wacc_pct":          _safe(meta, "wacc_pct"),
        "terminal_growth":   _safe(meta, "terminal_growth_pct"),
        "tv_method":         meta.get("tv_method"),
        "currency":          meta.get("currency", "USD"),
        "units":             meta.get("units", "Millions"),
        "enterprise_value":  _safe(val, "enterprise_value"),
        "equity_value":      _safe(val, "equity_value"),
        "per_share":         _safe(val, "per_share", "price"),
        "current_price":     _safe(val, "current_price", "price"),
        "upside_pct":        _safe(val, "upside_pct", "pct"),
        "scenarios":         scenarios_out,
        "sensitivity_table": dcf_output.get("sensitivity_table", {}),
        "forecast":          dcf_output.get("forecast", []),
        "checks":            dcf_output.get("checks", {}),
    }


def get_scenarios_for_platform(dcf_output: dict[str, Any]) -> dict[str, Any]:
    """
    Convert dcf_output into the format research_platform scenario_engine expects.
    Allows seamless display in web app, PDF, and AI chat.
    """
    summary = get_valuation_summary(dcf_output)
    if summary.get("status") == "not_run":
        return {}

    return {
        "ticker":        summary["ticker"],
        "current_price": summary["current_price"],
        "scenarios": {
            label: {
                "price_per_share": summary["scenarios"][label]["per_share"],
                "upside_pct":      summary["scenarios"][label]["upside_pct"],
                "rating":          summary["scenarios"][label]["rating"] or "Hold",
                "key_assumption":  summary["scenarios"][label]["key_assumption"],
                "enterprise_value": None,
                "equity_value":    None,
                "revenue_growth":  None,
                "ebitda_margin":   None,
                "wacc":            summary["wacc_pct"],
                "terminal_growth": summary["terminal_growth"],
            }
            for label in ("base", "bull", "bear")
        },
        "sensitivity_table": summary["sensitivity_table"],
        "model_version": summary["model_version"],
        "run_at":        summary["run_at"],
        "source":        "dcf_contract",  # marks this came from external DCF
    }
