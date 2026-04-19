# BACKEND DATA INVENTORY REPORT
## Market Pulse in 15 — Research Platform API

**Diagnostic Date:** 2026-04-19
**Backend Path:** `backend/research_platform`
**API Entry:** `api_server.py` (23 endpoints)

---

## 1. RESEARCH ANALYSIS ENDPOINT: POST /api/research/analyze

**Status:** Referenced in `frontend/src/services/api.js` but **NOT IMPLEMENTED** in backend.
Frontend expects a one-shot endpoint; actual flow is:
- `POST /api/research/new` → creates session stub
- `POST /api/research/{session_id}/run-scenarios` → generates valuations
- `GET /api/research/{session_id}` → retrieves full state

### Top-Level Keys Returned by `GET /api/research/{session_id}`

```json
{
  "session_id": "str",
  "ticker": "str (e.g., RELIANCE.NS)",
  "meta": {
    "_session_created": "ISO date",
    "_sector": "str (mapped sector name)",
    "_sector_mapped": "str",
    "hypothesis": "str | null",
    "variant_view": "str | null"
  },
  "assumptions": {
    "risk_free_rate": "float (%)",
    "equity_risk_premium": "float (%)",
    "beta": "float",
    "cost_of_debt": "float (%)",
    "tax_rate": "float (%)",
    "wacc": "float (%)  | wacc_direct: float",
    "terminal_growth_rate": "float (%)",
    "forecast_years": "int",
    "revenue_growth": "float (%)",
    "ebitda_margin": "float (%)",
    "capex_pct": "float",
    "debt_equity_ratio": "float",
    "base_revenue": "float (INR millions)",
    "shares_outstanding": "float (millions)",
    "current_price": "float (INR)",
    "_data_confidence": "str (low|medium|high)"
  },
  "scenarios": {
    "bull": {
      "price_per_share": "float (₹)",
      "upside_pct": "float",
      "revenue_growth": "float (%)",
      "ebitda_margin": "float (%)",
      "rating": "str (buy|hold|sell|avoid)",
      "key_assumption": "str (one-liner)"
    },
    "base": "{same structure}",
    "bear": "{same structure}",
    "reverse_dcf": {
      "market_cap": "float",
      "implied_growth_rate": "float (%)",
      "implied_wacc": "float (%)",
      "interpretation": "str"
    },
    "sensitivity": {
      "wacc_grid": "[floats]",
      "growth_grid": "[floats]",
      "matrix": "[[price per share grid]]"
    }
  },
  "assumption_history": [
    {
      "metric": "str",
      "old_value": "float | null",
      "new_value": "float",
      "reason": "str",
      "timestamp": "ISO date"
    }
  ],
  "guardrail_breaches": [
    {
      "metric": "str",
      "value": "float",
      "lower_bound": "float | null",
      "upper_bound": "float | null",
      "severity": "str (warn|error)"
    }
  ]
}
```

### Scoring / SWOT / Porter / Thesis

- **Scoring:** Not returned in the session payload. Signal scores exist but are computed via chat intent `ACTION_SHOW_THESIS`.
- **SWOT & Porter's Five Forces:** LLM-generated inside chat flow only. **No structured JSON endpoint.**
- **Thesis (bull/bear):** Stored in session file `thesis.txt`, served only via chat.
- **Scenarios:** Present under `scenarios.bull|base|bear` (price_per_share, upside_pct, rating, key_assumption).
- **Reverse DCF:** Present under `scenarios.reverse_dcf`.

### Financials

- **Historical:** Pulled from `price_history`; exposed only as `base_revenue` + `current_price` in assumptions.
- **Projected:** Year-by-year forecast not exposed (engine has it; API hides it).
- **No quarterly/annual breakdowns** returned.

---

## 2. DCF: `/dcf/run`, `/dcf/status`, SIDECAR JSON

### Status: Hybrid (file-based, not HTTP)

DCF runs via script, not HTTP endpoints. Results land as sidecar JSON.

### `dcf_output.json` (sidecar)

**Path:** `{session_dir}/dcf_output.json`
**Written by:** external DCF model after consuming `assumptions.json`
**Read by:** `dcf_bridge.py::read_dcf_results()` + `dcf_contract/reader.py`

