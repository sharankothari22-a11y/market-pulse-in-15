"""
processing/cleaner.py
──────────────────────
Data cleaning utilities applied to raw collected records
before they reach the database.
"""

from __future__ import annotations

import re
from typing import Any, Optional


def strip_whitespace(record: dict[str, Any]) -> dict[str, Any]:
    """Strip leading/trailing whitespace from all string fields."""
    return {
        k: (v.strip() if isinstance(v, str) else v)
        for k, v in record.items()
    }


def normalise_ticker(ticker: str, exchange: str = "NSE") -> str:
    """Uppercase, strip spaces, remove -EQ suffix common in NSE files."""
    t = ticker.strip().upper()
    if exchange == "NSE":
        t = re.sub(r"-EQ$", "", t)
    return t


def coerce_numeric(value: Any) -> Optional[float]:
    """Convert value to float, stripping commas. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[,\s₹$]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalise_indian_number(value: str) -> Optional[float]:
    """
    Parse Indian number format strings, e.g. '1,23,456.78' → 123456.78
    Also handles crore/lakh suffixes.
    """
    if not value:
        return None
    v = str(value).strip().upper()
    multiplier = 1.0
    if v.endswith("CR") or v.endswith("CR."):
        multiplier = 1e7
        v = v.rstrip(".").rstrip("CR").strip()
    elif "LAKH" in v:
        multiplier = 1e5
        v = re.sub(r"LAKH?S?", "", v).strip()
    elif v.endswith("L"):
        multiplier = 1e5
        v = v[:-1].strip()
    cleaned = re.sub(r"[,\s]", "", v)
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """Apply all cleaning steps to a raw record dict."""
    record = strip_whitespace(record)
    return record
