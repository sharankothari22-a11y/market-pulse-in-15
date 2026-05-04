"""
ai_engine/chat_app.py
──────────────────────
Layer 14 — Streamlit Chat Interface.

FIXES vs previous version:
  - Auto-detects sector from ticker when starting new session
  - Handles thesis / variant_view / catalyst intents
  - Handles all 6 output types (market report, commodity, alerts, etc.)
  - Macro-micro linkage ("why is this stock moving?")
  - Sidebar shows thesis and catalysts

Run:
    streamlit run research_platform/ai_engine/chat_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import streamlit as st

from ai_engine.intent_parser import (
    parse_intent, describe_intent,
    ACTION_NEW_SESSION, ACTION_LOAD_SESSION, ACTION_SHOW_ASSUMPTIONS,
    ACTION_UPDATE_ASSUMPTION, ACTION_SHOW_SCENARIOS, ACTION_RUN_SCENARIOS,
    ACTION_SCAN_NEWS, ACTION_SHOW_SIGNALS, ACTION_GENERATE_REPORT,
    ACTION_SHOW_HISTORY, ACTION_ROLLBACK, ACTION_SHOW_SOURCES,
    ACTION_SHOW_GUARDRAILS, ACTION_REVERSE_DCF, ACTION_UNKNOWN,
    ACTION_SET_THESIS, ACTION_SHOW_THESIS, ACTION_SET_VARIANT_VIEW,
    ACTION_SHOW_VARIANT_VIEW, ACTION_LOG_CATALYST, ACTION_SHOW_CATALYSTS,
    ACTION_MARKET_REPORT, ACTION_COMMODITY_REPORT, ACTION_CHECK_ALERTS,
    ACTION_INVESTOR_REPORT, ACTION_POLITICS_REPORT, ACTION_MACRO_MICRO,
)
from ai_engine.session_manager import (
    new_session, load_session, list_sessions, ResearchSession
)

st.set_page_config(page_title="Research Platform", page_icon="📊", layout="wide")


def _init_state():
    for k, v in {"session": None, "messages": [], "pending_confirm": None,
                 "sector": "universal"}.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def _session() -> ResearchSession | None:
    return st.session_state.session

def _add(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def _fmt_assumptions(a: dict) -> str:
    rows = [f"| `{k}` | `{v}` |" for k, v in a.items() if not k.startswith("_")]
    return "| Metric | Value |\n|--------|-------|\n" + "\n".join(rows)

def _fmt_scenarios(sc: dict) -> str:
    out = []
    for label in ("bull","base","bear"):
        s = sc.get("scenarios",{}).get(label)
        if s:
            up = s.get("upside_pct")
            out.append(f"**{label.upper()}** — ₹{s.get('price_per_share','?')} "
                       f"({f'{up:+.1f}%' if up else 'N/A'}) · {s.get('rating','?').upper()}\n"
                       f"> {s.get('key_assumption','')}")
    rdcf = sc.get("reverse_dcf")
    if rdcf:
        out.append(f"\n**Reverse DCF:** {rdcf.get('interpretation','')}")
    return "\n\n".join(out) if out else "No scenarios yet. Say **run scenarios**."


def execute_intent(intent) -> str:
    a   = intent.action
    ses = _session()

    # ── New session ──────────────────────────────────────────────────────────
    if a == ACTION_NEW_SESSION:
        ticker = intent.ticker or "UNKNOWN"
        sector = intent.params.get("suggested_sector", st.session_state.sector)
        st.session_state.sector = sector

        from ai_engine.dcf_bridge import build_full_assumptions
        from ai_engine.assumption_engine import AssumptionEngine
        new_ses = new_session(ticker)
        base    = build_full_assumptions(ticker, sector=sector)
        AssumptionEngine(new_ses).initialize(base)
        st.session_state.session = new_ses
        return (f"New session: **{ticker}** (sector: **{sector}**)\n"
                f"`{new_ses.session_id}`\n\n"
                f"Loaded {len([k for k in base if not k.startswith('_')])} assumptions.\n\n"
                f"💡 Set your thesis: *my thesis is RELIANCE is undervalued due to GRM recovery*\n"
                f"💡 Log a catalyst: *add catalyst Q1 results due 15 May*\n"
                f"💡 Or: **scan news** · **show assumptions** · **run scenarios**")

    # ── Load session ─────────────────────────────────────────────────────────
    if a == ACTION_LOAD_SESSION:
        if intent.session_id:
            loaded = load_session(intent.session_id)
        elif intent.ticker:
            from ai_engine.session_manager import latest_session
            loaded = latest_session(intent.ticker)
        else:
            return "Specify session ID or ticker. Example: *load session RELIANCE*"
        if not loaded:
            return f"No session found."
        st.session_state.session = loaded
        return f"Loaded `{loaded.session_id}` for **{loaded.ticker}**."

    if not ses:
        return "No active session. Say **research TICKER** to start."

    # ── Thesis ───────────────────────────────────────────────────────────────
    if a == ACTION_SET_THESIS:
        thesis = intent.params.get("thesis", intent.raw_input)
        ses.update_thesis(thesis)
        return f"Thesis recorded:\n> *{thesis}*\n\nThis will anchor the research session."

    if a == ACTION_SHOW_THESIS:
        thesis = ses.get_thesis()
        vv     = ses.get_variant_view()
        return (f"**Thesis for {ses.ticker}:**\n> {thesis or 'Not set yet.'}\n\n"
                f"**Variant view:**\n> {vv or 'Not set yet.'}")

    # ── Variant view ──────────────────────────────────────────────────────────
    if a == ACTION_SET_VARIANT_VIEW:
        vv = intent.params.get("variant_view", intent.raw_input)
        ses.update_variant_view(vv)
        return f"Variant view recorded:\n> *{vv}*"

    if a == ACTION_SHOW_VARIANT_VIEW:
        return f"**Variant view:** {ses.get_variant_view() or 'Not set.'}"

    # ── Catalysts ─────────────────────────────────────────────────────────────
    if a == ACTION_LOG_CATALYST:
        desc = intent.params.get("description", intent.raw_input)
        ses.log_catalyst(description=desc)
        return f"Catalyst logged: *{desc}*"

    if a == ACTION_SHOW_CATALYSTS:
        cats = ses.get_catalysts()
        if not cats:
            return "No catalysts logged. Say **add catalyst Q1 results due 15 May**."
        lines = [f"- [{c.get('type','?')}] {c['description']} ({c.get('expected_date','date TBD')})"
                 for c in cats]
        return f"**Catalysts for {ses.ticker}:**\n\n" + "\n".join(lines)

    # ── Assumptions ──────────────────────────────────────────────────────────
    if a == ACTION_SHOW_ASSUMPTIONS:
        return f"**Assumptions for {ses.ticker}:**\n\n{_fmt_assumptions(ses.get_assumptions())}"

    if a == ACTION_UPDATE_ASSUMPTION:
        if not intent.metric or intent.value is None:
            return "Specify metric and value. Example: *set wacc 11.5*"
        from ai_engine.assumption_engine import AssumptionEngine
        AssumptionEngine(ses).manual_override(intent.metric, intent.value, reason=intent.raw_input)
        return f"Updated `{intent.metric}` → **{intent.value}**. Say **run scenarios** to refresh targets."

    # ── Scenarios ─────────────────────────────────────────────────────────────
    if a == ACTION_RUN_SCENARIOS:
        from ai_engine.scenario_engine import run_scenarios
        base = ses.get_assumptions()
        run_scenarios(ses, base,
                      shares_outstanding=float(base.get("shares_outstanding", 6760) or 6760),
                      base_revenue=float(base.get("base_revenue", 100) or 100))
        return f"**Scenarios for {ses.ticker}:**\n\n{_fmt_scenarios(ses.get_scenarios())}"

    if a == ACTION_SHOW_SCENARIOS:
        sc = ses.get_scenarios()
        return f"**Scenarios:**\n\n{_fmt_scenarios(sc)}"

    # ── News scan ─────────────────────────────────────────────────────────────
    if a == ACTION_SCAN_NEWS:
        from sqlalchemy import select, desc
        from database.connection import get_session as db_sess
        from database.models import Event
        from ai_engine.signal_detector import scan_events_for_signals, deduplicate_signals
        from ai_engine.factor_engine import signals_to_factors
        from ai_engine.assumption_engine import AssumptionEngine
        from datetime import date

        with db_sess() as db:
            rows = db.scalars(select(Event).order_by(desc(Event.created_at)).limit(50)).all()
        events  = [{"title": r.title, "source": r.entity_type or "news"} for r in rows]
        sector  = st.session_state.sector
        signals = deduplicate_signals(scan_events_for_signals(events, ticker=ses.ticker, sector=sector))

        if not signals:
            return f"No signals in latest {len(events)} items."

        for s in signals:
            ses.log_insight(signal_type=s.signal_id, description=s.signal_name,
                            source_name=s.source_name, severity=s.severity,
                            factor=", ".join(s.factors))
        deltas  = signals_to_factors(signals, ses.get_assumptions())
        if deltas:
            AssumptionEngine(ses).process_deltas(deltas, event_date=date.today())

        lines = [f"- **{s.signal_name}** [{s.severity}]: {s.transmission[:80]}..."
                 for s in signals]
        return (f"**{len(signals)} signals** from {len(events)} events:\n\n"
                + "\n".join(lines) + "\n\nAssumptions updated where confidence ≥ 0.45.")

    if a == ACTION_SHOW_SIGNALS:
        insights = json.loads(ses.insights_file.read_text()) if ses.insights_file.exists() else []
        if not insights:
            return "No signals yet. Say **scan news**."
        lines = [f"- **{i['signal_type']}** [{i['severity']}]: {i['description']}"
                 for i in insights[-10:]]
        return "**Detected signals:**\n\n" + "\n".join(lines)

    # ── Output types ──────────────────────────────────────────────────────────
    if a == ACTION_MARKET_REPORT:
        from ai_engine.output_engine import daily_market_report
        return daily_market_report()

    if a == ACTION_COMMODITY_REPORT:
        from ai_engine.output_engine import commodity_daily_report
        return commodity_daily_report()

    if a == ACTION_CHECK_ALERTS:
        from ai_engine.output_engine import check_alerts, format_alerts_report
        alerts = check_alerts()
        return format_alerts_report(alerts)

    if a == ACTION_INVESTOR_REPORT:
        from ai_engine.output_engine import investor_tracking_report
        return investor_tracking_report()

    if a == ACTION_POLITICS_REPORT:
        from ai_engine.output_engine import politics_macro_report
        return politics_macro_report()

    if a == ACTION_MACRO_MICRO:
        from ai_engine.output_engine import macro_micro_linkage
        sector = st.session_state.sector
        result = macro_micro_linkage(ses.ticker, sector)
        drivers = result.get("drivers", [])
        if not drivers:
            return f"No macro-micro linkage found for {ses.ticker}. Run collectors first to populate macro data."
        lines = [f"- **{d['macro_indicator']}** ({d['value']}) → {d['signal']} → {d['transmission'][:80]}"
                 for d in drivers[:5]]
        return f"**Why is {ses.ticker} moving? — Macro drivers:**\n\n" + "\n".join(lines)

    # ── Report ────────────────────────────────────────────────────────────────
    if a == ACTION_GENERATE_REPORT:
        from ai_engine.llm_layer import generate_full_report
        report = generate_full_report(ses, ses.ticker, st.session_state.sector)
        return f"Report generated → `summary.md`\n\n---\n\n{report[:2000]}..."

    # ── History / rollback ────────────────────────────────────────────────────
    if a == ACTION_SHOW_HISTORY:
        from ai_engine.audit_export import get_assumption_audit
        hist = get_assumption_audit(ses)
        if not hist:
            return "No changes recorded."
        lines = [f"- `{h['metric']}`: {h.get('old_value','?')} → **{h.get('new_value','?')}** ({h.get('reason','')[:50]})"
                 for h in hist[-15:]]
        return "**Assumption history:**\n\n" + "\n".join(lines)

    if a == ACTION_ROLLBACK:
        idx = intent.params.get("index", -1)
        if idx < 0:
            return "Specify index. Example: *rollback to 3*"
        from ai_engine.version_control import rollback_to_index
        rollback_to_index(ses, idx)
        return f"Rolled back to index {idx}. Say **show assumptions** to verify."

    if a == ACTION_SHOW_SOURCES:
        sources = json.loads(ses.sources_file.read_text()) if ses.sources_file.exists() else []
        lines   = [f"- **{s['name']}** ({s['source_type']})" for s in sources[-15:]]
        return f"**Sources ({len(sources)} total):**\n\n" + "\n".join(lines)

    if a == ACTION_SHOW_GUARDRAILS:
        from ai_engine.audit_export import get_guardrail_audit
        breaches = get_guardrail_audit(ses)
        if not breaches:
            return "No guardrail breaches."
        lines = [f"- `{b['metric']}`: {b['attempted_value']:.2f} → {b['capped_value']:.2f} ({b['rule']})"
                 for b in breaches]
        return f"**Guardrail breaches ({len(lines)}):**\n\n" + "\n".join(lines)

    if a == ACTION_REVERSE_DCF:
        from ai_engine.dcf_bridge import reverse_dcf
        a_c    = ses.get_assumptions()
        price  = a_c.get("current_price_inr")
        shares = a_c.get("shares_outstanding")
        if not price or not shares:
            return "Need current_price_inr and shares_outstanding. Update them first."
        result = reverse_dcf(
            market_cap=float(price)*float(shares),
            base_ebit=float(a_c.get("base_revenue",100))*float(a_c.get("ebitda_margin",18))/100*0.85,
            tax_rate=float(a_c.get("tax_rate",25))/100, wacc=float(a_c.get("wacc",12))/100,
            net_debt=float(a_c.get("net_debt",0) or 0))
        return (f"**Reverse DCF for {ses.ticker}:**\n\n"
                f"Implied growth: **{result['implied_growth_rate']}%**\n\n"
                f"{result['interpretation']}")

    if a == ACTION_UNKNOWN:
        return (f"Didn't understand: *{intent.raw_input}*\n\n"
                "**Research workflow:**\n"
                "- `research RELIANCE` — new session\n"
                "- `my thesis is X is undervalued because Y` — set hypothesis\n"
                "- `add catalyst Q1 results due 15 May` — track timing\n"
                "- `scan news` — detect signals\n"
                "- `show assumptions` · `set wacc 11.5` — manage inputs\n"
                "- `run scenarios` — Bull/Base/Bear\n"
                "- `generate report` — full research note\n\n"
                "**Market outputs:**\n"
                "- `daily market report` · `commodity report`\n"
                "- `check alerts` · `investor tracking` · `politics report`\n"
                "- `why is RELIANCE moving` — macro-micro linkage")

    return f"Action `{a}` not implemented."


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Research Platform")
    st.caption("Unified Financial Intelligence System")
    st.divider()

    sector = st.selectbox("Sector", ["universal","petroleum","banking","fmcg",
                                      "pharma","it","real_estate","auto"])
    st.session_state.sector = sector

    ses = _session()
    if ses:
        st.success(f"**{ses.ticker}**")
        st.caption(ses.session_id[:30])

        meta = ses.meta()
        if meta.get("thesis"):
            st.info(f"📌 {meta['thesis'][:80]}")
        if meta.get("catalysts"):
            st.caption(f"⚡ {len(meta['catalysts'])} catalysts logged")

        col1, col2 = st.columns(2)
        col1.metric("Sources", meta["source_count"])
        col2.metric("Signals", meta["insight_count"])
        col1.metric("Changes", meta["assumption_changes"])
        col2.metric("Guardrails", meta["guardrail_breaches"])

        st.divider()
        if st.button("📊 Excel"):
            from ai_engine.audit_export import export_to_excel
            out = export_to_excel(ses); st.success(out.name)
        if st.button("📄 HTML/PDF"):
            from ai_engine.audit_export import export_to_html
            out = export_to_html(ses); st.success(out.name)
        if st.button("🗜 Zip"):
            from ai_engine.audit_export import export_session_zip
            out = export_session_zip(ses); st.success(out.name)
    else:
        st.info("Type **research TICKER** to start.")

    st.divider()
    st.caption("Recent sessions:")
    for s in list_sessions()[:5]:
        ticker = s.get("ticker","?")
        thesis = (s.get("thesis","") or "")[:30]
        label  = f"{ticker} — {thesis}" if thesis else ticker
        if st.button(label[:28], key=s["session_id"]):
            st.session_state.session = load_session(s["session_id"])
            _add("assistant", f"Loaded `{s['session_id']}`.")
            st.rerun()


# ── Main chat ─────────────────────────────────────────────────────────────────
st.title("Research Chat")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.pending_confirm:
    intent = st.session_state.pending_confirm
    st.warning(f"⚠️ **Confirm:** {describe_intent(intent)}")
    c1, c2 = st.columns(2)
    if c1.button("✅ Confirm", type="primary"):
        response = execute_intent(intent)
        st.session_state.pending_confirm = None
        _add("assistant", response)
        st.rerun()
    if c2.button("❌ Cancel"):
        st.session_state.pending_confirm = None
        _add("assistant", "Cancelled.")
        st.rerun()

if prompt := st.chat_input("Research a company, scan signals, update assumptions..."):
    _add("user", prompt)
    ses = _session()
    intent = parse_intent(prompt,
                          current_session_id=ses.session_id if ses else None,
                          current_ticker=ses.ticker if ses else None,
                          current_assumptions=ses.get_assumptions() if ses else {})
    if intent.requires_confirmation:
        st.session_state.pending_confirm = intent
        _add("assistant", f"⚠️ **Confirm:** {describe_intent(intent)}\n\nClick Confirm or Cancel above.")
    else:
        _add("assistant", execute_intent(intent))
    st.rerun()
