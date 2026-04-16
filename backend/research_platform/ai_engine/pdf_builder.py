"""
ai_engine/pdf_builder.py
─────────────────────────
2-page A4 print-ready HTML report.

Usage:
    from ai_engine.pdf_builder import build_report
    path = build_report(session, sector="petroleum_energy")
    # Open in Chrome → Ctrl+P → Save as PDF

The HTML file is written to session_dir/{ticker}_report_PRINT.html

Never raises — returns an error-page HTML if something fails.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.scoring import score_session, ScoringResult
from ai_engine.swot   import generate_swot
from ai_engine.porter import generate_porter


# ─────────────────────────────────────────────────────────────────────────────
# Financial table builder
# ─────────────────────────────────────────────────────────────────────────────

def build_financial_table(session: Any) -> list[dict]:
    """
    Pull last 3 years of financials.
    Priority: database price_history → yfinance fallback → empty list.

    Returns list of dicts with keys:
      period, revenue, ebitda, net_income, free_cash_flow,
      gross_margin, ebitda_margin, net_margin,
      revenue_growth_yoy, net_debt_to_ebitda
    """
    rows: list[dict] = []

    # ── 1. Try database ───────────────────────────────────────────────────────
    try:
        from sqlalchemy import select, desc
        from database.connection import get_session as dbs
        from database.models import PriceHistory

        with dbs() as db:
            records = db.scalars(
                select(PriceHistory)
                .where(PriceHistory.ticker == session.ticker)
                .order_by(desc(PriceHistory.date))
                .limit(3)
            ).all()

            if records:
                for r in records:
                    rows.append({
                        "period":            str(getattr(r, "date", ""))[:4],
                        "revenue":           getattr(r, "revenue", None),
                        "ebitda":            getattr(r, "ebitda", None),
                        "net_income":        getattr(r, "net_income", None),
                        "free_cash_flow":    getattr(r, "free_cash_flow", None),
                        "gross_margin":      getattr(r, "gross_margin", None),
                        "ebitda_margin":     getattr(r, "ebitda_margin", None),
                        "net_margin":        getattr(r, "net_margin", None),
                        "revenue_growth_yoy":getattr(r, "revenue_growth_yoy", None),
                        "net_debt_to_ebitda":getattr(r, "net_debt_to_ebitda", None),
                    })
    except Exception as exc:
        logger.debug(f"[pdf_builder] DB financials unavailable: {exc}")

    # ── 2. yfinance fallback ──────────────────────────────────────────────────
    if not rows:
        try:
            import yfinance as yf
            ticker = session.ticker
            if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
                ticker_yf = ticker + ".NS"
            else:
                ticker_yf = ticker

            t = yf.Ticker(ticker_yf)
            fin = t.financials  # columns = dates, rows = line items
            if fin is not None and not fin.empty:
                for col in list(fin.columns)[:3]:
                    year = str(col)[:4]
                    rev  = fin.loc["Total Revenue",           col] if "Total Revenue"           in fin.index else None
                    ebit = fin.loc["EBITDA",                  col] if "EBITDA"                  in fin.index else None
                    ni   = fin.loc["Net Income",              col] if "Net Income"              in fin.index else None
                    fcf  = None
                    gm   = None
                    em   = round(float(ebit) / float(rev) * 100, 2) if (ebit and rev) else None
                    nm   = round(float(ni)   / float(rev) * 100, 2) if (ni   and rev) else None

                    # Convert to Cr (÷ 10,000,000) if raw INR
                    def to_cr(v: Any) -> Optional[float]:
                        try:
                            fv = float(v)
                            return round(fv / 1e7, 2) if abs(fv) > 1e9 else round(fv, 2)
                        except (TypeError, ValueError):
                            return None

                    rows.append({
                        "period":            year,
                        "revenue":           to_cr(rev),
                        "ebitda":            to_cr(ebit),
                        "net_income":        to_cr(ni),
                        "free_cash_flow":    to_cr(fcf),
                        "gross_margin":      gm,
                        "ebitda_margin":     em,
                        "net_margin":        nm,
                        "revenue_growth_yoy":None,
                        "net_debt_to_ebitda":None,
                    })
        except Exception as exc:
            logger.debug(f"[pdf_builder] yfinance financials failed: {exc}")

    # ── 3. Add YoY growth ─────────────────────────────────────────────────────
    try:
        for i in range(len(rows) - 1):
            r_curr = rows[i]
            r_prev = rows[i + 1]
            if r_curr.get("revenue") and r_prev.get("revenue") and float(r_prev["revenue"]) != 0:
                growth = (float(r_curr["revenue"]) - float(r_prev["revenue"])) / abs(float(r_prev["revenue"])) * 100
                r_curr["revenue_growth_yoy"] = round(growth, 2)
    except Exception:
        pass

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# HTML builders
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(v: Any, unit: str = "", decimals: int = 1) -> str:
    """Format numeric value safely."""
    try:
        if v is None:
            return "—"
        f = round(float(v), decimals)
        return f"{f:,.{decimals}f}{unit}"
    except (TypeError, ValueError):
        return "—"


def _color_upside(upside: Any) -> str:
    """Return inline style color for upside/downside value."""
    try:
        v = float(upside)
        if v > 20:
            return "color:#155724;font-weight:bold"
        elif v >= 0:
            return "color:#856404;font-weight:bold"
        else:
            return "color:#721c24;font-weight:bold"
    except (TypeError, ValueError):
        return "color:#2d3748"


def _rec_badge(rec: str) -> str:
    styles = {
        "Buy":              "background:#d4edda;color:#155724",
        "Hold":             "background:#fff3cd;color:#856404",
        "Avoid":            "background:#f8d7da;color:#721c24",
        "Insufficient Data":"background:#e2e8f0;color:#2d3748",
    }
    style = styles.get(rec, styles["Insufficient Data"])
    return (
        f'<span style="display:inline-block;{style};padding:4px 12px;'
        f'border-radius:4px;font-weight:bold;font-size:14px">{rec}</span>'
    )


def _quality_badge(q: str) -> str:
    colors = {"A": "#155724", "B": "#0c5460", "C": "#856404", "D": "#721c24"}
    bgs    = {"A": "#d4edda", "B": "#d1ecf1", "C": "#fff3cd", "D": "#f8d7da"}
    c = colors.get(q, "#2d3748")
    b = bgs.get(q, "#e2e8f0")
    return (
        f'<span style="display:inline-block;background:{b};color:{c};padding:4px 14px;'
        f'border-radius:4px;font-weight:bold;font-size:16px">{q}</span>'
    )


def _score_bar(label: str, score: float) -> str:
    pct = int(max(0, min(100, score)))
    return f"""
