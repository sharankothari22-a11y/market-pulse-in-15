"""
processing/hidden_api.py
─────────────────────────
Hidden API discovery and caller.
"Turning a no-API site into an API" — reverse-engineer XHR endpoints
from browser DevTools, then call them directly with proper headers.

How to use:
    1. Open the target site in Chrome DevTools → Network tab → XHR filter
    2. Copy the request URL, headers (especially cookies/tokens)
    3. Add an entry to KNOWN_HIDDEN_APIS below
    4. Call hidden_get(api_name, params) anywhere in the codebase

Pre-discovered APIs already working:
    nse_option_chain  — NSE official option chain (unofficial stable endpoint)
    nse_oi_spurts     — NSE OI spurts (unofficial)
    screener_ratios   — Screener.in company data endpoint (unofficial)
"""
from __future__ import annotations
import time
from typing import Any, Optional
import requests
from loguru import logger

# ── Discovered hidden APIs ────────────────────────────────────────────────────
# Format: name → {url_template, headers, method, notes}
# Rotate cookies/tokens when they expire.
KNOWN_HIDDEN_APIS: dict[str, dict] = {
    "nse_option_chain": {
        "url":     "https://www.nseindia.com/api/option-chain-indices?symbol={symbol}",
        "headers": {
            "User-Agent":  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept":      "application/json, text/plain, */*",
            "Referer":     "https://www.nseindia.com/option-chain",
            "X-Requested-With": "XMLHttpRequest",
        },
        "method":  "GET",
        "notes":   "Requires Referer header + NSE session cookie from homepage visit",
    },
    "nse_oi_spurts": {
        "url":     "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings",
        "headers": {
            "User-Agent":  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept":      "application/json",
            "Referer":     "https://www.nseindia.com/market-data/oi-spurts",
        },
        "method":  "GET",
        "notes":   "Rate limit: ~10 req/min. Use session cookie from homepage.",
    },
    "screener_ratios": {
        "url":     "https://www.screener.in/company/{ticker}/consolidated/",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept":     "text/html,application/xhtml+xml",
            "Referer":    "https://www.screener.in/",
        },
        "method":  "GET",
        "notes":   "Returns HTML; parse with BeautifulSoup. No JSON endpoint available.",
    },
    "moneycontrol_stock": {
        "url":     "https://priceapi.moneycontrol.com/pricefeed/nse/equitys/{mc_code}",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept":     "application/json",
            "Origin":     "https://www.moneycontrol.com",
            "Referer":    "https://www.moneycontrol.com/",
        },
        "method":  "GET",
        "notes":   "mc_code is Moneycontrol internal ID (e.g. RELI for Reliance).",
    },
    "trendlyne_drhp": {
        "url":     "https://trendlyne.com/research-reports/ipo/{ticker}/",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept":     "text/html",
            "Referer":    "https://trendlyne.com/",
        },
        "method":  "GET",
        "notes":   "HTML scrape — no hidden JSON available for this endpoint.",
    },
}


class HiddenApiSession:
    """
    Manages a session for a target site — handles the initial homepage visit
    to capture session cookies before calling the hidden API.
    """

    def __init__(self, base_url: str, delay: float = 1.0):
        self.base_url  = base_url
        self.delay     = delay
        self._session  = requests.Session()
        self._warmed   = False
        self._last_req = 0.0

    def warm(self, homepage: Optional[str] = None) -> bool:
        """
        Visit the homepage to capture session cookies.
        Many NSE/BSE hidden APIs require a valid session cookie.
        """
        url = homepage or self.base_url
        try:
            self._session.get(url, timeout=10,
                              headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            self._warmed = True
            logger.debug(f"[hidden_api] Session warmed for {url}")
            return True
        except Exception as e:
            logger.warning(f"[hidden_api] Warm failed for {url}: {e}")
            return False

    def get(self, url: str, headers: Optional[dict] = None,
            params: Optional[dict] = None) -> Optional[requests.Response]:
        """Rate-limited GET with session cookies intact."""
        elapsed = time.monotonic() - self._last_req
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        try:
            resp = self._session.get(url, headers=headers, params=params, timeout=15)
            self._last_req = time.monotonic()
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.warning(f"[hidden_api] GET failed {url}: {e}")
            return None


def hidden_get(api_name: str, url_params: Optional[dict] = None,
               query_params: Optional[dict] = None,
               session: Optional[HiddenApiSession] = None) -> Optional[Any]:
    """
    Call a known hidden API by name.
    Returns parsed JSON dict, or raw text if JSON parsing fails.

    Example:
        data = hidden_get("nse_option_chain", url_params={"symbol": "NIFTY"})
    """
    spec = KNOWN_HIDDEN_APIS.get(api_name)
    if not spec:
        logger.error(f"[hidden_api] Unknown API: '{api_name}'. "
                     f"Available: {list(KNOWN_HIDDEN_APIS)}")
        return None

    url = spec["url"]
    if url_params:
        url = url.format(**url_params)

    headers = dict(spec.get("headers", {}))

    if session:
        resp = session.get(url, headers=headers, params=query_params)
    else:
        try:
            resp = requests.get(url, headers=headers, params=query_params, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"[hidden_api] {api_name} failed: {e}")
            return None

    if not resp:
        return None

    try:
        return resp.json()
    except Exception:
        return resp.text


def discover_api_endpoints(url: str, filter_path: str = "/api/") -> list[dict]:
    """
    Use Playwright to capture all XHR/fetch calls a page makes.
    Requires playwright to be installed.

    Usage: find hidden APIs on any site:
        endpoints = discover_api_endpoints("https://www.nseindia.com/option-chain")
        for ep in endpoints:
            print(ep["url"])
    """
    try:
        from processing.playwright_scraper import extract_network_requests
        return extract_network_requests(url, filter_path=filter_path)
    except ImportError:
        logger.warning("[hidden_api] Playwright not available for endpoint discovery")
        return []
