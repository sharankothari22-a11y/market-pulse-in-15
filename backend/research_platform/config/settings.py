"""
config/settings.py
──────────────────
Central settings loader. All config consumed from environment variables.
Never hardcode credentials — always read from .env via python-dotenv.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env — override=True so research_platform/.env wins over parent .env
load_dotenv(dotenv_path=Path(__file__).parents[1] / ".env", override=True)


def _require(key: str) -> str:
    """Return env var or raise a descriptive error at startup."""
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"See .env.example for guidance."
        )
    return val


# ── Database ──────────────────────────────────────────────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "research_platform")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

DATABASE_URL: str = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── API Keys ──────────────────────────────────────────────────────────────────
FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")
EIA_API_KEY: str = os.getenv("EIA_API_KEY", "")

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_DIR: str = os.getenv("CACHE_DIR", "/tmp/research_platform_cache")
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR: str = os.getenv("LOG_DIR", "./logs")

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "Asia/Kolkata")

# ── Source URLs ───────────────────────────────────────────────────────────────
NSE_BHAVCOPY_BASE_URL: str = os.getenv(
    "NSE_BHAVCOPY_BASE_URL",
    "https://archives.nseindia.com/content/historical/EQUITIES",
)
BSE_BHAVCOPY_BASE_URL: str = os.getenv(
    "BSE_BHAVCOPY_BASE_URL",
    "https://www.bseindia.com/download/BhavCopy/Equity",
)
NSE_FIIDII_BASE_URL: str = os.getenv(
    "NSE_FIIDII_BASE_URL",
    "https://archives.nseindia.com/content/nsccl",
)
COINGECKO_API_URL: str = os.getenv(
    "COINGECKO_API_URL", "https://api.coingecko.com/api/v3"
)
FRED_BASE_URL: str = os.getenv("FRED_BASE_URL", "https://fred.stlouisfed.org")
FRANKFURTER_API_URL: str = os.getenv(
    "FRANKFURTER_API_URL", "https://api.frankfurter.app"
)
WORLD_BANK_API_URL: str = os.getenv(
    "WORLD_BANK_API_URL", "https://api.worldbank.org/v2"
)
EIA_API_URL: str = os.getenv("EIA_API_URL", "https://api.eia.gov/v2")
GDELT_BASE_URL: str = os.getenv(
    "GDELT_BASE_URL", "http://data.gdeltproject.org/gdeltv2"
)
AMFI_NAV_URL: str = os.getenv(
    "AMFI_NAV_URL", "https://www.amfiindia.com/spages/NAVAll.txt"
)
RBI_DBIE_BASE_URL: str = os.getenv("RBI_DBIE_BASE_URL", "https://dbie.rbi.org.in")
SEBI_PORTAL_BASE_URL: str = os.getenv("SEBI_PORTAL_BASE_URL", "https://www.sebi.gov.in")
MCA_PORTAL_BASE_URL: str = os.getenv("MCA_PORTAL_BASE_URL", "https://www.mca.gov.in")
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

BLOOMBERG_API_KEY: str = os.getenv("BLOOMBERG_API_KEY", "")

REFINITIV_API_KEY: str = os.getenv("REFINITIV_API_KEY", "")

ACE_EQUITY_API_KEY: str = os.getenv("ACE_EQUITY_API_KEY", "")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
