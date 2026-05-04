"""
processing/normalizer.py
─────────────────────────
Normalises data from different sources into a common schema
before ORM model instantiation.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from processing.cleaner import coerce_numeric, normalise_ticker


def normalise_date(value: Any) -> Optional[date]:
    """
    Convert various date representations to a Python date object.
    Handles: date, datetime, ISO strings, '%d-%b-%Y', '%d%m%Y', etc.
    """
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%b-%Y",  # 01-Jan-2024
        "%d%m%Y",    # 01012024
        "%Y%m%d",    # 20240101
        "%b %d, %Y",
        "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalise_nse_price_row(row: dict[str, Any], trade_date: date) -> dict[str, Any]:
    """Normalise a raw NSE Bhavcopy row into price_history schema."""
    return {
        "ticker": normalise_ticker(str(row.get("SYMBOL", row.get("Symbol", "")))),
        "date": trade_date,
        "open": coerce_numeric(row.get("OPEN", row.get("Open"))),
        "high": coerce_numeric(row.get("HIGH", row.get("High"))),
        "low": coerce_numeric(row.get("LOW", row.get("Low"))),
        "close": coerce_numeric(row.get("CLOSE", row.get("Close"))),
        "volume": coerce_numeric(row.get("TOTTRDQTY", row.get("TotalTradedQuantity"))),
        "exchange": "NSE",
    }


def normalise_fred_observation(
    series_id: str, obs_date: Any, value: Any, country_id: Optional[int]
) -> dict[str, Any]:
    """Normalise a FRED observation into macro_indicators schema."""
    return {
        "country_id": country_id,
        "indicator": series_id,
        "date": normalise_date(obs_date),
        "value": coerce_numeric(value),
        "source": "FRED",
    }
