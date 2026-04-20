"""
collectors/registry.py
──────────────────────
Complete registry — Phase 1 (14) + Phase 2 (19) + Phase 3 (10) + Paid (5) + v4 additions (3)
Total: 51 collectors.
"""
from __future__ import annotations
from typing import Type
from collectors.base import BaseCollector

# ── Phase 1: Free ─────────────────────────────────────────────────────────────
from collectors.free.nse_csv            import NseCsvCollector
from collectors.free.fred               import FredCollector
from collectors.free.coingecko          import CoinGeckoCollector
from collectors.free.amfi               import AmfiCollector
from collectors.free.frankfurter        import FrankfurterCollector
from collectors.free.rbi_dbie           import RbiDbieCollector
from collectors.free.mca_portal         import McaPortalCollector
from collectors.free.sebi_portal        import SebiPortalCollector
from collectors.free.eia                import EiaCollector
from collectors.free.gdelt              import GdeltCollector
from collectors.free.world_bank         import WorldBankCollector
from collectors.free.rss_feeds          import RssFeedsCollector
# Phase 1 Paid
from collectors.paid.finnhub            import FinnhubCollector
from collectors.paid.newsapi            import NewsApiCollector

# ── Phase 2: Free ─────────────────────────────────────────────────────────────
from collectors.free.metals             import MetalsCollector
from collectors.free.opec               import OpecCollector
from collectors.free.baltic_dry         import BalticDryCollector
from collectors.free.nse_fno            import NseFnoCollector
from collectors.free.insider_trades     import InsiderTradesCollector
from collectors.free.credit_ratings     import CreditRatingsCollector
from collectors.free.screener           import ScreenerCollector
from collectors.free.reddit_news        import RedditNewsCollector
from collectors.free.wikipedia_signals  import WikipediaSignalsCollector
from collectors.free.sec_edgar          import SecEdgarCollector
from collectors.free.sebi_pms           import SebiPmsCollector
from collectors.free.politician_portfolio import PoliticianPortfolioCollector
from collectors.free.india_budget       import IndiaBudgetCollector
from collectors.free.weather            import WeatherCollector
from collectors.free.patents            import PatentsCollector
from collectors.free.imf                import ImfCollector
from collectors.free.youtube_transcripts import YouTubeTranscriptsCollector
from collectors.free.earnings_transcripts import EarningsTranscriptsCollector
from collectors.free.job_postings       import JobPostingsCollector

# ── Phase 3: Free ─────────────────────────────────────────────────────────────
from collectors.free.sebi_analysts      import SebiAnalystsCollector
from collectors.free.linkedin_scraper   import LinkedinScraperCollector
from collectors.free.industry_associations import IndustryAssociationsCollector
from collectors.free.gst_portal         import GstPortalCollector
from collectors.free.app_store_ratings  import AppStoreRatingsCollector
from collectors.free.twitter_nitter     import TwitterNitterCollector
from collectors.free.un_comtrade        import UnComtradeCollector
from collectors.free.pli_schemes        import PliSchemesCollector
from collectors.free.aif_data           import AifDataCollector
from collectors.free.vc_funding         import VcFundingCollector
from collectors.free.short_interest     import ShortInterestCollector
from collectors.free.beneficial_ownership import BeneficialOwnershipCollector

# ── Paid (add API key to .env to activate) ───────────────────────────────────
from collectors.paid.bloomberg          import BloombergCollector
from collectors.paid.refinitiv          import RefinitivCollector
from collectors.paid.ace_equity         import AceEquityCollector
# ── New collectors (v4 additions) ─────────────────────────────────────────────
from collectors.free.binance_ws          import BinanceWsCollector
from collectors.free.playwright_scraper  import PlaywrightNewsCollector
from collectors.free.data_marketplace    import DataMarketplaceCollector

