#!/usr/bin/env python3
"""
Append the DCF summary-JSON cell to the notebook. Idempotent: if a cell
tagged "dcf-summary-sidecar" already exists, replace its source.
"""
from pathlib import Path
import nbformat

REPO = Path(__file__).resolve().parent.parent
NB = REPO / "notebooks" / "DCF_Multi_Source_Pipeline_REFACTORED.ipynb"

CELL_TAG = "dcf-summary-sidecar"

CELL_SOURCE = '''\
# ── 9E: DCF SUMMARY JSON — sidecar for backend consumption ─────────────────
# Writes {xlsm_stem}.summary.json next to the output workbook. Backend reads
# this instead of the .xlsm so it can surface computed values without needing
# Excel to recalc formulas (openpyxl does not execute formulas).
import json as _json
from pathlib import Path as _Path

def _j(v):
    try:
        if v is None: return None
        if hasattr(v, "item"): v = v.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
        if isinstance(v, (int, float, str, bool)): return v
        return str(v)
    except Exception:
        return None

_out_xlsm = _Path(globals().get("OUTPUT_XLSM") or str(OUTPUT_XLSM_PATH))
_summary_path = _out_xlsm.with_name(_out_xlsm.stem + ".summary.json")

# Current market price (best-effort)
_current_price = None
try:
    _info = yf.Ticker(TICKER).info or {}
    _current_price = _info.get("currentPrice") or _info.get("regularMarketPrice")
except Exception:
    pass

def _series(df, col, year_col="FY"):
    out = []
    try:
        if df is None or df.empty or col not in df.columns: return out
        for _, r in df.sort_values(year_col).iterrows():
            if pd.notna(r.get(col)):
                out.append({"fy": _j(r.get(year_col)), col.lower(): _j(r[col])})
    except Exception:
        pass
    return out

_VAL = globals().get("VAL") or {}
_HIST = globals().get("HIST")
_FORE = globals().get("FORE")

_fv = _j(_VAL.get("PerShare"))
_cp = _j(_current_price)
_upside = None
try:
    if _fv is not None and _cp is not None and float(_cp) != 0.0:
        _upside = round((float(_fv) - float(_cp)) / float(_cp) * 100.0, 2)
except Exception:
    _upside = None

# Model warnings — surface obviously-wrong outputs rather than ship silently
_warnings = []
try:
    if _fv is not None and float(_fv) < 0:
        _warnings.append("Fair value is negative — model likely outside its reliable range for this ticker.")
    if _upside is not None and abs(float(_upside)) > 100:
        _warnings.append("Implied upside/downside exceeds 100% — treat with skepticism.")
    _fore_fcf_series = _series(_FORE, "FCFF")
    _hist_fcf_series = _series(_HIST, "FCFF")
    _any_neg_fore = any((r.get("fcff") is not None and float(r["fcff"]) < 0) for r in _fore_fcf_series)
    _last2_hist = [r for r in _hist_fcf_series if r.get("fcff") is not None][-2:]
    _last2_pos = (len(_last2_hist) == 2 and all(float(r["fcff"]) > 0 for r in _last2_hist))
    if _any_neg_fore and _last2_pos:
        _warnings.append("Forecast projects negative FCF despite recent positive history — check capex/NWC assumptions.")
    _wacc = _VAL.get("WACC")
    _tg = globals().get("TERMINAL_GROWTH")
    if _wacc is not None and _tg is not None and float(_tg) >= float(_wacc) * 100.0:
        _warnings.append("Terminal growth exceeds WACC — Gordon model invalid.")
except Exception as _e:
    _warnings.append(f"warning-check error: {_e}")

_summary = {
    "schema_version": 1,
    "model_warnings": _warnings,
    "ticker": TICKER,
    "currency": LOCAL_CURRENCY,
    "region": REGION,
    "run_timestamp": RUN_TS,
    "output_xlsm": _out_xlsm.name,
    "valuation": {
        "fair_value_per_share": _fv,
        "current_price":        _cp,
        "upside_pct":           _upside,
        "wacc":                 _j(_VAL.get("WACC")),
        "terminal_growth":      _j(globals().get("TERMINAL_GROWTH")),
        "tv_method":            _j(_VAL.get("TV_Method")),
        "pv_terminal_value":    _j(_VAL.get("PV_TV")),
        "pv_fcffs":             _j(_VAL.get("PV_FCFFs")),
        "enterprise_value":     _j(_VAL.get("EV")),
        "equity_value":         _j(_VAL.get("EquityValue")),
        "net_debt":             _j(_VAL.get("NetDebt")),
        "shares":               _j(_VAL.get("Shares")),
    },
    "assumptions": {
        "risk_free_pct":            _j(globals().get("RISK_FREE")),
        "erp_pct":                  _j(globals().get("EQUITY_RISK_PREMIUM")),
        "beta":                     _j(globals().get("BETA")),
        "cost_of_debt_pretax_pct":  _j(globals().get("COST_OF_DEBT_PRETAX")),
        "tax_rate_pct":             _j(globals().get("TAX_RATE")),
        "wacc_direct":              _j(globals().get("WACC_DIRECT")),
        "mid_year":                 _j(globals().get("MID_YEAR")),
        "use_exit_multiple":        _j(globals().get("USE_EXIT_MULTIPLE")),
        "base_year":                _j(globals().get("BASE_YEAR")),
        "forecast_years":           _j(globals().get("FORECAST_YEARS")),
    },
    "historical_fcf":   _series(_HIST, "FCFF"),
    "forecast_fcf":     _series(_FORE, "FCFF"),
    "forecast_revenue": _series(_FORE, "Revenue"),
}

_summary_path.write_text(_json.dumps(_summary, indent=2, default=str))
print(f"✅ Summary JSON: {_summary_path.name}")
'''


def main():
    nb = nbformat.read(str(NB), as_version=4)

    # Check for existing tagged cell
    for i, cell in enumerate(nb.cells):
        tags = cell.get("metadata", {}).get("tags", [])
        if cell.cell_type == "code" and CELL_TAG in tags:
            print(f"Replacing existing cell {i} (tag={CELL_TAG})")
            cell.source = CELL_SOURCE
            nbformat.write(nb, str(NB))
            return

    # Append new cell
    new_cell = nbformat.v4.new_code_cell(source=CELL_SOURCE)
    new_cell.metadata["tags"] = [CELL_TAG]
    nb.cells.append(new_cell)
    nbformat.write(nb, str(NB))
    print(f"Appended new cell (tag={CELL_TAG}). Total cells: {len(nb.cells)}")


if __name__ == "__main__":
    main()
