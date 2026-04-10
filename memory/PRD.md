# Indian Markets Financial Intelligence Dashboard - PRD

## Original Problem Statement
Build a React financial intelligence dashboard for Indian markets. Frontend only with no API calls, using static/mock data.

## Theme Update (Jan 2026)
Updated from dark theme to clean WHITE/LIGHT theme:
- Background: #ffffff (white)
- Surface cards: #f8fafc (light gray)
- Secondary surface: #f1f5f9
- Borders: #e5e7eb
- Primary accent: #2563eb (blue)
- Positive: #16a34a (green)
- Negative: #dc2626 (red)
- Text primary: #0f172a (dark)
- Text secondary: #64748b (gray)

## API Integration (Jan 2026)
Frontend connected to FastAPI backend at `http://localhost:8000`:
- API base URL configured in `/app/frontend/src/services/api.js`
- All pages fetch real data from backend endpoints
- Loading states and error handling implemented
- Polling for real-time updates (30s for market, 60s for signals/macro)

### Backend Endpoints Used:
- GET /api/market/overview - Market indices, top movers, FII/DII, commodities, news
- GET /api/macro - Economic indicators, global events, macro-micro transmission
- GET /api/signals - Trading signals feed
- GET /api/alerts - Active alerts
- POST /api/research/new - Create research session
- GET /api/research/{session_id} - Get research data
- POST /api/research/{session_id}/run-scenarios - Run scenario analysis
- GET /api/sessions - List research sessions
- POST /api/chat - AI chat interaction

## User Personas
- **Financial Analysts**: Track Indian market indices, FII/DII flows, macro indicators
- **Traders**: Monitor top movers, signals, alerts for trading decisions
- **Research Analysts**: Conduct stock research with scenario analysis, DCF models

## Core Requirements (Static)
- Three-column fixed layout (Sidebar, Main Content, Chat Panel)
- 4 Dashboard Pages (Market Overview, Research Session, Signals & Alerts, Macro Dashboard)
- Animated sidebar (64px → 200px on hover)
- AI Chat panel with mocked responses
- Dark theme with specified color palette
- IST clock, DB status indicator
- No backend/API integration (frontend only)

## What's Been Implemented (Jan 2026)
- ✅ Complete 3-column layout with animated sidebar
- ✅ Market Overview: 5 indices, Top Movers (with IRFC), FII/DII flow, Commodities, News Feed
- ✅ Research Session: RELIANCE analysis, Bull/Base/Bear scenarios, Catalysts, Sensitivity grid
- ✅ Signals & Alerts: Tabbed filtering (7 tabs), Signal feed with transmission notes, Active Alerts
- ✅ Macro Dashboard: GDP/CPI/Repo/Fed indicators, Chart placeholders, Global events, Macro-Micro table
- ✅ AI Chat Panel: Mock conversation, Typing input, Keyword-based responses, Collapse/expand
- ✅ TopBar with IST clock and DB status
- ✅ All mock data in mockData.js

## Prioritized Backlog
### P0 (Critical) - DONE
- All 4 pages functional
- Navigation working
- Chat panel interactive

### P1 (High) - Future
- Real chart integration (Recharts)
- Persistent chat history
- Alert management CRUD

### P2 (Medium) - Future
- Multi-ticker research
- Custom watchlists
- Export functionality

## Next Tasks
1. Integrate Recharts for actual chart visualizations
2. Add more interactive stock analysis features
3. Implement watchlist functionality