<div style="margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;margin-bottom:3px">
    <span style="font-size:11px;color:#2d3748;font-weight:500">{label}</span>
    <span style="font-size:11px;color:#1a1a2e;font-weight:bold">{pct}/100</span>
  </div>
  <div style="background:#e2e8f0;border-radius:4px;height:8px;width:100%">
    <div style="background:#1a1a2e;height:8px;border-radius:4px;width:{pct}%"></div>
  </div>
</div>"""


def _swot_item(text: str) -> str:
    """Render a SWOT item with appropriate tag colour."""
    if "[FACT]" in text:
        tag_style = "color:#155724"
        prefix    = "● "
        body = text.replace("[FACT]", "").strip()
    elif "[ASSUMPTION]" in text:
        tag_style = "color:#856404"
        prefix    = "◐ "
        body = text.replace("[ASSUMPTION]", "").strip()
    elif "[INTERPRETATION]" in text:
        tag_style = "color:#0c5460"
        prefix    = "○ "
        body = text.replace("[INTERPRETATION]", "").strip()
    else:
        tag_style = "color:#2d3748"
        prefix    = "• "
        body = text.strip()

    return (
        f'<div style="font-size:10px;margin-bottom:5px;{tag_style}">'
        f'{prefix}{body}</div>'
    )


def _force_badge(rating: str) -> str:
    colors = {"Low": "#155724", "Medium": "#856404", "High": "#721c24"}
    bgs    = {"Low": "#d4edda", "Medium": "#fff3cd", "High": "#f8d7da"}
    c = colors.get(rating, "#2d3748")
    b = bgs.get(rating, "#e2e8f0")
    return (
        f'<span style="background:{b};color:{c};padding:2px 8px;'
        f'border-radius:3px;font-size:10px;font-weight:bold">{rating}</span>'
    )


def _sensitivity_cell(val: Any, base_wacc: float, wacc: float,
                      base_tg: float, tg: float) -> str:
    is_base = (abs(float(wacc) - base_wacc) < 0.01 and
               abs(float(tg)   - base_tg)   < 0.01)
    try:
        v = float(val)
        if v > 20:
            bg, fg = "#d4edda", "#155724"
        elif v >= 0:
            bg, fg = "#fff3cd", "#856404"
        else:
            bg, fg = "#f8d7da", "#721c24"
    except (TypeError, ValueError):
        bg, fg = "#e2e8f0", "#2d3748"
    border = "border:2px solid #1a1a2e" if is_base else ""
    text   = _fmt(val, "%") if val is not None else "—"
    return (
        f'<td style="background:{bg};color:{fg};{border};text-align:center;'
        f'padding:5px 8px;font-size:10px;font-weight:{"bold" if is_base else "normal"}">'
        f'{text}</td>'
    )


def _financial_table_html(financials: list[dict]) -> str:
    if not financials:
        return '<p style="color:#856404;font-size:11px">No financial data available.</p>'

    header_cells = "".join(
        f'<th style="background:#1a1a2e;color:white;padding:6px 10px;'
        f'font-size:10px;text-align:right">{row.get("period","—")}</th>'
        for row in financials
    )

    def data_row(label: str, key: str, unit: str = "", neg_red: bool = True,
                 best_fn=None) -> str:
        values = [row.get(key) for row in financials]
        # Find best value
        valid = [v for v in values if v is not None]
        best_val = best_fn(valid) if (best_fn and valid) else None
        cells = ""
        for v in values:
            style = "text-align:right;padding:5px 10px;font-size:10px"
            text = _fmt(v, unit, 1)
            try:
                fv = float(v)
                if neg_red and fv < 0:
                    style += ";color:#721c24"
                if best_val is not None and abs(fv - best_val) < 0.01:
                    style += ";font-weight:bold"
            except (TypeError, ValueError):
                pass
            cells += f'<td style="{style}">{text}</td>'
        return (
            f'<tr><td style="padding:5px 10px;font-size:10px;font-weight:500;'
            f'background:#f8f9fa">{label}</td>{cells}</tr>'
        )

    rows_html = ""
    rows_html += data_row("Revenue (₹ Cr)", "revenue", " Cr", False, max)
    rows_html += data_row("EBITDA (₹ Cr)", "ebitda", " Cr", False, max)
    rows_html += data_row("Net Income (₹ Cr)", "net_income", " Cr", True, max)
    rows_html += data_row("Free Cash Flow (₹ Cr)", "free_cash_flow", " Cr", True, max)
    rows_html += data_row("EBITDA Margin", "ebitda_margin", "%", False, max)
    rows_html += data_row("Net Margin", "net_margin", "%", False, max)
    rows_html += data_row("Revenue Growth YoY", "revenue_growth_yoy", "%", True, max)
    rows_html += data_row("Net Debt / EBITDA", "net_debt_to_ebitda", "×", True, min)

    return f"""
