# Market Pulse — Project Context

Indian equity research platform. Backend: FastAPI (`server.py`) + Jupyter notebooks (papermill). Frontend: React (`frontend/`). Notebooks live under `notebooks/`. Core engine under `research_platform/`.

## Hard requirements

### 1. Frontend and backend must be fully wired end-to-end
Every backend endpoint that produces user-facing output must have a working
frontend surface that calls it, displays its result, and handles its error
and loading states. No orphan endpoints. No placeholder UI.

For every feature, the check is: can the user, clicking through the deployed
site, trigger the backend action and see/download the result without opening
devtools or hitting curl? If not, the feature is incomplete.

Specifically this applies to:
- `/dcf/run`, `/dcf/status`, `/dcf/output.xlsm` — must have the Run Full DCF
  button flow (Task 2)
- `/api/chat` — must have a chat UI in ResearchSession.jsx (extends Task 3)
- `/report/download` and `/report/xlsx` — verify buttons exist and work; if
  not, add them
- `/api/research/analyze` — verify the research flow renders all 11 JSON
  artifacts (assumptions, signals, thesis, scoring, scenarios, SWOT, Porter,
  audit log, etc.) in the UI; flag any that are fetched but not displayed

Before marking any task complete, do an end-to-end test: click the button in
the browser, confirm the backend logs show the call, confirm the UI updates
with real data. Report what you tested and what you saw.

### 2. DCF output must come exclusively from my DCF model
The only valuation output that ships to the user is the one produced by
`DCF_Multi_Source_Pipeline_REFACTORED.ipynb` against the `DCF.xlsm` template.

No other DCF implementation is allowed to produce the "fair value" number the
user sees. If you find any of the following, flag it and propose removing or
clearly marking it as internal-only, then wait for my approval:
- Alternative DCF implementations in `research_platform/ai_engine/` or
  elsewhere
- Hardcoded fair-value numbers anywhere in server.py or the frontend
- Any "fallback" valuation that silently substitutes when the notebook fails
  (the notebook failing should surface as an error, not a silent swap)

The scenario engine's Bull/Base/Bear outputs are allowed to exist as a
separate scenario framework, but they must be clearly labeled "Scenario
Analysis" in the UI — not "DCF" or "Fair Value". Only the notebook's output
gets called "DCF" or "Fair Value" in the UI.
