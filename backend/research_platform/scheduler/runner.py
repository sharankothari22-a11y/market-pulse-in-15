"""
scheduler/runner.py
────────────────────
APScheduler — Phase 1 + Phase 2 + Phase 3 + Paid + v4 additions.
Total: 53 jobs across 5 frequency tiers.
"""
from __future__ import annotations
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from config.settings import SCHEDULER_TIMEZONE
from scheduler.jobs import (
    # Real-time
    job_realtime_prices, job_realtime_fno,
    # Daily 06:00
    job_daily_nse, job_daily_amfi, job_daily_rss, job_daily_coingecko,
    job_daily_frankfurter, job_daily_metals, job_daily_opec,
    job_daily_insider, job_daily_reddit, job_daily_wikipedia,
    job_daily_weather, job_daily_india_budget, job_daily_sebi_pms,
    # Daily 08:00 + 09:00
    job_daily_failure_digest, job_daily_sentiment,
    # Weekly
    job_weekly_fred, job_weekly_world_bank, job_weekly_eia,
    job_weekly_baltic_dry, job_weekly_imf, job_weekly_credit_ratings,
    job_weekly_screener, job_weekly_sec_edgar, job_weekly_patents,
    job_weekly_politician, job_weekly_cleanup_logs,
    # Quarterly
    job_quarterly_sebi, job_quarterly_mca,
    job_quarterly_earnings, job_quarterly_youtube, job_quarterly_jobs,
    # Phase 3 + Paid
    job_daily_twitter, job_daily_app_ratings, job_daily_short_interest,
    job_daily_bloomberg, job_daily_refinitiv,
    job_weekly_sebi_analysts, job_weekly_linkedin, job_weekly_industry_assoc,
    job_weekly_gst, job_weekly_un_comtrade, job_weekly_pli,
    job_weekly_aif, job_weekly_vc_funding, job_weekly_ace_equity,
    job_monthly_beneficial,
    # v4 additions
    job_daily_binance, job_daily_playwright, job_weekly_data_market,
)