```json
{
  "schema_version": "1.0",
  "meta": {
    "ticker": "str",
    "model_version": "str (base|analyst|data_driven)",
    "run_at": "ISO date",
    "tv_method": "str (Gordon Growth | Exit Multiple)",
    "wacc_pct": "float",
    "terminal_growth_pct": "float",
    "currency": "INR",
    "units": "Millions",
    "forecast_years": "int",
    "status": "str (ok|error|pending)",
    "error_message": "str | null"
  },
  "valuation": {
    "enterprise_value": "float",
    "net_debt": "float",
    "equity_value": "float",
    "shares_outstanding": "float",
    "per_share": "float",
    "pv_fcffs": "float",
    "pv_terminal_value": "float",
    "current_price": "float",
    "upside_pct": "float"
  },
  "scenarios": {
    "base": { "per_share": "float", "upside_pct": "float", "rating": "str", "key_assumption": "str" },
    "bull": "{same}",
    "bear": "{same}"
  },
  "sensitivity_table": {
    "wacc_vs_growth": {
      "rows": ["6.0%", "7.0%", "…"],
      "cols": ["1.0%", "2.0%", "…"],
      "matrix": "[[prices per share]]"
    }
  },
  "forecast": [
    { "year": "int", "revenue": "float", "ebit": "float", "fcff": "float", "revenue_growth": "float", "ebit_margin": "float" }
  ],
  "checks": { "wacc_gt_zero": "bool", "g_lt_wacc": "bool", "fcff_present": "bool" }
}
```

### `assumptions.json` (bridge file written by backend)

```json
{
  "schema_version": "1.0",
  "meta": { "ticker", "sector", "session_id", "model_version", "generated_at", "data_confidence" },
  "wacc_inputs": { "risk_free", "equity_risk_premium", "beta", "cost_of_debt_pretax", "tax_rate", "target_debt_weight", "wacc_direct" },
  "dcf_parameters": { "forecast_years", "terminal_growth", "exit_multiple", "use_exit_multiple", "mid_year", "base_year" },
  "driver_overrides": { "revenue_growth", "ebit_margin", "capex_pct", "da_pct", "nwc_pct" },
  "year_overrides": "[ per-year driver dicts ]",
  "sensitivity": { "wacc_grid", "growth_grid", "exit_mult_grid", "margin_adj" }
}
```

### Reverse DCF (chat-only)

Via `POST /api/chat` intent `ACTION_REVERSE_DCF`:
```json
{ "market_cap": "float", "enterprise_value": "float", "implied_growth_rate": "float (%)", "implied_wacc": "float (%)", "interpretation": "str" }
```

---

## 3. MARKET OVERVIEW DATA SOURCES

### `GET /api/market/overview`

```json
{
  "data_date": "YYYY-MM-DD",
  "top_movers": [
    { "ticker": "str", "close": "float", "open": "float", "high": "float", "low": "float", "volume": "int", "change_pct": "float" }
  ],
  "fii_dii": [
    { "date": "YYYY-MM-DD", "category": "FII|DII", "buy_cr": "float", "sell_cr": "float", "net_cr": "float" }
  ],
  "fx": { "USD/INR": "float", "...": "..." },
  "commodities": [
    { "name": "str", "symbol": "str", "price": "float", "currency": "str", "change_24h": "float", "date": "YYYY-MM-DD" }
  ],
  "news": [
    { "title": "str", "type": "earnings|policy|…", "entity": "str", "date": "YYYY-MM-DD|null", "impact": "float 0–10", "source_url": "str|null" }
  ]
}
```

### `GET /api/macro`

```json
{
  "indicators": {
    "NY.GDP.MKTP.KD.ZG": {
      "latest": { "date": "YYYY-MM-DD", "value": "float", "source": "str" },
      "history": [ { "date": "YYYY-MM-DD", "value": "float", "source": "str" } ]
    },
    "FP.CPI.TOTL.ZG": "{…same}",
    "FEDFUNDS": "{…same}"
  }
}
```

Indicators include: GDP growth (World Bank), CPI inflation (World Bank), Fed Funds Rate (FRED), plus anything in `macro_indicators`.

### `GET /api/signals`

```json
{
  "signals": [
    { "id": "int", "title": "str", "type": "earnings|policy|filings|deal|regulatory|news", "entity": "str", "date": "YYYY-MM-DD|null", "impact": "float 0–10", "url": "str|null" }
  ],
  "total": "int"
}
```

Sources: RSS, GDELT, SEBI filings, company announcements, earnings calendars.

---

## 4. ALL ENDPOINTS

| Endpoint | Method | Returns | FE used? | Notes |
|---|---|---|---|---|
| `/api/health` | GET | `{status, db, timestamp}` | Yes | Health check |
| `/api/status` | GET | `{timestamp, collectors[], tables{}}` | No | Debug: collectors + row counts |
| `/api/market/overview` | GET | Movers, FII/DII, FX, commodities, news | Yes | Main dashboard |
| `/api/prices/{ticker}` | GET | 90-day OHLCV | Yes | Charts |
| `/api/macro` | GET | Indicators w/ 24-month history | Yes | Macro page |
| `/api/signals` | GET | Scored events | Yes | Signals page |
| `/api/alerts` | GET | `{alerts, count, checked_at}` | Partial | Threshold alerts |
| `/api/research/new` | POST | `{session_id, ticker, created_at}` | Legacy | Session stub |
| `/api/research/{id}` | GET | Full session state | Yes | Research dashboard |
| `/api/research/{id}/signals` | GET | Ticker-specific events | No | Not wired |
| `/api/research/{id}/run-scenarios` | POST | Bull/base/bear + sensitivity | Yes | Valuation trigger |
| `/api/research/{id}/assumption` | POST | `{metric, new_value, assumptions}` | Yes | Override metric |
| `/api/research/{id}/report` | GET | `{report: "markdown", cached}` | Yes | Full text report |
| `/api/sessions` | GET | `{sessions: [...]}` | No | List sessions |
| `/api/chat` | POST | Text response w/ intent router | Yes | Chat |
| `/api/reports/market` | GET | `{report, generated_at}` | **No** | Daily market LLM report |
| `/api/reports/commodity` | GET | `{report, generated_at}` | **No** | Daily commodity/FX report |
| `/api/reports/macro` | GET | `{report, generated_at}` | **No** | Daily macro/political report |
| `/api/reports/investor` | GET | `{report, generated_at}` | **No** | FII/DII sentiment report |

