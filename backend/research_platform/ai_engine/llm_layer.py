"""
ai_engine/llm_layer.py
────────────────────────
Layer 13 — Summary + Decision Layer (Brain 2).

The LLM layer ONLY:
  - Interprets pre-tagged signals (never raw text)
  - Explains every conclusion with source references
  - Generates the three-section research report
  - Uses llm_cache.json to avoid repeat API calls on identical content

Brain 2 NEVER does math. All numbers come from Brain 1.
The LLM reads finished assumptions and explains WHY.

From the document:
  "Three-section report: Moat Analysis / Earnings Model / DCF Valuation"
  "LLM explains every conclusion with source reference"
  "llm_cache.json prevents repeat API calls on same content"
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional

import requests
from loguru import logger

from ai_engine.session_manager import ResearchSession

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL     = "claude-sonnet-4-20250514"


def _cache_key(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def _call_llm(
    prompt: str,
    system: str,
    session: ResearchSession,
    cache_key_suffix: str = "",
    max_tokens: int = 2000,
) -> str:
    """
    Call Claude API with caching.
    Same content → returns cached response without API call.
    """
    ck = _cache_key(prompt + cache_key_suffix)
    cached = session.get_llm_cache(ck)
    if cached:
        logger.debug(f"[llm_layer] Cache hit: {ck[:12]}")
        return cached

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("[llm_layer] ANTHROPIC_API_KEY not set — returning placeholder.")
        return f"[LLM output placeholder — set ANTHROPIC_API_KEY to enable]\nPrompt: {prompt[:200]}"

    headers = {
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    body = {
        "model":      DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "system":     system,
        "messages":   [{"role": "user", "content": prompt}],
    }
    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        output = resp.json()["content"][0]["text"]
        session.set_llm_cache(ck, output)
        return output
    except Exception as exc:
        logger.error(f"[llm_layer] API call failed: {exc}")
        return f"[LLM call failed: {exc}]"


# ── Signal interpretation ─────────────────────────────────────────────────────

def interpret_signals(
    session: ResearchSession,
    signals: list[dict[str, Any]],
    ticker: str,
    sector: str,
) -> str:
    """
    Brain 2: interpret pre-tagged signals and explain assumption impacts.
    Input: structured signal dicts from signal_detector (NOT raw text).
    Output: natural language explanation with source references.
    """
    if not signals:
        return "No signals detected in the current data set."

    signals_json = json.dumps(signals, indent=2, default=str)
    prompt = f"""You are analysing pre-detected financial signals for {ticker} ({sector} sector).

These signals were identified by a deterministic keyword filter from news and data sources.
Your job is to explain what each signal means for the investment thesis — not to detect new signals.

Signals detected:
{signals_json}

For each signal:
1. State what event occurred (cite the source_name)
2. Explain the transmission chain: how does this signal affect the company's financials?
3. State whether this strengthens or weakens the investment case
4. Flag any signals that require urgent human review

Keep each signal explanation to 2-3 sentences. Be specific about numbers where available.
Format: plain text, one paragraph per signal."""

    system = (
        "You are a senior equity research analyst. You explain financial signals clearly "
        "and concisely with source references. You never make up numbers — only use what "
        "is provided in the signals JSON. You never do DCF calculations — that is handled separately."
    )
    return _call_llm(prompt, system, session, cache_key_suffix=ticker)


# ── Three-section research report ─────────────────────────────────────────────

def generate_section_moat(
    session: ResearchSession,
    ticker: str,
    sector: str,
    insights: list[dict[str, Any]],
) -> str:
    """Section 1: Moat / Business Quality Analysis."""
    prompt = f"""Write the Business Quality & Moat section of an equity research note for {ticker} ({sector}).

Available signals and insights:
{json.dumps(insights[:20], indent=2, default=str)}

Cover:
- What is the company's competitive advantage (cost, brand, switching costs, network effect)?
- Is the moat strengthening or eroding based on recent signals?
- Key risks to the moat

Length: 150-200 words. Cite the source_name for each claim."""

    system = "Senior equity analyst writing institutional research. Factual, concise, source-cited."
    return _call_llm(prompt, system, session, cache_key_suffix=f"{ticker}_moat")


def generate_section_earnings(
    session: ResearchSession,
    ticker: str,
    sector: str,
    assumptions: dict[str, Any],
    assumption_history: list[dict[str, Any]],
) -> str:
    """Section 2: Earnings Model commentary."""
    recent_changes = [
        h for h in assumption_history[-10:]
        if "metric" in h and h.get("metric") not in
        ("_updated_at", "_initialized_at", "_session_id")
    ]
    prompt = f"""Write the Earnings Model section of an equity research note for {ticker}.