def build_scheduler() -> BlockingScheduler:
    s = BlockingScheduler(timezone=SCHEDULER_TIMEZONE)

    # ── Real-time (market hours) ──────────────────────────────────────────────
    s.add_job(job_realtime_prices, IntervalTrigger(minutes=5),
              id="realtime_prices", name="Finnhub real-time prices",
              replace_existing=True, misfire_grace_time=60)
    s.add_job(job_realtime_fno, IntervalTrigger(minutes=15),
              id="realtime_fno", name="NSE F&O PCR",
              replace_existing=True, misfire_grace_time=60)

    # ── Daily 06:00 IST ───────────────────────────────────────────────────────
    for fn, jid, name in [
        (job_daily_nse,          "daily_nse",          "NSE Bhavcopy + FII/DII"),
        (job_daily_amfi,         "daily_amfi",         "AMFI mutual fund NAVs"),
        (job_daily_rss,          "daily_rss",          "RSS news feeds"),
        (job_daily_coingecko,    "daily_coingecko",    "CoinGecko crypto"),
        (job_daily_frankfurter,  "daily_frankfurter",  "Frankfurter FX rates"),
        (job_daily_metals,       "daily_metals",       "Gold/Silver/Platinum"),
        (job_daily_opec,         "daily_opec",         "OPEC decisions"),
        (job_daily_insider,      "daily_insider",      "NSE/BSE bulk deals"),
        (job_daily_reddit,       "daily_reddit",       "Reddit financial news"),
        (job_daily_wikipedia,    "daily_wikipedia",    "Wikipedia edit signals"),
        (job_daily_weather,      "daily_weather",      "Weather agri/energy"),
        (job_daily_india_budget, "daily_india_budget", "PIB/Budget/Ministry"),
        (job_daily_sebi_pms,     "daily_sebi_pms",     "SEBI PMS disclosures"),
        (job_daily_twitter,      "daily_twitter",      "Twitter/Nitter"),
        (job_daily_app_ratings,  "daily_app_ratings",  "App store ratings"),
        (job_daily_short_interest,"daily_short_int",   "NSE SLB short interest"),
        (job_daily_bloomberg,    "daily_bloomberg",    "Bloomberg Intelligence (paid)"),
        (job_daily_refinitiv,    "daily_refinitiv",    "Refinitiv Eikon (paid)"),
        (job_daily_binance,      "daily_binance",      "Binance crypto real-time"),
        (job_daily_playwright,   "daily_playwright",   "JS-rendered news (Playwright)"),
    ]:
        s.add_job(fn, CronTrigger(hour=6, minute=0, timezone=SCHEDULER_TIMEZONE),
                  id=jid, name=name, replace_existing=True, misfire_grace_time=3600)

    # ── Daily 08:00 — failure digest ──────────────────────────────────────────
    s.add_job(job_daily_failure_digest,
              CronTrigger(hour=8, minute=0, timezone=SCHEDULER_TIMEZONE),
              id="daily_failure_digest", name="Daily failure digest",
              replace_existing=True, misfire_grace_time=3600)

    # ── Daily 09:00 — sentiment scoring ──────────────────────────────────────
    s.add_job(job_daily_sentiment,
              CronTrigger(hour=9, minute=0, timezone=SCHEDULER_TIMEZONE),
              id="daily_sentiment", name="News sentiment scoring",
              replace_existing=True, misfire_grace_time=3600)

    # ── Weekly Sunday 02:00 IST ───────────────────────────────────────────────
    for fn, jid, name in [
        (job_weekly_fred,           "weekly_fred",           "FRED macro"),
        (job_weekly_world_bank,     "weekly_world_bank",     "World Bank"),
        (job_weekly_eia,            "weekly_eia",            "EIA energy"),
        (job_weekly_baltic_dry,     "weekly_baltic_dry",     "Baltic Dry Index"),
        (job_weekly_imf,            "weekly_imf",            "IMF WEO"),
        (job_weekly_credit_ratings, "weekly_credit_ratings", "Credit ratings"),
        (job_weekly_screener,       "weekly_screener",       "Screener.in ratios"),
        (job_weekly_sec_edgar,      "weekly_sec_edgar",      "SEC EDGAR 13F"),
        (job_weekly_patents,        "weekly_patents",        "Patent filings"),
        (job_weekly_politician,     "weekly_politician",     "Politician portfolio"),
        (job_weekly_cleanup_logs,   "weekly_cleanup_logs",   "Log cleanup"),
        (job_weekly_sebi_analysts,  "weekly_sebi_analysts",  "SEBI analyst registry"),
        (job_weekly_linkedin,       "weekly_linkedin",       "LinkedIn exec profiles"),
        (job_weekly_industry_assoc, "weekly_industry_assoc", "Industry associations"),
        (job_weekly_gst,            "weekly_gst",            "GST portal"),
        (job_weekly_un_comtrade,    "weekly_un_comtrade",    "UN Comtrade trade"),
        (job_weekly_pli,            "weekly_pli",            "PLI beneficiaries"),
        (job_weekly_aif,            "weekly_aif",            "SEBI AIF data"),
        (job_weekly_vc_funding,     "weekly_vc_funding",     "VC/Angel funding"),
        (job_weekly_ace_equity,     "weekly_ace_equity",     "ACE Equity (paid)"),
        (job_weekly_data_market,    "weekly_data_market",    "Quandl/STOOQ data marketplace"),
    ]:
        s.add_job(fn, CronTrigger(day_of_week="sun", hour=2, minute=0,
                                  timezone=SCHEDULER_TIMEZONE),
                  id=jid, name=name, replace_existing=True, misfire_grace_time=3600)

    # ── Monthly 1st 04:00 IST ─────────────────────────────────────────────────
    s.add_job(job_monthly_beneficial,
              CronTrigger(day=1, hour=4, minute=0, timezone=SCHEDULER_TIMEZONE),
              id="monthly_beneficial", name="Beneficial ownership mapping",
              replace_existing=True, misfire_grace_time=3600)

    # ── Quarterly 1 Jan/Apr/Jul/Oct 03:00 IST ────────────────────────────────
    for fn, jid, name in [
        (job_quarterly_sebi,     "quarterly_sebi",     "SEBI portal"),
        (job_quarterly_mca,      "quarterly_mca",      "MCA company filings"),
        (job_quarterly_earnings, "quarterly_earnings", "Earnings transcripts"),
        (job_quarterly_youtube,  "quarterly_youtube",  "YouTube transcripts"),
        (job_quarterly_jobs,     "quarterly_jobs",     "Job posting trends"),
    ]:
        s.add_job(fn, CronTrigger(month="1,4,7,10", day=1, hour=3, minute=0,
                                  timezone=SCHEDULER_TIMEZONE),
                  id=jid, name=name, replace_existing=True, misfire_grace_time=3600)

    return s


def start_scheduler() -> None:
    s = build_scheduler()
    jobs = list({j.id: j for j in s.get_jobs()}.values())
    logger.info("=" * 65)
    logger.info(f"research_platform — {len(jobs)} scheduled jobs")
    logger.info("=" * 65)
    for j in sorted(jobs, key=lambda x: x.id):
        logger.info(f"  [{j.id}] {j.name}")
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
