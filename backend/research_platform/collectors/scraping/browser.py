"""
collectors/scraping/browser.py
───────────────────────────────
Playwright browser automation for JS-rendered pages.
Used for sources that require login or JavaScript rendering.

NOTE: Playwright must be installed separately:
    pip install playwright
    playwright install chromium

This module is imported lazily so the rest of the system works even if
Playwright is not installed. Collectors that need it check availability
via is_available() before importing.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger


def is_available() -> bool:
    """Return True if playwright-python is installed."""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_rendered_html(
    url: str,
    wait_for: str = "networkidle",
    timeout_ms: int = 30_000,
    headless: bool = True,
) -> Optional[str]:
    """
    Load a page in a headless Chromium browser and return the fully rendered HTML.
    Returns None if Playwright is unavailable or the page fails to load.

    Args:
        url: Page URL to load.
        wait_for: Playwright wait_until strategy ('load', 'networkidle', 'domcontentloaded').
        timeout_ms: Max ms to wait for the page.
        headless: Run browser headlessly (default True).
    """
    if not is_available():
        logger.warning("[browser] Playwright not installed — skipping JS render.")
        return None

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-untyped]
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page.goto(url, wait_until=wait_for, timeout=timeout_ms)
            html = page.content()
            browser.close()
            return html
    except Exception as exc:
        logger.error(f"[browser] Playwright failed for {url}: {exc}")
        return None


def fetch_rendered_json(
    url: str,
    timeout_ms: int = 30_000,
) -> Optional[dict]:
    """
    Load a URL that returns JSON (XHR endpoint) and return the parsed response.
    """
    html = fetch_rendered_html(url, wait_for="networkidle", timeout_ms=timeout_ms)
    if not html:
        return None
    import json
    try:
        # The page body might be the raw JSON
        import re
        match = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL)
        raw = match.group(1) if match else html
        return json.loads(raw)
    except Exception:
        return None
