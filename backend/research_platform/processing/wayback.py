"""
processing/wayback.py
──────────────────────
Web Archive (Wayback Machine) fallback.
Used for: historical deleted pages, old filings, archived news.
CDX API — free, structured, no key needed.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import requests
from loguru import logger

CDX_API = "http://web.archive.org/cdx/search/cdx"
WAYBACK = "https://web.archive.org/web"


def get_archived_url(url: str, closest_to: Optional[date] = None) -> Optional[str]:
    """
    Get the Wayback Machine URL for an archived version of a page.
    Returns the archive URL or None if not found.
    """
    params = {
        "url":    url,
        "output": "json",
        "limit":  1,
        "fl":     "timestamp,original,statuscode",
        "filter": "statuscode:200",
    }
    if closest_to:
        params["closest"] = closest_to.strftime("%Y%m%d")
        params["output"]  = "json"

    try:
        resp = requests.get(CDX_API, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json()
        if len(results) > 1:  # First row is headers
            ts = results[1][0]
            return f"{WAYBACK}/{ts}/{url}"
    except Exception as e:
        logger.debug(f"[wayback] CDX lookup failed for {url}: {e}")
    return None


def fetch_archived_content(url: str, closest_to: Optional[date] = None) -> Optional[str]:
    """
    Fetch the HTML content of an archived page.
    Returns text content or None.
    """
    archive_url = get_archived_url(url, closest_to)
    if not archive_url:
        logger.debug(f"[wayback] No archive found for {url}")
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get(archive_url, headers=headers, timeout=20)
        resp.raise_for_status()
        logger.info(f"[wayback] Retrieved archived version of {url}")
        return resp.text
    except Exception as e:
        logger.warning(f"[wayback] Fetch failed for archived {url}: {e}")
        return None


def search_archives(query: str, domain: str = "", limit: int = 10,
                    from_date: Optional[date] = None,
                    to_date: Optional[date] = None) -> list[dict]:
    """
    Search Wayback CDX for archived pages matching a domain/query.
    Useful for finding historical versions of deleted SEBI/RBI pages.
    """
    params = {
        "url":    f"{domain}/*" if domain and not query else query,
        "output": "json",
        "limit":  limit,
        "fl":     "timestamp,original,mimetype,statuscode,length",
        "filter": "statuscode:200",
        "collapse": "urlkey",
    }
    if from_date:
        params["from"] = from_date.strftime("%Y%m%d")
    if to_date:
        params["to"] = to_date.strftime("%Y%m%d")

    try:
        resp = requests.get(CDX_API, params=params, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
        if len(rows) <= 1:
            return []
        headers_row = rows[0]
        return [
            dict(zip(headers_row, row)) for row in rows[1:]
        ]
    except Exception as e:
        logger.debug(f"[wayback] Search failed: {e}")
        return []
