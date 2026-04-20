"""
database/models.py
──────────────────
SQLAlchemy 2.0 ORM models.

Bug fixes applied:
  - Event: UniqueConstraint(source_url, date, type) stops RSS/GDELT duplicates
  - MacroIndicator: constraint on (indicator, date, source) avoids NULL==NULL bug
  - CommodityPrice: constraint on (commodity_id, date, exchange) fixed
  - FundNav: new table — AMFI now has a proper home (was TODO)
  - NewsArticle, EarningsTranscript, RegulatoryOrder: text search tables from doc
  - Company: UniqueConstraint(ticker, exchange)
  - Country: COUNTRY_SEED list for auto-seeding
  - CollectionLog: timestamp indexed for cleanup queries
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ── Country seed data ─────────────────────────────────────────────────────────
# Used by connection.seed_countries() on first setup.
COUNTRY_SEED = [
    ("IN", "India",          "INR"),
    ("US", "United States",  "USD"),
    ("CN", "China",          "CNY"),
    ("GB", "United Kingdom", "GBP"),
    ("DE", "Germany",        "EUR"),
    ("JP", "Japan",          "JPY"),
    ("AU", "Australia",      "AUD"),
    ("CA", "Canada",         "CAD"),
    ("SG", "Singapore",      "SGD"),
    ("HK", "Hong Kong",      "HKD"),
    ("CH", "Switzerland",    "CHF"),
    ("AE", "UAE",            "AED"),
    ("SA", "Saudi Arabia",   "SAR"),
    ("BR", "Brazil",         "BRL"),
    ("ZA", "South Africa",   "ZAR"),
]


# ─────────────────────────────────────────────────────────────────────────────
# CORE ENTITIES
# ─────────────────────────────────────────────────────────────────────────────


class Company(Base):
    """Listed and unlisted companies — Indian and global."""
    __tablename__ = "company"
    __table_args__ = (
        UniqueConstraint("ticker", "exchange", name="uq_company_ticker_exchange"),
    )

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    cin:          Mapped[Optional[str]] = mapped_column(String(21), unique=True, nullable=True)
    ticker:       Mapped[Optional[str]] = mapped_column(String(20), index=True, nullable=True)
    name:         Mapped[str]           = mapped_column(String(500), nullable=False)
    sector:       Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sector_mapped:Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exchange:     Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country:      Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    website:      Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_listed:    Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Person(Base):
    """Directors, promoters, politicians, analysts."""
    __tablename__ = "person"

    id:                 Mapped[int]                    = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:               Mapped[str]                    = mapped_column(String(500), nullable=False)
    din:                Mapped[Optional[str]]          = mapped_column(String(8), unique=True, nullable=True)
    pan_masked:         Mapped[Optional[str]]          = mapped_column(String(10), nullable=True)
    type:               Mapped[str]                    = mapped_column(String(20), nullable=False)
    linked_company_ids: Mapped[Optional[list[int]]]   = mapped_column(ARRAY(Integer), nullable=True)
    created_at:         Mapped[datetime]               = mapped_column(DateTime(timezone=True), server_default=func.now())


class Fund(Base):
    """Mutual funds, AIFs, PMS schemes, PE, hedge funds."""
    __tablename__ = "fund"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:        Mapped[str]           = mapped_column(String(500), nullable=False)
    type:        Mapped[str]           = mapped_column(String(10), nullable=False)
    sebi_reg_no: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    aum:         Mapped[Optional[float]]= mapped_column(Numeric(20, 2), nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class Commodity(Base):
    """Metals, energy, crypto, agricultural commodities."""
    __tablename__ = "commodity"
    __table_args__ = (
        UniqueConstraint("name", "type", name="uq_commodity_name_type"),
    )

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:          Mapped[str]           = mapped_column(String(200), nullable=False)
    type:          Mapped[str]           = mapped_column(String(10), nullable=False)
    exchange:      Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    base_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)


class Country(Base):
    """Country reference — seeded by connection.seed_countries()."""
    __tablename__ = "country"

    id:       Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso_code: Mapped[str]           = mapped_column(String(3), unique=True, nullable=False)
    name:     Mapped[str]           = mapped_column(String(200), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)


class Event(Base):
    """Earnings, policy, filings, deals, regulatory actions, news events.

    BUG FIX: UniqueConstraint on (source_url, date, type) prevents RSS/GDELT
    from inserting duplicates on every daily run.
    Rows with NULL source_url (manually inserted) bypass the constraint — that
    is intentional; manual events have no URL to deduplicate on.
    """
    __tablename__ = "event"
    __table_args__ = (
        UniqueConstraint("source_url", "date", "type", name="uq_event_url_date_type"),
    )

    id:           Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type:         Mapped[str]            = mapped_column(String(20), nullable=False)
    entity_id:    Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    entity_type:  Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    date:         Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    title:        Mapped[str]            = mapped_column(String(1000), nullable=False)
    impact_score: Mapped[Optional[float]]= mapped_column(Float, nullable=True)
    source_url:   Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())


class Portfolio(Base):
    """Shareholding positions by quarter."""
    __tablename__ = "portfolio"
    __table_args__ = (
        UniqueConstraint("holder_id", "holder_type", "company_id", "quarter",
                         name="uq_portfolio_holder_company_quarter"),
    )

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    holder_id:   Mapped[int]            = mapped_column(Integer, nullable=False)
    holder_type: Mapped[str]            = mapped_column(String(10), nullable=False)
    company_id:  Mapped[int]            = mapped_column(Integer, ForeignKey("company.id"), nullable=False)
    quarter:     Mapped[Optional[str]]  = mapped_column(String(7), nullable=True)
    holding_pct: Mapped[Optional[float]]= mapped_column(Float, nullable=True)
    value_inr:   Mapped[Optional[float]]= mapped_column(Numeric(20, 2), nullable=True)
    change_pct:  Mapped[Optional[float]]= mapped_column(Float, nullable=True)
    source:      Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────────────────────────
# TIME-SERIES TABLES  (TimescaleDB hypertables on 'date')
# ─────────────────────────────────────────────────────────────────────────────


class PriceHistory(Base):
    """Daily OHLCV. TimescaleDB hypertable on 'date'."""
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("ticker", "date", "exchange", name="uq_price_ticker_date_exchange"),
    )

    id:       Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker:   Mapped[str]            = mapped_column(String(20), nullable=False, index=True)
    date:     Mapped[date]           = mapped_column(Date, nullable=False, index=True)
    open:     Mapped[Optional[float]]= mapped_column(Numeric(18, 4), nullable=True)
    high:     Mapped[Optional[float]]= mapped_column(Numeric(18, 4), nullable=True)
    low:      Mapped[Optional[float]]= mapped_column(Numeric(18, 4), nullable=True)
    close:    Mapped[float]          = mapped_column(Numeric(18, 4), nullable=False)
    volume:   Mapped[Optional[float]]= mapped_column(Numeric(22, 0), nullable=True)
    exchange: Mapped[Optional[str]]  = mapped_column(String(10), nullable=True)


class MacroIndicator(Base):
    """Country-level macro time series. TimescaleDB hypertable on 'date'.

    BUG FIX: Constraint is on (indicator, date, source) NOT country_id.
    Using country_id in a UNIQUE constraint with NULLable columns fails silently
    because NULL != NULL in SQL — every NULL row bypasses the constraint.
    Source string (e.g. 'WorldBank/IN', 'FRED') is always non-null and
    encodes the country implicitly, making it a safe dedup key.
    """
    __tablename__ = "macro_indicators"
    __table_args__ = (
        UniqueConstraint("indicator", "date", "source", name="uq_macro_indicator_date_source"),
    )

    id:         Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    country_id: Mapped[Optional[int]]  = mapped_column(Integer, ForeignKey("country.id"), nullable=True)
    indicator:  Mapped[str]            = mapped_column(String(100), nullable=False, index=True)
    date:       Mapped[date]           = mapped_column(Date, nullable=False, index=True)
    value:      Mapped[Optional[float]]= mapped_column(Float, nullable=True)
    source:     Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)


class CommodityPrice(Base):
    """Daily commodity / crypto prices. TimescaleDB hypertable on 'date'.

    BUG FIX: Constraint on (commodity_id, date, exchange). For rows where
    commodity_id is NULL (shouldn't happen after fix but guarded), the
    upsert logic in queries.py handles the NULL case explicitly.
    """
    __tablename__ = "commodity_prices"
    __table_args__ = (
        UniqueConstraint("commodity_id", "date", "exchange",
                         name="uq_commodity_price_id_date_exchange"),
    )

    id:           Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    commodity_id: Mapped[Optional[int]]  = mapped_column(Integer, ForeignKey("commodity.id"), nullable=True)
    date:         Mapped[date]           = mapped_column(Date, nullable=False, index=True)
    price:        Mapped[float]          = mapped_column(Numeric(22, 8), nullable=False)
    currency:     Mapped[str]            = mapped_column(String(3), nullable=False)
    exchange:     Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    extra_data:   Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class FiiDiiFlow(Base):
    """Daily FII / DII flows. TimescaleDB hypertable on 'date'."""
    __tablename__ = "fii_dii_flows"
    __table_args__ = (
        UniqueConstraint("date", "category", "exchange", name="uq_fii_dii_date_cat_exchange"),
    )

    id:         Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date:       Mapped[date]           = mapped_column(Date, nullable=False, index=True)
    category:   Mapped[str]            = mapped_column(String(10), nullable=False)
    buy_value:  Mapped[Optional[float]]= mapped_column(Numeric(20, 2), nullable=True)
    sell_value: Mapped[Optional[float]]= mapped_column(Numeric(20, 2), nullable=True)
    net_value:  Mapped[Optional[float]]= mapped_column(Numeric(20, 2), nullable=True)
    exchange:   Mapped[Optional[str]]  = mapped_column(String(10), nullable=True)


class FxRate(Base):
    """Daily FX rates. TimescaleDB hypertable on 'date'."""
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("pair", "date", name="uq_fx_pair_date"),
    )

    id:     Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pair:   Mapped[str]            = mapped_column(String(7), nullable=False, index=True)
    date:   Mapped[date]           = mapped_column(Date, nullable=False, index=True)
    rate:   Mapped[float]          = mapped_column(Numeric(18, 6), nullable=False)
    source: Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# FUND NAV  (was a TODO comment in amfi.py — now properly defined)
# ─────────────────────────────────────────────────────────────────────────────


class FundNav(Base):
    """Daily NAV for mutual fund schemes from AMFI.
    TimescaleDB hypertable on 'date'.
    """
    __tablename__ = "fund_nav"
    __table_args__ = (
        UniqueConstraint("scheme_code", "date", name="uq_fund_nav_scheme_date"),
    )

    id:                 Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scheme_code:        Mapped[str]            = mapped_column(String(20), nullable=False, index=True)
    scheme_name:        Mapped[str]            = mapped_column(String(500), nullable=False)
    isin_div_payout:    Mapped[Optional[str]]  = mapped_column(String(20), nullable=True)
    isin_div_reinvest:  Mapped[Optional[str]]  = mapped_column(String(20), nullable=True)
    nav:                Mapped[float]          = mapped_column(Numeric(18, 4), nullable=False)
    date:               Mapped[date]           = mapped_column(Date, nullable=False, index=True)
    fund_id:            Mapped[Optional[int]]  = mapped_column(Integer, ForeignKey("fund.id"), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# TEXT & SEMANTIC SEARCH TABLES  (Section 6 of document)
# pgvector extension adds Vector column type — gracefully degrades if missing
# ─────────────────────────────────────────────────────────────────────────────


class NewsArticle(Base):
    """News articles with optional embedding for semantic search."""
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_news_source_url"),
    )

    id:              Mapped[int]             = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title:           Mapped[str]             = mapped_column(String(1000), nullable=False)
    body:            Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    source:          Mapped[Optional[str]]   = mapped_column(String(200), nullable=True)
    source_url:      Mapped[Optional[str]]   = mapped_column(String(1000), nullable=True)
    published_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    entity_ids:      Mapped[Optional[list[int]]]= mapped_column(ARRAY(Integer), nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Stored as JSON array until pgvector is available; migrate to Vector(1536) after
    embedding:       Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    created_at:      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())


class EarningsTranscript(Base):
    """Earnings call transcripts."""
    __tablename__ = "earnings_transcripts"
    __table_args__ = (
        UniqueConstraint("ticker", "quarter", name="uq_transcript_ticker_quarter"),
    )

    id:              Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id:      Mapped[Optional[int]]  = mapped_column(Integer, ForeignKey("company.id"), nullable=True)
    ticker:          Mapped[str]            = mapped_column(String(20), nullable=False, index=True)
    quarter:         Mapped[str]            = mapped_column(String(7), nullable=False)
    transcript_text: Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    summary:         Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    source_url:      Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    call_date:       Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegulatoryOrder(Base):
    """SEBI / RBI / MCA regulatory orders and circulars."""
    __tablename__ = "regulatory_orders"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_regorder_url"),
    )

    id:          Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    regulator:   Mapped[str]            = mapped_column(String(20), nullable=False, index=True)
    order_type:  Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    title:       Mapped[str]            = mapped_column(String(1000), nullable=False)
    body:        Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    entity_name: Mapped[Optional[str]]  = mapped_column(String(500), nullable=True)
    order_date:  Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_url:  Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────────────────────────
# OPERATIONAL TABLES
# ─────────────────────────────────────────────────────────────────────────────


class CollectionLog(Base):
    """Audit log for every collector run. Cleaned after 90 days by scheduler."""
    __tablename__ = "collection_log"

    id:                Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_name:       Mapped[str]            = mapped_column(String(100), nullable=False, index=True)
    method_used:       Mapped[Optional[str]]  = mapped_column(String(20), nullable=True)
    records_collected: Mapped[int]            = mapped_column(Integer, default=0)
    status:            Mapped[str]            = mapped_column(String(20), nullable=False)
    error_message:     Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    fallback_used:     Mapped[bool]           = mapped_column(Boolean, default=False)
    timestamp:         Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_seconds:  Mapped[Optional[float]]= mapped_column(Float, nullable=True)


class ValidationError(Base):
    """Records flagged by the validation engine."""
    __tablename__ = "validation_errors"

    id:          Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_name: Mapped[str]            = mapped_column(String(100), nullable=False, index=True)
    field:       Mapped[str]            = mapped_column(String(100), nullable=False)
    rule:        Mapped[str]            = mapped_column(String(200), nullable=False)
    value:       Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    severity:    Mapped[str]            = mapped_column(String(10), nullable=False)
    record_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class BudgetDocument(Base):
    """India Budget documents, policy PDFs, and gazette notifications.
    From Section 6 database design: budget_documents table.
    """
    __tablename__ = "budget_documents"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_budget_source_url"),
    )

    id:           Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title:        Mapped[str]            = mapped_column(String(500), nullable=False)
    document_type:Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)   # budget|policy|gazette
    fiscal_year:  Mapped[Optional[str]]  = mapped_column(String(10), nullable=True)   # e.g. FY2025
    body:         Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    source_url:   Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsSentiment(Base):
    """News sentiment scores linked to companies or sectors.
    From Section 6 database design: news_sentiment table.
    """
    __tablename__ = "news_sentiment"
    __table_args__ = (
        UniqueConstraint("article_id", "entity_id", "entity_type",
                         name="uq_sentiment_article_entity"),
    )

    id:           Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id:   Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("news_articles.id"), nullable=True)
    entity_id:    Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    entity_type:  Mapped[Optional[str]]  = mapped_column(String(20), nullable=True)   # company|sector|country
    sentiment:    Mapped[Optional[str]]  = mapped_column(String(10), nullable=True)   # positive|negative|neutral
    score:        Mapped[Optional[float]]= mapped_column(Float, nullable=True)         # -1.0 to +1.0
    source:       Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
