"""
collectors/scraping/pdf_extractor.py
──────────────────────────────────────
PDF text and table extraction using pdfplumber.
Used for RBI minutes, SEBI orders, Budget docs, OPEC reports, and any
other source that publishes data as PDFs.

Fallback: pytesseract OCR for scanned PDFs where pdfplumber returns empty text.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any, Optional

import requests
from loguru import logger

TIMEOUT = 60


def download_pdf(url: str, timeout: int = TIMEOUT) -> Optional[bytes]:
    """Download a PDF from a URL and return raw bytes."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        if "pdf" not in resp.headers.get("Content-Type", "").lower() and not url.lower().endswith(".pdf"):
            logger.warning(f"[pdf_extractor] URL may not be a PDF: {url}")
        return resp.content
    except Exception as exc:
        logger.error(f"[pdf_extractor] Failed to download {url}: {exc}")
        return None


def extract_text(pdf_bytes: bytes, max_pages: Optional[int] = None) -> str:
    """
    Extract full text from a PDF using pdfplumber.
    Falls back to pytesseract OCR if pdfplumber returns empty text.
    Returns empty string if both methods fail.
    """
    try:
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError:
        logger.error("[pdf_extractor] pdfplumber not installed. Run: pip install pdfplumber")
        return ""

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
            text = "\n\n".join(
                p.extract_text() or "" for p in pages
            ).strip()

        if text:
            return text

        # pdfplumber returned empty — likely a scanned PDF, try OCR
        logger.info("[pdf_extractor] pdfplumber returned empty text — attempting OCR")
        return _ocr_fallback(pdf_bytes, max_pages)

    except Exception as exc:
        logger.error(f"[pdf_extractor] pdfplumber error: {exc}")
        return _ocr_fallback(pdf_bytes, max_pages)


def extract_tables(pdf_bytes: bytes, max_pages: Optional[int] = None) -> list[list[list[Any]]]:
    """
    Extract tables from a PDF using pdfplumber.
    Returns a list of tables; each table is a list of rows; each row is a list of cell values.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("[pdf_extractor] pdfplumber not installed")
        return []

    all_tables = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
            for page in pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as exc:
        logger.error(f"[pdf_extractor] Table extraction error: {exc}")
    return all_tables


def _ocr_fallback(pdf_bytes: bytes, max_pages: Optional[int]) -> str:
    """Use pytesseract to OCR a scanned PDF. Requires pdf2image + poppler."""
    try:
        import pytesseract  # type: ignore[import-untyped]
        from pdf2image import convert_from_bytes  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("[pdf_extractor] pytesseract/pdf2image not installed — OCR unavailable")
        return ""

    try:
        images = convert_from_bytes(pdf_bytes, dpi=200)
        if max_pages:
            images = images[:max_pages]
        return "\n\n".join(pytesseract.image_to_string(img) for img in images).strip()
    except Exception as exc:
        logger.error(f"[pdf_extractor] OCR failed: {exc}")
        return ""


def extract_text_from_url(url: str, max_pages: Optional[int] = None) -> str:
    """Convenience: download + extract text in one call."""
    pdf_bytes = download_pdf(url)
    if not pdf_bytes:
        return ""
    return extract_text(pdf_bytes, max_pages=max_pages)
