"""
collectors/scraping/wayback.py
───────────────────────────────
Wayback Machine (Internet Archive) CDX API client.
Used to retrieve archived versions of pages/files when the live source is
unavailable or when historical snapshots are needed.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests
from loguru import logger

CDX_API = "http://web.archive.org/cdx/search/cdx"
WAYBACK_PREFIX = "https://web.archive.org/web"
TIMEOUT = 30


def get_snapshot_url(
    original_url: str,
    target_date: Optional[date] = None,
    output: str = "json",
) -> Optional[str]:
    """
    Find the closest Wayback Machine snapshot for original_url.
    If target_date is given, finds the closest snapshot to that date.
    Returns a wayback URL string or None if not found.
    """
    params: dict = {
        "url": original_url,
        "output": output,
        "limit": 1,
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
    }
    if target_date:
        params["closest"] = target_date.strftime("%Y%m%d")
        params["output"] = "json"

    try:
        resp = requests.get(CDX_API, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        # data[0] is the header row, data[1] is the first result
        if len(data) < 2:
            logger.info(f"[wayback] No snapshot found for {original_url}")
            return None
        timestamp = data[1][0]
        return f"{WAYBACK_PREFIX}/{timestamp}/{original_url}"
    except Exception as exc:
        logger.error(f"[wayback] CDX lookup failed for {original_url}: {exc}")
        return None


def fetch_archived_html(
    original_url: str,
    target_date: Optional[date] = None,
) -> Optional[str]:
    """
    Fetch HTML content from the Wayback Machine archive.
    Returns raw HTML string or None.
    """
    snapshot_url = get_snapshot_url(original_url, target_date)
    if not snapshot_url:
        return None
    try:
        resp = requests.get(snapshot_url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        logger.error(f"[wayback] Failed to fetch snapshot {snapshot_url}: {exc}")
        return None


def list_snapshots(
    original_url: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 10,
) -> list[dict]:
    """
    List available snapshots for a URL within a date range.
    Returns list of dicts with keys: timestamp, url, statuscode.
    """
    params: dict = {
        "url": original_url,
        "output": "json",
        "limit": limit,
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
    }
    if from_date:
        params["from"] = from_date.strftime("%Y%m%d")
    if to_date:
        params["to"] = to_date.strftime("%Y%m%d")

    try:
        resp = requests.get(CDX_API, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
        if len(rows) < 2:
            return []
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]
    except Exception as exc:
        logger.error(f"[wayback] List snapshots failed: {exc}")
        return []
