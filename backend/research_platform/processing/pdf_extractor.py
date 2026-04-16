"""
processing/pdf_extractor.py
────────────────────────────
OCR / PDF extraction pipeline.
Handles: text PDFs, scanned PDFs, tables, RBI bulletins, SEBI orders, Budget docs.

Tools:
  pdfplumber  — text + tables from digital PDFs (primary)
  pytesseract — OCR for scanned/image PDFs (fallback)
  camelot     — complex table extraction (optional)
"""
from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from loguru import logger

# ── Extraction functions ──────────────────────────────────────────────────────


def extract_text_from_pdf(pdf_path: str | Path | bytes | io.BytesIO,
                           max_pages: int = 50) -> dict[str, Any]:
    """
    Extract text and tables from a PDF.
    Returns: {text, tables, page_count, method, error}
    """
    result = {"text": "", "tables": [], "page_count": 0, "method": None, "error": None}

    # Normalise input to bytes
    raw_bytes = _get_bytes(pdf_path)
    if not raw_bytes:
        result["error"] = "Could not read PDF"
        return result

    # Try pdfplumber first (best for digital PDFs)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            result["page_count"] = len(pdf.pages)
            texts, tables = [], []
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text() or ""
                texts.append(page_text)
                for table in (page.extract_tables() or []):
                    if table:
                        tables.append(table)
            full_text = "\n\n".join(texts).strip()
            result["text"]   = full_text
            result["tables"] = tables
            result["method"] = "pdfplumber"
            # If less than 100 chars per page on average, likely scanned
            if len(full_text) < result["page_count"] * 100 and result["page_count"] > 0:
                logger.info(f"[pdf_extractor] Low text density — trying OCR fallback")
                ocr_result = _ocr_fallback(raw_bytes, max_pages)
                if ocr_result and len(ocr_result) > len(full_text):
                    result["text"]   = ocr_result
                    result["method"] = "pdfplumber+ocr"
            return result
    except ImportError:
        logger.warning("[pdf_extractor] pdfplumber not installed — pip install pdfplumber")
    except Exception as e:
        logger.warning(f"[pdf_extractor] pdfplumber failed: {e}")

    # Fallback: OCR
    ocr_text = _ocr_fallback(raw_bytes, max_pages)
    if ocr_text:
        result["text"]   = ocr_text
        result["method"] = "ocr"
    else:
        result["error"] = "All extraction methods failed"
    return result


