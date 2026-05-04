"""
processing/entity_resolver.py
──────────────────────────────
Resolves raw identifiers (ticker strings, company names, country ISOs)
to database entity IDs. Uses in-memory LRU-style caches per session.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from loguru import logger
from sqlalchemy import select

from database.connection import get_session
from database.models import Commodity, Company, Country


@lru_cache(maxsize=2048)
def resolve_country_id(iso_code: str) -> Optional[int]:
    """Return country.id for a given ISO code, creating the row if absent."""
    if not iso_code:
        return None
    iso = iso_code.strip().upper()
    try:
        with get_session() as session:
            country = session.scalar(select(Country).where(Country.iso_code == iso))
            if not country:
                country = Country(iso_code=iso, name=iso)  # name resolved later
                session.add(country)
                session.flush()
            return country.id
    except Exception as exc:
        logger.warning(f"[entity_resolver] Country lookup failed for {iso}: {exc}")
        return None


@lru_cache(maxsize=4096)
def resolve_company_id(ticker: str, exchange: str = "NSE") -> Optional[int]:
    """Return company.id for a ticker, creating a stub row if absent."""
    if not ticker:
        return None
    try:
        with get_session() as session:
            company = session.scalar(
                select(Company).where(
                    Company.ticker == ticker,
                    Company.exchange == exchange,
                )
            )
            if not company:
                company = Company(ticker=ticker, name=ticker, exchange=exchange)
                session.add(company)
                session.flush()
            return company.id
    except Exception as exc:
        logger.warning(f"[entity_resolver] Company lookup failed for {ticker}: {exc}")
        return None


@lru_cache(maxsize=512)
def resolve_commodity_id(name: str, commodity_type: str = "energy") -> Optional[int]:
    """Return commodity.id, creating stub row if absent."""
    if not name:
        return None
    try:
        with get_session() as session:
            commodity = session.scalar(
                select(Commodity).where(
                    Commodity.name == name,
                    Commodity.type == commodity_type,
                )
            )
            if not commodity:
                commodity = Commodity(name=name, type=commodity_type)
                session.add(commodity)
                session.flush()
            return commodity.id
    except Exception as exc:
        logger.warning(f"[entity_resolver] Commodity lookup failed for {name}: {exc}")
        return None


def clear_caches() -> None:
    """Clear all resolver caches (call after bulk imports)."""
    resolve_country_id.cache_clear()
    resolve_company_id.cache_clear()
    resolve_commodity_id.cache_clear()