<table style="width:100%;border-collapse:collapse;font-family:Arial">
  <thead>
    <tr>
      <th style="background:#1a1a2e;color:white;padding:6px 10px;font-size:10px;text-align:left">Metric</th>
      {header_cells}
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>"""


def _scenarios_html(scenarios: dict) -> str:
    sc = scenarios.get("scenarios") or {}
    parts = []
    for label, bg, border, title in [
        ("bull", "#d4edda", "#155724", "🐂 Bull Case"),
        ("base", "#fff3cd", "#856404", "📊 Base Case"),
        ("bear", "#f8d7da", "#721c24", "🐻 Bear Case"),
    ]:
        s = sc.get(label) or {}
        up = s.get("upside_pct")
        price = s.get("price_per_share")
        rating = (s.get("rating") or "").upper()
        key_ass = s.get("key_assumption") or "—"
        up_text = _fmt(up, "%") if up is not None else "—"
        price_text = f"₹{_fmt(price)}" if price is not None else "—"

        parts.append(f"""
<div style="flex:1;background:{bg};border:1px solid {border};border-radius:6px;
            padding:12px;margin:0 4px">
  <div style="font-weight:bold;font-size:12px;color:{border};margin-bottom:6px">{title}</div>
  <div style="font-size:22px;font-weight:bold;color:{border}">{price_text}</div>
  <div style="font-size:12px;color:{border};margin-top:2px">{up_text} upside &nbsp;·&nbsp; {rating}</div>
  <div style="font-size:10px;color:#2d3748;margin-top:8px;font-style:italic">{key_ass[:80]}</div>
