"""
ai_engine/intent_parser.py
────────────────────────────
Layer 14 — Intent Parser.

FIXES vs previous version:
  - Added thesis / hypothesis / variant_view / catalyst intents
  - Sector auto-detection hint for new_session
  - Show market report / commodity report / alerts intents
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParsedIntent:
    action:               str
    ticker:               Optional[str]   = None
    metric:               Optional[str]   = None
    value:                Optional[float] = None
    text_query:           Optional[str]   = None
    session_id:           Optional[str]   = None
    requires_confirmation: bool           = False
    raw_input:            str             = ""
    params:               dict[str, Any]  = field(default_factory=dict)


# ── Action constants ──────────────────────────────────────────────────────────

ACTION_NEW_SESSION        = "new_session"
ACTION_LOAD_SESSION       = "load_session"
ACTION_SHOW_ASSUMPTIONS   = "show_assumptions"
ACTION_UPDATE_ASSUMPTION  = "update_assumption"
ACTION_SHOW_SCENARIOS     = "show_scenarios"
ACTION_RUN_SCENARIOS      = "run_scenarios"
ACTION_SCAN_NEWS          = "scan_news"
ACTION_SHOW_SIGNALS       = "show_signals"
ACTION_GENERATE_REPORT    = "generate_report"
ACTION_SHOW_HISTORY       = "show_history"
ACTION_ROLLBACK           = "rollback"
ACTION_SHOW_SOURCES       = "show_sources"
ACTION_SHOW_GUARDRAILS    = "show_guardrails"
ACTION_REVERSE_DCF        = "reverse_dcf"
ACTION_COMPARE_SESSIONS   = "compare_sessions"
# Equity research framework intents
ACTION_SET_THESIS         = "set_thesis"
ACTION_SHOW_THESIS        = "show_thesis"
ACTION_SET_VARIANT_VIEW   = "set_variant_view"
ACTION_SHOW_VARIANT_VIEW  = "show_variant_view"
ACTION_LOG_CATALYST       = "log_catalyst"
ACTION_SHOW_CATALYSTS     = "show_catalysts"
# Output types
ACTION_MARKET_REPORT      = "market_report"
ACTION_COMMODITY_REPORT   = "commodity_report"
ACTION_CHECK_ALERTS       = "check_alerts"
ACTION_INVESTOR_REPORT    = "investor_report"
ACTION_POLITICS_REPORT    = "politics_report"
ACTION_MACRO_MICRO        = "macro_micro_linkage"
ACTION_UNKNOWN            = "unknown"

METRIC_ALIASES: dict[str, str] = {
    "revenue growth": "revenue_growth",  "growth": "revenue_growth",
    "ebitda": "ebitda_margin",           "ebitda margin": "ebitda_margin",
    "margin": "ebitda_margin",           "gross margin": "gross_margin",
    "wacc": "wacc",                      "cost of capital": "wacc",
    "terminal growth": "terminal_growth_rate",
    "terminal": "terminal_growth_rate",  "terminal rate": "terminal_growth_rate",
    "capex": "capex_pct_revenue",        "tax": "tax_rate",
    "tax rate": "tax_rate",              "cost of debt": "cost_of_debt",
    "risk premium": "equity_risk_premium", "erp": "equity_risk_premium",
    "working capital": "working_capital_days",
    "nim": "nim_pct",                    "npa": "npl_ratio",
    "npl": "npl_ratio",                  "crude": "crude_price_usd_bbl",
    "crude price": "crude_price_usd_bbl", "grm": "grm_usd_bbl",
    "refining margin": "grm_usd_bbl",   "d/e": "debt_equity_ratio",
    "debt equity": "debt_equity_ratio",
}

LARGE_CHANGE_THRESHOLDS: dict[str, float] = {
    "revenue_growth": 5.0,  "ebitda_margin": 3.0,  "wacc": 1.5,
    "terminal_growth_rate": 1.0, "capex_pct_revenue": 4.0,
    "cost_of_debt": 1.5,   "equity_risk_premium": 1.5,
}

SECTOR_TICKER_MAP: dict[str, str] = {
    "RELIANCE": "petroleum", "BPCL": "petroleum", "IOCL": "petroleum",
    "HPCL": "petroleum",     "ONGC": "petroleum",
    "HDFCBANK": "banking",   "ICICIBANK": "banking", "SBIN": "banking",
    "AXISBANK": "banking",   "KOTAKBANK": "banking", "BAJFINANCE": "banking",
    "HINDUNILVR": "fmcg",    "ITC": "fmcg",        "DABUR": "fmcg",
    "MARICO": "fmcg",        "NESTLEIND": "fmcg",
    "SUNPHARMA": "pharma",   "DRREDDY": "pharma",  "CIPLA": "pharma",
    "LUPIN": "pharma",       "DIVISLAB": "pharma",
    "TCS": "it",             "INFY": "it",         "WIPRO": "it",
    "HCLTECH": "it",         "TECHM": "it",        "LTIM": "it",
    "DLF": "real_estate",    "GODREJPROP": "real_estate", "OBEROIRLTY": "real_estate",
    "TATAMOTORS": "auto",    "MARUTI": "auto",     "M&M": "auto",
    "BAJAJ-AUTO": "auto",    "HEROMOTOCO": "auto",
}


def _extract_ticker(text: str) -> Optional[str]:
    matches = re.findall(r'\b([A-Z]{2,15}(?:BANK|LTD|IND|AUTO|TECH|PHARMA)?)\b', text)
    stopwords = {"AND","THE","FOR","WITH","SHOW","RUN","SET","GET","NEW","LOAD",
                 "SCAN","BULL","BASE","BEAR","DCF","LLM","WHAT","WHY","HOW",
                 "MY","IS","IN","ON","BY","TO","OF","THESIS","REPORT","NEWS",
                 "SIGNALS","MARKET","DAILY","TODAY","CATALYST","VARIANT"}
    for m in matches:
        if m not in stopwords:
            return m
    return None

def _extract_number(text: str) -> Optional[float]:
    m = re.search(r'[-+]?\d+\.?\d*', text)
    return float(m.group()) if m else None

def _resolve_metric(text: str) -> Optional[str]:
    text_lower = text.lower()
    for alias, canonical in METRIC_ALIASES.items():
        if alias in text_lower:
            return canonical
    return None

def _infer_sector(ticker: str) -> str:
    return SECTOR_TICKER_MAP.get(ticker.upper(), "universal")

def _needs_confirmation(metric: str, current: float, new_value: float) -> bool:
    return abs(new_value - current) > LARGE_CHANGE_THRESHOLDS.get(metric, 5.0)


def parse_intent(
    text: str,
    current_session_id: Optional[str] = None,
    current_ticker:     Optional[str] = None,
    current_assumptions: Optional[dict[str, Any]] = None,
) -> ParsedIntent:
    raw   = text.strip()
    lower = raw.lower()
    ca    = current_assumptions or {}

    # ── New session ───────────────────────────────────────────────────────────
    if any(p in lower for p in ["new session","start session","research ","analyse ","analyze "]):
        ticker = _extract_ticker(raw) or current_ticker
        sector = _infer_sector(ticker) if ticker else "universal"
        return ParsedIntent(action=ACTION_NEW_SESSION, ticker=ticker,
                            raw_input=raw, params={"suggested_sector": sector})

    # ── Load session ──────────────────────────────────────────────────────────
    if any(p in lower for p in ["load session","open session","resume session"]):
        sid = re.search(r'[A-Z]+_\d{8}_\d{6}', raw)
        return ParsedIntent(action=ACTION_LOAD_SESSION,
                            session_id=sid.group() if sid else None,
                            ticker=_extract_ticker(raw) or current_ticker, raw_input=raw)

    # ── Thesis / hypothesis ───────────────────────────────────────────────────
    if any(p in lower for p in ["set thesis","my thesis is","hypothesis is","i think","research question"]):
        thesis_text = re.sub(r'^(set\s+thesis|my\s+thesis\s+is|hypothesis\s+is|i\s+think|research\s+question)\s*[:—-]?\s*', '', lower, flags=re.I).strip()
        return ParsedIntent(action=ACTION_SET_THESIS, raw_input=raw,
                            ticker=current_ticker, params={"thesis": thesis_text or raw})

    if any(p in lower for p in ["what is my thesis","show thesis","my hypothesis","what's my thesis","view thesis"]):
        return ParsedIntent(action=ACTION_SHOW_THESIS, ticker=current_ticker, raw_input=raw)

    # ── Variant view ──────────────────────────────────────────────────────────
    if any(p in lower for p in ["set variant","variant view is","my variant","differ from consensus"]):
        vv_text = re.sub(r'^(set\s+variant(\s+view)?|variant\s+view\s+is|my\s+variant)\s*[:—-]?\s*', '', lower, flags=re.I).strip()
        return ParsedIntent(action=ACTION_SET_VARIANT_VIEW, raw_input=raw,
                            ticker=current_ticker, params={"variant_view": vv_text or raw})

    if any(p in lower for p in ["show variant","what is my variant","view variant"]):
        return ParsedIntent(action=ACTION_SHOW_VARIANT_VIEW, ticker=current_ticker, raw_input=raw)

    # ── Catalysts ─────────────────────────────────────────────────────────────
    if any(p in lower for p in ["add catalyst","log catalyst","catalyst is","upcoming event","key event"]):
        return ParsedIntent(action=ACTION_LOG_CATALYST, raw_input=raw,
                            ticker=current_ticker, params={"description": raw})

    if any(p in lower for p in ["show catalyst","list catalyst","upcoming catalyst","catalysts","what catalyst"]):
        return ParsedIntent(action=ACTION_SHOW_CATALYSTS, ticker=current_ticker, raw_input=raw)

    # ── Assumptions ──────────────────────────────────────────────────────────
    if any(p in lower for p in ["show assumption","current assumption","what are my","list assumption"]):
        return ParsedIntent(action=ACTION_SHOW_ASSUMPTIONS, ticker=current_ticker, raw_input=raw)

    if any(p in lower for p in ["set ","update ","change ","assume "]):
        metric  = _resolve_metric(lower)
        value   = _extract_number(raw)
        confirm = False
        if metric and value is not None:
            confirm = _needs_confirmation(metric, float(ca.get(metric, 0)), value)
        return ParsedIntent(action=ACTION_UPDATE_ASSUMPTION, metric=metric, value=value,
                            requires_confirmation=confirm, ticker=current_ticker,
                            raw_input=raw, params={"reason": raw})

    # ── Scenarios ─────────────────────────────────────────────────────────────
    if any(p in lower for p in ["run scenario","generate scenario","bull bear","scenarios"]):
        return ParsedIntent(action=ACTION_RUN_SCENARIOS, ticker=current_ticker, raw_input=raw)
    if any(p in lower for p in ["show scenario","view scenario","price target"]):
        return ParsedIntent(action=ACTION_SHOW_SCENARIOS, ticker=current_ticker, raw_input=raw)

    # ── News / signals ────────────────────────────────────────────────────────
    if any(p in lower for p in ["scan news","scan events","latest news","what's happening","any signals","why is","why did"]):
        return ParsedIntent(action=ACTION_SCAN_NEWS,
                            ticker=current_ticker or _extract_ticker(raw), raw_input=raw)
    if any(p in lower for p in ["show signal","detected signal","list signal"]):
        return ParsedIntent(action=ACTION_SHOW_SIGNALS, ticker=current_ticker, raw_input=raw)

    # ── Output types ──────────────────────────────────────────────────────────
    if any(p in lower for p in ["market report","daily market","why did market","market moved"]):
        return ParsedIntent(action=ACTION_MARKET_REPORT, raw_input=raw)
    if any(p in lower for p in ["commodity report","gold report","oil report","commodity daily"]):
        return ParsedIntent(action=ACTION_COMMODITY_REPORT, raw_input=raw)
    if any(p in lower for p in ["check alerts","show alerts","any alerts","trigger"]):
        return ParsedIntent(action=ACTION_CHECK_ALERTS, raw_input=raw)
    if any(p in lower for p in ["investor tracking","investor dashboard","fund holdings","pms holdings"]):
        return ParsedIntent(action=ACTION_INVESTOR_REPORT, raw_input=raw)
    if any(p in lower for p in ["politics report","geopolitical","macro report","modi","trump","fed"]):
        return ParsedIntent(action=ACTION_POLITICS_REPORT, raw_input=raw)
    if any(p in lower for p in ["why is","why moving","macro micro","what macro","driving the stock"]):
        return ParsedIntent(action=ACTION_MACRO_MICRO, ticker=current_ticker, raw_input=raw)

    # ── Report ────────────────────────────────────────────────────────────────
    if any(p in lower for p in ["generate report","write report","create report","full report","research note"]):
        return ParsedIntent(action=ACTION_GENERATE_REPORT, ticker=current_ticker, raw_input=raw)

    # ── Rollback / history ────────────────────────────────────────────────────
    if any(p in lower for p in ["rollback","undo","revert","go back"]):
        idx = _extract_number(raw)
        return ParsedIntent(action=ACTION_ROLLBACK, params={"index": int(idx) if idx is not None else -1},
                            raw_input=raw, requires_confirmation=True)
    if any(p in lower for p in ["show history","assumption history","what changed","changes"]):
        return ParsedIntent(action=ACTION_SHOW_HISTORY, ticker=current_ticker, raw_input=raw)

    # ── Sources / guardrails ──────────────────────────────────────────────────
    if any(p in lower for p in ["show source","data source","sources used"]):
        return ParsedIntent(action=ACTION_SHOW_SOURCES, ticker=current_ticker, raw_input=raw)
    if any(p in lower for p in ["guardrail","show limits","breach"]):
        return ParsedIntent(action=ACTION_SHOW_GUARDRAILS, ticker=current_ticker, raw_input=raw)

    # ── Reverse DCF ───────────────────────────────────────────────────────────
    if any(p in lower for p in ["reverse dcf","implied growth","market pricing","what growth"]):
        return ParsedIntent(action=ACTION_REVERSE_DCF, ticker=current_ticker, raw_input=raw)

    return ParsedIntent(action=ACTION_UNKNOWN, text_query=raw,
                        ticker=current_ticker, raw_input=raw)


def describe_intent(intent: ParsedIntent) -> str:
    a = intent.action
    if a == ACTION_NEW_SESSION:
        return f"Start new session for {intent.ticker}. Suggested sector: {intent.params.get('suggested_sector','universal')}."
    if a == ACTION_UPDATE_ASSUMPTION:
        return (f"Update {intent.metric} → {intent.value}."
                + (" ⚠️ Large change — confirm." if intent.requires_confirmation else ""))
    if a == ACTION_SET_THESIS:
        return f"Set thesis: {intent.params.get('thesis','')[:80]}"
    if a == ACTION_LOG_CATALYST:
        return f"Log catalyst: {intent.params.get('description','')[:80]}"
    if a == ACTION_RUN_SCENARIOS:
        return f"Run Bull/Base/Bear scenarios for {intent.ticker}."
    if a == ACTION_GENERATE_REPORT:
        return f"Generate full research report for {intent.ticker}."
    if a == ACTION_ROLLBACK:
        return f"Roll back assumptions to index {intent.params.get('index')}. ⚠️ Overwrites current."
    if a == ACTION_SCAN_NEWS:
        return f"Scan latest news for {intent.ticker} signals."
    return f"Action: {a}"
