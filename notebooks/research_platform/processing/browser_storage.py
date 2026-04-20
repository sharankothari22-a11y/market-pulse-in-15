"""
processing/browser_storage.py
───────────────────────────────
Read browser localStorage / sessionStorage from live pages.
Useful when sites cache API responses in storage (e.g., NSE caches
option chain data in localStorage before rendering).

Requires Playwright:
  pip install playwright && playwright install chromium

How it works:
  Sites often store API data in localStorage to avoid re-fetching.
  If you open DevTools → Application → Local Storage on NSE, you can
  see keys like "optionChain_NIFTY". This module automates reading them.
"""
from __future__ import annotations
from typing import Optional
from loguru import logger


def read_local_storage(url: str, wait_ms: int = 3000) -> dict:
    """
    Load a URL in headless Chromium and read its localStorage.
    Returns all key-value pairs as a dict.

    Example:
        data = read_local_storage("https://www.nseindia.com/option-chain")
        # Look for cached option chain data
    """
    try:
        from processing.playwright_scraper import read_browser_storage
        result = read_browser_storage(url, storage_type="localStorage")
        logger.info(f"[browser_storage] Read {len(result)} localStorage keys from {url}")
        return result
    except ImportError:
        logger.warning("[browser_storage] playwright_scraper not available")
        return {}


def read_session_storage(url: str) -> dict:
    """
    Load a URL and read its sessionStorage.
    """
    try:
        from processing.playwright_scraper import read_browser_storage
        result = read_browser_storage(url, storage_type="sessionStorage")
        logger.info(f"[browser_storage] Read {len(result)} sessionStorage keys from {url}")
        return result
    except ImportError:
        logger.warning("[browser_storage] playwright_scraper not available")
        return {}


def find_api_data_in_storage(url: str, keywords: Optional[list[str]] = None) -> dict:
    """
    Read localStorage and filter keys that likely contain API data.
    Looks for JSON-serialised values containing financial keywords.

    Example:
        data = find_api_data_in_storage(
            "https://www.nseindia.com/option-chain",
            keywords=["optionChain", "strikePrice", "CE", "PE"]
        )
    """
    import json
    storage = read_local_storage(url)
    keywords = keywords or ["price", "data", "result", "stock", "market"]
    found = {}
    for key, value in storage.items():
        if not value:
            continue
        if any(kw.lower() in key.lower() for kw in keywords):
            try:
                found[key] = json.loads(value)
            except Exception:
                found[key] = value
        elif any(kw.lower() in str(value).lower() for kw in keywords):
            try:
                found[key] = json.loads(value)
            except Exception:
                found[key] = value[:500]
    return found
