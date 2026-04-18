#!/usr/bin/env python3
"""
Append a diagnostic cell to the notebook that dumps HIST, FORE, drivers,
and raw yfinance values to a .debug.json sidecar. Idempotent on the tag
"dcf-forecast-debug".
"""
from pathlib import Path
import nbformat

REPO = Path(__file__).resolve().parent.parent
NB = REPO / "notebooks" / "DCF_Multi_Source_Pipeline_REFACTORED.ipynb"
CELL_TAG = "dcf-forecast-debug"

CELL_SOURCE = '''\
# ── DEBUG: dump HIST, FORE, drivers, raw yfinance to {xlsm_stem}.debug.json
import json as _dj
from pathlib import Path as _DP

def _djv(v):
    try:
        if v is None: return None
        if hasattr(v, "item"): v = v.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
        if isinstance(v, (int, float, str, bool)): return v
        return str(v)
    except Exception:
        return None

def _dump_df(df):
    try:
        if df is None or (hasattr(df, "empty") and df.empty): return []
        return [
            {k: _djv(v) for k, v in r.items()}
            for _, r in df.sort_values(df.columns[0] if "FY" not in df.columns else "FY").iterrows()
        ]
    except Exception as e:
        return [{"_error": str(e)}]

_out_xlsm = _DP(globals().get("OUTPUT_XLSM") or str(OUTPUT_XLSM_PATH))
_debug_path = _out_xlsm.with_name(_out_xlsm.stem + ".debug.json")

# Re-derive drivers for logging
_drv_out = None
try:
    if "infer_drivers" in globals() and "HIST" in globals():
        _drv_out = infer_drivers(HIST, window=5)
except Exception as _e:
    _drv_out = {"_error": str(_e)}

# Compute the per-ratio 5-year windows (the values being fed into median())
_ratio_windows = {}
try:
    _h = HIST.dropna(subset=["Revenue"]).sort_values("FY").tail(5).copy()
    _h["RevenueGrowth"] = _h["Revenue"].pct_change()
    for col, (num, den) in [
        ("EBIT/Revenue",   ("EBIT",   "Revenue")),
        ("Capex/Revenue",  ("Capex",  "Revenue")),
        ("NWC/Revenue",    ("NWC",    "Revenue")),
        ("DandA/Revenue",  ("DandA",  "Revenue")),
    ]:
        if num in _h.columns and den in _h.columns:
            _ratio_windows[col] = [
                {"fy": _djv(fy), "num": _djv(n), "den": _djv(d), "ratio": _djv(n/d if d else None)}
                for fy, n, d in zip(_h["FY"], _h[num], _h[den])
            ]
    _ratio_windows["RevenueGrowth"] = [
        {"fy": _djv(fy), "rev": _djv(r), "growth": _djv(g)}
        for fy, r, g in zip(_h["FY"], _h["Revenue"], _h["RevenueGrowth"])
    ]
except Exception as _e:
    _ratio_windows = {"_error": str(_e)}

# Raw yfinance snapshot for unit check
_yf_raw = {}
try:
    _tk = yf.Ticker(TICKER)
    _is = _tk.financials
    _cf = _tk.cashflow
    _bs = _tk.balance_sheet
    def _yf_rows(df, cols_wanted):
        out = {}
        if df is None or df.empty: return out
        for c in cols_wanted:
            if c in df.index:
                s = df.loc[c]
                out[c] = {str(k.year if hasattr(k, "year") else k): _djv(v) for k, v in s.items()}
        return out
    _yf_raw["income_statement"] = _yf_rows(_is, [
        "Total Revenue", "EBIT", "Operating Income", "Pretax Income",
        "Income Tax Expense", "Net Income"
    ])
    _yf_raw["cash_flow"] = _yf_rows(_cf, [
        "Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
        "Depreciation And Amortization"
    ])
    _yf_raw["balance_sheet"] = _yf_rows(_bs, [
        "Current Assets", "Current Liabilities",
        "Cash And Cash Equivalents", "Short Long Term Debt"
    ])
    _info = _tk.info or {}
    _yf_raw["info"] = {
        "currency": _djv(_info.get("currency")),
        "financialCurrency": _djv(_info.get("financialCurrency")),
        "currentPrice": _djv(_info.get("currentPrice")),
        "marketCap": _djv(_info.get("marketCap")),
        "sharesOutstanding": _djv(_info.get("sharesOutstanding")),
    }
except Exception as _e:
    _yf_raw = {"_error": str(_e)}

_debug = {
    "ticker": TICKER,
    "currency": LOCAL_CURRENCY,
    "run_timestamp": RUN_TS,
    "inputs": {
        "TAX_RATE": _djv(TAX_RATE),
        "RISK_FREE": _djv(RISK_FREE),
        "EQUITY_RISK_PREMIUM": _djv(EQUITY_RISK_PREMIUM),
        "BETA": _djv(BETA),
        "COST_OF_DEBT_PRETAX": _djv(COST_OF_DEBT_PRETAX),
        "BASE_YEAR": _djv(globals().get("BASE_YEAR")),
        "FORECAST_YEARS": _djv(globals().get("FORECAST_YEARS")),
        "TERMINAL_GROWTH": _djv(globals().get("TERMINAL_GROWTH")),
    },
    "drivers_inferred": _drv_out,
    "ratio_windows": _ratio_windows,
    "HIST": _dump_df(globals().get("HIST")),
    "FORE": _dump_df(globals().get("FORE")),
    "VAL": {k: _djv(v) for k, v in (globals().get("VAL") or {}).items()},
    "yfinance_raw": _yf_raw,
}
_debug_path.write_text(_dj.dumps(_debug, indent=2, default=str))
print(f"✅ Debug JSON: {_debug_path.name}")
'''


def main():
    nb = nbformat.read(str(NB), as_version=4)
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "code" and CELL_TAG in cell.get("metadata", {}).get("tags", []):
            print(f"Replacing existing cell {i}")
            cell.source = CELL_SOURCE
            nbformat.write(nb, str(NB))
            return
    new_cell = nbformat.v4.new_code_cell(source=CELL_SOURCE)
    new_cell.metadata["tags"] = [CELL_TAG]
    nb.cells.append(new_cell)
    nbformat.write(nb, str(NB))
    print(f"Appended debug cell. Total cells: {len(nb.cells)}")


if __name__ == "__main__":
    main()
