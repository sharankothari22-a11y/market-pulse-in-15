"""
scheduler/jobs.py
──────────────────
All APScheduler job functions — Phase 1 + Phase 2 + Phase 3.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone, time
import pytz
from loguru import logger
from collectors.registry import get_collector

IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN  = time(9, 15)
MARKET_CLOSE = time(15, 30)


def _is_market_hours() -> bool:
    now = datetime.now(IST)
    return now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE


def _run(source: str) -> None:
    try:
        result = get_collector(source).collect()
        icon = {"ok": "OK", "partial": "~~", "error": "ERR"}.get(result.status, "??")
        logger.info(f"[scheduler/{source}] {icon} — {result.record_count} records")
    except Exception as exc:
        logger.error(f"[scheduler/{source}] Exception: {exc}")


# ── Real-time (market hours only) ────────────────────────────────────────────
def job_realtime_prices() -> None:
    if not _is_market_hours():
        return
    _run("finnhub")

def job_realtime_fno() -> None:
    """NSE F&O PCR — every 15 min during market hours."""
    if not _is_market_hours():
        return
    _run("nse_fno")

# ── Daily 06:00 IST ───────────────────────────────────────────────────────────
def job_daily_nse()          -> None: _run("nse_csv")
def job_daily_amfi()         -> None: _run("amfi")
def job_daily_rss()          -> None: _run("rss_feeds")
def job_daily_coingecko()    -> None: _run("coingecko")
def job_daily_frankfurter()  -> None: _run("frankfurter")
def job_daily_metals()       -> None: _run("metals")
def job_daily_opec()         -> None: _run("opec")
def job_daily_insider()      -> None: _run("insider_trades")
def job_daily_reddit()       -> None: _run("reddit_news")
def job_daily_wikipedia()    -> None: _run("wikipedia_signals")
def job_daily_weather()      -> None: _run("weather")
def job_daily_india_budget() -> None: _run("india_budget")
def job_daily_sebi_pms()     -> None: _run("sebi_pms")

# ── Daily 08:00 IST — failure digest ─────────────────────────────────────────
def job_daily_failure_digest() -> None:
    try:
        from database.connection import get_session
        from database.models import CollectionLog
        from sqlalchemy import select, desc
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        with get_session() as session:
            failed = session.scalars(
                select(CollectionLog)
                .where(CollectionLog.status == "error", CollectionLog.timestamp >= cutoff)
                .order_by(desc(CollectionLog.timestamp))
            ).all()
        if not failed:
            logger.info("[scheduler/digest] All collectors healthy — no failures in 24h")
            return
        lines = [f"DAILY FAILURE DIGEST — {datetime.now().strftime('%Y-%m-%d %H:%M IST')}",
                 f"{'─'*60}"]
        for f in failed:
            lines.append(f"  [{f.source_name}] {f.status} | {f.error_message or 'N/A'} | {f.timestamp.strftime('%H:%M')}")
        logger.warning("\n".join(lines))
    except Exception as exc:
        logger.error(f"[scheduler/digest] Failed: {exc}")

# ── Daily 09:00 IST — sentiment scoring ──────────────────────────────────────
def job_daily_sentiment() -> None:
    """Score unscored news articles — runs after daily RSS collection."""
    try:
        from processing.sentiment_pipeline import batch_score_unscored_articles
        scored = batch_score_unscored_articles(limit=200)
        logger.info(f"[scheduler/sentiment] Scored {scored} articles")
    except Exception as exc:
        logger.error(f"[scheduler/sentiment] Failed: {exc}")

# ── Weekly Sunday 02:00 IST ───────────────────────────────────────────────────
def job_weekly_fred()           -> None: _run("fred")
def job_weekly_world_bank()     -> None: _run("world_bank")
def job_weekly_eia()            -> None: _run("eia")
def job_weekly_baltic_dry()     -> None: _run("baltic_dry")
def job_weekly_imf()            -> None: _run("imf")
def job_weekly_credit_ratings() -> None: _run("credit_ratings")
def job_weekly_screener()       -> None: _run("screener")
def job_weekly_sec_edgar()      -> None: _run("sec_edgar")
def job_weekly_patents()        -> None: _run("patents")
def job_weekly_politician()     -> None: _run("politician_portfolio")
def job_weekly_cleanup_logs()   -> None:
    try:
        from database.connection import cleanup_old_logs
        deleted = cleanup_old_logs(days=90)
        logger.info(f"[scheduler/cleanup] Pruned {deleted} old log rows.")
    except Exception as exc:
        logger.error(f"[scheduler/cleanup] Failed: {exc}")

# ── Quarterly ─────────────────────────────────────────────────────────────────
def job_quarterly_sebi()      -> None: _run("sebi_portal")
def job_quarterly_mca()       -> None: _run("mca_portal")
def job_quarterly_earnings()  -> None: _run("earnings_transcripts")
def job_quarterly_youtube()   -> None: _run("youtube_transcripts")
def job_quarterly_jobs()      -> None: _run("job_postings")

# ── Phase 3 ───────────────────────────────────────────────────────────────────
def job_daily_twitter()         -> None: _run("twitter_nitter")
def job_daily_app_ratings()     -> None: _run("app_store_ratings")
def job_daily_short_interest()  -> None: _run("short_interest")
def job_weekly_sebi_analysts()  -> None: _run("sebi_analysts")
def job_weekly_linkedin()       -> None: _run("linkedin_scraper")
def job_weekly_industry_assoc() -> None: _run("industry_associations")
def job_weekly_gst()            -> None: _run("gst_portal")
def job_weekly_un_comtrade()    -> None: _run("un_comtrade")
def job_weekly_pli()            -> None: _run("pli_schemes")
def job_weekly_aif()            -> None: _run("aif_data")
def job_weekly_vc_funding()     -> None: _run("vc_funding")
def job_monthly_beneficial()    -> None: _run("beneficial_ownership")

# ── Paid (no-op until key is set) ─────────────────────────────────────────────
def job_daily_bloomberg()       -> None: _run("bloomberg")
def job_daily_refinitiv()       -> None: _run("refinitiv")
def job_weekly_ace_equity()     -> None: _run("ace_equity")

# ── v4 additions ──────────────────────────────────────────────────────────────
def job_daily_binance()       -> None: _run("binance_ws")
def job_daily_playwright()    -> None: _run("playwright_news")
def job_weekly_data_market()  -> None: _run("data_marketplace")
