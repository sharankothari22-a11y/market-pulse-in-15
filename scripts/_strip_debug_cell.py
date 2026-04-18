#!/usr/bin/env python3
"""Remove any cell tagged 'dcf-forecast-debug' from the committed notebook."""
from pathlib import Path
import nbformat

NB = Path(__file__).resolve().parent.parent / "notebooks" / "DCF_Multi_Source_Pipeline_REFACTORED.ipynb"
TAG = "dcf-forecast-debug"

nb = nbformat.read(str(NB), as_version=4)
before = len(nb.cells)
nb.cells = [c for c in nb.cells if TAG not in c.get("metadata", {}).get("tags", [])]
nbformat.write(nb, str(NB))
print(f"Cells: {before} -> {len(nb.cells)}")
