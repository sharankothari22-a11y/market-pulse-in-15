#!/usr/bin/env python3
"""Run 5-ticker validation and emit a markdown table."""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _run_notebook_once import patch_and_run, NB_DIR

TICKERS = ["RELIANCE.NS", "TCS.NS", "HINDUNILVR.NS", "TATASTEEL.NS", "HDFCBANK.NS"]
REPO = Path(__file__).resolve().parent.parent


def load_summary(xlsm_path: Path):
    sp = xlsm_path.with_name(xlsm_path.stem + ".summary.json")
    if not sp.exists():
        return None
    return json.loads(sp.read_text())


def main():
    rows = []
    for tk in TICKERS:
        try:
            res = patch_and_run(tk)
            summary = load_summary(Path(res["output"]))
            if summary is None:
                rows.append((tk, None, None, None, None, ["missing summary json"], res["elapsed"]))
                continue
            v = summary.get("valuation", {})
            rows.append((
                tk,
                v.get("current_price"),
                v.get("fair_value_per_share"),
                v.get("upside_pct"),
                v.get("wacc"),
                summary.get("model_warnings", []),
                res["elapsed"],
            ))
        except Exception as e:
            rows.append((tk, None, None, None, None, [f"RUN ERROR: {e}"], None))

    def fmt(x, nd=2):
        if x is None:
            return "—"
        try:
            return f"{float(x):,.{nd}f}"
        except Exception:
            return str(x)

    def verdict(cur, fv, up, warns):
        if warns:
            return "OUT_OF_MODEL_SCOPE"
        if fv is None or cur is None:
            return "FAILED"
        try:
            if float(fv) < 0:
                return "REGRESSED"
            if abs(float(up)) > 75:
                return "OUT_OF_MODEL_SCOPE"
        except Exception:
            return "FAILED"
        return "PLAUSIBLE"

    lines = []
    lines.append(f"# DCF Forecast Fix — Validation Results\n")
    lines.append(f"Run: {datetime.now().isoformat(timespec='seconds')}\n")
    lines.append(f"Fix: capex taper + ΔRevenue-based NWC + recency-weighted drivers + model_warnings\n\n")
    lines.append("| Ticker | Current | Fair Value | Upside % | WACC | Verdict | Warnings |")
    lines.append("|--------|--------:|-----------:|---------:|-----:|---------|----------|")
    for tk, cur, fv, up, wacc, warns, _el in rows:
        v = verdict(cur, fv, up, warns)
        w = "; ".join(warns) if warns else "—"
        lines.append(f"| {tk} | {fmt(cur)} | {fmt(fv)} | {fmt(up)} | {fmt(wacc, 4)} | {v} | {w} |")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPO / "scripts" / f"validation_results_{ts}.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
