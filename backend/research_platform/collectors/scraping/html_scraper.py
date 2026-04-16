"""
collectors/scraping/html_scraper.py
────────────────────────────────────
BeautifulSoup + httpx HTML scraping utilities.
Used by collectors that have no official API or RSS feed.
Wraps every request with retry, User-Agent rotation, and rate limiting.
"""

from __future__ import annotations

import random
import time
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

DEFAULT_TIMEOUT = 30
DEFAULT_DELAY   = 1.5   # seconds between requests — be polite


def _headers(referer: str = "") -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
    }


def fetch_html(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = 3,
    delay: float = DEFAULT_DELAY,
    referer: str = "",
    params: Optional[dict] = None,
) -> Optional[BeautifulSoup]:
    """
    Fetch a URL and return a parsed BeautifulSoup object.
    Returns None on failure after all retries.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                url,
                headers=_headers(referer),
                timeout=timeout,
                params=params,
                allow_redirects=True,
            )
            resp.raise_for_status()
            time.sleep(delay)
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            wait = delay * (2 ** (attempt - 1))
            logger.warning(f"[html_scraper] Attempt {attempt}/{retries} failed for {url}: {exc}")
            if attempt < retries:
                time.sleep(wait)
    return None


def fetch_json_api(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = 3,
    delay: float = DEFAULT_DELAY,
    params: Optional[dict] = None,
    referer: str = "",
) -> Optional[Any]:
    """
    Fetch a hidden/unofficial JSON endpoint (XHR-style).
    Returns parsed JSON or None on failure.
    """
    hdrs = _headers(referer)
    hdrs["Accept"] = "application/json, text/javascript, */*; q=0.01"
    hdrs["X-Requested-With"] = "XMLHttpRequest"

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=hdrs, timeout=timeout, params=params)
            resp.raise_for_status()
            time.sleep(delay)
            return resp.json()
        except Exception as exc:
            wait = delay * (2 ** (attempt - 1))
            logger.warning(f"[html_scraper] JSON attempt {attempt}/{retries} failed for {url}: {exc}")
            if attempt < retries:
                time.sleep(wait)
    return None


def extract_table(soup: BeautifulSoup, table_index: int = 0) -> list[dict[str, str]]:
    """
    Extract the Nth HTML table from a page as a list of dicts.
    Column names are taken from <th> elements in the first row.
    """
    tables = soup.find_all("table")
    if not tables or table_index >= len(tables):
        return []
    table = tables[table_index]
    rows = table.find_all("tr")
    if not rows:
        return []

    # Header
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    if not headers:
        return []

    result = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) == len(headers):
            result.append(dict(zip(headers, cells)))
    return result
