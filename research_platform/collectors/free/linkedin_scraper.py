"""
collectors/free/linkedin_scraper.py
─────────────────────────────────────
LinkedIn public profile scraping for executive/analyst commentary.
Source: LinkedIn public profiles (no login needed for basic data)
Uses Playwright for JS-rendered pages.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import NewsArticle
from database.queries import upsert_news_article

# Key Indian financial executives / analysts to monitor
PROFILES = [
    {"name": "Nilesh Shah",    "url": "https://www.linkedin.com/in/nilesh-shah-kotak/"},
    {"name": "Prashant Jain",  "url": "https://www.linkedin.com/in/prashant-jain-3rdbridge/"},
    {"name": "Saurabh Mukherjea","url": "https://www.linkedin.com/in/saurabh-mukherjea/"},
    {"name": "Raamdeo Agrawal","url": "https://www.linkedin.com/in/raamdeo-agrawal/"},
]

class LinkedinScraperCollector(BaseCollector):
    source_name = "linkedin_scraper"
    fallback_chain = ["scrape", "cache"]

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Use Playwright to scrape LinkedIn public activity."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("[linkedin] Playwright not installed. Run: playwright install chromium")
            return self._try_api(target_date)

        records = []
        today = target_date or date.today()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = ctx.new_page()

            for profile in PROFILES[:3]:  # Rate limit
                try:
                    page.goto(profile["url"], wait_until="networkidle", timeout=20000)
                    # Extract recent activity / posts
                    posts = page.query_selector_all(".feed-shared-update-v2__description, .break-words")
                    for post in posts[:3]:
                        text = post.inner_text().strip()
                        if len(text) > 50:
                            art = NewsArticle(
                                title=f"[LinkedIn/{profile['name']}] {text[:200]}",
                                body=text[:2000],
                                source=f"LinkedIn/{profile['name']}",
                                source_url=profile["url"],
                            )
                            records.append(art)
                except Exception as e:
                    logger.debug(f"[linkedin] {profile['name']} failed: {e}")

            browser.close()

        if not records:
            return None

        with get_session() as s:
            for art in records:
                upsert_news_article(s, art)

        logger.info(f"[linkedin] {len(records)} posts stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="scrape")

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Fallback: scrape without Playwright using httpx."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            records = []
            today = target_date or date.today()
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept-Language": "en-US,en;q=0.9",
            }
            for profile in PROFILES[:2]:
                try:
                    resp = httpx.get(profile["url"], headers=headers, timeout=15, follow_redirects=True)
                    soup = BeautifulSoup(resp.text, "lxml")
                    # Extract any visible text content
                    for el in soup.select(".profile-position, .pv-about-section, h1, h2")[:5]:
                        text = el.get_text(strip=True)
                        if len(text) > 20:
                            art = NewsArticle(
                                title=f"[LinkedIn/{profile['name']}] {text[:200]}",
                                source=f"LinkedIn/{profile['name']}",
                                source_url=profile["url"],
                            )
                            records.append(art)
                except Exception:
                    continue
            if not records:
                return None
            with get_session() as s:
                for art in records:
                    upsert_news_article(s, art)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="api")
        except Exception as e:
            logger.warning(f"[linkedin] httpx fallback failed: {e}")
            return None