</div>""")

    return f'<div style="display:flex;margin-bottom:12px">\n{"".join(parts)}\n</div>'


def _sensitivity_html(scenarios: dict) -> str:
    sens = scenarios.get("sensitivity") or {}
    grid = sens.get("grid")
    if not grid:
        return '<p style="font-size:10px;color:#856404">Run scenarios to generate sensitivity table.</p>'

    wacc_range = sens.get("wacc_range", [])
    tg_range   = sens.get("terminal_growth_range", [])
    base_assumptions = scenarios.get("base_assumptions") or {}
    base_wacc = float(base_assumptions.get("wacc", 0) or 0)
    base_tg   = float(base_assumptions.get("terminal_growth", 0) or 0)

    header = "".join(
        f'<th style="background:#1a1a2e;color:white;padding:4px 8px;'
        f'font-size:9px;text-align:center">TG {_fmt(tg, "%")}</th>'
        for tg in tg_range
    )
    body_rows = ""
    for i, wacc in enumerate(wacc_range):
        row_cells = f'<td style="background:#f8f9fa;font-size:9px;font-weight:500;padding:4px 8px">WACC {_fmt(wacc, "%")}</td>'
        for j, tg in enumerate(tg_range):
            try:
                val = grid[i][j]
            except (IndexError, TypeError):
                val = None
            row_cells += _sensitivity_cell(val, base_wacc, float(wacc), base_tg, float(tg))
        body_rows += f"<tr>{row_cells}</tr>"

    return f"""
<table style="width:100%;border-collapse:collapse;font-family:Arial">
  <thead><tr>
    <th style="background:#1a1a2e;color:white;padding:4px 8px;font-size:9px">WACC \\ TG</th>
    {header}
  </tr></thead>
  <tbody>{body_rows}</tbody>
</table>
<div style="font-size:9px;color:#2d3748;margin-top:4px">
  ● Bold border = base case &nbsp;
  <span style="color:#155724">■</span> >20% upside &nbsp;
  <span style="color:#856404">■</span> 0-20% &nbsp;
  <span style="color:#721c24">■</span> negative
</div>"""


def _porter_html(porter: dict) -> str:
    force_labels = {
        "competitive_rivalry":    "Competitive Rivalry",
        "supplier_power":         "Supplier Power",
        "buyer_power":            "Buyer Power",
        "threat_of_substitutes":  "Threat of Substitutes",
        "threat_of_new_entrants": "Threat of New Entrants",
    }
    rows = ""
    for key, label in force_labels.items():
        f = porter.get(key) or {}
        rating = f.get("rating", "Medium")
        rationale = f.get("rationale", "—")
        tag = f.get("tag", "ASSUMPTION")
        rows += f"""
<tr>
  <td style="padding:5px 8px;font-size:10px;font-weight:500;background:#f8f9fa">{label}</td>
  <td style="padding:5px 8px;text-align:center">{_force_badge(rating)}</td>
  <td style="padding:5px 8px;font-size:10px;color:#2d3748">{rationale}</td>
  <td style="padding:5px 8px;font-size:9px;color:#0c5460;text-align:center">{tag}</td>
</tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;font-family:Arial">
  <thead><tr>
    <th style="background:#1a1a2e;color:white;padding:6px 8px;font-size:10px;text-align:left">Force</th>
    <th style="background:#1a1a2e;color:white;padding:6px 8px;font-size:10px;text-align:center">Rating</th>
    <th style="background:#1a1a2e;color:white;padding:6px 8px;font-size:10px;text-align:left">Rationale</th>
    <th style="background:#1a1a2e;color:white;padding:6px 8px;font-size:10px;text-align:center">Source</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""