### FE-configured but NOT implemented in backend

(defined in `frontend/src/services/api.js`, missing handlers)

- `/api/research/analyze` — FE expects one-shot; actual is split new+run-scenarios
- `/api/research/{id}/catalyst` — chat-only (intent `ACTION_SHOW_CATALYSTS`)
- `/api/research/{id}/thesis` — chat-only (intent `ACTION_SHOW_THESIS`)
- `/api/research/{id}/dcf` — file-only (no HTTP; reads `dcf_output.json`)

---

## 5. DATA THE BACKEND HAS THAT THE UI DOES NOT SURFACE (OR SHOWS POORLY)

High-value gaps:

1. **Four daily LLM reports unused.** `/api/reports/{market,commodity,macro,investor}` are fully wired on backend, **not called anywhere in frontend**. Each is a paragraph-style daily brief — could be hero cards on Market Overview, Macro Dashboard, Signals page.
2. **Thesis + Catalysts are chat-gated.** Bull/bear thesis (`thesis.txt`) and catalysts exist per session but are only retrievable by asking in chat. Research Session should show these as structured panels.
3. **SWOT & Porter's Five Forces — chat-only.** LLM generates these on demand; never stored as JSON. If we want panels, the backend needs a new endpoint OR the chat intents need persisting to disk.
4. **Forecast array from DCF is hidden.** `dcf_output.json.forecast[]` has year-by-year revenue/EBIT/FCFF + margins. None of this shows in the UI. Prime opportunity: a forecast chart on Research Session.
5. **Sensitivity matrix exists but underused.** `scenarios.sensitivity` (WACC × growth grid of prices). Currently only used numerically — could be a proper heatmap component.
6. **Assumption history timeline unused.** Every override writes to `assumption_history`. UI doesn't show this audit trail.
7. **Guardrail breaches not surfaced.** `guardrail_breaches[]` carries warn/error flags per metric. UI doesn't highlight risky assumptions.
8. **Reverse DCF interpretation text unused.** `scenarios.reverse_dcf.interpretation` is a ready-made narrative string. Perfect for a "What does the market believe?" card.
9. **`/api/research/{id}/signals` unused.** Per-ticker event stream already scoped server-side; FE instead filters the global `/api/signals` client-side.
10. **News items carry `impact` scores (0–10), `type`, `source_url`.** UI currently shows titles only — no impact badges, no category filters.
11. **Commodities carry `change_24h`.** FE currently shows "—" for missing change (per Fix 4), but when change IS present, the field exists — should render semantic color.
12. **Price endpoint `/api/prices/{ticker}`** returns 90-day OHLCV. Research Session chart exists but may not be showing volume or OHLC body — verify.
13. **FII/DII breakdown (buy_cr, sell_cr) unused.** UI shows only net. Gross flows tell a different story (confidence vs panic).
14. **Macro history 24 months** returned; UI likely shows latest value only — history is chart-ready.

Low-priority flags:

- `/api/alerts` wiring status ambiguous. Confirm whether bell icon consumes it.
- `/api/sessions` list never fetched; no "recent research" surface in UI.
- `model_version` field (base|analyst|data_driven) in DCF meta never displayed.

---

## 6. DATABASE TABLES (reference)

Time-series (TimescaleDB):
- `price_history` (ticker, date, OHLCV, exchange)
- `macro_indicators` (indicator, date, value, source)
- `commodity_prices` (commodity_id, date, price, currency, extra_data JSON)
- `fii_dii_flows` (date, category, buy/sell/net, exchange)
- `fx_rates` (pair, date, rate, source)
- `fund_nav` (scheme_id, date, nav)

Reference:
- `company` (ticker, sector, sector_mapped, exchange, country)
- `event` (type, title, date, impact_score, source_url) — deduped on (source_url, date, type)

---

**Generated:** 2026-04-19. Coverage: 23/23 endpoints, ~40% feature depth (SWOT/Porter/thesis only in chat layer; DCF only in sidecar JSON).