def extract_from_url(url: str, max_pages: int = 30) -> dict[str, Any]:
    """Download a PDF from URL and extract its text."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            return {"text": "", "tables": [], "error": "Not a PDF", "method": None, "page_count": 0}
        result = extract_text_from_pdf(resp.content, max_pages=max_pages)
        result["source_url"] = url
        return result
    except Exception as e:
        logger.warning(f"[pdf_extractor] URL fetch failed {url}: {e}")
        return {"text": "", "tables": [], "error": str(e), "method": None, "page_count": 0}


def extract_key_sections(text: str, doc_type: str = "general") -> dict[str, str]:
    """
    Extract named sections from a PDF text based on document type.
    doc_type: rbi_policy | sebi_order | annual_report | budget | general
    """
    sections = {}
    text_lower = text.lower()

    if doc_type == "rbi_policy":
        patterns = {
            "rate_decision":   r"(?:repo rate|policy rate)[^\n]{0,200}",
            "inflation":       r"(?:inflation|cpi)[^\n]{0,300}",
            "growth_outlook":  r"(?:gdp|growth|output gap)[^\n]{0,300}",
            "liquidity":       r"(?:liquidity|crr|slr)[^\n]{0,200}",
        }
    elif doc_type == "sebi_order":
        patterns = {
            "violation":       r"(?:violated|breach|contravention)[^\n]{0,300}",
            "penalty":         r"(?:penalty|fine|impound)[^\n]{0,200}",
            "entity":          r"(?:noticee|respondent|company)[^\n]{0,200}",
        }
    elif doc_type == "annual_report":
        patterns = {
            "revenue":         r"(?:revenue|total income)[^\n]{0,200}",
            "profit":          r"(?:profit after tax|pat|net profit)[^\n]{0,200}",
            "outlook":         r"(?:outlook|guidance|expect)[^\n]{0,400}",
            "management":      r"(?:managing director|ceo|chairman)[^\n]{0,300}",
        }
    elif doc_type == "budget":
        patterns = {
            "fiscal_deficit":  r"(?:fiscal deficit)[^\n]{0,200}",
            "tax_changes":     r"(?:income tax|gst|customs duty)[^\n]{0,300}",
            "pli_schemes":     r"(?:pli|production linked)[^\n]{0,300}",
            "capex":           r"(?:capital expenditure|infrastructure)[^\n]{0,300}",
        }
    else:
        patterns = {
            "summary":         r"(?:summary|overview|highlights)[^\n]{0,500}",
        }

    for section_name, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            sections[section_name] = " | ".join(matches[:3])

    return sections


def classify_pdf_type(text: str, url: str = "") -> str:
    """Auto-detect document type from content."""
    text_lower = text.lower()
    url_lower  = url.lower()

    if any(kw in text_lower for kw in ["monetary policy", "repo rate", "rbi"]):
        return "rbi_policy"
    if any(kw in text_lower for kw in ["sebi", "securities exchange", "noticee"]):
        return "sebi_order"
    if any(kw in text_lower for kw in ["annual report", "director's report", "auditor"]):
        return "annual_report"
    if any(kw in text_lower for kw in ["union budget", "fiscal deficit", "finance minister"]):
        return "budget"
    return "general"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_bytes(src) -> Optional[bytes]:
    if isinstance(src, bytes):
        return src
    if isinstance(src, io.BytesIO):
        return src.getvalue()
    if isinstance(src, (str, Path)):
        p = Path(src)
        if p.exists():
            return p.read_bytes()
    return None


def _ocr_fallback(raw_bytes: bytes, max_pages: int = 10) -> Optional[str]:
    """OCR using pytesseract for scanned PDFs."""
    try:
        import pytesseract
        from PIL import Image
        import pdf2image
    except ImportError:
        logger.warning("[pdf_extractor] pytesseract/pdf2image not installed for OCR")
        return None
    try:
        images = pdf2image.convert_from_bytes(raw_bytes, dpi=200, first_page=1, last_page=max_pages)
        texts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="eng")
            texts.append(text)
        return "\n\n".join(texts).strip()
    except Exception as e:
        logger.warning(f"[pdf_extractor] OCR failed: {e}")
        return None


# ── Convenience wrappers for common documents ─────────────────────────────────

def extract_rbi_policy_minutes(url: str) -> dict[str, Any]:
    result = extract_from_url(url, max_pages=30)
    if result["text"]:
        result["sections"] = extract_key_sections(result["text"], "rbi_policy")
        result["doc_type"] = "rbi_policy"
    return result


def extract_sebi_order(url: str) -> dict[str, Any]:
    result = extract_from_url(url, max_pages=20)
    if result["text"]:
        result["sections"] = extract_key_sections(result["text"], "sebi_order")
        result["doc_type"] = "sebi_order"
    return result


def extract_annual_report(url_or_path: str) -> dict[str, Any]:
    if url_or_path.startswith("http"):
        result = extract_from_url(url_or_path, max_pages=50)
    else:
        result = extract_text_from_pdf(url_or_path, max_pages=50)
    if result["text"]:
        result["sections"] = extract_key_sections(result["text"], "annual_report")
        result["doc_type"] = "annual_report"
    return result


def extract_budget_document(url: str) -> dict[str, Any]:
    result = extract_from_url(url, max_pages=100)
    if result["text"]:
        result["sections"] = extract_key_sections(result["text"], "budget")
        result["doc_type"] = "budget"
    return result