def _signals_html(insights: list[dict]) -> str:
    if not insights:
        return '<p style="font-size:10px;color:#856404">No signals detected. Run signal scan first.</p>'

    top = sorted(
        insights,
        key=lambda s: {"high": 0, "medium": 1, "low": 2}.get((s.get("severity") or "low").lower(), 2),
    )[:5]

    rows = ""
    for sig in top:
        name = sig.get("signal_name") or sig.get("name") or sig.get("title") or "Signal"
        sev  = (sig.get("severity") or "low").capitalize()
        src  = sig.get("source") or sig.get("source_ref") or "—"
        sev_styles = {
            "High":   "background:#f8d7da;color:#721c24",
            "Medium": "background:#fff3cd;color:#856404",
            "Low":    "background:#d4edda;color:#155724",
        }
        s = sev_styles.get(sev, sev_styles["Low"])
        rows += f"""
<tr>
  <td style="padding:5px 8px;font-size:10px">{name}</td>
  <td style="padding:5px 8px;text-align:center">
    <span style="{s};padding:2px 7px;border-radius:3px;font-size:9px;font-weight:bold">{sev}</span>
  </td>
  <td style="padding:5px 8px;font-size:9px;color:#2d3748">{str(src)[:50]}</td>
</tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;font-family:Arial">
  <thead><tr>
    <th style="background:#1a1a2e;color:white;padding:5px 8px;font-size:10px;text-align:left">Signal</th>
    <th style="background:#1a1a2e;color:white;padding:5px 8px;font-size:10px;text-align:center">Severity</th>
    <th style="background:#1a1a2e;color:white;padding:5px 8px;font-size:10px;text-align:left">Source</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""


# ─────────────────────────────────────────────────────────────────────────────
# Main HTML assembler
# ─────────────────────────────────────────────────────────────────────────────

def build_html(
    session:    Any,
    scoring:    ScoringResult,
    swot:       dict,
    porter:     dict,
    financials: list[dict],
) -> str:
    """
    Assemble 2-page print-ready A4 HTML report.
    Returns complete HTML string.
    """
    ticker   = getattr(session, "ticker", "TICKER")
    sid      = getattr(session, "session_id", "—")
    now_str  = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    # Load live data from session
    assumptions: dict = {}
    scenarios:   dict = {}
    insights:    list = []
    catalysts:   list = []
    thesis       = ""
    variant_view = ""

    try:
        assumptions = session.get_assumptions() or {}
    except Exception:
        pass
    try:
        scenarios = session.get_scenarios() or {}
    except Exception:
        pass
    try:
        ins = json.loads(session.insights_file.read_text()) if session.insights_file.exists() else []
        insights = ins if isinstance(ins, list) else []
    except Exception:
        pass
    try:
        thesis = session.get_thesis() or ""
    except Exception:
        pass
    try:
        variant_view = session.get_variant_view() or ""
    except Exception:
        pass
    try:
        meta = session.get_meta() if hasattr(session, "get_meta") else {}
        catalysts = meta.get("catalysts") or []
    except Exception:
        pass

    current_price = assumptions.get("current_price_inr") or assumptions.get("current_price")
    price_str     = f"₹{_fmt(current_price)}" if current_price else "—"
    sector_label  = (assumptions.get("_sector") or "").replace("_", " ").title() or "—"

    # Reverse DCF
    rdcf       = scenarios.get("reverse_dcf") or {}
    rdcf_growth = _fmt(rdcf.get("implied_growth_rate"), "%")
    rdcf_ebitda = _fmt(rdcf.get("implied_ebitda_margin"), "%")
    rdcf_assessment = (rdcf.get("assessment") or rdcf.get("interpretation") or "—")

    # SWOT
    def swot_quad(items: list, header: str, bg: str, border: str) -> str:
        content = "".join(_swot_item(i) for i in items) if items else \
                  '<div style="font-size:10px;color:#aaa;font-style:italic">—</div>'
        return f"""
