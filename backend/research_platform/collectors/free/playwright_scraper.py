"""
collectors/free/playwright_scraper.py
──────────────────────────────────────
Playwright browser automation — for JS-rendered pages.
Used when requests+BS4 returns empty or login-walled content.

Install:  pip install playwright && playwright install chromium

Targets currently using Playwright:
  - NSE derivatives page (JS-rendered OI tables)
  - Screener.in company pages (JS-rendered ratios)
  - Moneycontrol (JS-rendered news tickers)
"""
from __future__ import annotations
import os
import time
from datetime import date
from typing import Optional
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import NewsArticle
from database.queries import upsert_news_article

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


def _ensure_playwright() -> bool:
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning(
            "[playwright] playwright not installed. "
            "Run: pip install playwright && playwright install chromium"
        )
        return False
    return True


def fetch_js_page(url: str, wait_selector: Optional[str] = None,
                  timeout_ms: int = 20_000, headless: bool = True) -> Optional[str]:
    """
    Fetch a JS-rendered page and return its HTML after the DOM settles.
    Returns None if playwright is unavailable or fetch fails.
    """
    if not _ensure_playwright():
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=timeout_ms)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.warning(f"[playwright] fetch failed {url}: {e}")
        return None


def extract_network_requests(url: str, filter_path: str = "",
                              timeout_ms: int = 15_000) -> list[dict]:
    """
    Capture all XHR/fetch network requests made by a page.
    Use this to reverse-engineer hidden API endpoints.

    Example:
        reqs = extract_network_requests("https://www.nseindia.com/market-data/oi-spurts")
        # Inspect reqs to find the hidden API URL the page calls
    """
    if not _ensure_playwright():
        return []
    captured = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def on_request(request):
                if filter_path in request.url:
                    captured.append({
                        "url":     request.url,
                        "method":  request.method,
                        "headers": dict(request.headers),
                    })

            page.on("request", on_request)
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            browser.close()
    except Exception as e:
        logger.warning(f"[playwright] network capture failed: {e}")
    return captured


def read_browser_storage(url: str, storage_type: str = "localStorage") -> dict:
    """
    Read browser localStorage or sessionStorage from a page.
    Useful for sites that cache API responses in storage.

    storage_type: "localStorage" | "sessionStorage"
    """
    if not _ensure_playwright():
        return {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20_000, wait_until="networkidle")
            data = page.evaluate(f"""() => {{
                const result = {{}};
                const store = window.{storage_type};
                for (let i = 0; i < store.length; i++) {{
                    const key = store.key(i);
                    result[key] = store.getItem(key);
                }}
                return result;
            }}""")
            browser.close()
            return data or {}
    except Exception as e:
        logger.warning(f"[playwright] storage read failed {url}: {e}")
        return {}


class PlaywrightNewsCollector(BaseCollector):
    """
    Collects JS-rendered news from Moneycontrol top stories.
    Falls back to RSS if Playwright unavailable.
    """
    source_name    = "playwright_news"
    fallback_chain = ["scrape", "cache"]

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        if not _ensure_playwright():
            return None
        from bs4 import BeautifulSoup
        html = fetch_js_page(
            "https://www.moneycontrol.com/news/",
            wait_selector=".clearfix.MT15",
            timeout_ms=25_000,
        )
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")
        records = []
        for item in soup.select("li.clearfix")[:20]:
            a = item.find("a", href=True)
            if not a:
                continue
            title = a.get_text(strip=True)
            href  = a["href"]
            if not title or len(title) < 15:
                continue
            art = NewsArticle(
                title=title[:500],
                source="Moneycontrol/Playwright",
                source_url=href[:1000] if href.startswith("http") else None,
            )
            records.append(art)

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_news_article(s, r)
        logger.info(f"[playwright_news] {len(records)} articles stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(
            source_name=self.source_name, records=records, status="ok", method_used="scrape"
        )
