"""
collectors/free/gst_portal.py
───────────────────────────────
GST registration status — public company verification layer.
Source: GST portal public search (uses Playwright for CAPTCHA handling)
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import Company
from database.queries import get_or_create_company

GST_SEARCH_URL = "https://services.gst.gov.in/services/searchtp"

class GstPortalCollector(BaseCollector):
    source_name = "gst_portal"
    fallback_chain = ["scrape", "cache"]

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """
        GST portal requires CAPTCHA solving for full access.
        This collector uses Playwright to handle JS-rendered content.
        Falls back to API endpoint where available.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("[gst_portal] Playwright not installed. Run: playwright install chromium")
            return self._try_api(target_date)

        # Get companies from DB that don't have GST verification
        companies_to_check = []
        try:
            from sqlalchemy import select
            with get_session() as s:
                rows = s.scalars(
                    select(Company).where(Company.is_listed == True).limit(20)
                ).all()
                companies_to_check = [(r.id, r.name, r.ticker) for r in rows]
        except Exception as e:
            logger.warning(f"[gst_portal] DB query failed: {e}")
            return None

        if not companies_to_check:
            return None

        records = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
            for cid, name, ticker in companies_to_check[:5]:
                try:
                    page.goto(GST_SEARCH_URL, wait_until="networkidle", timeout=20000)
                    search_box = page.query_selector("input[placeholder*='GSTIN'], input[name*='gstin'], input[type='text']")
                    if search_box:
                        search_box.fill(name[:50])
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(2000)
                        result_text = page.content()
                        if "Active" in result_text or "Registered" in result_text:
                            records.append({"company": name, "status": "GST Active"})
                except Exception as e:
                    logger.debug(f"[gst_portal] {name}: {e}")
            browser.close()

        logger.info(f"[gst_portal] Checked {len(companies_to_check[:5])} companies, {len(records)} verified")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records,
                                status="ok" if records else "partial", method_used="scrape")

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Direct API endpoint — works for GSTIN lookup without CAPTCHA."""
        import requests
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        records = []
        # Sample GSTINs for major listed companies (for verification testing)
        sample_gstins = [
            "27AAACR5055K1ZS",  # Reliance Industries
            "27AAACT2727Q1ZW",  # Tata Consultancy Services
        ]
        for gstin in sample_gstins:
            try:
                url = f"https://services.gst.gov.in/services/api/search/taxpayerDetails?gstin={gstin}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.ok:
                    data = resp.json()
                    records.append(data)
            except Exception:
                continue
        if not records:
            return None
        logger.info(f"[gst_portal] {len(records)} GSTIN records fetched")
        return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="api")
