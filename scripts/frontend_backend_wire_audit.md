# Frontend ↔ Backend Wire Audit
**Date:** 2026-04-19 · **Scope:** every HTTP call FE makes + every endpoint BE exposes.

## ⚠️ Correction to prior inventory

The earlier `backend_data_inventory.md` report inspected `backend/research_platform/api_server.py` and claimed that `/api/research/analyze`, `/dcf/run`, `/dcf/status`, `/catalyst`, `/thesis`, `/report/download` were missing. **That was wrong.**

There are **two FastAPI apps** in the repo:
- `backend/server.py` — the real, mounted app (`app.include_router(api_router)` at line 2171). Has 27 `/api/*` routes including all the "missing" ones above.
- `backend/research_platform/api_server.py` — a **standalone alternative** (`uvicorn api_server:app` in its own docstring, line 8). **Not mounted by server.py.** In production this file's routes are unreachable.

Every conclusion below rests on `server.py` being the production backend.

---

## 1. Inventory of FE API call sites

| # | File:line | Method + path | Backend route in `server.py` |
|---|---|---|---|
| 1 | [ResearchSession.jsx:45](frontend/src/pages/ResearchSession.jsx:45) | GET `/api/prices/{ticker}?days=90` | `server.py:2125` |
| 2 | [ResearchSession.jsx:165](frontend/src/pages/ResearchSession.jsx:165) | GET `/api/sessions` | `server.py:833` |
| 3 | [ResearchSession.jsx:181](frontend/src/pages/ResearchSession.jsx:181) | GET `/api/research/{id}` | `server.py:1304` |
| 4 | [ResearchSession.jsx:214](frontend/src/pages/ResearchSession.jsx:214) | GET `/api/research/{id}` | `server.py:1304` |
| 5 | [ResearchSession.jsx:229](frontend/src/pages/ResearchSession.jsx:229) | POST `/api/research/analyze` | `server.py:899` |
| 6 | [ResearchSession.jsx:253](frontend/src/pages/ResearchSession.jsx:253) | GET `/api/sessions` | `server.py:833` |
| 7 | [ResearchSession.jsx:269](frontend/src/pages/ResearchSession.jsx:269) | POST `/api/research/analyze` (with hypothesis/variant/sector) | `server.py:899` |
| 8 | [ResearchSession.jsx:293](frontend/src/pages/ResearchSession.jsx:293) | GET `/api/sessions` | `server.py:833` |
| 9 | [ResearchSession.jsx:307](frontend/src/pages/ResearchSession.jsx:307) | POST `/api/research/{id}/dcf` | `server.py:1753` |
| 10 | [ResearchSession.jsx:308](frontend/src/pages/ResearchSession.jsx:308) | GET `/api/research/{id}` | `server.py:1304` |
| 11 | [ResearchSession.jsx:324](frontend/src/pages/ResearchSession.jsx:324) | POST `/api/research/{id}/catalyst` | `server.py:1738` |
| 12 | [ResearchSession.jsx:342](frontend/src/pages/ResearchSession.jsx:342) | POST `/api/research/{id}/thesis` | `server.py:1743` |
| 13 | [ResearchSession.jsx:356](frontend/src/pages/ResearchSession.jsx:356) | POST `/api/research/{id}/thesis` | `server.py:1743` |
| 14 | [ResearchSession.jsx:372](frontend/src/pages/ResearchSession.jsx:372) | POST `/api/research/{id}/dcf` | `server.py:1753` |
| 15 | [ResearchSession.jsx:373](frontend/src/pages/ResearchSession.jsx:373) | GET `/api/research/{id}` | `server.py:1304` |
| 16 | [ResearchSession.jsx:386](frontend/src/pages/ResearchSession.jsx:386) | GET `/api/research/{id}` | `server.py:1304` |
| 17 | [ResearchSession.jsx:409](frontend/src/pages/ResearchSession.jsx:409) | GET `/api/research/{id}/dcf/status` | `server.py:1644` |
| 18 | [ResearchSession.jsx:417](frontend/src/pages/ResearchSession.jsx:417) | POST `/api/research/{id}/dcf/run` | `server.py:1584` |
| 19 | [ResearchSession.jsx:423](frontend/src/pages/ResearchSession.jsx:423) | GET `/api/research/{id}/dcf/status` | `server.py:1644` |
| 20 | [ResearchSession.jsx:445](frontend/src/pages/ResearchSession.jsx:445) | GET `/api/research/{id}/report/download` | `server.py:1834` |
| 21 | [MacroDashboard.jsx:28](frontend/src/pages/MacroDashboard.jsx:28) | GET `/api/macro` | `server.py:2109` |
| 22 | [MarketOverview.jsx:521](frontend/src/pages/MarketOverview.jsx:521) | GET `/api/market/overview` | `server.py:686` |
| 23 | [TopBar.jsx:45](frontend/src/components/layout/TopBar.jsx:45) | GET `/api/macro` | `server.py:2109` |
| 24 | [SignalsAlerts.jsx:70](frontend/src/pages/SignalsAlerts.jsx:70) | GET `/api/signals` | `server.py:2115` |
| 25 | [SignalsAlerts.jsx:71](frontend/src/pages/SignalsAlerts.jsx:71) | GET `/api/alerts` | `server.py:2120` |
| 26 | [ChatPanel.jsx:28](frontend/src/components/layout/ChatPanel.jsx:28) | POST `/api/chat` | `server.py:2144` |

**Total FE call sites: 26.** Every one resolves to an existing `server.py` route.

---

## 2. Shape-match spot checks

### `POST /api/research/analyze` response (server.py:1093–1138)

FE reads: `session_id`, `ticker`, `dcf.current_price`, `dcf.fair_value`, `dcf.upside_pct` ([ResearchSession.jsx:231–249](frontend/src/pages/ResearchSession.jsx:231)).
BE emits all of these plus `scenarios`, `sensitivity`, `reverse_dcf`, `scoring`, `meta`. **✓ match.**

### `GET /api/research/{id}` response

FE reads: `data.dcf_output.status`, `data.dcf_output.scenarios`, `data.scenarios`, `data.ticker`, `data.hypothesis`, `data.variant_view`, `data.session_id` ([ResearchSession.jsx:215, 310–311, 457–459](frontend/src/pages/ResearchSession.jsx:215)).
BE enriches with cached analyze response (server.py:1321). **✓ match** — but `data.dcf_output` only populated after `POST /dcf`; otherwise FE falls back to `data.scenarios`.

### `GET /api/market/overview` → MarketOverview transformers

BE returns `{data_date, top_movers[], fii_dii[], fx{}, commodities[], news[]}`. FE transforms all five. **✓ match.**

### `GET /api/prices/{ticker}` → chart

BE returns 90-day OHLCV. FE consumes on line 45. **✓ match** (not verified field-by-field).

---

## 3. Backend routes FE never calls

### In `server.py` (production, reachable)
| Route | What it returns | FE benefit? | Where it would land |
|---|---|---|---|
| GET `/api/` | Root hello | No | — |
| GET `/api/version` | Version metadata | Low | TopBar tooltip maybe |
| GET `/api/ping` | Liveness | No | — |
| DELETE `/api/research/{id}/dcf/cancel` | Cancels running DCF | Yes | Cancel button next to "Running…" in DCF panel |
| POST `/api/research/{id}/run-scenarios` | Re-runs scenarios (RP engine) | Maybe | "Re-run scenarios" button on Research (currently FE uses `POST /dcf` instead — see overlap note below) |
| GET `/api/research/{id}/dcf/output.xlsx` / `.xlsm` | Direct file download | Yes | Used indirectly via `download_url` from `/dcf/status` — already wired |
| GET `/api/research/{id}/report/xlsx` | 6-sheet research Excel | **Yes** | "Download Excel" button on Research (currently only HTML report downloads) |
| GET `/api/research/{id}/report/csv` | CSV export | Yes | Optional export menu item |

### In `research_platform/api_server.py` (standalone, NOT mounted — dead to FE)
- `/api/status` — collector health + row counts (debug)
- `/api/research/{id}/signals` — ticker-scoped events
- `/api/research/{id}/assumption` — manual metric override
- `/api/research/{id}/report` (GET) — markdown/text report
- `/api/reports/market`, `/api/reports/commodity`, `/api/reports/macro`, `/api/reports/investor` — daily LLM briefs

These **would** be high-value (daily briefs especially) but they are **not reachable** without mounting api_server.py into server.py or running it as a second process. **Surfacing any of them requires a backend change** (out of scope per the rules).

---

## 4. Categorized findings

### A. BROKEN (FE calls a nonexistent endpoint)
**Count: 0.**

### B. MISMATCHED (endpoint exists, response shape doesn't match)
**Count: 0** (spot-checked the four richest calls; no divergences found. Full field-by-field diff not performed — see "verifications not performed" below).

### C. UNUSED (rich backend data FE doesn't consume)
**Count: 13**, ranked by payoff:

1. **`scenarios`, `reverse_dcf`, `scoring`, `sensitivity`** on `POST /api/research/analyze` response — all present in BE payload; FE currently uses only `dcf.*` and ignores the other four. High payoff: BULL/BEAR prices, reverse-DCF narrative, composite score, heatmap grid are all one JSON-read away. No new endpoint needed.
2. **`/api/research/{id}/report/xlsx`** (6-sheet research Excel) — server.py:1949, no FE caller.
3. **`/api/research/{id}/report/csv`** — server.py:2071, no FE caller.
4. **`/api/research/{id}/dcf/cancel`** — server.py:1723, no FE caller (DCF poll cannot be stopped).
5. **`assumption_history[]`** on `/api/research/{id}` — audit trail, never shown.
6. **`guardrail_breaches[]`** on `/api/research/{id}` — risk flags per metric, never shown.
7. **News items' `impact` score, `type`, `source_url`** from `/api/market/overview.news[]` — FE renders titles only.
8. **FII/DII `buy_cr` + `sell_cr`** — FE shows only `net_cr`; gross flows carry extra info.
9. **Commodities `change_24h`** — verify FE actually renders semantic color when field is present (recent fix defaults to "—").
10. **Macro 24-month `history[]`** per indicator — FE likely shows latest value only; history is chart-ready.
11. **OHLCV `volume`** on `/api/prices/{ticker}` — confirm chart uses it.
12. **DCF sensitivity matrix** on analyze response (`sensitivity`) — never rendered as heatmap.
13. **`/api/research/{id}/run-scenarios`** — distinct from `/dcf`; re-runs RP scenarios without a full DCF cycle. FE currently conflates the two by always calling `/dcf`.

### D. HEALTHY (wire works end-to-end)
**Count: 26** (all FE call sites in §1 hit a real `server.py` route; spot checks found no shape mismatches).

---

## 5. Overlap / design smells noticed during audit (NOT fixing)

- **Two parallel research backends exist** (`server.py` vs `research_platform/api_server.py`). The latter has 4 daily LLM report endpoints and some RP-only endpoints that are dead code in production. Either mount api_server.py or port the routes into server.py. Flag only — out of scope.
- **FE calls `POST /api/research/{id}/dcf` to "run scenarios"** ([ResearchSession.jsx:307](frontend/src/pages/ResearchSession.jsx:307)) instead of `POST /run-scenarios`. Both exist in server.py. May or may not matter; worth clarifying with BE owner.
- **`downloadReport` uses `fetch()` directly** ([ResearchSession.jsx:445](frontend/src/pages/ResearchSession.jsx:445)) bypassing `apiRequest`'s error handling. Minor.
- **`API_ENDPOINTS.researchSignals`, `researchAssumption`, `researchReport`, `reportMarket`, `reportCommodity`, `reportMacro`, `reportInvestor`** are defined in `api.js` but never referenced anywhere in `src/`. Dead config.
- **`API_ENDPOINTS.researchAnalyze` is used**, but in `api.js:21` the comment still says "one-shot: creates session + runs analysis + returns price" — that's now accurate; the prior inventory was wrong.
- **`API_ENDPOINTS.researchDcf`, `researchCatalyst`, `researchThesis`** are defined in `api.js` but the call sites in ResearchSession.jsx build URLs manually (`` `/api/research/${sid}/dcf` ``) instead of using the constant. Inconsistency, not breakage.

## 6. Verifications NOT performed
- Did not run either backend; no live request/response sampling.
- Did not diff every individual FE `data.xxx` read against BE emission (only the four highest-value responses).
- Did not confirm whether the running Emergent deployment actually serves `server.py` (assumed from code structure; FE config uses `process.env.REACT_APP_BACKEND_URL`).

---

## Bottom line
**No wires are broken.** The earlier "backend doesn't have /api/research/analyze" conclusion was an artifact of reading the wrong backend file. The real gap is category **C (unused data)** — chiefly the `scenarios`, `reverse_dcf`, `scoring`, `sensitivity` blocks already in the analyze response, plus the unused Excel/CSV/cancel endpoints.
