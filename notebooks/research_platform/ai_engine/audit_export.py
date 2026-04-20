"""
ai_engine/audit_export.py   [UPDATED — File 5]
───────────────────────────
Layer 15 — Audit Trail + Report Export.

Every change logged. Full source traceability.
Export: Excel (.xlsx), PDF (via HTML), session folder zip, summary.md.

CHANGE in this version:
  export_to_html() now delegates to ai_engine.pdf_builder.build_report()
  which produces the full 2-page A4 report with scoring, SWOT, Porter,
  financial table, scenarios, and sensitivity table.

  Signature extended with optional `sector` parameter.
  All other functions are unchanged.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.session_manager import ResearchSession


# ── Audit trail ───────────────────────────────────────────────────────────────

def get_full_audit(session: ResearchSession) -> list[dict[str, Any]]:
    """Return complete audit log for this session."""
    if not session.audit_log_file.exists():
        return []
    return json.loads(session.audit_log_file.read_text())


def get_assumption_audit(session: ResearchSession) -> list[dict[str, Any]]:
    """Return assumption changes only, in chronological order."""
    if not session.assumptions_history_file.exists():
        return []
    history = json.loads(session.assumptions_history_file.read_text())
    return [h for h in history if "metric" in h]


def get_guardrail_audit(session: ResearchSession) -> list[dict[str, Any]]:
    """Return all guardrail breaches for this session."""
    if not session.guardrail_log_file.exists():
        return []
    return json.loads(session.guardrail_log_file.read_text())


# ── Excel export ──────────────────────────────────────────────────────────────

def export_to_excel(
    session: ResearchSession,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Export full session to Excel workbook with 6 sheets:
      1. Assumptions (current)
      2. Assumption History
      3. Scenarios (Bull/Base/Bear)
      4. Sensitivity Table
      5. Signals & Insights
      6. Data Sources + Audit Log
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas required for Excel export — pip install pandas openpyxl")

    out = output_path or (
        session.session_dir / f"{session.ticker}_research_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

    with pd.ExcelWriter(out, engine="openpyxl") as writer:

        # ── Sheet 1: Current Assumptions ────────────────────────────────────
        assumptions = session.get_assumptions()
        df_assum = pd.DataFrame([
            {"metric": k, "value": v}
            for k, v in assumptions.items()
            if not k.startswith("_")
        ])
        df_assum.to_excel(writer, sheet_name="Assumptions", index=False)

        # ── Sheet 2: Assumption History ──────────────────────────────────────
        hist = get_assumption_audit(session)
        if hist:
            df_hist = pd.DataFrame(hist)
            df_hist.to_excel(writer, sheet_name="Assumption History", index=False)
        else:
            pd.DataFrame(columns=["metric","old_value","new_value","reason","source","timestamp"]).to_excel(
                writer, sheet_name="Assumption History", index=False
            )

        # ── Sheet 3: Scenarios ───────────────────────────────────────────────
        scenarios = session.get_scenarios()
        scenario_rows = []
        for label in ("bull", "base", "bear"):
            sc = scenarios.get("scenarios", {}).get(label)
            if sc:
                scenario_rows.append(sc)
        if scenario_rows:
            pd.DataFrame(scenario_rows).to_excel(writer, sheet_name="Scenarios", index=False)
        else:
            pd.DataFrame().to_excel(writer, sheet_name="Scenarios", index=False)

        # ── Sheet 4: Sensitivity Table ───────────────────────────────────────
        sens = scenarios.get("sensitivity", {})
        if sens and sens.get("grid"):
            wacc_range = sens.get("wacc_range", [])
            tg_range   = sens.get("terminal_growth_range", [])
            grid       = sens.get("grid", [])
            df_sens    = pd.DataFrame(grid, index=wacc_range, columns=tg_range)
            df_sens.index.name   = "WACC \ TG Rate"
            df_sens.to_excel(writer, sheet_name="Sensitivity")
        else:
            pd.DataFrame().to_excel(writer, sheet_name="Sensitivity", index=False)

        # ── Sheet 5: Signals & Insights ──────────────────────────────────────
        insights_path = session.insights_file
        insights = json.loads(insights_path.read_text()) if insights_path.exists() else []
        if insights:
            pd.DataFrame(insights).to_excel(writer, sheet_name="Signals & Insights", index=False)
        else:
            pd.DataFrame().to_excel(writer, sheet_name="Signals & Insights", index=False)

        # ── Sheet 6: Sources + Audit ─────────────────────────────────────────
        sources = json.loads(session.sources_file.read_text()) if session.sources_file.exists() else []
        audit   = get_full_audit(session)
        df_src  = pd.DataFrame(sources) if sources else pd.DataFrame()
        df_src.to_excel(writer, sheet_name="Sources & Audit", index=False)

    logger.info(f"[audit_export] Excel exported: {out}")
    return out


# ── HTML / PDF export  ────────────────────────────────────────────────────────
# UPDATED: delegates to pdf_builder.build_report() for the full 2-page report.

def export_to_html(
    session:     ResearchSession,
    sector:      str = "other",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Export session as a 2-page print-ready HTML report.

    Delegates entirely to ai_engine.pdf_builder.build_report() which
    produces the full structured report with:
      Page 1: Scoring bars, financial table, SWOT, risk signals
      Page 2: Investment thesis, DCF scenarios, sensitivity table,
              reverse DCF, signal summary, Porter's Five Forces

    Open the returned file in Chrome:
      File → Print → Save as PDF
      Settings: Background graphics = ON, Margins = None

    Args:
        session:     ResearchSession instance
        sector:      sector string (e.g. "petroleum_energy", "it_tech")
                     Auto-detected from session_meta.json if not provided.
        output_path: optional override for output file path

    Returns:
        Path to the written HTML file
    """
    # ── Auto-detect sector from session_meta if caller passed "other" ────────
    if sector == "other":
        try:
            meta_file = session.session_dir / "session_meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                detected = meta.get("sector_mapped") or meta.get("_sector") or "other"
                if detected and detected != "other":
                    sector = detected
                    logger.debug(f"[audit_export] sector auto-detected: {sector}")
        except Exception as exc:
            logger.debug(f"[audit_export] sector auto-detect failed: {exc}")

    from ai_engine.pdf_builder import build_report
    return build_report(session, sector=sector, output_path=output_path)


# ── Session zip export ────────────────────────────────────────────────────────

def export_session_zip(
    session: ResearchSession,
    output_path: Optional[Path] = None,
) -> Path:
    """Zip the entire session folder for archiving or sharing."""
    out = output_path or (
        session.session_dir.parent / f"{session.session_id}.zip"
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in session.session_dir.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(session.session_dir))
    logger.info(f"[audit_export] Session zipped: {out}")
    return out