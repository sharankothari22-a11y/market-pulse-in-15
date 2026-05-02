# Beaver Intelligence — Wiring Audit
**Audit Date:** 2026-05-01  
**Auditor:** Claude Sonnet 4.6 (read-only)  
**Scope:** Full stack — backend routes, AI engine modules, all frontend pages and panels

---

## Summary Table

> Sorted: 🔴 STUB first, then 🟡 PARTIAL, then ✅ WIRED, then ⏸️ COMING SOON

| Page | Element | Status | Notes |
|---|---|---|---|
| Market | News feed (mockData.js `newsSignals`) | 🔴 STUB | `mockData.js` defines `newsSignals` but `NewsFeed.jsx` calls `/api/news` — however signals page doesn't use the real API feed |
| Signals | Signal feed content | 🔴 STUB | `/api/signals` tries DB (SQLAlchemy), DB almost certainly unavailable → returns `{"signals": []}` every time; no fallback data shown |
| Macro | Global Events | 🔴 STUB | `/api/macro` tries DB (SQLAlchemy); DB likely unavailable → returns `[]`; `macroData.js` mock exists but is NOT used |
| Macro | Economic Indicators (FRED) | 🔴 STUB | Same as above — DB path required; no yfinance fallback for FRED data |
| Research | Guardrail Log panel | 🔴 STUB | Reads `guardrail_log.json` from RP session; this file is never written during the `analyze` pipeline in `server.py` |
| Research | Assumption History panel | 🔴 STUB | Reads `assumptions_history.json`; only written if RP scenarios run AND assumption engine is called interactively — never called during `POST /analyze` |
| Research | Insider Trades panel | 🔴 STUB | `/api/insider-trades` tries DB `Event` table with `entity_type=insider_trade`; DB unavailable → always `{"trades": []}` |
| Research | F&O Analytics panel | ⏸️ COMING SOON | Panel renders "Q3 2026" placeholder; `/api/derivatives/{ticker}` exists but panel doesn't call it |
| Market | FII/DII chart + tiles | 🟡 PARTIAL | Live NSE fetch attempted; `fii_net/dii_net` wired; `change_percent` always 0 (Frankfurter doesn't return day-over-day change) |
| Market | FX rates (6 tiles) | 🟡 PARTIAL | Rate values real (Frankfurter API); `change_percent` always 0.0 (not fetched) |
| Market | Commodities (4 cards) | 🟡 PARTIAL | Price + `change_pct` real via yfinance; only 4 of 5 symbols displayed (NG=F excluded by `COMMODITY_LABELS` in UI) |
| Research | Valuation panel | 🟡 PARTIAL | `base.price_per_share` comes from Excel P30 (real DCF); `upside_pct` and `rating` derived from P30 vs current price (real); `revenue_growth`/`ebitda_margin`/`wacc` sub-fields shown as ConfChips — real if scenarios ran, else from yfinance sector defaults |
| Research | Score (5-dim) panel | 🟡 PARTIAL | All 5 dimension scores computed in `scoring.py` from yfinance actuals + sector defaults; composite score real; `business_quality` field present in scoring object but NOT in `SCORE_DIMS` array — never rendered |
| Research | Factor Scores panel | 🟡 PARTIAL | Derived in frontend from `scoring` object (momentum/value/quality/macro); real when `scoring` is present; falls back to API `/api/research/{id}/factors` which maps same scoring fields |
| Research | SWOT panel | 🟡 PARTIAL | `swot.py` generates lists using scoring + sector framework JSON; items tagged FACT/ASSUMPTION/INTERPRETATION; relies on sector defaults when financial data thin |
| Research | Porter's Five Forces | 🟡 PARTIAL | `porter.py` generates from sector defaults + assumptions; rating is real sector logic but rationale is templated text, not LLM |
| Research | Financial Charts | 🟡 PARTIAL | 6 charts generated via matplotlib + yfinance; real data when yfinance works; silently returns fewer charts if individual chart generation fails |
| Research | Peer Comparison | 🟡 PARTIAL | Fetches P/E, EV/EBITDA, ROE via yfinance for sector peers; real when yfinance works; peer list is hardcoded sector map (`PEER_MAP`) not dynamic |
| Research | 5-Year Forecast panel | 🟡 PARTIAL | Reads `dcf_summary.forecast` from papermill notebook output JSON; real when notebook runs successfully; shows "next release" if notebook failed |
| Research | Sensitivity heatmap | 🟡 PARTIAL | Real WACC×terminal_growth matrix from `scenario_engine.py`; shows "next release" if RP scenarios failed |
| Research | Reverse DCF panel | 🟡 PARTIAL | `implied_growth_rate`, `implied_wacc`, `market_cap` from `scenario_engine.py`; real when RP available |
| Research | Audit Trail panel | 🟡 PARTIAL | Reads `audit_log.json` and `sources.json` from RP session dir; pipeline does write audit events; sources defaults to `[{api_name: "yfinance", status: "ok"}]` when sources.json absent |
| Research | Sources Tracker panel | 🟡 PARTIAL | Same `/api/research/{id}/audit` call as Audit Trail; sources real when RP session exists |
| Research | HTML Report download | 🟡 PARTIAL | Template `Beaver_ER_Template_Pro_Forest.html` populated with real DCF numbers, yfinance company data, and Claude LLM commentary; LLM commentary absent if `ANTHROPIC_API_KEY` not set |
| Research | MD download | 🟡 PARTIAL | Returns `summary.md` from RP session dir (written by `analyze` pipeline); fallback minimal MD generated from scoring if file absent |
| Research | Excel DCF download | 🟡 PARTIAL | Triggers papermill notebook; downloads `.xlsm` output; depends on notebook completing within 10-min timeout; polling UI present |
| Signals | Sector tabs (All/High/Banking/IT/…) | 🟡 PARTIAL | Tabs wired to filter `signals` array from API; works correctly when signals array is non-empty; currently always empty (DB unavailable) |
| Signals | Summary bar (count badges) | 🟡 PARTIAL | Counts derived from `signals` array; correctly updates when data flows; currently always 0 |
| Macro | Live Market Indices (NIFTY/SENSEX/Global) | 🟡 PARTIAL | Fetched from `/api/macro` → `indicators` array; filtered by `INDEX_IDS`; populated only if DB has `MacroIndicator` rows — otherwise empty skeleton shown |
| TopBar | NIFTY 50 / SENSEX chips | ✅ WIRED | Calls `/api/market/overview`; reads `nifty.raw_value`, `nifty.change_percent`, etc.; yfinance + cache fallback; refreshes every 60s |
| TopBar | IST clock | ✅ WIRED | Client-side `setInterval(1s)` — always live |
| TopBar | Last refresh timestamp | ✅ WIRED | Set on each successful `/api/market/overview` fetch |
| Market | Top Movers table | ✅ WIRED | yfinance → `fetch_nse_movers_safe()` → `top_movers` array; Twelve Data fallback; skeleton fallback |
| Market | Status strip (NSE hours + refresh time) | ✅ WIRED | Refresh timestamp from state; NSE hours text is static but accurate |
| Market | News feed (NewsFeed component) | ✅ WIRED | `/api/news` → RSS scrape from ET Markets + Mint → real article titles, URLs, timestamps |
| Market | Ticker hero input | ✅ WIRED | Routes to `/research` page and triggers `POST /api/research/analyze` |
| Research | Company header (ticker, price, change%) | ✅ WIRED | `current_price` + `change_pct` from yfinance via `analyze` and `_enrich_with_live_price` |
| Research | Download Report button | ✅ WIRED | `GET /api/research/{id}/report/download` — returns template HTML populated with real data |
| Research | Sector Callout strip | ✅ WIRED | `/api/research/sector/{sector}` reads framework `signals.json` files; key drivers and valuation focus real |
| Research | Risk Flags panel | ✅ WIRED | Reads `guardrail_breaches` from session response; when no breaches, shows "All checks passed" — correctly wired even when empty |
| Research | Chat panel (Beaver AI) | ✅ WIRED | `POST /api/chat/message` → Claude Sonnet via Anthropic SDK; returns real LLM response; 503 when `ANTHROPIC_API_KEY` missing |
| Splash | Logo + progress bar | ✅ WIRED | 10-second timer, client-side only, no API dependency |
| Research | XLSX audit export | ✅ WIRED | `/api/research/{id}/report/xlsx` — prefers 6-sheet RP export, falls back to openpyxl simple sheet; always returns a file |

---

## Section 1: AI Engine Modules (L01–L17)

| ID | Filename | One-line purpose | Invoked in /analyze? | Output in response JSON | Frontend consumer |
|---|---|---|---|---|---|
| L01 | `session_manager.py` | Creates and manages per-company session folders with all metadata and JSON files | Yes — `rp_new_session()` is the first RP call | `session_id`, `rp_session_id` | All panels (session ID used to fetch sub-resources) |
| L02 | `scenario_engine.py` | Runs Bull/Base/Bear DCF scenarios + WACC×growth sensitivity matrix | Yes — `rp_run_scenarios()` called after assumptions built | `scenarios` (bull/base/bear), `sensitivity` (matrix), `reverse_dcf` | ValuationPanel, SensitivityPanel, ReverseDcfPanel |
| L03 | `scoring.py` | 5-dimension scoring (financial_strength, growth_quality, valuation_attractiveness, risk_score, market_positioning) + composite | Yes — `rp_score_session()` called after scenarios | `scoring` object with all 5 dims + composite + recommendation | ScorePanel, FactorScoresPanel |
| L04 | `swot.py` | Generates 4-quadrant SWOT from scoring + sector framework + assumptions | Yes — `rp_generate_swot()` called with scoring result | `swot` (strengths/weaknesses/opportunities/threats arrays) | SWOTPanel.jsx |
| L05 | `porter.py` | Generates Porter's Five Forces ratings (Low/Medium/High) from sector framework + assumptions | Yes — `rp_generate_porter()` called after scoring | `porter` (dict of 5 forces with rating + rationale) | PorterPanel.jsx |
| L06 | `signal_detector.py` | Hybrid keyword+pattern signal detection from sector context and news headlines | Yes — `rp_detect_signals()` called with sector text + news | `signals` (list of signal dicts) | Not directly rendered; feeds factor_engine |
| L07 | `factor_engine.py` | Maps detected signals to DCF assumption deltas (e.g., "oil +15% → EBITDA margin -2%") | Yes — `rp_signals_to_factors()` called after signal detection | `factor_deltas` (list of factor delta dicts) | Not currently rendered in any visible panel |
| L08 | `assumption_engine.py` | Translates factor deltas to DCF inputs with guardrail enforcement and history logging | **No** — NOT called in `POST /analyze`; only called if someone uses the interactive chat/CLI workflow | n/a (file never writes `guardrail_log.json` or `assumptions_history.json` during analyze) | GuardrailPanel and AssumptionHistoryPanel (both empty as a result) |
| L09 | `audit_export.py` | Exports session data to Excel (.xlsx) and HTML report; also provides `get_full_audit()` | Partially — `rp_export_excel()` called in report download; `get_full_audit()` called during analyze to populate `audit_trail` | `audit_trail` (list of audit entries in analyze response); xlsx file at report endpoint | AuditPanel, SourcesPanel |
| L10 | `pdf_builder.py` | Generates 2-page A4 print-ready HTML report from session data | Partially — `rp_build_report()` is fallback #2 in `/report/download` if template fails | HTML file on disk | "Download Report" button (fallback path) |
| L11 | `confidence_scorer.py` | Tags each assumption High/Medium/Low confidence based on source quality and recency | **No** — not called in `POST /analyze`; `_confidence_tags` in assumptions dict are set statically to "medium" in `_build_rp_assumptions()` | `assumption_confidence` dict (all "medium") | ConfChip badges in ValuationPanel |
| L12 | `dcf_bridge.py` | Builds live assumption inputs from DB, writes `assumptions.json`, reads DCF results back | **No** — explicitly bypassed in server.py comment: "Build assumptions WITHOUT the DB-dependent dcf_bridge" | n/a | n/a |
| L13 | `version_control.py` | Snapshot hashing + assumption rollback + cross-session data drift detection | **No** — not imported or called anywhere in server.py | n/a | n/a |
| L14 | `llm_layer.py` | Claude LLM integration for interpreting tagged signals and generating research commentary | **No** — not called in analyze pipeline; LLM commentary in reports goes through `generate_report_commentary()` inline in server.py | n/a | HTML Report commentary (via inline server.py code, not this module) |
| L15 | `output_engine.py` | Generates 6 output types (market report, commodity report, alerts, company deep-dive, investor tracking, macro) | **No** — not imported in server.py | n/a | n/a |
| L16 | `intent_parser.py` | Parses natural language user intents (new session, update assumption, show report, etc.) | **No** — not imported in server.py; used only in `chat_app.py` Streamlit interface | n/a | n/a |
| L17 | `chat_app.py` | Streamlit chat interface for interactive research sessions | **No** — standalone Streamlit app, not part of FastAPI server | n/a | n/a |

**Summary:** 7 of 17 modules are invoked in the analyze pipeline (L01–L07, L09 partially). L08/L11–L17 are either bypassed, not imported, or standalone. The two most consequential bypasses are `dcf_bridge.py` (L12, DB-dependent) and `assumption_engine.py` (L08, guardrail writer).

---

## Section 2: Research Page Panels

### Panel: Company Header
- **Backend route/field:** `POST /api/research/analyze` → `ticker`, `current_price`, `change_pct`, `sector`, `session_id`, `status`
- **Status:** ✅ WIRED
- **Evidence:** `ResearchSession.jsx:99-213` reads `researchData.ticker`, `livePrice` (from `researchData.current_price`), `liveChangePct`

---

### Panel: Valuation (base scenario hero + bull/bear secondary)
- **Backend route/field:** `POST /api/research/analyze` → `response["scenarios"]["base"]["price_per_share"]`, `upside_pct`, `rating`
- **Status:** 🟡 PARTIAL
- **Real fields:** `price_per_share` = Excel P30 (DCF sheet of papermill notebook); `upside_pct` derived from P30 vs yfinance price; `rating` (BUY/HOLD/SELL) derived from upside threshold
- **Hardcoded/conditional:** `revenue_growth`, `ebitda_margin`, `wacc` shown as ConfChips — real from `scenario_engine.py` if RP ran; all ConfChip confidence levels always "medium" (L11 bypassed)
- **Evidence:** `server.py:1506-1540` (P30 wiring); `ResearchSession.jsx:234-343` (ValuationPanel)

---

### Panel: Score (5-dimension composite)
- **Backend route/field:** `POST /api/research/analyze` → `response["scoring"]` object
- **Status:** 🟡 PARTIAL
- **Real fields:** `composite_score`, `recommendation`, `financial_strength`, `growth_quality`, `valuation_attractiveness`, `risk_score`, `market_positioning`
- **Missing:** `business_quality` is in the scoring object but NOT in `SCORE_DIMS` array at `ResearchSession.jsx:396-402` — never rendered
- **Evidence:** `server.py:1197-1215` (scoring computation); `ResearchSession.jsx:396-496`

---

### Panel: Factor Scores
- **Backend route/field:** `POST /api/research/analyze` → `factor_scores` (4-bucket object); fallback: `GET /api/research/{id}/factors`
- **Status:** 🟡 PARTIAL
- **Real fields:** momentum, value, quality, macro — all derived from scoring dimensions
- **Note:** Frontend derives these client-side from `scoring` prop first; API call skipped if scoring available
- **Evidence:** `server.py:1448-1456`; `ResearchSession.jsx:1251-1327`

---

### Panel: SWOT
- **Backend route/field:** `GET /api/research/{session_id}/swot` → strengths/weaknesses/opportunities/threats arrays
- **Status:** 🟡 PARTIAL
- **Real fields:** All 4 quadrants generated by `swot.py` using sector defaults + scoring data; items tagged FACT/ASSUMPTION/INTERPRETATION
- **Limitations:** When scoring unavailable, items fall back to sector-default boilerplate. LLM interpretation not used.
- **Evidence:** `server.py:1778-1805`; `SWOTPanel.jsx`; `ai_engine/swot.py`

---

### Panel: Porter's Five Forces
- **Backend route/field:** `GET /api/research/{session_id}/porter` → forces array with name/rating/comment
- **Status:** 🟡 PARTIAL
- **Real fields:** Force names, ratings (Low/Medium/High) from sector defaults in `porter.py`
- **Limitations:** Rationale is templated text from sector framework, not LLM-generated. `tag` field (FACT/ASSUMPTION) present in source but not rendered in `PorterPanel.jsx` (renders `f.tag` only in Basis column, which is sparse)
- **Evidence:** `server.py:1808-1851`; `PorterPanel.jsx`

---

### Panel: Sensitivity Heatmap
- **Backend route/field:** `POST /api/research/analyze` → `response["sensitivity"]` → `wacc_grid`, `terminal_growth_range`, `matrix`
- **Status:** 🟡 PARTIAL
- **Real fields:** Full WACC×terminal_growth matrix from `scenario_engine.py`
- **Empty state:** Shows "Sensitivity analysis in the next release" if `rp_scenarios` is None (RP unavailable or failed)
- **Evidence:** `server.py:1444-1445`; `ResearchSession.jsx:498-614`

---

### Panel: 5-Year Forecast
- **Backend route/field:** `POST /api/research/analyze` → `response["dcf_summary"]["forecast"]` (from papermill output JSON)
- **Status:** 🟡 PARTIAL
- **Real fields:** year, revenue, ebit, fcff, revenue_growth — from `DCF_Output_{TICKER}_INR.summary.json`
- **Empty state:** Shows "5-year forecast in the next release" if notebook didn't run or JSON not found
- **Evidence:** `server.py:1499-1503`, `_load_dcf_summary()` at line 1986; `ResearchSession.jsx:617-673`

---

### Panel: Peer Comparison
- **Backend route/field:** `GET /api/research/{session_id}/peers` → array of {ticker, name, pe_fy25e, ev_ebitda, roe}
- **Status:** 🟡 PARTIAL
- **Real fields:** P/E (`trailingPE`/`forwardPE`), EV/EBITDA, ROE from yfinance
- **Hardcoded:** Peer selection is from hardcoded `PEER_MAP` dict keyed by sector name — not dynamic
- **Evidence:** `server.py:2568-2583` (PEER_MAP), `4367-4399`; `ResearchSession.jsx:1148-1247`

---

### Panel: Financial Charts
- **Backend route/field:** `GET /api/research/{session_id}/charts` → charts array with `name`, `type`, `image_base64`
- **Status:** 🟡 PARTIAL
- **Real charts:** Price History (1Y), Revenue (3Y), EBITDA Margin, Net Margin, Revenue Growth YoY, Volume (3M) — all from yfinance
- **Failure behavior:** Each chart silently skipped if yfinance data absent; returns fewer than 6 charts or empty array
- **Evidence:** `server.py:4153-4333`; `ResearchSession.jsx:1102-1145`

---

### Panel: Sources Tracker
- **Backend route/field:** `GET /api/research/{session_id}/audit` → `sources` array
- **Status:** 🟡 PARTIAL
- **Real fields:** `api_name`, `endpoint`, `fetched_at`, `status` from `sources.json` in RP session dir
- **Fallback:** When `sources.json` absent, synthesizes a single `{api_name: "yfinance", status: "ok"}` entry
- **Evidence:** `server.py:3661-3690`; `ResearchSession.jsx:871-933`

---

### Panel: Guardrail Log
- **Backend route/field:** `GET /api/research/{session_id}/guardrails` → `guardrails` array, `all_passed` bool
- **Status:** 🔴 STUB
- **Why stub:** `assumption_engine.py` (L08) is NOT called during `POST /analyze`. Nothing writes `guardrail_log.json`. Every session returns `{guardrails: [], all_passed: true}`.
- **Evidence:** `server.py:3693-3698`; `ai_engine/assumption_engine.py` (never imported in server.py)

---

### Panel: Assumption History
- **Backend route/field:** `GET /api/research/{session_id}/assumption_history` → `history` array
- **Status:** 🔴 STUB
- **Why stub:** `assumptions_history.json` is written by `assumption_engine.py` (L08) which is never called. Array always empty.
- **Evidence:** `server.py:3701-3706`

---

### Panel: Audit Trail
- **Backend route/field:** `GET /api/research/{session_id}/audit` → `audit_log` array
- **Status:** 🟡 PARTIAL
- **Real data:** `audit_log.json` IS written during `analyze` (session_created, scoring_complete, signals_detected, factors_mapped, swot_generated, porter_generated, pipeline_complete events). However `fields_changed` is always empty since these are milestone events not field updates.
- **Evidence:** `server.py:1271-1291`; `ResearchSession.jsx:793-855`

---

### Panel: Excel DCF Download
- **Backend route/field:** `POST /api/research/{id}/dcf/run` → `GET /api/research/{id}/dcf/status` (poll) → `GET /api/research/{id}/dcf/output.xlsm`
- **Status:** 🟡 PARTIAL
- **Real:** Papermill executes `DCF_Multi_Source_Pipeline_REFACTORED.ipynb`; real Excel with DCF model
- **Risk:** Depends on papermill + notebook available; 10-minute timeout; ticker cell patching required. If notebook fails, UI shows "Retry Excel".
- **Evidence:** `server.py:2279-2415`; `ResearchSession.jsx:1571-1605`

---

### Panel: HTML Report Download
- **Backend route/field:** `GET /api/research/{session_id}/report/download`
- **Status:** 🟡 PARTIAL
- **Tier 1 (main):** Populates `Beaver_ER_Template_Pro_Forest.html` with real DCF numbers + yfinance data + Claude LLM commentary (if `ANTHROPIC_API_KEY` set)
- **Missing when ANTHROPIC_KEY absent:** All LLM text sections (thesis, exec summary, rationale, drivers, risks, kill switch) render as "—"
- **Evidence:** `server.py:2945-3343`

---

### Panel: MD Download
- **Backend route/field:** `GET /api/research/{session_id}/report/markdown`
- **Status:** 🟡 PARTIAL
- **Real:** Returns `summary.md` from RP session dir (written during `analyze` pipeline); real scoring, SWOT, Porter, scenarios
- **Fallback:** Minimal generated MD if `summary.md` absent
- **Evidence:** `server.py:3613-3658`

---

### Panel: Anthropic Chat Panel
- **Backend route/field:** `POST /api/chat/message`
- **Status:** ✅ WIRED (when `ANTHROPIC_API_KEY` configured)
- **Real:** Claude Sonnet (`claude-sonnet-4-20250514`) with equity research system prompt; `session_id` passed in request body but NOT currently used by the backend (not read from request in `chat_message` handler — only `message` field used)
- **Note:** Session context not injected into chat prompt — Beaver AI has no knowledge of current analysis
- **Evidence:** `server.py:4114-4146`; `ChatPanel.jsx:59-70`

---

### Panel: Insider Trades
- **Backend route/field:** `GET /api/insider-trades?ticker=X`
- **Status:** 🔴 STUB
- **Why stub:** Requires `research_platform.database` SQLAlchemy connection (`Event` table with `entity_type=insider_trade`); DB consistently unavailable → always `{"trades": []}`
- **Evidence:** `server.py:3983-4050`; `ResearchSession.jsx:1329-1387`

---

## Section 3: Market Page

### FX Rates (5 tile grid)
- **Route:** `GET /api/market/overview` → `fx` dict
- **Source:** Frankfurter API (`https://api.frankfurter.app/latest?from=INR`)
- **Status:** 🟡 PARTIAL — rate values are real; `change_percent` always 0.0 (Frankfurter returns only current rate, not previous day)
- **Tiles shown:** CNYINR, EURINR, GBPINR, JPYINR, SGDINR (5 of 6 — USDINR would be 6th but UI takes `slice(0,5)`)
- **Evidence:** `server.py:454-486`; `MarketOverview.jsx:613`

### Top Movers Table (10 rows)
- **Route:** `GET /api/market/overview` → `top_movers` array
- **Source:** yfinance `Tickers` batch → Twelve Data fallback → Mongo cache → skeleton
- **Status:** ✅ WIRED — symbol, LTP, change%, volume all real when yfinance accessible
- **Evidence:** `server.py:318-415`; `MarketOverview.jsx:616`

### FII/DII Chart + Net Tiles
- **Route:** `GET /api/market/overview` → `fii_dii` array
- **Source:** NSE `fiidiiTradeReact` API (with cookie bootstrap) → Mongo cache → zero-filled skeleton
- **Status:** 🟡 PARTIAL — `fii_net`/`dii_net` in ₹ Cr are real; 14-day rolling history maintained; `nifty_close` always 0 (not fetched)
- **Evidence:** `server.py:604-687`; `MarketOverview.jsx:79-96`

### Commodities (4 cards)
- **Route:** `GET /api/market/overview` → `commodities` array
- **Source:** yfinance (GC=F, SI=F, CL=F, BZ=F, NG=F)
- **Status:** 🟡 PARTIAL — 5 symbols fetched but `COMMODITY_LABELS` in UI only maps 4 (NG=F excluded); prices real when yfinance works
- **Evidence:** `server.py:490-538`; `MarketOverview.jsx:19-24`, `610-612`

### News Feed
- **Route:** `GET /api/news?limit=10` (NewsFeed calls `/api/news`)
- **Source:** ET Markets + Mint RSS feeds scraped via httpx
- **Status:** ✅ WIRED — real article titles, URLs, publication timestamps
- **Evidence:** `server.py:542-579`; `NewsFeed.jsx:45-59`

---

## Section 4: Signals Page

### Signal Feed
- **Route:** `GET /api/signals`
- **Source:** SQLAlchemy `Event` table (type IN ["signal", "regulatory"]) → `signals_out` list
- **Status:** 🔴 STUB — DB (`research_platform.database`) unavailable → returns `{"signals": []}` every call; no fallback data
- **Evidence:** `server.py:3760-3798`

### Sector Tabs (All / High Priority / Banking / IT / Petroleum / Pharma / FMCG)
- **Status:** 🟡 PARTIAL — tab logic correctly filters the `signals` array by `sector` field and `severity`; correctly designed; currently always shows "No signals in this category" because array is empty
- **Evidence:** `SignalsAlerts.jsx:7-24`

### Summary Bar (signal count, bullish/bearish/warning badges)
- **Status:** 🟡 PARTIAL — correctly counts from `signals` array; shows "0 signals / 0 bullish / 0 bearish / 0 warnings" because array empty
- **Evidence:** `SignalsAlerts.jsx:84-124`

### Active Alerts section
- **Status:** ⏸️ COMING SOON — intentionally removed per commit `5f81f9a`; `activeAlerts` still in `mockData.js` but not rendered

---

## Section 5: Macro Page

### Live Market Indices (NIFTY/SENSEX/Global — 6 tiles)
- **Route:** `GET /api/macro` → `indicators` array filtered by `INDEX_IDS`
- **Source:** SQLAlchemy `MacroIndicator` table → fallback to `FxRate` table
- **Status:** 🔴 STUB (effectively) — DB unavailable → `indicators: []`; filtered list is empty; skeleton pulse animation shown indefinitely
- **Note:** There is an inconsistency: `/api/market/overview` fetches NIFTY/SENSEX live via yfinance, but `/api/macro` does NOT — it only reads from DB. The Macro page never shows live NIFTY/SENSEX values even though TopBar does.
- **Evidence:** `server.py:3709-3758`; `MacroDashboard.jsx:70-119`

### Economic Indicators (FRED data)
- **Route:** `GET /api/macro` → `indicators` filtered by non-INDEX_IDS
- **Status:** 🔴 STUB — same DB dependency; `MacroIndicator` table never populated by any visible pipeline
- **Evidence:** `MacroDashboard.jsx:122-131`

### Global Events
- **Route:** `GET /api/macro` → `globalEvents` array
- **Source:** SQLAlchemy `Event` table (type="regulatory")
- **Status:** 🔴 STUB — DB unavailable → `[]`; shows "No global events"
- **Evidence:** `server.py:3746-3755`; `MacroDashboard.jsx:134-168`

### Macro-Micro Transmission table
- **Status:** ⏸️ COMING SOON — `macroMicro` always returned as `[]` from backend (hardcoded in `return`); UI shows "Coming Soon · Q3 2026" placeholder
- **Evidence:** `server.py:3758` (`"macroMicro": []`); `MacroDashboard.jsx:171-185`

---

## Section 6: Splash & Nav

### Splash Screen
- **Status:** ✅ WIRED (client-only) — 10-second progress animation using `setInterval`; no API calls; fades out then calls `onDone()`
- **Branding:** Beaver-only (Tipsons lockup removed per commit `f1ddf25`)
- **Evidence:** `SplashScreen.jsx:1-104`

### TopBar — NIFTY 50 / SENSEX live chips
- **Route:** `GET /api/market/overview` → `nifty.raw_value`, `nifty.change_percent`
- **Status:** ✅ WIRED — fetches every 60s; yfinance → cache → null fallback
- **Evidence:** `TopBar.jsx:44-72`

### TopBar — IST Clock
- **Status:** ✅ WIRED — `setInterval(1s)` client-side; `formatIST()` using `en-IN` locale + `Asia/Kolkata` timezone
- **Evidence:** `TopBar.jsx:39-41`

### TopBar — Last Refresh indicator
- **Status:** ✅ WIRED — set on each successful `fetchIdx()` call; shows time of last successful API response
- **Evidence:** `TopBar.jsx:163-165`

### TopBar — Nav links (MARKET / RESEARCH / SIGNALS / MACRO)
- **Status:** ✅ WIRED — active state correctly tracks `currentPage` prop; calls `onNavigate` to update App.js state
- **Evidence:** `TopBar.jsx:119-145`; `App.js:27-40`

### TopBar — Connected pulse dot
- **Status:** ✅ WIRED (visually) — always green; no real connection-health check (does not check if API is reachable)
- **Evidence:** `TopBar.jsx:165-170`

---

## Critical Gaps Summary

1. **DB dependency silently kills 3 pages.** `/api/signals`, `/api/macro`, and insider trades all require a live SQLAlchemy connection to `research_platform.database`. With DB unavailable, all three endpoints return empty data with no visible error to the user. Signals page and Macro page appear loaded but show nothing.

2. **`assumption_engine.py` and `dcf_bridge.py` never called.** L08 and L12 are the guardrail and DCF-input pipeline, respectively. Neither is wired into `POST /analyze`. `dcf_bridge` was explicitly bypassed. This means `guardrail_log.json` is never written → GuardrailPanel always "All checks passed" (a false positive). `assumptions_history.json` never written → Assumption History panel always empty.

3. **ANTHROPIC_API_KEY controls large portions of the product.** When absent: HTML report renders with "—" in all text sections; chat returns 503. There is no graceful degradation messaging in the UI for these states.

4. **DCF notebook is a single point of failure for Valuation.** The `POST /analyze` endpoint raises HTTP 503 if `_get_dcf_excel_p30()` returns None. If the papermill notebook fails (yfinance timeout, missing template, etc.), the entire analyze flow 503s — even though all other data (scoring, SWOT, Porter) was already computed.

5. **`factor_deltas` computed but never rendered.** L07 (`factor_engine.py`) runs and populates `factor_deltas` in the response JSON, but no frontend panel reads this field.

6. **Chat session context not injected.** `session_id` is passed from `ChatPanel` to `POST /api/chat/message` but the backend `chat_message` handler does not read it — Claude has no knowledge of the current analysis when responding.
