"""
processing/validator.py
────────────────────────
Rules-based validation engine for all collected financial data.

Design principles:
  - Never crashes — every record is flagged, not dropped
  - Returns ValidationResult with per-field errors
  - Logs all violations with severity: error | warning | info
  - Persists violations to validation_errors table for audit
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from loguru import logger

from database.connection import get_session
from database.models import ValidationError
from database.queries import insert_validation_error

# ── ISO 4217 currency codes (subset — extend as needed) ─────────────────────
VALID_CURRENCIES: frozenset[str] = frozenset([
    "AED", "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "MXN", "MYR", "NOK",
    "NZD", "PHP", "PLN", "RON", "RUB", "SAR", "SEK", "SGD", "THB", "TRY",
    "TWD", "UAH", "USD", "VND", "ZAR", "XAU", "XAG", "BTC", "ETH",
])

# NSE ticker: uppercase alpha/numeric, 1–20 chars
NSE_TICKER_RE = re.compile(r"^[A-Z0-9&\-]{1,20}$")
# BSE ticker: numeric, 6 digits
BSE_TICKER_RE = re.compile(r"^\d{4,6}$")


@dataclass
class FieldError:
    field: str
    rule: str
    value: Any
    severity: str  # error | warning | info


@dataclass
class ValidationResult:
    source_name: str
    record: dict[str, Any]
    is_valid: bool = True
    errors: list[FieldError] = field(default_factory=list)

    def add_error(
        self, field_name: str, rule: str, value: Any, severity: str = "error"
    ) -> None:
        self.errors.append(FieldError(field=field_name, rule=rule, value=value, severity=severity))
        if severity == "error":
            self.is_valid = False

    @property
    def has_warnings(self) -> bool:
        return any(e.severity == "warning" for e in self.errors)


class Validator:
    """
    Validates financial data records against hard rules.
    Call validate(record, source_name) and inspect ValidationResult.
    """

    def validate(
        self,
        record: dict[str, Any],
        source_name: str,
        record_type: str = "generic",
    ) -> ValidationResult:
        """
        Dispatch to the appropriate rule set based on record_type.
        Supported types: price, fii_dii, macro, commodity, fx, generic
        """
        result = ValidationResult(source_name=source_name, record=record)

        dispatch = {
            "price": self._validate_price,
            "fii_dii": self._validate_fii_dii,
            "macro": self._validate_macro,
            "commodity": self._validate_commodity,
            "fx": self._validate_fx,
        }
        validate_fn = dispatch.get(record_type, self._validate_generic)
        validate_fn(record, result)

        # Common rules applied to all record types
        self._validate_date_fields(record, result)
        self._validate_currency_fields(record, result)
        self._validate_percentage_fields(record, result)

        # Persist errors to DB (non-blocking)
        if result.errors:
            self._persist_errors(result)

        return result

    # ── Record-type validators ────────────────────────────────────────────────

    def _validate_price(self, record: dict[str, Any], result: ValidationResult) -> None:
        """Rules for price_history records."""
        close = record.get("close")
        volume = record.get("volume")
        open_ = record.get("open")
        high = record.get("high")
        low = record.get("low")
        ticker = record.get("ticker", "")
        exchange = record.get("exchange", "NSE")

        # Price cannot be zero or negative
        if close is not None:
            try:
                close_f = float(close)
                if close_f <= 0:
                    result.add_error("close", "price_must_be_positive", close, severity="error")
            except (TypeError, ValueError):
                result.add_error("close", "price_not_numeric", close, severity="error")

        # Volume cannot be negative
        if volume is not None:
            try:
                vol_f = float(volume)
                if vol_f < 0:
                    result.add_error("volume", "volume_cannot_be_negative", volume, severity="error")
            except (TypeError, ValueError):
                result.add_error("volume", "volume_not_numeric", volume, severity="warning")

        # OHLC sanity: high >= low, high >= open/close, low <= open/close
        if high is not None and low is not None:
            try:
                if float(high) < float(low):
                    result.add_error("high", "high_less_than_low", f"H={high} L={low}", severity="error")
            except (TypeError, ValueError):
                pass

        if high is not None and close is not None:
            try:
                if float(close) > float(high) * 1.001:  # 0.1% tolerance
                    result.add_error("close", "close_exceeds_high", f"C={close} H={high}", severity="warning")
            except (TypeError, ValueError):
                pass

        # Ticker format
        if ticker:
            if exchange == "NSE" and not NSE_TICKER_RE.match(str(ticker).upper()):
                result.add_error("ticker", "ticker_format_nse", ticker, severity="warning")
            elif exchange == "BSE" and not BSE_TICKER_RE.match(str(ticker)):
                result.add_error("ticker", "ticker_format_bse", ticker, severity="info")

    def _validate_fii_dii(self, record: dict[str, Any], result: ValidationResult) -> None:
        """Rules for fii_dii_flows records."""
        category = record.get("category", "")
        buy = record.get("buy_value")
        sell = record.get("sell_value")
        net = record.get("net_value")

        if category not in ("FII", "DII"):
            result.add_error("category", "invalid_category", category, severity="error")

        for field_name, val in [("buy_value", buy), ("sell_value", sell)]:
            if val is not None:
                try:
                    f = float(val)
                    if f < 0:
                        result.add_error(field_name, "flow_cannot_be_negative", val, severity="warning")
                except (TypeError, ValueError):
                    result.add_error(field_name, "not_numeric", val, severity="error")

        # Net = buy - sell consistency check
        if buy is not None and sell is not None and net is not None:
            try:
                expected_net = float(buy) - float(sell)
                if abs(expected_net - float(net)) > 0.01:
                    result.add_error(
                        "net_value",
                        "net_inconsistent",
                        f"expected={expected_net:.2f} got={net}",
                        severity="warning",
                    )
            except (TypeError, ValueError):
                pass

    def _validate_macro(self, record: dict[str, Any], result: ValidationResult) -> None:
        """Rules for macro_indicators records."""
        value = record.get("value")
        indicator = record.get("indicator", "")

        if value is not None:
            try:
                float(value)
            except (TypeError, ValueError):
                result.add_error("value", "not_numeric", value, severity="error")
        else:
            result.add_error("value", "value_is_null", None, severity="warning")

        if not indicator:
            result.add_error("indicator", "indicator_empty", indicator, severity="error")

    def _validate_commodity(self, record: dict[str, Any], result: ValidationResult) -> None:
        """Rules for commodity_prices records."""
        price = record.get("price")

        if price is not None:
            try:
                p = float(price)
                if p <= 0:
                    result.add_error("price", "price_must_be_positive", price, severity="error")
            except (TypeError, ValueError):
                result.add_error("price", "not_numeric", price, severity="error")
        else:
            result.add_error("price", "price_is_null", None, severity="error")

    def _validate_fx(self, record: dict[str, Any], result: ValidationResult) -> None:
        """Rules for fx_rates records."""
        rate = record.get("rate")
        pair = record.get("pair", "")

        if rate is not None:
            try:
                r = float(rate)
                if r <= 0:
                    result.add_error("rate", "rate_must_be_positive", rate, severity="error")
            except (TypeError, ValueError):
                result.add_error("rate", "not_numeric", rate, severity="error")

        if pair and "/" not in pair:
            result.add_error("pair", "invalid_pair_format", pair, severity="warning")

    def _validate_generic(self, record: dict[str, Any], result: ValidationResult) -> None:
        """Minimal sanity checks for unknown record types."""
        # Revenue cannot be negative
        revenue = record.get("revenue")
        if revenue is not None:
            try:
                if float(revenue) < 0:
                    result.add_error("revenue", "revenue_cannot_be_negative", revenue, severity="error")
            except (TypeError, ValueError):
                pass

        # Capex cannot exceed revenue
        capex = record.get("capex")
        if capex is not None and revenue is not None:
            try:
                if float(capex) > float(revenue):
                    result.add_error(
                        "capex",
                        "capex_exceeds_revenue",
                        f"capex={capex} revenue={revenue}",
                        severity="warning",
                    )
            except (TypeError, ValueError):
                pass

        # Margins between -100% and 100%
        for margin_field in ("gross_margin", "ebitda_margin", "net_margin", "operating_margin"):
            margin = record.get(margin_field)
            if margin is not None:
                try:
                    m = float(margin)
                    if not (-100 <= m <= 100):
                        result.add_error(
                            margin_field,
                            "margin_out_of_range",
                            margin,
                            severity="error",
                        )
                except (TypeError, ValueError):
                    pass

    # ── Cross-cutting rules ───────────────────────────────────────────────────

    def _validate_date_fields(
        self, record: dict[str, Any], result: ValidationResult
    ) -> None:
        """Date cannot be in the future."""
        today = date.today()
        for date_field in ("date", "filing_date", "event_date", "obs_date"):
            val = record.get(date_field)
            if val is None:
                continue
            try:
                if isinstance(val, str):
                    val = date.fromisoformat(val[:10])
                if isinstance(val, datetime):
                    val = val.date()
                if isinstance(val, date) and val > today:
                    result.add_error(
                        date_field,
                        "date_in_future",
                        str(val),
                        severity="error",
                    )
            except (ValueError, TypeError):
                result.add_error(date_field, "invalid_date_format", val, severity="warning")

    def _validate_currency_fields(
        self, record: dict[str, Any], result: ValidationResult
    ) -> None:
        """Currency must be a valid ISO 4217 code."""
        for cur_field in ("currency", "base_currency", "quote_currency"):
            val = record.get(cur_field)
            if val is None:
                continue
            if str(val).upper() not in VALID_CURRENCIES:
                result.add_error(
                    cur_field,
                    "invalid_iso_4217_currency",
                    val,
                    severity="warning",
                )

    def _validate_percentage_fields(
        self, record: dict[str, Any], result: ValidationResult
    ) -> None:
        """Percentage fields must be between -100 and 100."""
        pct_suffixes = ("_pct", "_pct_24h", "_pct_change", "holding_pct", "change_pct")
        for key, val in record.items():
            if val is None:
                continue
            if any(key.endswith(suffix) or key == suffix.lstrip("_") for suffix in pct_suffixes):
                try:
                    f = float(val)
                    if not (-100 <= f <= 100):
                        result.add_error(
                            key,
                            "percentage_out_of_range",
                            val,
                            severity="warning",
                        )
                except (TypeError, ValueError):
                    pass

    # ── Persistence ───────────────────────────────────────────────────────────

    def _persist_errors(self, result: ValidationResult) -> None:
        """Write all validation errors to the validation_errors table."""
        try:
            with get_session() as session:
                for err in result.errors:
                    ve = ValidationError(
                        source_name=result.source_name,
                        field=err.field,
                        rule=err.rule,
                        value=str(err.value)[:500] if err.value is not None else None,
                        severity=err.severity,
                        record_json={
                            k: (str(v)[:200] if v is not None else None)
                            for k, v in result.record.items()
                        },
                    )
                    insert_validation_error(session, ve)
        except Exception as exc:
            # Never let DB failure crash validation
            logger.error(f"[validator] Failed to persist validation errors: {exc}")

        for err in result.errors:
            log_level = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}.get(
                err.severity, "DEBUG"
            )
            logger.log(
                log_level,
                f"[validator/{result.source_name}] "
                f"field={err.field} rule={err.rule} value={err.value!r}",
            )


# Module-level singleton
validator = Validator()
