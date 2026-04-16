"""
collectors/base.py
──────────────────
Abstract base class for every data collector.

Fallback order: API → RSS → scrape → cache → alert+log
All network calls retry with exponential backoff (max 2 attempts).
Every run writes a CollectionLog record regardless of outcome.
"""

from __future__ import annotations

import signal
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

import diskcache
from loguru import logger

from config.settings import CACHE_DIR, CACHE_TTL_SECONDS
from database.connection import get_session
from database.models import CollectionLog
from database.queries import insert_collection_log

# Shared disk cache — all collectors use the same cache directory
_cache: diskcache.Cache = diskcache.Cache(CACHE_DIR)

MAX_RETRIES: int = 2
RETRY_BASE_DELAY: float = 0.5  # seconds; doubles each attempt
COLLECTOR_TIMEOUT: int = 30    # hard wall-clock limit per collector (seconds)


@dataclass
class CollectionResult:
    """Standardised return value from every collector run."""

    source_name: str
    method_used: Optional[str] = None       # api | rss | scrape | cache
    records: list[Any] = field(default_factory=list)
    status: str = "ok"                      # ok | error | partial
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    fallback_used: bool = False

    @property
    def record_count(self) -> int:
        return len(self.records)


class BaseCollector(ABC):
    """Abstract collector. Subclasses override _try_api / _try_rss / _try_scrape."""

    # Override in subclass
    source_name: str = "unknown"

    # Override in subclass to customise the fallback order.
    # Valid entries: "api", "rss", "scrape", "cache"
    fallback_chain: list[str] = ["api", "rss", "scrape", "cache"]

    def __init__(self) -> None:
        self._cache = _cache
        self._cache_ttl = CACHE_TTL_SECONDS

    # ── Public entry point ────────────────────────────────────────────────────

    def collect(self, target_date: Optional[date] = None) -> CollectionResult:
        """
        Run the fallback chain until one method succeeds.
        Always logs the outcome to collection_log.
        Hard wall-clock timeout of COLLECTOR_TIMEOUT seconds guards against hangs.
        """
        start_ts = time.monotonic()
        result = CollectionResult(source_name=self.source_name)

        def _timeout_handler(signum, frame):
            raise TimeoutError(f"[{self.source_name}] exceeded {COLLECTOR_TIMEOUT}s wall-clock limit")

        # SIGALRM is Unix-only; skip on platforms that don't support it
        _alarm_set = False
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(COLLECTOR_TIMEOUT)
            _alarm_set = True

        try:
            method_map = {
                "api": self._try_api,
                "rss": self._try_rss,
                "scrape": self._try_scrape,
                "cache": self._try_cache,
            }

            first_method = True
            for method_name in self.fallback_chain:
                method_fn = method_map.get(method_name)
                if method_fn is None:
                    logger.warning(
                        f"[{self.source_name}] Unknown fallback method: {method_name}"
                    )
                    continue

                if not first_method:
                    result.fallback_used = True
                    logger.info(
                        f"[{self.source_name}] Falling back to method: {method_name}"
                    )
                first_method = False

                attempt_result = self._retry(method_fn, target_date=target_date)
                if attempt_result is not None and attempt_result.status in ("ok", "partial"):
                    attempt_result.method_used = method_name
                    attempt_result.fallback_used = result.fallback_used
                    result = attempt_result
                    break
            else:
                # All methods exhausted
                result.status = "error"
                result.error = "All fallback methods failed"
                result.method_used = "none"
                logger.error(
                    f"[{self.source_name}] All fallback methods exhausted. Raising alert."
                )
                self._alert(result)

        except TimeoutError as exc:
            result.status = "error"
            result.error = str(exc)
            result.method_used = "timeout"
            logger.error(str(exc))
        finally:
            if _alarm_set:
                signal.alarm(0)  # cancel the alarm

        result.timestamp = datetime.utcnow()
        elapsed = time.monotonic() - start_ts
        self._log_result(result, duration_seconds=elapsed)
        return result

    # ── Override these in subclasses ──────────────────────────────────────────

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Fetch from primary API. Override in subclass."""
        return None

    def _try_rss(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Fetch from RSS feed. Override in subclass."""
        return None

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Scrape from web page. Override in subclass."""
        return None

    def _try_cache(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Return last known-good data from disk cache."""
        cache_key = self._cache_key(target_date)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info(f"[{self.source_name}] Cache hit: {cache_key}")
            return CollectionResult(
                source_name=self.source_name,
                method_used="cache",
                records=cached,
                status="partial",
            )
        logger.warning(f"[{self.source_name}] Cache miss: {cache_key}")
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cache_key(self, target_date: Optional[date] = None) -> str:
        date_str = target_date.isoformat() if target_date else "latest"
        return f"{self.source_name}:{date_str}"

    def _store_cache(self, records: list[Any], target_date: Optional[date] = None) -> None:
        """Persist records to disk cache after a successful collection."""
        key = self._cache_key(target_date)
        self._cache.set(key, records, expire=self._cache_ttl)
        logger.debug(f"[{self.source_name}] Stored {len(records)} records in cache.")

    def _retry(
        self,
        fn: Any,
        target_date: Optional[date] = None,
    ) -> Optional[CollectionResult]:
        """Call fn up to MAX_RETRIES times with exponential backoff."""
        delay = RETRY_BASE_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = fn(target_date=target_date)
                if result is not None:
                    return result
            except Exception as exc:
                logger.warning(
                    f"[{self.source_name}] Attempt {attempt}/{MAX_RETRIES} failed: {exc}"
                )
                if attempt < MAX_RETRIES:
                    logger.debug(
                        f"[{self.source_name}] Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(
                        f"[{self.source_name}] All {MAX_RETRIES} retry attempts failed."
                    )
        return None

    def _log_result(
        self, result: CollectionResult, duration_seconds: float = 0.0
    ) -> None:
        """Write outcome to collection_log table."""
        log_record = CollectionLog(
            source_name=result.source_name,
            method_used=result.method_used,
            records_collected=result.record_count,
            status=result.status,
            error_message=result.error,
            fallback_used=result.fallback_used,
            timestamp=result.timestamp,
            duration_seconds=round(duration_seconds, 3),
        )
        try:
            with get_session() as session:
                insert_collection_log(session, log_record)
        except Exception as exc:
            # Log to file only — never let DB failure crash the collector
            logger.error(f"[{self.source_name}] Failed to write collection log: {exc}")

        level = "SUCCESS" if result.status == "ok" else "WARNING" if result.status == "partial" else "ERROR"
        logger.log(
            level if level != "SUCCESS" else "INFO",
            f"[{self.source_name}] {result.status.upper()} | "
            f"method={result.method_used} | records={result.record_count} | "
            f"fallback={result.fallback_used} | duration={duration_seconds:.2f}s",
        )

    def _alert(self, result: CollectionResult) -> None:
        """
        Called when all fallback methods are exhausted.
        Override to send Slack / email / PagerDuty alerts.
        """
        logger.critical(
            f"[{self.source_name}] ALERT — all methods failed. "
            f"Error: {result.error}. Manual intervention may be required."
        )
