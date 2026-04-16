"""
ai_engine/dcf_contract/runner.py
─────────────────────────────────
Triggers the DCF notebook and waits for dcf_output.json.

How it works:
  1. Write assumptions.json to session folder
  2. Copy assumptions.json to DCF notebook folder
  3. Execute DCF notebook via nbconvert (papermill-style)
  4. Copy dcf_output.json back to session folder
  5. Return parsed output

The DCF notebook reads assumptions.json via dcf_patch.py (injected at top).
After running, dcf_patch.py writes dcf_output.json.

If nbconvert is not available, falls back to writing assumptions.json
and returning {"status": "pending"} — user runs DCF manually.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.dcf_contract.schema import write_json, empty_output
from ai_engine.dcf_contract.writer import write_assumptions
from ai_engine.dcf_contract.reader import read_dcf_output, get_valuation_summary


# ── Config ────────────────────────────────────────────────────────────────────

DCF_NOTEBOOK_PATH = Path(
    os.environ.get("DCF_NOTEBOOK_PATH", "DCF_Multi_Source_Pipeline_REFACTORED.ipynb")
)
DCF_FOLDER = DCF_NOTEBOOK_PATH.parent if DCF_NOTEBOOK_PATH.parent != Path(".") else Path.cwd()
OUTPUT_WAIT_SECONDS = 300  # 5 minutes max wait
POLL_INTERVAL = 5


# ── Main entry point ─────────────────────────────────────────────────────────

def run_dcf(
    session,
    model_version: str = "base",
    dcf_notebook_path: Optional[Path] = None,
    timeout: int = OUTPUT_WAIT_SECONDS,
) -> dict[str, Any]:
    """
    Full DCF run for a session.

    Args:
        session:           ResearchSession
        model_version:     "base" | "analyst" | "data_driven"
        dcf_notebook_path: override path to DCF notebook
        timeout:           seconds to wait for output

    Returns:
        valuation summary dict (from get_valuation_summary)
    """
    nb_path = Path(dcf_notebook_path) if dcf_notebook_path else DCF_NOTEBOOK_PATH
    session_dir = session.session_dir

    logger.info(f"[dcf_contract.runner] Starting DCF run — ticker={session.ticker} model={model_version}")

    # Step 1: Write assumptions.json
    assumptions_path = write_assumptions(session, model_version=model_version)
    logger.info(f"[dcf_contract.runner] assumptions.json written: {assumptions_path}")

    # Step 2: Copy to DCF folder
    dcf_assumptions = nb_path.parent / "assumptions.json"
    try:
        shutil.copy2(assumptions_path, dcf_assumptions)
        logger.info(f"[dcf_contract.runner] Copied to DCF folder: {dcf_assumptions}")
    except Exception as exc:
        logger.warning(f"[dcf_contract.runner] Could not copy assumptions to DCF folder: {exc}")

    # Step 3: Execute DCF notebook
    dcf_output_src = nb_path.parent / "dcf_output.json"
    executed = _execute_notebook(nb_path, timeout=timeout)

    if not executed:
        # Manual mode — return pending status
        logger.warning("[dcf_contract.runner] Notebook execution not available. Manual run required.")
        _write_pending(session_dir, session.ticker, model_version, assumptions_path)
        return {
            "status": "pending",
            "message": "assumptions.json written. Run DCF notebook manually then call refresh.",
            "assumptions_path": str(assumptions_path),
        }

    # Step 4: Wait for dcf_output.json
    output_data = _wait_for_output(dcf_output_src, session_dir, session.ticker, timeout=timeout)

    if output_data is None:
        logger.error("[dcf_contract.runner] DCF output not produced within timeout")
        return {
            "status": "error",
            "message": f"DCF did not produce output within {timeout}s",
        }

    # Step 5: Copy output back to session folder
    session_output = session_dir / "dcf_output.json"
    write_json(output_data, session_output)
    logger.info(f"[dcf_contract.runner] dcf_output.json saved to session: {session_output}")

    return get_valuation_summary(output_data)


def run_all_versions(session, dcf_notebook_path=None) -> dict[str, Any]:
    """
    Run all 3 DCF versions sequentially.
    Returns dict with keys "base", "analyst", "data_driven".
    """
    results = {}
    for version in ("base", "analyst", "data_driven"):
        logger.info(f"[dcf_contract.runner] Running version: {version}")
        try:
            results[version] = run_dcf(session, model_version=version,
                                        dcf_notebook_path=dcf_notebook_path)
        except Exception as exc:
            logger.error(f"[dcf_contract.runner] {version} failed: {exc}")
            results[version] = {"status": "error", "message": str(exc)}
    return results


def refresh_from_output(session) -> Optional[dict[str, Any]]:
    """
    Read existing dcf_output.json from session (for manual-run mode).
    Call this after user has manually run the DCF notebook.
    """
    data = read_dcf_output(session.session_dir, ticker=session.ticker)
    if data:
        return get_valuation_summary(data)
    return None


# ── Notebook execution ────────────────────────────────────────────────────────

def _execute_notebook(nb_path: Path, timeout: int = 300) -> bool:
    """
    Execute notebook via jupyter nbconvert.
    Returns True if executed successfully, False if not available.
    """
    if not nb_path.exists():
        logger.warning(f"[dcf_contract.runner] Notebook not found: {nb_path}")
        return False

    # Try papermill first (better for parameterized notebooks)
    try:
        import papermill as pm
        logger.info(f"[dcf_contract.runner] Executing via papermill: {nb_path.name}")
        output_nb = nb_path.parent / f"_dcf_run_{int(time.time())}.ipynb"
        pm.execute_notebook(
            str(nb_path),
            str(output_nb),
            kernel_name="python3",
            execution_timeout=timeout,
        )
        # Clean up executed notebook
        try:
            output_nb.unlink()
        except Exception:
            pass
        return True
    except ImportError:
        logger.debug("[dcf_contract.runner] papermill not available, trying nbconvert")
    except Exception as exc:
        logger.error(f"[dcf_contract.runner] papermill execution failed: {exc}")
        return False

    # Fall back to nbconvert
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "jupyter", "nbconvert",
                "--to", "notebook",
                "--execute",
                "--inplace",
                f"--ExecutePreprocessor.timeout={timeout}",
                str(nb_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 30,
            cwd=str(nb_path.parent),
        )
        if result.returncode != 0:
            logger.error(f"[dcf_contract.runner] nbconvert failed: {result.stderr[:500]}")
            return False
        return True
    except FileNotFoundError:
        logger.debug("[dcf_contract.runner] jupyter nbconvert not found")
        return False
    except subprocess.TimeoutExpired:
        logger.error("[dcf_contract.runner] notebook execution timed out")
        return False
    except Exception as exc:
        logger.error(f"[dcf_contract.runner] notebook execution error: {exc}")
        return False


def _wait_for_output(
    dcf_output_src: Path,
    session_dir: Path,
    ticker: str,
    timeout: int = 300,
) -> Optional[dict[str, Any]]:
    """Poll for dcf_output.json, return parsed data or None."""
    start = time.time()
    while time.time() - start < timeout:
        # Check DCF folder
        if dcf_output_src.exists():
            try:
                data = json.loads(dcf_output_src.read_text())
                if data.get("meta", {}).get("status") in ("ok", "error"):
                    return data
            except Exception:
                pass
        # Check session folder too (in case DCF writes directly there)
        session_out = session_dir / "dcf_output.json"
        if session_out.exists():
            try:
                data = json.loads(session_out.read_text())
                if data.get("meta", {}).get("status") in ("ok", "error"):
                    return data
            except Exception:
                pass
        time.sleep(POLL_INTERVAL)
    return None


def _write_pending(session_dir: Path, ticker: str, model_version: str, assumptions_path: Path):
    """Write a pending placeholder to session folder."""
    pending = empty_output(ticker=ticker, model_version=model_version)
    pending["meta"]["status"] = "pending"
    pending["meta"]["error_message"] = f"Run DCF notebook manually. assumptions.json at: {assumptions_path}"
    write_json(pending, session_dir / "dcf_output.json")
