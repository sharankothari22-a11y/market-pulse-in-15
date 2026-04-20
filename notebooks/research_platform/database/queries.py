"""
database/queries.py
───────────────────
Reusable query helpers. SQLAlchemy 2.0 style throughout.

Bug fixes:
  - upsert_macro_indicator: NULL country_id no longer breaks dedup
    (constraint is now on indicator+date+source, not country_id)
  - upsert_commodity_price: NULL commodity_id handled explicitly
  - upsert_event: new — prevents RSS/GDELT duplicates via source_url+date+type
  - upsert_fund_nav: new — AMFI now persists properly
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from database.models import (
    CollectionLog,
    Company,
    CommodityPrice,
    EarningsTranscript,
    Event,
    FiiDiiFlow,
    FundNav,
    FxRate,
    MacroIndicator,
    NewsArticle,
    PriceHistory,
    RegulatoryOrder,
    ValidationError,
)


# ── Price History ─────────────────────────────────────────────────────────────

def get_prices(
    session: Session,
    ticker: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[PriceHistory]:
    stmt = select(PriceHistory).where(PriceHistory.ticker == ticker)
    if start:
        stmt = stmt.where(PriceHistory.date >= start)
    if end:
        stmt = stmt.where(PriceHistory.date <= end)
    return list(session.scalars(stmt.order_by(PriceHistory.date)))


def upsert_price(session: Session, record: PriceHistory) -> None:
    exists = session.scalar(
        select(PriceHistory).where(
            and_(
                PriceHistory.ticker == record.ticker,
                PriceHistory.date == record.date,
                PriceHistory.exchange == record.exchange,
            )
        )
    )
    if not exists:
        session.add(record)


# ── FII / DII ─────────────────────────────────────────────────────────────────

def upsert_fii_dii_flow(session: Session, record: FiiDiiFlow) -> None:
    exists = session.scalar(
        select(FiiDiiFlow).where(
            and_(
                FiiDiiFlow.date == record.date,
                FiiDiiFlow.category == record.category,
                FiiDiiFlow.exchange == record.exchange,
            )
        )
    )
    if not exists:
        session.add(record)


# ── Macro Indicators ──────────────────────────────────────────────────────────

def upsert_macro_indicator(session: Session, record: MacroIndicator) -> None:
    """Dedup on (indicator, date, source) — NOT country_id.

    BUG FIX: The old code used country_id in the WHERE clause. In SQL,
    NULL == NULL evaluates to NULL (not TRUE), so every record with
    country_id=None bypassed the exists check and got inserted fresh
    each run — producing infinite duplicates.

    The MacroIndicator table now has a UNIQUE constraint on
    (indicator, date, source) which is always non-NULL, fixing this
    at the DB level. This function mirrors that logic.
    """
    exists = session.scalar(
        select(MacroIndicator).where(
            and_(
                MacroIndicator.indicator == record.indicator,
                MacroIndicator.date == record.date,
                MacroIndicator.source == record.source,
            )
        )
    )
    if not exists:
        session.add(record)


def get_macro_series(
    session: Session,
    indicator: str,
    country_id: Optional[int] = None,
    start: Optional[date] = None,
) -> list[MacroIndicator]:
    stmt = select(MacroIndicator).where(MacroIndicator.indicator == indicator)
    if country_id is not None:
        stmt = stmt.where(MacroIndicator.country_id == country_id)
    if start:
        stmt = stmt.where(MacroIndicator.date >= start)
    return list(session.scalars(stmt.order_by(MacroIndicator.date)))


# ── Commodity Prices ──────────────────────────────────────────────────────────

def upsert_commodity_price(session: Session, record: CommodityPrice) -> None:
    """Dedup on (commodity_id, date, exchange).

    BUG FIX: When commodity_id is None, the old code's WHERE clause
    `CommodityPrice.commodity_id == None` evaluated to SQL NULL and
    never matched existing rows. We now handle NULL explicitly.
    """
    if record.commodity_id is not None:
        exists = session.scalar(
            select(CommodityPrice).where(
                and_(
                    CommodityPrice.commodity_id == record.commodity_id,
                    CommodityPrice.date == record.date,
                    CommodityPrice.exchange == record.exchange,
                )
            )
        )
    else:
        # commodity_id is None — should not happen after coingecko/eia fixes,
        # but guard against it: dedup on exchange+date only
        exists = session.scalar(
            select(CommodityPrice).where(
                and_(
                    CommodityPrice.commodity_id.is_(None),
                    CommodityPrice.date == record.date,
                    CommodityPrice.exchange == record.exchange,
                )
            )
        )
    if not exists:
        session.add(record)


# ── FX Rates ──────────────────────────────────────────────────────────────────

def upsert_fx_rate(session: Session, record: FxRate) -> None:
    exists = session.scalar(
        select(FxRate).where(
            and_(FxRate.pair == record.pair, FxRate.date == record.date)
        )
    )
    if not exists:
        session.add(record)


# ── Events ────────────────────────────────────────────────────────────────────

def upsert_event(session: Session, record: Event) -> None:
    """Insert event only if source_url+date+type not already present.

    BUG FIX: RSS and GDELT collectors previously used session.add() directly,
    producing duplicates on every run. Events with no source_url are always
    inserted (manual events cannot be deduplicated by URL).
    """
    if not record.source_url:
        session.add(record)
        return
    # Flush pending inserts so the SELECT sees rows added earlier in this session
    session.flush()
    exists = session.scalar(
        select(Event).where(
            and_(
                Event.source_url == record.source_url,
                Event.date == record.date,
                Event.type == record.type,
            )
        )
    )
    if not exists:
        session.add(record)


# ── Fund NAV ──────────────────────────────────────────────────────────────────

def upsert_fund_nav(session: Session, record: FundNav) -> None:
    """Insert NAV if scheme_code+date not already present."""
    exists = session.scalar(
        select(FundNav).where(
            and_(
                FundNav.scheme_code == record.scheme_code,
                FundNav.date == record.date,
            )
        )
    )
    if not exists:
        session.add(record)


def get_fund_nav(
    session: Session,
    scheme_code: str,
    start: Optional[date] = None,
) -> list[FundNav]:
    stmt = select(FundNav).where(FundNav.scheme_code == scheme_code)
    if start:
        stmt = stmt.where(FundNav.date >= start)
    return list(session.scalars(stmt.order_by(FundNav.date)))


# ── News Articles ─────────────────────────────────────────────────────────────

def upsert_news_article(session: Session, record: NewsArticle) -> None:
    if not record.source_url:
        session.add(record)
        return
    exists = session.scalar(
        select(NewsArticle).where(NewsArticle.source_url == record.source_url)
    )
    if not exists:
        session.add(record)


# ── Regulatory Orders ─────────────────────────────────────────────────────────

def upsert_regulatory_order(session: Session, record: RegulatoryOrder) -> None:
    if not record.source_url:
        session.add(record)
        return
    exists = session.scalar(
        select(RegulatoryOrder).where(RegulatoryOrder.source_url == record.source_url)
    )
    if not exists:
        session.add(record)


# ── Earnings Transcripts ──────────────────────────────────────────────────────

def upsert_earnings_transcript(session: Session, record: EarningsTranscript) -> None:
    exists = session.scalar(
        select(EarningsTranscript).where(
            and_(
                EarningsTranscript.ticker == record.ticker,
                EarningsTranscript.quarter == record.quarter,
            )
        )
    )
    if not exists:
        session.add(record)


# ── Collection Log ────────────────────────────────────────────────────────────

def insert_collection_log(session: Session, record: CollectionLog) -> None:
    session.add(record)


def get_recent_logs(
    session: Session, source_name: Optional[str] = None, limit: int = 50
) -> list[CollectionLog]:
    stmt = select(CollectionLog)
    if source_name:
        stmt = stmt.where(CollectionLog.source_name == source_name)
    return list(session.scalars(stmt.order_by(desc(CollectionLog.timestamp)).limit(limit)))


# ── Validation Errors ─────────────────────────────────────────────────────────

def insert_validation_error(session: Session, record: ValidationError) -> None:
    session.add(record)


# ── Company ───────────────────────────────────────────────────────────────────

def get_or_create_company(session: Session, ticker: str, name: str, exchange: str = "NSE") -> Company:
    company = session.scalar(
        select(Company).where(
            and_(Company.ticker == ticker, Company.exchange == exchange)
        )
    )
    if not company:
        company = Company(ticker=ticker, name=name, exchange=exchange)
        session.add(company)
        session.flush()
    return company