<div style="background:{bg};border:1px solid {border};border-radius:4px;padding:10px">
  <div style="font-weight:bold;font-size:11px;color:{border};margin-bottom:6px;
              text-transform:uppercase;letter-spacing:0.5px">{header}</div>
  {content}
</div>"""

    swot_html = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
  {swot_quad(swot.get("strengths",   []), "Strengths",     "#d4edda", "#155724")}
  {swot_quad(swot.get("weaknesses",  []), "Weaknesses",    "#f8d7da", "#721c24")}
  {swot_quad(swot.get("opportunities",[]), "Opportunities", "#d1ecf1", "#0c5460")}
  {swot_quad(swot.get("threats",     []), "Threats",       "#fff3cd", "#856404")}
</div>"""

    # Catalysts
    cat_items = ""
    for c in (catalysts or [])[:5]:
        desc  = c.get("description") or c.get("catalyst") or str(c)[:80]
        cdate = c.get("expected_date") or c.get("date") or ""
        ctype = (c.get("catalyst_type") or c.get("type") or "").capitalize()
        cat_items += (
            f'<div style="font-size:10px;margin-bottom:4px">⚡ {desc}'
            f'{"  ·  " + cdate if cdate else ""}{"  ·  " + ctype if ctype else ""}</div>'
        )
    if not cat_items:
        cat_items = '<div style="font-size:10px;color:#aaa;font-style:italic">No catalysts logged yet.</div>'

    # Risk signals
    risk_items = ""
    high_sev = [s for s in insights if (s.get("severity") or "").lower() == "high"]
    for s in high_sev[:4]:
        name = s.get("signal_name") or s.get("name") or s.get("title") or "Signal"
        risk_items += f'<div style="font-size:10px;color:#721c24;margin-bottom:3px">⚠ {name}</div>'
    if not risk_items:
        risk_items = '<div style="font-size:10px;color:#155724">No high-severity risk signals detected.</div>'

    # ──────────────────────────────────────────────────────────────────────────
    # Page CSS
    # ──────────────────────────────────────────────────────────────────────────
    css = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; color: #2d3748; background: transparent; }