REGISTRY: dict[str, Type[BaseCollector]] = {
    # ── Phase 1 Free ──────────────────────────────────────────────────────────
    "nse_csv":              NseCsvCollector,
    "fred":                 FredCollector,
    "coingecko":            CoinGeckoCollector,
    "amfi":                 AmfiCollector,
    "frankfurter":          FrankfurterCollector,
    "rbi_dbie":             RbiDbieCollector,
    "mca_portal":           McaPortalCollector,
    "sebi_portal":          SebiPortalCollector,
    "eia":                  EiaCollector,
    "gdelt":                GdeltCollector,
    "world_bank":           WorldBankCollector,
    "rss_feeds":            RssFeedsCollector,
    # Phase 1 Paid
    "finnhub":              FinnhubCollector,
    "newsapi":              NewsApiCollector,

    # ── Phase 2 Free ──────────────────────────────────────────────────────────
    "metals":               MetalsCollector,
    "opec":                 OpecCollector,
    "baltic_dry":           BalticDryCollector,
    "nse_fno":              NseFnoCollector,
    "insider_trades":       InsiderTradesCollector,
    "credit_ratings":       CreditRatingsCollector,
    "screener":             ScreenerCollector,
    "reddit_news":          RedditNewsCollector,
    "wikipedia_signals":    WikipediaSignalsCollector,
    "sec_edgar":            SecEdgarCollector,
    "sebi_pms":             SebiPmsCollector,
    "politician_portfolio": PoliticianPortfolioCollector,
    "india_budget":         IndiaBudgetCollector,
    "weather":              WeatherCollector,
    "imf":                  ImfCollector,
    "patents":              PatentsCollector,
    "youtube_transcripts":  YouTubeTranscriptsCollector,
    "earnings_transcripts": EarningsTranscriptsCollector,
    "job_postings":         JobPostingsCollector,

    # ── Phase 3 Free ──────────────────────────────────────────────────────────
    "sebi_analysts":           SebiAnalystsCollector,
    "linkedin_scraper":        LinkedinScraperCollector,
    "industry_associations":   IndustryAssociationsCollector,
    "gst_portal":              GstPortalCollector,
    "app_store_ratings":       AppStoreRatingsCollector,
    "twitter_nitter":          TwitterNitterCollector,
    "un_comtrade":             UnComtradeCollector,
    "pli_schemes":             PliSchemesCollector,
    "aif_data":                AifDataCollector,
    "vc_funding":              VcFundingCollector,
    "short_interest":          ShortInterestCollector,
    "beneficial_ownership":    BeneficialOwnershipCollector,

    # ── Paid (key required in .env) ───────────────────────────────────────────
    "bloomberg":    BloombergCollector,
    "refinitiv":    RefinitivCollector,
    "ace_equity":   AceEquityCollector,

    # ── v4 additions ──────────────────────────────────────────────────────────
    "binance_ws":         BinanceWsCollector,
    "playwright_news":    PlaywrightNewsCollector,
    "data_marketplace":   DataMarketplaceCollector,
}


def get_collector(source_name: str) -> BaseCollector:
    cls = REGISTRY.get(source_name)
    if cls is None:
        raise ValueError(f"Unknown source: '{source_name}'. Available: {sorted(REGISTRY.keys())}")
    return cls()

def all_collectors() -> list[BaseCollector]:
    return [cls() for cls in REGISTRY.values()]

def collectors_by_phase(phase: int) -> list[BaseCollector]:
    p1 = {"nse_csv","fred","coingecko","amfi","frankfurter","rbi_dbie","mca_portal",
          "sebi_portal","eia","gdelt","world_bank","rss_feeds","finnhub","newsapi"}
    p2 = {"metals","opec","baltic_dry","nse_fno","insider_trades","credit_ratings",
          "screener","reddit_news","wikipedia_signals","sec_edgar","sebi_pms",
          "politician_portfolio","india_budget","weather","imf","patents",
          "youtube_transcripts","earnings_transcripts","job_postings"}
    p3 = {"sebi_analysts","linkedin_scraper","industry_associations","gst_portal",
          "app_store_ratings","twitter_nitter","un_comtrade","pli_schemes",
          "aif_data","vc_funding","short_interest","beneficial_ownership"}
    paid = {"bloomberg","refinitiv","ace_equity"}
    if phase == 1:   return [cls() for n,cls in REGISTRY.items() if n in p1]
    if phase == 2:   return [cls() for n,cls in REGISTRY.items() if n in p2]
    p4 = {"binance_ws","playwright_news","data_marketplace"}
    if phase == 3:   return [cls() for n,cls in REGISTRY.items() if n in p3]
    if phase == 4:   return [cls() for n,cls in REGISTRY.items() if n in p4]
    if phase == 99:  return [cls() for n,cls in REGISTRY.items() if n in paid]
    return all_collectors()
