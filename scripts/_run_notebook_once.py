#!/usr/bin/env python3
"""
One-shot local runner for DCF_Multi_Source_Pipeline_REFACTORED.ipynb.
Mirrors the TICKER_INPUT-patching logic from backend/server.py so this
stays in sync with the production execution path.
"""
import sys
import time
from pathlib import Path

import nbformat
import papermill as pm

REPO_ROOT = Path(__file__).resolve().parent.parent
NB_SRC = REPO_ROOT / "notebooks" / "DCF_Multi_Source_Pipeline_REFACTORED.ipynb"
NB_DIR = REPO_ROOT / "notebooks"

RUN_DIR = REPO_ROOT / ".dcf_local_run"
RUN_DIR.mkdir(exist_ok=True)


def patch_and_run(ticker: str) -> dict:
    ticker = ticker.strip().upper()
    ticker_ns = ticker if "." in ticker else f"{ticker}.NS"

    nb = nbformat.read(str(NB_SRC), as_version=4)
    patched = False
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        if "TICKER_INPUT" in cell.source and "MASTER CONFIG" in cell.source:
            lines = cell.source.split("\n")
            new_lines = []
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("TICKER_INPUT =") and "globals" not in line:
                    indent = line[: len(line) - len(stripped)]
                    new_lines.append(
                        f'{indent}TICKER_INPUT = globals().get("TICKER_INPUT") or "{ticker_ns}"'
                    )
                else:
                    new_lines.append(line)
            cell.source = "\n".join(new_lines)
            patched = True
            break

    if not patched:
        raise RuntimeError("Could not find TICKER_INPUT cell to patch")

    patched_path = RUN_DIR / "patched_input.ipynb"
    executed_path = RUN_DIR / f"{ticker}_executed.ipynb"
    nbformat.write(nb, str(patched_path))

    print(f"Running notebook for {ticker_ns}")
    print(f"  cwd       : {NB_DIR}")
    print(f"  patched   : {patched_path}")
    print(f"  executed  : {executed_path}")

    start = time.monotonic()
    pm.execute_notebook(
        input_path=str(patched_path),
        output_path=str(executed_path),
        parameters={"TICKER_INPUT": ticker_ns},
        kernel_name="python3",
        cwd=str(NB_DIR),
        progress_bar=True,
        log_output=False,
        execution_timeout=600,
    )
    elapsed = time.monotonic() - start

    # Find output file
    candidates = []
    for pat in [
        f"DCF_Output_{ticker_ns}_*.xlsm",
        f"DCF_Output_{ticker_ns}_*.xlsx",
        f"DCF_Output_{ticker}_*.xlsm",
        f"DCF_Output_{ticker}_*.xlsx",
    ]:
        hits = list(NB_DIR.glob(pat))
        if hits:
            candidates = hits
            break

    if not candidates:
        all_outputs = list(NB_DIR.glob("DCF_Output_*"))
        raise FileNotFoundError(
            f"No DCF_Output file for {ticker}. Existing: {[p.name for p in all_outputs]}"
        )

    output_file = max(candidates, key=lambda p: p.stat().st_mtime)
    return {
        "ticker": ticker,
        "elapsed": round(elapsed, 2),
        "output": str(output_file),
    }


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    result = patch_and_run(ticker)
    print("\nDONE")
    print(f"  elapsed : {result['elapsed']}s")
    print(f"  output  : {result['output']}")
