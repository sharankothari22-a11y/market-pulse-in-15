"""
tests/test_collectors.py
─────────────────────────
Unit tests for collectors, validator, and processing utilities.
Uses pytest. Database calls are mocked so tests run without PostgreSQL.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Make project root importable
sys.path.insert(0, str(Path(__file__).parents[1]))


# ─────────────────────────────────────────────────────────────────────────────
# Validator tests
# ─────────────────────────────────────────────────────────────────────────────


class TestValidator:
    """Tests for the validation rules engine."""

    def setup_method(self) -> None:
        # Patch DB session so tests don't need a running PostgreSQL
        patcher = patch("processing.validator.get_session")
        self.mock_session = patcher.start()
        self.mock_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
        self.mock_session.return_value.__exit__ = MagicMock(return_value=False)

        from processing.validator import Validator
        self.v = Validator()

    # ── Price validation ──────────────────────────────────────────────────────

    def test_valid_price_record_passes(self) -> None:
        record = {
            "ticker": "RELIANCE",
            "date": "2024-01-15",
            "open": 2400.0,
            "high": 2450.0,
            "low": 2390.0,
            "close": 2440.0,
            "volume": 5000000,
            "exchange": "NSE",
        }
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        errors = [e for e in result.errors if e.severity == "error"]
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_zero_close_price_fails(self) -> None:
        record = {"ticker": "TEST", "close": 0, "exchange": "NSE", "date": "2024-01-15"}
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        assert not result.is_valid
        rules = [e.rule for e in result.errors]
        assert "price_must_be_positive" in rules

    def test_negative_close_price_fails(self) -> None:
        record = {"ticker": "TEST", "close": -100, "exchange": "NSE", "date": "2024-01-15"}
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        assert not result.is_valid

    def test_negative_volume_fails(self) -> None:
        record = {"ticker": "TEST", "close": 100, "volume": -500, "exchange": "NSE", "date": "2024-01-15"}
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        assert not result.is_valid
        rules = [e.rule for e in result.errors]
        assert "volume_cannot_be_negative" in rules

    def test_high_less_than_low_fails(self) -> None:
        record = {
            "ticker": "TEST",
            "close": 100,
            "high": 90,
            "low": 110,
            "exchange": "NSE",
            "date": "2024-01-15",
        }
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        assert not result.is_valid
        rules = [e.rule for e in result.errors]
        assert "high_less_than_low" in rules

    # ── Date validation ───────────────────────────────────────────────────────

    def test_future_date_fails(self) -> None:
        record = {
            "ticker": "TEST",
            "close": 100.0,
            "date": "2099-01-01",
            "exchange": "NSE",
        }
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        assert not result.is_valid
        rules = [e.rule for e in result.errors]
        assert "date_in_future" in rules

    def test_valid_past_date_passes(self) -> None:
        record = {
            "ticker": "TEST",
            "close": 100.0,
            "date": "2020-06-15",
            "exchange": "NSE",
        }
        result = self.v.validate(record, source_name="nse_csv", record_type="price")
        date_errors = [e for e in result.errors if e.field == "date"]
        assert len(date_errors) == 0

    # ── Currency validation ───────────────────────────────────────────────────

    def test_valid_currency_passes(self) -> None:
        record = {"price": 100.0, "currency": "INR", "date": "2024-01-15"}
        result = self.v.validate(record, source_name="coingecko", record_type="commodity")
        currency_errors = [e for e in result.errors if e.field == "currency"]
        assert len(currency_errors) == 0

    def test_invalid_currency_warns(self) -> None:
        record = {"price": 100.0, "currency": "FAKE", "date": "2024-01-15"}
        result = self.v.validate(record, source_name="test", record_type="commodity")
        rules = [e.rule for e in result.errors]
        assert "invalid_iso_4217_currency" in rules

    # ── Financial rules ───────────────────────────────────────────────────────

    def test_negative_revenue_fails(self) -> None:
        record = {"revenue": -1000, "date": "2024-01-15"}
        result = self.v.validate(record, source_name="test", record_type="generic")
        assert not result.is_valid
        rules = [e.rule for e in result.errors]
        assert "revenue_cannot_be_negative" in rules

    def test_capex_exceeds_revenue_warns(self) -> None:
        record = {"revenue": 1000, "capex": 5000, "date": "2024-01-15"}
        result = self.v.validate(record, source_name="test", record_type="generic")
        rules = [e.rule for e in result.errors]
        assert "capex_exceeds_revenue" in rules

    def test_margin_out_of_range_fails(self) -> None:
        record = {"gross_margin": 150, "date": "2024-01-15"}  # 150% is impossible
        result = self.v.validate(record, source_name="test", record_type="generic")
        rules = [e.rule for e in result.errors]
        assert "margin_out_of_range" in rules

    def test_valid_margin_passes(self) -> None:
        record = {"gross_margin": 45.5, "date": "2024-01-15"}
        result = self.v.validate(record, source_name="test", record_type="generic")
        margin_errors = [e for e in result.errors if e.field == "gross_margin"]
        assert len(margin_errors) == 0

    # ── FII/DII validation ────────────────────────────────────────────────────

    def test_valid_fii_dii_record_passes(self) -> None:
        record = {
            "category": "FII",
            "buy_value": 5000.0,
            "sell_value": 3000.0,
            "net_value": 2000.0,
            "date": "2024-01-15",
        }
        result = self.v.validate(record, source_name="nse_csv", record_type="fii_dii")
        errors = [e for e in result.errors if e.severity == "error"]
        assert len(errors) == 0

    def test_invalid_fii_dii_category_fails(self) -> None:
        record = {"category": "UNKNOWN", "date": "2024-01-15"}
        result = self.v.validate(record, source_name="nse_csv", record_type="fii_dii")
        assert not result.is_valid

    # ── FX validation ─────────────────────────────────────────────────────────

    def test_zero_fx_rate_fails(self) -> None:
        record = {"pair": "USD/INR", "rate": 0, "date": "2024-01-15"}
        result = self.v.validate(record, source_name="frankfurter", record_type="fx")
        assert not result.is_valid

    def test_invalid_pair_format_warns(self) -> None:
        record = {"pair": "USDINR", "rate": 83.5, "date": "2024-01-15"}
        result = self.v.validate(record, source_name="frankfurter", record_type="fx")
        rules = [e.rule for e in result.errors]
        assert "invalid_pair_format" in rules


# ─────────────────────────────────────────────────────────────────────────────
# Cleaner / Normalizer tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCleaner:
    def test_strip_whitespace(self) -> None:
        from processing.cleaner import strip_whitespace
        record = {"ticker": "  RELIANCE  ", "exchange": "NSE "}
        out = strip_whitespace(record)
        assert out["ticker"] == "RELIANCE"
        assert out["exchange"] == "NSE"

    def test_normalise_ticker_nse(self) -> None:
        from processing.cleaner import normalise_ticker
        assert normalise_ticker("reliance-EQ", "NSE") == "RELIANCE"
        assert normalise_ticker("HDFCBANK", "NSE") == "HDFCBANK"

    def test_coerce_numeric_comma(self) -> None:
        from processing.cleaner import coerce_numeric
        assert coerce_numeric("1,23,456.78") == pytest.approx(123456.78)
        assert coerce_numeric("₹1000") == pytest.approx(1000.0)
        assert coerce_numeric("bad") is None
        assert coerce_numeric(None) is None

    def test_normalise_indian_number_crore(self) -> None:
        from processing.cleaner import normalise_indian_number
        result = normalise_indian_number("1.5CR")
        assert result == pytest.approx(1.5e7)

    def test_normalise_indian_number_lakh(self) -> None:
        from processing.cleaner import normalise_indian_number
        result = normalise_indian_number("5L")
        assert result == pytest.approx(5e5)


class TestNormalizer:
    def test_normalise_date_iso(self) -> None:
        from processing.normalizer import normalise_date
        assert normalise_date("2024-01-15") == date(2024, 1, 15)

    def test_normalise_date_dmy(self) -> None:
        from processing.normalizer import normalise_date
        assert normalise_date("15-01-2024") == date(2024, 1, 15)

    def test_normalise_date_bmy(self) -> None:
        from processing.normalizer import normalise_date
        assert normalise_date("15-Jan-2024") == date(2024, 1, 15)

    def test_normalise_date_yyyymmdd(self) -> None:
        from processing.normalizer import normalise_date
        assert normalise_date("20240115") == date(2024, 1, 15)

    def test_normalise_date_none(self) -> None:
        from processing.normalizer import normalise_date
        assert normalise_date(None) is None

    def test_normalise_date_from_date(self) -> None:
        from processing.normalizer import normalise_date
        d = date(2024, 6, 1)
        assert normalise_date(d) == d


# ─────────────────────────────────────────────────────────────────────────────
# Base collector tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseCollector:
    def test_collection_result_record_count(self) -> None:
        from collectors.base import CollectionResult
        r = CollectionResult(source_name="test", records=[1, 2, 3], status="ok")
        assert r.record_count == 3

    def test_fallback_chain_default(self) -> None:
        from collectors.base import BaseCollector

        class DummyCollector(BaseCollector):
            source_name = "dummy"

        dc = DummyCollector()
        assert "api" in dc.fallback_chain
        assert "cache" in dc.fallback_chain

    @patch("collectors.base.get_session")
    def test_collect_returns_result_on_cache_hit(self, mock_session: Any) -> None:
        """When all network methods fail, cache hit returns partial result."""
        mock_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        from collectors.base import BaseCollector, CollectionResult

        class CacheOnlyCollector(BaseCollector):
            source_name = "cache_test"
            fallback_chain = ["cache"]

            def _try_cache(self, target_date=None):
                return CollectionResult(
                    source_name=self.source_name,
                    records=["cached_data"],
                    status="partial",
                    method_used="cache",
                )

        c = CacheOnlyCollector()
        result = c.collect()
        assert result.status == "partial"
        assert result.record_count == 1

    @patch("collectors.base.get_session")
    def test_collect_returns_error_when_all_fail(self, mock_session: Any) -> None:
        mock_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        from collectors.base import BaseCollector

        class AlwaysFailCollector(BaseCollector):
            source_name = "always_fail"
            fallback_chain = ["api"]

            def _try_api(self, target_date=None):
                return None

        c = AlwaysFailCollector()
        result = c.collect()
        assert result.status == "error"
