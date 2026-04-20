#!/usr/bin/env bash
# Boot-time wrapper for the research_platform service.
# 1) Runs the one-shot setup script (idempotent — patches main.py, smoke-tests).
# 2) Execs into the long-running uvicorn server so supervisor monitors it.

set -u
cd "$(dirname "$0")"

SETUP_SCRIPT="research_platform_v6_with_PDF_report.py"
SETUP_LOG="setup.log"

echo "[$(date '+%F %T')] running one-shot setup: $SETUP_SCRIPT" >> "$SETUP_LOG"
python3 -u "$SETUP_SCRIPT" >> "$SETUP_LOG" 2>&1 || {
  echo "[$(date '+%F %T')] setup exited non-zero — continuing to server anyway" >> "$SETUP_LOG"
}

# Hand off to the real server. `exec` replaces this shell so supervisor
# monitors the uvicorn process directly.
cd research_platform
exec python3 -u -m uvicorn api_server:app --host 0.0.0.0 --port 8765
