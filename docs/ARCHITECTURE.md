# Architecture Decision Record

## Decision: Emergent as the single backend

**Context**: The app has two potential backends — Mac (local) and Emergent (cloud).

**Decision**: All logic runs on Emergent. Mac is only used for development.

**Reasons**:
1. Emergent is always on — Mac being offline doesn't break the app
2. Single URL, no ngrok/tunnel complexity
3. Frontend and backend on same domain — no CORS issues
4. MongoDB already provisioned on Emergent

**Workflow**:
```
Mac (edit) → GitHub (source of truth) → Emergent (serve)
```

---

## Data Flow: One-Click Research

```
User types ticker
       ↓
POST /api/research/analyze
       ↓
1. Create MongoDB session
2. Fetch live data (yfinance .NS / .BO)
3. Detect sector (RELIANCE → petroleum)
4. Run DCF (Bull/Base/Bear + sensitivity)
5. Store in MongoDB
       ↓
Frontend polls GET /api/research/{id}
       ↓
Display: scenarios + DCF + sensitivity table
       ↓
GET /api/research/{id}/report/download
       ↓
2-page HTML report
```

---

## DCF Model Design

```
Inputs (from yfinance):
  - Revenue (TTM)
  - EBIT margin
  - D&A % of revenue
  - Capex % of revenue
  - Net debt
  - Shares outstanding
  - Current price

WACC calculation:
  - Risk-free rate = India 10Y GSec (~7%)
  - Beta from yfinance
  - ERP = 7.5% (India default)
  - Cost of debt = from balance sheet
  - D/E ratio from balance sheet

DCF:
  - 10-year projection
  - FCFF = NOPAT + D&A - Capex - ΔWC
  - Terminal value = Gordon Growth Model
  - 3 scenarios: Bull (+3% growth, +2% margin), Base, Bear (-4%, -3%)

Output:
  - Enterprise value per scenario
  - Equity value = EV - Net debt
  - Price per share = Equity / Shares
  - Upside % vs current price
  - Sensitivity table (WACC × terminal growth)
  - Reverse DCF (market's implied growth rate)
```

---

## NBFC/Banking Special Case

For financial companies (IRFC, HDFC Bank, etc.):
- `effective_net_debt = 0` (loan book is NOT corporate debt)
- `base_fcf = net_income × 0.7` (use net income, not FCFF)
- This prevents the ₹0 valuation bug

---

## Session Structure (MongoDB)

```json
{
  "session_id": "uuid",
  "ticker": "RELIANCE.NS",
  "sector": "petroleum",
  "created_at": "ISO timestamp",
  "status": "complete",
  "market_data": { ... yfinance data ... },
  "dcf_results": {
    "bull": { "price": 3086, "upside": 30.2 },
    "base": { "price": 1894, "upside": -19.8 },
    "bear": { "price": 959, "upside": -59.4 },
    "sensitivity": { "grid": [...] },
    "reverse_dcf": { "implied_growth_rate": 12.5 }
  },
  "report_html": "..."
}
```
