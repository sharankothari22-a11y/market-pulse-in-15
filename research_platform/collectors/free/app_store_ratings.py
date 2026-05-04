"""
collectors/free/app_store_ratings.py
──────────────────────────────────────
App store ratings — consumer sentiment proxy for B2C companies.
Source: Google Play Store (public) + Apple App Store RSS
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

# B2C companies with apps — (company_name, google_play_id, apple_app_id)
APP_MAP = [
    ("HDFC Bank",       "com.hdfcbank.mobilebanking",   "422386065"),
    ("ICICI Bank",      "com.csam.icici.bank.imobile",  "321954683"),
    ("Paytm",           "net.one97.paytm",              "473894718"),
    ("Zerodha Kite",    "com.zerodha.kite3",            "1260566518"),
    ("PhonePe",         "com.phonepe.app",              "1170497028"),
    ("Swiggy",          "bundl.technologies.swiggy",    "989540920"),
    ("Zomato",          "com.application.zomato",       "434618427"),
    ("Nykaa",           "com.fss.nykaa",                "1089681356"),
]
# Google Play Store informal API
GP_RATINGS_URL = "https://play.google.com/store/apps/details?id={app_id}&hl=en"
APPLE_RSS = "https://itunes.apple.com/in/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"

class AppStoreRatingsCollector(BaseCollector):
    source_name = "app_store_ratings"
    fallback_chain = ["api", "scrape", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Apple App Store ratings via public RSS (JSON)."""
        records = []
        today = target_date or date.today()
        for company, _, apple_id in APP_MAP[:6]:
            try:
                url = APPLE_RSS.format(app_id=apple_id)
                resp = requests.get(url, timeout=10,
                                    headers={"User-Agent": "Mozilla/5.0"})
                if not resp.ok:
                    continue
                data = resp.json()
                feed = data.get("feed", {})
                entry = feed.get("entry", [])
                if not entry:
                    continue
                # Average rating from recent reviews
                ratings = []
                for review in (entry if isinstance(entry, list) else [entry])[:20]:
                    r = review.get("im:rating", {}).get("label", "")
                    if r.isdigit():
                        ratings.append(int(r))
                if ratings:
                    avg = sum(ratings) / len(ratings)
                    rec = MacroIndicator(
                        indicator=f"AppRating/{company}/Apple",
                        date=today, value=round(avg, 2),
                        source="AppStore/Apple",
                    )
                    records.append(rec)
                    logger.debug(f"[app_ratings] {company}: {avg:.1f}/5 ({len(ratings)} reviews)")
            except Exception as e:
                logger.debug(f"[app_ratings] {company} Apple failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_macro_indicator(s, r)
        logger.info(f"[app_ratings] {len(records)} app ratings stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape Google Play Store ratings."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            records = []
            today = target_date or date.today()
            for company, gp_id, _ in APP_MAP[:5]:
                try:
                    url = GP_RATINGS_URL.format(app_id=gp_id)
                    resp = httpx.get(url, timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(resp.text, "lxml")
                    # Find rating element
                    rating_el = (soup.find("div", attrs={"itemprop": "ratingValue"}) or
                                 soup.find("meta", attrs={"itemprop": "ratingValue"}))
                    if rating_el:
                        val_str = (rating_el.get("content") or rating_el.get_text(strip=True)).replace(",",".")
                        try:
                            rec = MacroIndicator(
                                indicator=f"AppRating/{company}/GooglePlay",
                                date=today, value=float(val_str),
                                source="AppStore/Google",
                            )
                            records.append(rec)
                        except ValueError:
                            pass
                except Exception:
                    continue
            if not records:
                return None
            with get_session() as s:
                for r in records:
                    upsert_macro_indicator(s, r)
            return CollectionResult(source_name=self.source_name, records=records, status="partial", method_used="scrape")
        except Exception as e:
            logger.warning(f"[app_ratings] scrape failed: {e}")
            return None
