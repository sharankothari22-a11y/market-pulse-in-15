"""
ai_engine/dcf_contract/writer.py
──────────────────────────────────
research_platform side of the contract.
Reads from a ResearchSession and writes assumptions.json
that the DCF model will consume.

Three model versions:
  "base"        -> actuals from DB only, no overrides
  "analyst"     -> manual overrides from session
  "data_driven" -> signal-adjusted assumptions from assumption engine
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.dcf_contract.schema import (
    empty_assumptions,
    validate_assumptions,
    write_json,
)

_SECTOR_WACC = {
    "petroleum_energy": 10.5, "banking_nbfc": 12.0, "pharma": 11.0,
    "it_tech": 11.5, "fmcg_retail": 10.0, "auto": 11.0,
    "real_estate": 12.5, "other": 11.0,
}
_SECTOR_TGR = {
    "petroleum_energy": 2.0, "banking_nbfc": 4.0, "pharma": 3.5,
    "it_tech": 4.0, "fmcg_retail": 5.0, "auto": 3.0,
    "real_estate": 3.5, "other": 3.0,
}
_SECTOR_BETA = {
    "petroleum_energy": 1.20, "banking_nbfc": 1.10, "pharma": 0.90,
    "it_tech": 1.15, "fmcg_retail": 0.80, "auto": 1.10,
    "real_estate": 1.30, "other": 1.10,
}


def _get(d, key, default=None):
    v = d.get(key)
    if v is None:
        return default
    try:
        if isinstance(v, float) and (v != v):  # NaN
            return default
    except Exception:
        pass
    return v


def write_assumptions(session, model_version="base", output_path=None):
    """Build and write assumptions.json for a research session."""
    out_path = output_path or (session.session_dir / "assumptions.json")

    sector = "other"
    try:
        meta_file = session.session_dir / "session_meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            sector = (meta.get("sector_mapped") or meta.get("_sector") or meta.get("sector") or "other")
    except Exception as exc:
        logger.debug(f"[dcf_contract.writer] sector detection failed: {exc}")

    data = empty_assumptions(
        ticker=session.ticker,
        sector=sector,
        session_id=session.session_id,
        model_version=model_version,
    )

    try:
        raw = session.get_assumptions() or {}
        data["meta"]["data_confidence"] = raw.get("data_confidence") or raw.get("_data_confidence")

        wi = data["wacc_inputs"]
        wi["risk_free"]           = _get(raw, "risk_free_rate", 4.0)
        wi["equity_risk_premium"] = _get(raw, "equity_risk_premium", 5.0)
        wi["beta"]                = _get(raw, "beta", _SECTOR_BETA.get(sector, 1.10))
        wi["cost_of_debt_pretax"] = _get(raw, "cost_of_debt", 5.0)
        wi["tax_rate"]            = _get(raw, "tax_rate", 25.0)
        dr = _get(raw, "debt_equity_ratio", None)
        wi["target_debt_weight"]  = float(dr) * 100 if dr is not None else 20.0
        wi["wacc_direct"]         = _get(raw, "wacc_direct", _get(raw, "wacc", None))

        dp = data["dcf_parameters"]
        dp["forecast_years"]    = int(_get(raw, "forecast_years", 5))
        dp["terminal_growth"]   = _get(raw, "terminal_growth_rate", _SECTOR_TGR.get(sector, 3.0))
        dp["mid_year"]          = bool(_get(raw, "mid_year", True))
        dp["use_exit_multiple"] = bool(_get(raw, "use_exit_multiple", False))
        dp["exit_multiple"]     = _get(raw, "exit_multiple", 12.0)

        if model_version in ("analyst", "data_driven"):
            do = data["driver_overrides"]
            rev_g = _get(raw, "revenue_growth", _get(raw, "revenue_growth_y1", None))
            if rev_g is not None:
                rv = float(rev_g)
                do["revenue_growth"] = rv / 100.0 if rv > 1 else rv

            ebit_m = _get(raw, "ebit_margin", _get(raw, "ebitda_margin", None))
            if ebit_m is not None:
                em = float(ebit_m)
                do["ebit_margin"] = em / 100.0 if em > 1 else em

            capex = _get(raw, "capex_pct_revenue", None)
            if capex is not None:
                cp = float(capex)
                do["capex_pct"] = cp / 100.0 if cp > 1 else cp

            da = _get(raw, "da_pct", None)
            if da is not None:
                dav = float(da)
                do["da_pct"] = dav / 100.0 if dav > 1 else dav

        import numpy as np
        data["sensitivity"]["wacc_grid"] = list(
            _get(raw, "wacc_grid", [round(x, 4) for x in np.arange(0.07, 0.13, 0.01)])
        )
        data["sensitivity"]["growth_grid"] = list(
            _get(raw, "growth_grid", [0.01, 0.02, 0.025, 0.03, 0.035])
        )

    except Exception as exc:
        logger.warning(f"[dcf_contract.writer] assumption population partial: {exc}")

    errors = validate_assumptions(data)
    if errors:
        logger.warning(f"[dcf_contract.writer] validation warnings: {errors}")

    write_json(data, out_path)
    logger.info(f"[dcf_contract.writer] assumptions.json written: {out_path}  (model={model_version})")
    return out_path


def write_base_assumptions(session, output_path=None):
    return write_assumptions(session, model_version="base", output_path=output_path)

def write_analyst_assumptions(session, output_path=None):
    return write_assumptions(session, model_version="analyst", output_path=output_path)

def write_data_driven_assumptions(session, output_path=None):
    return write_assumptions(session, model_version="data_driven", output_path=output_path)