@page { size: A4; margin: 0; }
.page {
  width: 210mm;
  min-height: 297mm;
  padding: 14mm 16mm 12mm 16mm;
  background: white;
  page-break-after: always;
  overflow: hidden;
}
.page:last-child { page-break-after: avoid; }
@media screen {
  body { background: #e8e8e8; padding: 20px; }
  .page {
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    margin: 0 auto 24px auto;
  }
}
@media print {
  .no-print { display: none !important; }
  body { background: white; padding: 0; }
}
.section-header {
  font-size: 11px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #1a1a2e;
  border-bottom: 2px solid #e94560;
  padding-bottom: 3px;
  margin-bottom: 8px;
  margin-top: 12px;
}
</style>"""

    # ──────────────────────────────────────────────────────────────────────────
    # Print bar (sticky, no-print)
    # ──────────────────────────────────────────────────────────────────────────
    print_bar = f"""
<div class="no-print" style="position:sticky;top:0;z-index:999;
  background:#1a1a2e;color:white;padding:10px 20px;font-family:Arial;font-size:13px;
  display:flex;align-items:center;justify-content:space-between;">
  <span>📄 {ticker} Research Note</span>
  <button onclick="window.print()"
    style="background:#e94560;color:white;border:none;padding:8px 18px;
    border-radius:4px;cursor:pointer;font-weight:bold;font-size:13px;">
    🖨️ Save as PDF
  </button>
</div>"""

    # ──────────────────────────────────────────────────────────────────────────
    # PAGE 1
    # ──────────────────────────────────────────────────────────────────────────
    page1 = f"""
<div class="page">

  <!-- Header bar -->
  <div style="background:#1a1a2e;color:white;padding:10px 14px;border-radius:4px;
              display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
    <div>
      <span style="font-size:18px;font-weight:bold">{ticker}</span>
      <span style="margin-left:10px;background:#e94560;padding:2px 8px;
                  border-radius:3px;font-size:11px">{sector_label}</span>
    </div>
    <div style="text-align:right;font-size:10px;opacity:0.8">
      {now_str}<br>
      <span style="font-style:italic;font-size:9px">Confidential Research Note</span>
    </div>
  </div>

  <!-- Metric cards row -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:10px;text-align:center">
      <div style="font-size:9px;text-transform:uppercase;color:#2d3748;margin-bottom:4px">Recommendation</div>
      {_rec_badge(scoring.recommendation)}
    </div>
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:10px;text-align:center">
      <div style="font-size:9px;text-transform:uppercase;color:#2d3748;margin-bottom:4px">Composite Score</div>
      <div style="font-size:22px;font-weight:bold;color:#1a1a2e">{scoring.composite_score:.0f}</div>
      <div style="font-size:9px;color:#2d3748">/100</div>
    </div>
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:10px;text-align:center">
      <div style="font-size:9px;text-transform:uppercase;color:#2d3748;margin-bottom:4px">Current Price</div>
      <div style="font-size:18px;font-weight:bold;color:#1a1a2e">{price_str}</div>
    </div>
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:10px;text-align:center">
      <div style="font-size:9px;text-transform:uppercase;color:#2d3748;margin-bottom:4px">Business Quality</div>
      {_quality_badge(scoring.business_quality)}
    </div>
  </div>

  <!-- Score bars -->
  <div style="margin-bottom:14px">
    {_score_bar("Financial Strength",        scoring.financial_strength)}
    {_score_bar("Growth Quality",            scoring.growth_quality)}
    {_score_bar("Valuation Attractiveness",  scoring.valuation_attractiveness)}
    {_score_bar("Risk Score (higher = safer)", scoring.risk_score)}
    {_score_bar("Market Positioning",        scoring.market_positioning)}
  </div>

  <!-- Financial Highlights -->
  <div class="section-header">Financial Highlights</div>
  {_financial_table_html(financials)}

  <!-- SWOT -->
  <div class="section-header">SWOT Analysis</div>
  {swot_html}

  <!-- Risk Signals -->
  <div class="section-header">Risk Signals</div>
  {risk_items}

</div>"""

    # ──────────────────────────────────────────────────────────────────────────
    # PAGE 2
    # ──────────────────────────────────────────────────────────────────────────
    # Rationale + caveats for Investment Thesis
    rationale_html = "".join(
        f'<div style="font-size:10px;margin-bottom:3px;color:#155724">✓ {r}</div>'
        for r in scoring.rationale[:5]
    ) or '<div style="font-size:10px;color:#aaa">Run scenarios to populate.</div>'

    page2 = f"""
<div class="page">

  <!-- Header bar -->
  <div style="background:#1a1a2e;color:white;padding:8px 14px;border-radius:4px;
              display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-size:14px;font-weight:bold">{ticker} — Valuation &amp; Investment Thesis</span>
    <span style="font-size:10px;opacity:0.7">{now_str}</span>
  </div>

  <!-- Investment Thesis -->
  <div class="section-header">Investment Thesis</div>
  <div style="background:#f8f9fa;border-left:3px solid #1a1a2e;padding:8px 12px;
              border-radius:0 4px 4px 0;margin-bottom:8px">
    <div style="font-size:11px;font-weight:bold;margin-bottom:3px">Hypothesis</div>
    <div style="font-size:10px">{thesis or "Not set — use update_thesis() to add."}</div>
  </div>
  {"" if not variant_view else f'<div style="background:#fff3cd;border-left:3px solid #856404;padding:8px 12px;border-radius:0 4px 4px 0;margin-bottom:8px"><div style="font-size:11px;font-weight:bold;color:#856404;margin-bottom:3px">Variant View (vs Consensus)</div><div style="font-size:10px">{variant_view}</div></div>'}
  <div style="margin-bottom:8px">
    <div style="font-size:11px;font-weight:bold;margin-bottom:4px">Model Rationale</div>
    {rationale_html}
  </div>
  <div>
    <div style="font-size:11px;font-weight:bold;margin-bottom:4px">Catalysts</div>
    {cat_items}
  </div>

  <!-- DCF Valuation -->
  <div class="section-header">DCF Valuation — Bull / Base / Bear</div>
  {_scenarios_html(scenarios)}

  <!-- Sensitivity Table -->
  <div style="margin-bottom:10px">
    <div style="font-size:10px;font-weight:bold;margin-bottom:5px">
      Sensitivity Table — Upside % (WACC × Terminal Growth Rate)
    </div>
    {_sensitivity_html(scenarios)}
  </div>

  <!-- Reverse DCF -->
  <div class="section-header">Reverse DCF</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px">
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:8px;text-align:center">
      <div style="font-size:9px;color:#2d3748;margin-bottom:2px">Implied Growth Rate</div>
      <div style="font-size:16px;font-weight:bold;color:#1a1a2e">{rdcf_growth}</div>
    </div>
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:8px;text-align:center">
      <div style="font-size:9px;color:#2d3748;margin-bottom:2px">Implied EBITDA Margin</div>
      <div style="font-size:16px;font-weight:bold;color:#1a1a2e">{rdcf_ebitda}</div>
    </div>
    <div style="border:1px solid #e2e8f0;border-radius:4px;padding:8px;text-align:center">
      <div style="font-size:9px;color:#2d3748;margin-bottom:2px">Assessment</div>
      <div style="font-size:12px;font-weight:bold;color:#1a1a2e">{str(rdcf_assessment)[:40]}</div>
    </div>
  </div>

  <!-- Signal Summary -->
  <div class="section-header">Signal Summary (Top 5)</div>
  {_signals_html(insights)}

  <!-- Porter's Five Forces -->
  <div class="section-header">Porter's Five Forces</div>
  {_porter_html(porter)}

  <!-- Footer -->
  <div style="margin-top:14px;border-top:1px solid #e2e8f0;padding-top:6px;
              display:flex;justify-content:space-between;align-items:center">
    <span style="font-size:9px;color:#2d3748">
      Generated by Unified Financial Intelligence System &nbsp;·&nbsp;
      Session: {sid}
    </span>
    <span style="font-size:9px;color:#e94560;font-style:italic">
      This is not investment advice
    </span>
    <span style="font-size:9px;color:#2d3748">{now_str}</span>
  </div>

</div>"""

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{css}</head><body>{print_bar}{page1}{page2}</body></html>"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_report(
    session:     Any,
    sector:      str = "other",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Orchestrate full 2-page PDF report.

    Steps:
      1. score_session()
      2. generate_swot()
      3. generate_porter()
      4. build_financial_table()
      5. build_html()
      6. Write to session_dir/{ticker}_report_PRINT.html

    Never raises — returns error-page HTML file if something fails.

    Args:
        session:     ResearchSession instance
        sector:      sector string
        output_path: optional override for output file path

    Returns:
        Path to the written HTML file
    """
    try:
        logger.info(f"[pdf_builder] Building report for {session.ticker} sector={sector}")

        scoring    = score_session(session, sector=sector)
        swot       = generate_swot(session, scoring, sector=sector)
        porter     = generate_porter(session, sector=sector)
        financials = build_financial_table(session)
        html       = build_html(session, scoring, swot, porter, financials)

        out = output_path or (
            session.session_dir /
            f"{session.ticker}_report_PRINT.html"
        )
        out = Path(out)
        out.write_text(html, encoding="utf-8")

        logger.info(f"[pdf_builder] Report written: {out}")
        return out

    except Exception as exc:
        logger.error(f"[pdf_builder] build_report failed: {exc}")
        # Write minimal error page
        ticker = getattr(session, "ticker", "UNKNOWN")
        err_html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>
<div style="font-family:Arial;padding:40px">
<h2 style="color:#e94560">Report Generation Error</h2>
<p>Ticker: {ticker}</p>
<pre style="background:#f8f9fa;padding:12px;border-radius:4px">{exc}</pre>
<p>Check the session data and try again.</p>
</div></body></html>"""
        try:
            out = output_path or (session.session_dir / f"{ticker}_report_ERROR.html")
            Path(out).write_text(err_html, encoding="utf-8")
            return Path(out)
        except Exception:
            fallback = Path(f"/tmp/{ticker}_report_ERROR.html")
            fallback.write_text(err_html, encoding="utf-8")
            return fallback
