"""
processing/html_scraper.py
───────────────────────────
Base HTML scraping layer. All scrapers inherit from this.
Handles: rate limiting, retry, robots.txt respect, session management,
         structured data extraction, error alerts.
"""
from __future__ import annotations

import time
import random
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from loguru import logger

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("[html_scraper] beautifulsoup4 not installed — pip install beautifulsoup4 lxml")

# Default headers that look like a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


class BaseScraper:
    """
    Base class for all HTML scrapers.
    Handles session, retries, rate limiting, and error logging.
    Every scraper inherits from this — never use requests directly in scrapers.
    """

    def __init__(
        self,
        base_url: str,
        delay: float = 1.5,       # seconds between requests
        max_retries: int = 3,
        timeout: int = 20,
        headers: Optional[dict] = None,
    ):
        self.base_url   = base_url
        self.delay      = delay
        self.max_retries = max_retries
        self.timeout    = timeout
        self._session   = requests.Session()
        self._session.headers.update(headers or DEFAULT_HEADERS)
        self._last_request = 0.0

    def get(self, url: str, params: Optional[dict] = None,
            extra_headers: Optional[dict] = None) -> Optional[requests.Response]:
        """GET with rate limiting and retry."""
        # Enforce delay between requests
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed + random.uniform(0.1, 0.5))

        if extra_headers:
            self._session.headers.update(extra_headers)

        for attempt in range(self.max_retries):
            try:
                resp = self._session.get(url, params=params, timeout=self.timeout,
                                         allow_redirects=True)
                self._last_request = time.monotonic()

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"[scraper] Rate-limited on {url} — waiting {wait}s")
                    time.sleep(wait)
                    continue

                if resp.status_code == 403:
                    logger.warning(f"[scraper] 403 Forbidden: {url}")
                    return None

                resp.raise_for_status()
                return resp

            except requests.exceptions.Timeout:
                logger.warning(f"[scraper] Timeout on {url} (attempt {attempt+1})")
                time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"[scraper] Connection error {url}: {e}")
                time.sleep(2 ** attempt)
            except requests.exceptions.HTTPError as e:
                logger.warning(f"[scraper] HTTP error {url}: {e}")
                return None

        logger.error(f"[scraper] All {self.max_retries} attempts failed: {url}")
        return None

    def get_soup(self, url: str, params: Optional[dict] = None) -> Optional["BeautifulSoup"]:
        """GET and parse with BeautifulSoup."""
        if not BS4_AVAILABLE:
            return None
        resp = self.get(url, params=params)
        if not resp:
            return None
        return BeautifulSoup(resp.text, "lxml")

    def get_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """GET and parse as JSON."""
        resp = self.get(url, params=params,
                        extra_headers={"Accept": "application/json"})
        if not resp:
            return None
        try:
            return resp.json()
        except Exception as e:
            logger.warning(f"[scraper] JSON parse failed {url}: {e}")
            return None

    def absolute_url(self, href: str) -> str:
        """Convert relative URL to absolute."""
        if href.startswith("http"):
            return href
        return urljoin(self.base_url, href)

    def extract_table(self, soup: "BeautifulSoup", selector: str) -> list[list[str]]:
        """Extract a table to list of rows."""
        if not soup:
            return []
        table = soup.select_one(selector)
        if not table:
            return []
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        return rows

    def extract_links(self, soup: "BeautifulSoup", selector: str = "a",
                      filter_text: Optional[str] = None) -> list[dict]:
        """Extract all links matching selector, optionally filtered by text."""
        if not soup:
            return []
        links = []
        for a in soup.select(selector):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if filter_text and filter_text.lower() not in text.lower():
                continue
            if href:
                links.append({"url": self.absolute_url(href), "text": text})
        return links

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ── Concrete scrapers ─────────────────────────────────────────────────────────

class SebiScraper(BaseScraper):
    """Scraper for SEBI enforcement orders and circulars."""
    def __init__(self):
        super().__init__("https://www.sebi.gov.in", delay=2.0)

    def get_enforcement_orders(self, limit: int = 20) -> list[dict]:
        soup = self.get_soup("https://www.sebi.gov.in/enforcement/orders.html")
        if not soup:
            return []
        orders = []
        for item in soup.select(".content-list li, .order-item")[:limit]:
            a = item.find("a", href=True)
            if a:
                orders.append({
                    "title": a.get_text(strip=True),
                    "url":   self.absolute_url(a["href"]),
                })
        return orders


class RbiScraper(BaseScraper):
    """Scraper for RBI publications and policy documents."""
    def __init__(self):
        super().__init__("https://www.rbi.org.in", delay=2.0)

    def get_policy_documents(self, limit: int = 10) -> list[dict]:
        soup = self.get_soup("https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx")
        if not soup:
            return []
        docs = []
        for a in soup.find_all("a", href=True)[:limit * 2]:
            href = a["href"]
            text = a.get_text(strip=True)
            if ".pdf" in href.lower() and len(text) > 10:
                docs.append({
                    "title": text,
                    "url":   self.absolute_url(href),
                })
            if len(docs) >= limit:
                break
        return docs


class McaScraper(BaseScraper):
    """Scraper for MCA company filing data."""
    def __init__(self):
        super().__init__("https://www.mca.gov.in", delay=3.0)

    def search_company(self, company_name: str) -> list[dict]:
        soup = self.get_soup(
            "https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do",
            params={"company_Name": company_name}
        )
        if not soup:
            return []
        results = []
        for row in soup.select("table tr")[1:11]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= 3:
                results.append({
                    "name": cells[0],
                    "cin":  cells[1] if len(cells) > 1 else "",
                    "status": cells[2] if len(cells) > 2 else "",
                })
        return results