Current model assumptions:
{json.dumps({k: v for k, v in assumptions.items() if not k.startswith('_')}, indent=2, default=str)}

Recent assumption changes (with reasons):
{json.dumps(recent_changes, indent=2, default=str)}

Cover:
- Key revenue growth driver and your confidence in it
- Margin trajectory and what could cause upside/downside
- Any assumption changes made this session and why

Length: 150-200 words. Every claim must reference a reason from the assumption changes above."""

    system = "Senior equity analyst. Explains earnings model changes clearly. Never invents data."
    return _call_llm(prompt, system, session, cache_key_suffix=f"{ticker}_earnings")


def generate_section_valuation(
    session: ResearchSession,
    ticker: str,
    scenarios: dict[str, Any],
    current_price: Optional[float],
) -> str:
    """Section 3: DCF Valuation summary."""
    prompt = f"""Write the Valuation section of an equity research note for {ticker}.

Current market price: {current_price or 'Not available'}

Scenario outputs:
{json.dumps(scenarios.get('scenarios', {}), indent=2, default=str)}

Reverse DCF (market's implied assumptions):
{json.dumps(scenarios.get('reverse_dcf', {}), indent=2, default=str)}

Cover:
- Bull/Base/Bear price targets and the single key bet in each scenario
- What growth rate is the current market price implying (reverse DCF)?
- Is the market pricing too much optimism or too much pessimism?
- Your rating and primary catalyst for re-rating

Length: 150-200 words."""

    system = "Senior equity analyst. Interprets DCF outputs. Clear buy/hold/sell reasoning."
    return _call_llm(prompt, system, session, cache_key_suffix=f"{ticker}_valuation")


# ── Full report assembler ─────────────────────────────────────────────────────

def generate_full_report(
    session: ResearchSession,  # llm_cache.json prevents repeat API calls — see _call_llm()
    ticker: str,
    sector: str,
) -> str:
    """
    Assemble the complete three-section research report.
    Reads all session files to build context — no external calls for data.
    """
    from ai_engine.version_control import get_assumption_history

    assumptions   = session.get_assumptions()
    scenarios     = session.get_scenarios()
    insights      = _read_json_list(session.insights_file)
    sources       = _read_json_list(session.sources_file)
    hist          = get_assumption_history(session)
    current_price = assumptions.get("current_price_inr")
    base_rating   = scenarios.get("scenarios", {}).get("base", {}).get("rating", "hold").upper()
    base_target   = scenarios.get("scenarios", {}).get("base", {}).get("price_per_share")
    bull_target   = scenarios.get("scenarios", {}).get("bull", {}).get("price_per_share")
    bear_target   = scenarios.get("scenarios", {}).get("bear", {}).get("price_per_share")

    moat_section      = generate_section_moat(session, ticker, sector, insights)
    earnings_section  = generate_section_earnings(session, ticker, sector, assumptions, hist)
    valuation_section = generate_section_valuation(session, ticker, scenarios, current_price)

    source_list = "\n".join(
        f"- {s.get('name', '?')} ({s.get('source_type', '?')}) [{s.get('timestamp','')[:10]}]"
        for s in sources[:15]
    )

    report = f"""# {ticker} — Equity Research Note
**Sector:** {sector.title()} | **Rating:** {base_rating} | **Session:** {session.session_id}

---

## 1. Business Quality & Moat

{moat_section}

---

## 2. Earnings Model

{earnings_section}

---

## 3. Valuation

{valuation_section}

---

## Price Targets

| Scenario | Price Target | Upside |
|----------|-------------|--------|
| Bull     | ₹{bull_target or 'N/A'} | {scenarios.get('scenarios',{}).get('bull',{}).get('upside_pct','?')}% |
| Base     | ₹{base_target or 'N/A'} | {scenarios.get('scenarios',{}).get('base',{}).get('upside_pct','?')}% |
| Bear     | ₹{bear_target or 'N/A'} | {scenarios.get('scenarios',{}).get('bear',{}).get('upside_pct','?')}% |

Current price: ₹{current_price or 'N/A'}

---

## Data Sources Used

{source_list}

---
*Generated by research_platform · Session {session.session_id}*
"""
    session.write_summary(report)
    session.audit("report_generated", f"Full research report generated for {ticker}")
    return report


def _read_json_list(path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []
