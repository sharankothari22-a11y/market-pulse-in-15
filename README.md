# Market Pulse — Unified Financial Intelligence System

Indian equity research platform combining live data collection, AI-powered signal detection, DCF valuation, and automated research reports.

---

## Architecture

```
market-pulse-in-15/
│
├── backend/                          ← Emergent server (always live)
│   ├── server.py                     ← FastAPI app (main entry point)
│   ├── collectors/
│   │   └── yfinance_nse.py           ← Live price fetcher
│   ├── research_platform/            ← Full intelligence engine
│   │   ├── ai_engine/                ← Signal detection, DCF, scoring, reports
│   │   │   ├── session_manager.py    ← Per-company research sessions
│   │   │   ├── scenario_engine.py    ← Bull/Base/Bear DCF scenarios
│   │   │   ├── signal_detector.py    ← Keyword → signal pipeline
│   │   │   ├── factor_engine.py      ← Signal → assumption delta mapping
│   │   │   ├── scoring.py            ← 5-dimension scoring (0-100)
│   │   │   ├── swot.py               ← SWOT generator
│   │   │   ├── porter.py             ← Porter's Five Forces
│   │   │   ├── pdf_builder.py        ← 2-page A4 print-ready report
│   │   │   ├── llm_layer.py          ← Claude API (report text)
│   │   │   └── frameworks/           ← Sector signal libraries
│   │   │       ├── universal.json
│   │   │       ├── petroleum/
│   │   │       ├── banking/
│   │   │       ├── pharma/
│   │   │       ├── it/
│   │   │       ├── fmcg/
│   │   │       ├── auto/
│   │   │       └── real_estate/
│   │   ├── collectors/               ← 51 data collectors
│   │   │   ├── free/                 ← NSE, SEBI, RBI, FRED, Reddit, etc.
│   │   │   └── paid/                 ← Bloomberg, Refinitiv, ACE Equity
│   │   ├── database/                 ← PostgreSQL models (future)
│   │   └── processing/               ← PDF/HTML scraping, sentiment, vectors
│   └── requirements.txt
│
├── frontend/                         ← React UI (Emergent)
│   └── src/
│       ├── pages/
│       │   ├── ResearchSession.jsx   ← Main research page
│       │   ├── MarketOverview.jsx
│       │   ├── MacroDashboard.jsx
│       │   └── SignalsAlerts.jsx
│       └── services/api.js           ← All API calls
│
├── notebooks/                        ← Mac local development & testing
│   ├── DCF_Multi_Source_Pipeline_REFACTORED.ipynb   ← DCF engine (full)
│   └── research_platform_v6_with_PDF_report.ipynb  ← Full research platform
│
├── excel/
│   └── DCF.xlsm                      ← Excel DCF template (macro-enabled)
│
└── docs/
    └── (architecture diagrams, API docs)
```

---

## Live URLs

| Service | URL |
|---------|-----|
| Frontend | https://design-review-38.preview.emergentagent.com/ |
| Backend API | https://design-review-38.preview.emergentagent.com/api/ |
| Health | https://design-review-38.preview.emergentagent.com/api/health |

---

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/research/analyze` | **One-click analysis** — ticker → full research |
| POST | `/api/research/{id}/dcf` | Run DCF (server-side, live yfinance) |
| GET | `/api/research/{id}/report/download` | Download HTML report |
| GET | `/api/sessions` | List all research sessions |
| GET | `/api/market/overview` | Live market data |
| GET | `/api/health` | Health check |

---

## DCF Engine (Notebooks)

The `notebooks/` folder contains the full Mac-side DCF pipeline:

**`DCF_Multi_Source_Pipeline_REFACTORED.ipynb`**
- Sources: yfinance API, Excel files, PDF financials, CSV exports
- Outputs: Bull/Base/Bear scenarios, sensitivity table (WACC × terminal growth), reverse DCF
- Writes results into `excel/DCF.xlsm` and triggers the sensitivity macro

**`excel/DCF.xlsm`**
- Sheet `DCF`: Live model (Revenue → EBIT → FCF → Terminal Value → Sensitivity table)
- Sheet `Cost of Capital`: WACC calculator (Beta, Risk Free Rate, ERP, Debt/Equity mix)
- Sheet `DCF - Original`: Best Buy reference example

---

## Research Platform (51 Collectors)

Organized in 3 phases:

| Phase | Count | Sources |
|-------|-------|---------|
| Phase 1 | 14 | NSE CSV, FRED, CoinGecko, AMFI, Frankfurter, RBI, MCA, SEBI, EIA, GDELT, World Bank, RSS, Finnhub, NewsAPI |
| Phase 2 | 19 | Metals, OPEC, Baltic Dry, NSE F&O, Insider trades, Credit ratings, Screener, Reddit, Wikipedia signals, SEC EDGAR, SEBI PMS, Politician portfolio, India Budget, Weather, IMF, Patents, YouTube transcripts, Earnings transcripts, Job postings |
| Phase 3 | 12 | SEBI analysts, LinkedIn, Industry associations, GST portal, App ratings, Twitter/Nitter, UN Comtrade, PLI schemes, AIF data, VC funding, Short interest, Beneficial ownership |
| v4 | 3 | Binance WebSocket, Playwright news, Data marketplace |
| Paid | 3 | Bloomberg, Refinitiv, ACE Equity |

---

## AI Pipeline (15 Layers)

```
Layer 1  → Data collection (51 collectors)
Layer 2  → Session manager (per-company research isolation)
Layer 3  → Data validation & cleaning
Layer 4  → Entity resolution (ticker → company → sector)
Layer 5  → Hash registry (data drift detection)
Layer 6  → Signal detection (keyword filter → DetectedSignal)
Layer 7  → Factor engine (Signal → AssumptionDelta)
Layer 8  → Confidence scorer (source reliability × recency × corroboration)
Layer 9  → Assumption engine + guardrails
Layer 10 → Version control + rollback
Layer 11 → DCF bridge (assumptions.json → DCF engine)
Layer 12 → Scenario engine (Bull/Base/Bear + sensitivity)
Layer 13 → LLM layer / Brain 2 (Claude interprets signals, writes report sections)
Layer 14 → Intent parser + chat interface
Layer 15 → Audit trail + report export (2-page A4 HTML/PDF)
```

---

## Development Workflow

```bash
# 1. Edit code on Mac (VS Code)
# 2. Push to GitHub
git add -A && git commit -m "your message" && git push

# 3. Emergent auto-pulls (or manually trigger restart)
# 4. Test at https://design-review-38.preview.emergentagent.com/
```

---

## Sector Coverage

| Sector | Key Signals | Valuation |
|--------|-------------|-----------|
| Petroleum / Energy | Crude price, GRM, OPEC, refinery utilization | EV/EBITDA + DCF |
| Banking / NBFC | NIM, credit growth, NPL, RBI rate | P/BV + ROE-DDM |
| FMCG | Volume growth, input costs, rural demand | DCF + EV/EBITDA |
| Pharma | FDA approvals, API prices, US generic pricing | DCF + P/E |
| IT / Tech | Deal wins, attrition, USD/INR | DCF + P/E |
| Real Estate | Pre-sales, collections, home loan rates | NAV + EV/EBITDA |
| Auto | Monthly volumes, EV transition, commodity costs | EV/EBITDA + DCF |

---

## Indian Market Coverage

- **Exchanges**: NSE (primary), BSE (fallback)
- **Ticker format**: `RELIANCE.NS`, `IRFC.NS`, `TCS.NS`
- **Regulators**: SEBI, RBI, MCA
- **Data sources**: Screener.in, Tijori Finance, NSE Bhavcopy, AMFI NAV
- **Currency**: INR (₹), converted from USD where needed

---

*Built for Indian equity research. Not investment advice.*
