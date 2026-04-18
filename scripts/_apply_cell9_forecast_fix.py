#!/usr/bin/env python3
"""
Replace Cell 9 of DCF_Multi_Source_Pipeline_REFACTORED.ipynb with the new
forecast engine:

  Fix A  — recency-weighted driver inference (weights [0.40 0.25 0.18 0.12 0.05]
           most-recent first; NaN-safe; renormalised when fewer history years).
  Fix B  — CapexPct tapers linearly from the historical driver value in year 1
           down to max(driver_DApct, 0.05) in the terminal year.
  Fix C  — NWC modelled as ΔRevenue-proportional (ΔNWC = ΔRev × NWCpct),
           eliminating the year-1 mean-reversion shock.

Legacy behaviour is preserved as _legacy_infer_drivers / _legacy_project_fcff
for post-rollout comparison, callable but unused by default.

Idempotent: if the cell already contains the marker 'recency-weighted', the
script does nothing.
"""
from pathlib import Path
import nbformat

REPO = Path(__file__).resolve().parent.parent
NB = REPO / "notebooks" / "DCF_Multi_Source_Pipeline_REFACTORED.ipynb"
MARKER = "recency-weighted"

NEW_CELL_SOURCE = '''\
# ── 4A: Infer drivers & forecast ─────────────────────────────────────────────

def _safe_default(x, fallback):
    try: return fallback if (x is None or (isinstance(x, float) and np.isnan(x))) else x
    except: return fallback


# ════════════════════════════════════════════════════════════════════════════
# Legacy driver logic — kept for comparison during the fix rollout.
# Not called by default. Safe to remove after validation.
# ════════════════════════════════════════════════════════════════════════════
def _legacy_infer_drivers(hist, window=5):
    h = hist.dropna(subset=["Revenue"]).sort_values("FY").tail(window)
    h = h.copy()
    h["RevenueGrowth"] = h["Revenue"].pct_change()
    def _ratio(num, den): return (h[num]/h[den]).replace([np.inf,-np.inf],np.nan)
    return {
        "RevenueGrowth_default": float(_safe_default(h["RevenueGrowth"].median(skipna=True), 0.02)),
        "EBITMargin_default":    float(_safe_default(_ratio("EBIT","Revenue").median(skipna=True), 0.15)),
        "CapexPct_default":      float(abs(_safe_default(_ratio("Capex","Revenue").median(skipna=True), 0.03))),
        "NWCpct_default":        float(_safe_default(_ratio("NWC","Revenue").median(skipna=True), 0.00)),
        "DApct_default":         float(_safe_default(_ratio("DandA","Revenue").median(skipna=True), 0.03)),
    }

def _legacy_project_fcff(hist, base_year, years, drivers, overrides=None):
    last_row = hist.loc[hist["FY"].idxmax()].copy()
    revenue   = float(last_row["Revenue"])
    nwc       = float(last_row["NWC"]) if pd.notna(last_row.get("NWC")) else 0.0
    tr        = TAX_RATE / 100.0
    g_def     = max(-0.5, min(0.5, drivers["RevenueGrowth_default"]))
    m_def     = max(-0.5, min(0.5, drivers["EBITMargin_default"]))
    capex_def = max(0.0,  min(0.5, drivers["CapexPct_default"]))
    nwc_def   = max(-0.5, min(0.5, drivers["NWCpct_default"]))
    da_def    = max(0.0,  min(0.5, drivers["DApct_default"]))
    rows = []
    OVR_df = overrides
    for t in range(1, years + 1):
        g = g_def; m = m_def; capex_pct = capex_def; nwc_pct = nwc_def; da_pct = da_def
        if OVR_df is not None and t in OVR_df["YearIdx"].values:
            ov = OVR_df[OVR_df["YearIdx"] == t].iloc[0]
            if pd.notna(ov["RevenueGrowth_override"]): g         = float(ov["RevenueGrowth_override"])
            if pd.notna(ov["EBITMargin_override"]):    m         = float(ov["EBITMargin_override"])
            if pd.notna(ov["CapexPct_override"]):      capex_pct = float(ov["CapexPct_override"])
            if pd.notna(ov["NWCpct_override"]):        nwc_pct   = float(ov["NWCpct_override"])
            if pd.notna(ov["DApct_override"]):         da_pct    = float(ov["DApct_override"])
        revenue      = revenue * (1 + g)
        ebit         = revenue * m
        nopat        = ebit * (1 - tr)
        danda        = revenue * da_pct
        capex        = revenue * capex_pct
        target_nwc   = revenue * nwc_pct
        delta_nwc    = target_nwc - nwc
        nwc          = target_nwc
        fcff         = nopat + danda - capex - delta_nwc
        rows.append({
            "FY": base_year + t, "Revenue": revenue, "EBIT": ebit, "NOPAT": nopat,
            "DandA": danda, "Capex": capex, "DeltaNWC": delta_nwc, "FCFF": fcff,
            "EBITMargin": m, "DApct": da_pct, "CapexPct": capex_pct,
            "NWCpct": nwc_pct, "RevenueGrowth": g,
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════════════
# Current driver logic — recency-weighted drivers (A) + capex taper (B)
# + ΔRevenue-based NWC (C).
# ════════════════════════════════════════════════════════════════════════════
_DRIVER_WEIGHTS = (0.40, 0.25, 0.18, 0.12, 0.05)  # most-recent first


def _decay_weighted(series, weights=_DRIVER_WEIGHTS):
    """Decay-weighted average over an ascending-FY pandas Series.
    Drops NaN; renormalises remaining weights. Returns None if empty."""
    try:
        s = series.dropna()
        if s.empty: return None
        vals_newest_first = s.tolist()[::-1]
        w = list(weights)[:len(vals_newest_first)]
        tot = sum(w)
        if tot <= 0: return None
        return sum(v * wi for v, wi in zip(vals_newest_first, w)) / tot
    except Exception:
        return None


def infer_drivers(hist, window=5):
    """Recency-weighted drivers. Window of 5 most-recent historical years."""
    h = hist.dropna(subset=["Revenue"]).sort_values("FY").tail(window).copy()
    h["RevenueGrowth"] = h["Revenue"].pct_change()
    def _ratio(num, den):
        if num not in h.columns or den not in h.columns:
            return pd.Series(dtype=float)
        return (h[num] / h[den]).replace([np.inf, -np.inf], np.nan)
    return {
        "RevenueGrowth_default": float(_safe_default(_decay_weighted(h["RevenueGrowth"]), 0.02)),
        "EBITMargin_default":    float(_safe_default(_decay_weighted(_ratio("EBIT",   "Revenue")), 0.15)),
        "CapexPct_default":      float(abs(_safe_default(_decay_weighted(_ratio("Capex",  "Revenue")), 0.03))),
        "NWCpct_default":        float(_safe_default(_decay_weighted(_ratio("NWC",    "Revenue")), 0.00)),
        "DApct_default":         float(_safe_default(_decay_weighted(_ratio("DandA",  "Revenue")), 0.03)),
    }


def project_fcff(hist, base_year, years, drivers, overrides=None):
    """Forecast FCFF. Capex tapers to maintenance level over horizon;
    ΔNWC scales with ΔRevenue, not level."""
    last_row     = hist.loc[hist["FY"].idxmax()].copy()
    prev_revenue = float(last_row["Revenue"])
    tr           = TAX_RATE / 100.0
    g_def     = max(-0.5, min(0.5, drivers["RevenueGrowth_default"]))
    m_def     = max(-0.5, min(0.5, drivers["EBITMargin_default"]))
    capex_def = max(0.0,  min(0.5, drivers["CapexPct_default"]))
    nwc_def   = max(-0.5, min(0.5, drivers["NWCpct_default"]))
    da_def    = max(0.0,  min(0.5, drivers["DApct_default"]))

    # Fix B: capex taper endpoints. Terminal = max(D&A%, 5%) — maintenance capex.
    capex_terminal = max(da_def, 0.05)

    rows   = []
    OVR_df = overrides
    for t in range(1, years + 1):
        g = g_def; m = m_def; nwc_pct = nwc_def; da_pct = da_def

        # Fix B: linear interpolation of capex_pct from capex_def (t=1) to
        # capex_terminal (t=years). Single-year horizon keeps start value.
        frac = (t - 1) / (years - 1) if years > 1 else 0.0
        capex_pct = capex_def + (capex_terminal - capex_def) * frac

        # Per-year overrides (preserved from legacy behaviour).
        if OVR_df is not None and t in OVR_df["YearIdx"].values:
            ov = OVR_df[OVR_df["YearIdx"] == t].iloc[0]
            if pd.notna(ov["RevenueGrowth_override"]): g         = float(ov["RevenueGrowth_override"])
            if pd.notna(ov["EBITMargin_override"]):    m         = float(ov["EBITMargin_override"])
            if pd.notna(ov["CapexPct_override"]):      capex_pct = float(ov["CapexPct_override"])
            if pd.notna(ov["NWCpct_override"]):        nwc_pct   = float(ov["NWCpct_override"])
            if pd.notna(ov["DApct_override"]):         da_pct    = float(ov["DApct_override"])

        revenue   = prev_revenue * (1 + g)
        ebit      = revenue * m
        nopat     = ebit * (1 - tr)
        danda     = revenue * da_pct
        capex     = revenue * capex_pct
        # Fix C: ΔNWC scales with ΔRevenue, not level.
        delta_nwc = (revenue - prev_revenue) * nwc_pct
        fcff      = nopat + danda - capex - delta_nwc

        rows.append({
            "FY": base_year + t, "Revenue": revenue, "EBIT": ebit, "NOPAT": nopat,
            "DandA": danda, "Capex": capex, "DeltaNWC": delta_nwc, "FCFF": fcff,
            "EBITMargin": m, "DApct": da_pct, "CapexPct": capex_pct,
            "NWCpct": nwc_pct, "RevenueGrowth": g,
        })
        prev_revenue = revenue
    return pd.DataFrame(rows)


drivers = infer_drivers(HIST, window=5)

# Year-by-year override table (set values to override defaults)
OVR = pd.DataFrame({
    "YearIdx":                list(range(1, FORECAST_YEARS + 1)),
    "RevenueGrowth_override": np.nan,
    "EBITMargin_override":    np.nan,
    "CapexPct_override":      np.nan,
    "NWCpct_override":        np.nan,
    "DApct_override":         np.nan,
})

FORE = project_fcff(HIST, BASE_YEAR, FORECAST_YEARS, drivers, OVR)
print("✅ Forecast (FORE) built:")
FORE
'''


def main():
    nb = nbformat.read(str(NB), as_version=4)
    target_idx = None
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        src = cell.source
        if "def infer_drivers(" in src and "def project_fcff(" in src:
            target_idx = i
            break
    if target_idx is None:
        raise RuntimeError(
            "Could not locate forecast cell (looking for infer_drivers + project_fcff)"
        )
    if MARKER in nb.cells[target_idx].source:
        print(f"Cell {target_idx} already patched (marker '{MARKER}' found)")
        return
    nb.cells[target_idx].source = NEW_CELL_SOURCE
    nbformat.write(nb, str(NB))
    print(f"Patched Cell {target_idx} with new forecast engine")


if __name__ == "__main__":
    main()
