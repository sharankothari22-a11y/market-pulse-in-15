"""
main.py
────────
research_platform CLI.

Usage:
    python main.py collect --source nse_csv
    python main.py collect --all
    python main.py collect --source nse_csv --date 2025-03-31
    python main.py schedule
    python main.py validate --source nse_csv
    python main.py status
    python main.py cleanup
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from config.settings import LOG_DIR, LOG_LEVEL

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL, colorize=True, enqueue=True)
logger.add(
    f"{LOG_DIR}/research_platform_{{time:YYYY-MM-DD}}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG",
    enqueue=True,
)


@click.group()
def cli() -> None:
    """research_platform — unified financial data collection engine."""
    pass


@cli.command()
@click.option("--source", "-s", default=None, help="Collector source name")
@click.option("--all", "collect_all", is_flag=True, help="Run all collectors")
@click.option("--date", "target_date", default=None, help="YYYY-MM-DD")
def collect(source: Optional[str], collect_all: bool, target_date: Optional[str]) -> None:
    """Collect data from one or all sources."""
    from collectors.registry import all_collectors, get_collector

    run_date: Optional[date] = None
    if target_date:
        try:
            run_date = date.fromisoformat(target_date)
        except ValueError:
            click.echo(f"Invalid date: {target_date}. Use YYYY-MM-DD.", err=True)
            sys.exit(1)

    _ensure_db()

    if collect_all:
        for c in all_collectors():
            click.echo(f"→ {c.source_name}")
            _print_result(c.collect(target_date=run_date))
    elif source:
        try:
            collector = get_collector(source)
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        click.echo(f"→ {source}")
        _print_result(collector.collect(target_date=run_date))
    else:
        click.echo("Specify --source <name> or --all.", err=True)
        sys.exit(1)


@cli.command()
def schedule() -> None:
    """Start the APScheduler blocking scheduler."""
    _ensure_db()
    from scheduler.runner import start_scheduler
    start_scheduler()


@cli.command()
@click.option("--source", "-s", required=True)
@click.option("--limit", default=100, show_default=True)
def validate(source: str, limit: int) -> None:
    """Show recent validation errors for a source."""
    from sqlalchemy import select, desc
    from database.connection import get_session
    from database.models import ValidationError

    with get_session() as session:
        rows = session.scalars(
            select(ValidationError)
            .where(ValidationError.source_name == source)
            .order_by(desc(ValidationError.created_at))
            .limit(limit)
        ).all()

    if not rows:
        click.echo(f"No validation errors for: {source}")
        return

    click.echo(f"\n{'─'*70}")
    click.echo(f"Validation errors for: {source}  ({len(rows)} most recent)")
    click.echo(f"{'─'*70}")
    for row in rows:
        color = {"error": "red", "warning": "yellow", "info": "cyan"}.get(row.severity, "white")
        click.echo(
            f"[{click.style(row.severity.upper(), fg=color)}] "
            f"field={row.field}  rule={row.rule}  value={row.value}"
        )
    click.echo(f"{'─'*70}\n")


@cli.command()
def status() -> None:
    """System status dashboard."""
    from sqlalchemy import select, func, desc
    from database.connection import get_session, check_connection
    from database.models import (
        CollectionLog, PriceHistory, FiiDiiFlow,
        CommodityPrice, FxRate, MacroIndicator, Event, FundNav,
    )

    click.echo(f"\n{'═'*65}")
    click.echo("  research_platform — system status")
    click.echo(f"{'═'*65}")

    db_ok = check_connection()
    click.echo(f"\n  Database : {click.style('CONNECTED', fg='green') if db_ok else click.style('OFFLINE', fg='red')}")

    if not db_ok:
        click.echo("  Cannot retrieve stats.\n")
        return

    with get_session() as session:
        click.echo("\n  Collection log (last run per source):")
        click.echo(f"  {'Source':<22} {'Status':<10} {'Records':>8}  {'Method':<8}  When")
        click.echo(f"  {'─'*60}")

        subq = (
            select(CollectionLog.source_name, func.max(CollectionLog.timestamp).label("last_ts"))
            .group_by(CollectionLog.source_name)
            .subquery()
        )
        logs = session.scalars(
            select(CollectionLog).join(
                subq,
                (CollectionLog.source_name == subq.c.source_name) &
                (CollectionLog.timestamp == subq.c.last_ts),
            )
        ).all()

        for log in sorted(logs, key=lambda x: x.source_name):
            color = "green" if log.status == "ok" else "yellow" if log.status == "partial" else "red"
            ts = log.timestamp.strftime("%m-%d %H:%M") if log.timestamp else "—"
            click.echo(
                f"  {log.source_name:<22} "
                f"{click.style(log.status, fg=color):<10} "
                f"{log.records_collected:>8,}  {(log.method_used or '—'):<8}  {ts}"
            )

        click.echo("\n  Table row counts:")
        counts = [
            ("price_history",    PriceHistory,    "Equity prices"),
            ("fii_dii_flows",    FiiDiiFlow,      "FII/DII flows"),
            ("commodity_prices", CommodityPrice,  "Crypto + commodity"),
            ("fx_rates",         FxRate,          "FX rates"),
            ("macro_indicators", MacroIndicator,  "Macro indicators"),
            ("fund_nav",         FundNav,         "MF NAVs"),
            ("event",            Event,           "Events / news"),
        ]
        for _, model, label in counts:
            n = session.scalar(select(func.count()).select_from(model)) or 0
            click.echo(f"    {label:<22} {n:>10,} rows")

    click.echo(f"\n{'═'*65}\n")


@cli.command()
@click.option("--days", default=90, show_default=True, help="Delete logs older than N days")
def cleanup(days: int) -> None:
    """Prune old collection_log rows."""
    from database.connection import cleanup_old_logs
    _ensure_db()
    deleted = cleanup_old_logs(days=days)
    click.echo(f"Deleted {deleted} collection_log rows older than {days} days.")


def _ensure_db() -> None:
    from database.connection import check_connection, full_setup
    if not check_connection():
        click.echo(
            "ERROR: Cannot connect to PostgreSQL.\n"
            "Check DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in .env",
            err=True,
        )
        sys.exit(1)
    full_setup()   # create tables + hypertables + seed countries (idempotent)


def _print_result(result: object) -> None:
    color = {"ok": "green", "partial": "yellow", "error": "red"}.get(
        getattr(result, "status", ""), "white"
    )
    click.echo(
        f"   {click.style(result.status, fg=color)}  "  # type: ignore[attr-defined]
        f"{result.record_count} records  "              # type: ignore[attr-defined]
        f"method={result.method_used}"                  # type: ignore[attr-defined]
    )
    if getattr(result, "error", None):
        click.echo(f"   ↳ {result.error}", err=True)    # type: ignore[attr-defined]



@cli.command()
@click.option("--session", "session_id", default=None, help="Existing session ID")
@click.option("--ticker", default=None, help="Ticker — creates new session if --session not given")
@click.option("--sector", default="other", show_default=True,
              help="petroleum_energy | banking_nbfc | fmcg_retail | pharma | it_tech | real_estate | auto | other")
def report(session_id, ticker, sector):
    """Generate a 2-page A4 HTML research report.

    Examples:\n
        python main.py report --session RELIANCE_20260413_120000\n
        python main.py report --ticker RELIANCE --sector petroleum_energy
    """
    import sys
    from ai_engine.pdf_builder import build_report
    from ai_engine.session_manager import load_session, new_session
    from ai_engine.scoring import score_session

    ses = None
    if session_id:
        ses = load_session(session_id)
        if ses is None:
            click.echo(f"Session not found: {session_id}", err=True); sys.exit(1)
        click.echo(f"Loaded: {ses.session_id}")
        if sector == "other":
            try:
                import json as _j
                mf = ses.session_dir / "session_meta.json"
                if mf.exists():
                    d = _j.loads(mf.read_text())
                    detected = d.get("sector_mapped") or d.get("_sector") or "other"
                    if detected != "other": sector = detected; click.echo(f"Sector: {sector}")
            except Exception: pass
    elif ticker:
        ses = new_session(ticker.upper()); click.echo(f"Session: {ses.session_id}")
    else:
        click.echo("Specify --session or --ticker.", err=True); sys.exit(1)

    click.echo(f"Building report (sector={sector}) ...")
    try:
        html_path = build_report(ses, sector=sector)
        scoring   = score_session(ses, sector=sector)
        click.echo(click.style("✓ Report: ", fg="green") + str(html_path.resolve()))
        click.echo(f"  Rec: {scoring.recommendation}  Score: {scoring.composite_score:.0f}/100  Quality: {scoring.business_quality}")
        click.echo("Open in Chrome → Ctrl+P → Save as PDF")
    except Exception as exc:
        click.echo(f"Failed: {exc}", err=True); sys.exit(1)


if __name__ == "__main__":
    cli()
