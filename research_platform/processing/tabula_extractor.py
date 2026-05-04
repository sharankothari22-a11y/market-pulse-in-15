"""
processing/tabula_extractor.py
────────────────────────────────
tabula-py wrapper for complex PDF table extraction.
Use when pdfplumber returns malformed or merged cells.

Install: pip install tabula-py
Requires Java: apt-get install default-jre  (or download from adoptium.net)

When to use tabula vs pdfplumber vs camelot:
  pdfplumber  — best for most PDFs with clean text layers (primary)
  camelot     — lattice mode for PDFs with visible grid lines
  tabula      — stream mode for borderless tables; good for SEBI annual reports
"""
from __future__ import annotations
import io
import tempfile
from pathlib import Path
from typing import Any, Optional, Union
from loguru import logger


def extract_tables_tabula(
    pdf_path: Union[str, Path, bytes, io.BytesIO],
    pages: str = "all",
    lattice: bool = False,
    area: Optional[list] = None,
) -> list[list[list[str]]]:
    """
    Extract tables from a PDF using tabula-py.
    Returns list of tables, each table is list of rows, each row is list of strings.

    Args:
        pdf_path: file path, bytes, or BytesIO
        pages:    "all" | "1" | "1,3" | "1-4"
        lattice:  True for bordered tables, False for borderless/stream mode
        area:     [top, left, bottom, right] in % of page to restrict extraction

    Returns: list of tables (list of list of list of str)
    """
    try:
        import tabula
    except ImportError:
        logger.warning("[tabula] tabula-py not installed. Run: pip install tabula-py")
        return []

    # Normalise input
    if isinstance(pdf_path, io.BytesIO):
        pdf_path = pdf_path.read()
    if isinstance(pdf_path, bytes):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_path)
            tmp_path = f.name
    else:
        tmp_path = str(pdf_path)

    kwargs: dict[str, Any] = {
        "pages":    pages,
        "lattice":  lattice,
        "stream":   not lattice,
        "guess":    True,
        "silent":   True,
        "pandas_options": {"dtype": str, "keep_default_na": False},
    }
    if area:
        kwargs["area"] = area

    try:
        dfs = tabula.read_pdf(tmp_path, **kwargs)
        tables = []
        for df in dfs:
            if df.empty:
                continue
            # Include header as first row
            rows = [list(df.columns)]
            for _, row in df.iterrows():
                rows.append([str(v).strip() for v in row.values])
            tables.append(rows)
        return tables
    except Exception as e:
        logger.warning(f"[tabula] Extraction failed: {e}")
        return []
    finally:
        if isinstance(pdf_path, bytes):
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass


def extract_sebi_annual_report_tables(url: str) -> list[dict]:
    """
    Specialist wrapper for SEBI annual report PDFs.
    SEBI uses borderless tables that tabula handles better than pdfplumber.
    """
    import requests
    try:
        resp = requests.get(url, timeout=30,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[tabula] SEBI download failed {url}: {e}")
        return []

    tables = extract_tables_tabula(
        resp.content,
        lattice=False,  # SEBI reports use borderless tables
        pages="all",
    )
    result = []
    for i, table in enumerate(tables):
        if len(table) >= 2:
            result.append({"table_index": i, "rows": table, "row_count": len(table)})
    logger.info(f"[tabula] Extracted {len(result)} tables from SEBI report")
    return result
