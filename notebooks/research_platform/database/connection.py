"""
database/connection.py
──────────────────────
SQLAlchemy 2.0 engine, session factory, schema management.

Added:
  - seed_countries()  — populates country table on first run (FRED/WorldBank need it)
  - cleanup_old_logs() — prunes collection_log older than 90 days
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL
from database.models import Base, COUNTRY_SEED, Country, CollectionLog

engine: Engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional session, rolling back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Database session error: {exc}")
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """Create all ORM-mapped tables if they don't exist."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully.")


def create_hypertables() -> None:
    """Register TimescaleDB hypertables. Safe to call multiple times."""
    targets = [
        ("price_history",    "date"),
        ("macro_indicators", "date"),
        ("commodity_prices", "date"),
        ("fii_dii_flows",    "date"),
        ("fx_rates",         "date"),
        ("fund_nav",         "date"),
    ]
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'timescaledb'")
        )
        if result.scalar() == 0:
            logger.warning(
                "TimescaleDB not found — tables work as standard PostgreSQL tables."
            )
            return
        for table, col in targets:
            try:
                conn.execute(
                    text(f"SELECT create_hypertable('{table}', '{col}', if_not_exists => TRUE)")
                )
                logger.info(f"Hypertable ensured: {table}.{col}")
            except Exception as exc:
                logger.warning(f"Hypertable {table} skipped: {exc}")
        conn.commit()


def seed_countries() -> None:
    """Insert country reference rows if the table is empty.

    FRED and World Bank both store data linked to Country.id.
    Without this seed, country_id is always NULL and macro-micro
    linkage never works.
    """
    with get_session() as session:
        existing = session.scalar(select(Country).limit(1))
        if existing:
            logger.debug("Countries already seeded — skipping.")
            return
        for iso, name, currency in COUNTRY_SEED:
            session.add(Country(iso_code=iso, name=name, currency=currency))
        logger.info(f"Seeded {len(COUNTRY_SEED)} countries into country table.")


def cleanup_old_logs(days: int = 90) -> int:
    """Delete collection_log rows older than `days` days. Returns rows deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_session() as session:
        rows = session.execute(
            text("DELETE FROM collection_log WHERE timestamp < :cutoff RETURNING id"),
            {"cutoff": cutoff},
        )
        deleted = rows.rowcount
        if deleted:
            logger.info(f"Cleaned {deleted} old collection_log rows (>{days} days).")
        return deleted




def create_pgvector_indexes() -> None:
    """
    Create pgvector HNSW indexes for semantic search on news_articles.embedding.
    Requires: CREATE EXTENSION IF NOT EXISTS vector; in PostgreSQL.
    Safe to call even if pgvector is not installed — skips gracefully.
    """
    with engine.connect() as conn:
        try:
            # Check if pgvector extension is available
            result = conn.execute(text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'"))
            if result.scalar() == 0:
                # Try to create it
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
                    logger.info("pgvector extension created")
                except Exception:
                    logger.info("pgvector extension not available — semantic search will use keyword fallback")
                    return
            # Create HNSW index on news_articles.embedding (stored as JSONB)
            # When migrating to native vector type, use: USING hnsw (embedding vector_cosine_ops)
            # For now, GIN index on JSONB for faster queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_news_articles_embedding
                ON news_articles USING GIN (embedding jsonb_path_ops)
                WHERE embedding IS NOT NULL
            """))
            conn.commit()
            logger.info("pgvector/GIN index created on news_articles.embedding")
        except Exception as exc:
            logger.debug(f"pgvector index skipped: {exc}")


def full_setup() -> None:
    """One-shot: create tables → hypertables → seed countries.
    Call this from main.py on first run.
    """
    create_all_tables()
    create_hypertables()
    seed_countries()
    create_pgvector_indexes()


def check_connection() -> bool:
    """Return True if database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False
