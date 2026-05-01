"""
Ticker resolver: maps any raw ticker string to exchange, region,
currency, risk-free rate, and equity risk premium.

Supports: India (NSE/BSE), US (NASDAQ/NYSE), UK (LSE).
Other exchanges: yfinance currency fallback, ERP default 5%.

RF rates:
  US  — live 10Y Treasury ^TNX (fallback 4.2%)
  IN  — 7.2%  (India 10Y G-Sec)
  GB  — 4.3%  (UK 10Y Gilt)
  EU  — 2.4%  (Germany 10Y Bund)
  JP  — 1.0%  (Japan 10Y JGB)

ERP from Damodaran Jan 2026:
  US 5.5%, IN 6.8%, GB 5.0%, EU 5.5%, JP 5.5%
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Suffix → region code
# ---------------------------------------------------------------------------
_SUFFIX_REGION: dict[str, str] = {
    ".NS": "IN",
    ".BO": "IN",
    ".L":  "GB",
    ".PA": "EU",
    ".DE": "EU",
    ".AS": "EU",  # Amsterdam
    ".MI": "EU",  # Milan
    ".MC": "EU",  # Madrid
    ".T":  "JP",
}

# ---------------------------------------------------------------------------
# Region metadata (rf_rate None → fetch live for US)
# ---------------------------------------------------------------------------
_REGION_META: dict[str, dict] = {
    "IN": {
        "default_exchange": "NSE",
        "currency": "INR",
        "currency_symbol": "₹",
        "rf_rate": 0.072,   # India 10Y G-Sec — hardcoded
        "equity_risk_premium": 0.068,  # Damodaran Jan 2026
    },
    "US": {
        "default_exchange": "NASDAQ",
        "currency": "USD",
        "currency_symbol": "$",
        "rf_rate": None,    # fetched live from ^TNX
        "equity_risk_premium": 0.055,  # Damodaran Jan 2026
    },
    "GB": {
        "default_exchange": "LSE",
        "currency": "GBP",
        "currency_symbol": "£",
        "rf_rate": 0.043,   # UK 10Y Gilt — hardcoded
        "equity_risk_premium": 0.050,  # Damodaran Jan 2026
    },
    "EU": {
        "default_exchange": "XETRA",
        "currency": "EUR",
        "currency_symbol": "€",
        "rf_rate": 0.024,   # Germany 10Y Bund — hardcoded
        "equity_risk_premium": 0.055,  # Damodaran Jan 2026
    },
    "JP": {
        "default_exchange": "TSE",
        "currency": "JPY",
        "currency_symbol": "¥",
        "rf_rate": 0.010,   # Japan 10Y JGB — hardcoded
        "equity_risk_premium": 0.055,  # Damodaran Jan 2026
    },
}

# ---------------------------------------------------------------------------
# Known US tickers — skip yfinance lookup for these
# ---------------------------------------------------------------------------
_KNOWN_US: frozenset[str] = frozenset({
    # Mega-caps
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    "BRK.A", "BRK.B",
    # Tech
    "NFLX", "AMD", "INTC", "QCOM", "AVGO", "TXN", "MU", "AMAT",
    "KLAC", "LRCX", "CRM", "ORCL", "ADBE", "NOW", "SNOW", "PLTR",
    "UBER", "LYFT", "ABNB", "COIN", "HOOD", "RBLX", "SPOT", "ZM",
    "DOCU", "TWLO", "MDB", "DDOG", "CRWD", "PANW", "ZS", "NET",
    "FTNT", "OKTA", "SPLK", "ESTC",
    # Finance
    "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "SCHW", "USB",
    "PNC", "AXP", "V", "MA", "PYPL", "SQ",
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR",
    "BMY", "AMGN", "GILD", "REGN", "BIIB", "VRTX", "MRNA", "BNTX",
    # Consumer
    "WMT", "HD", "NKE", "MCD", "SBUX", "TGT", "COST", "DIS", "CMCSA",
    "PG", "KO", "PEP", "PM", "MO", "CL", "GIS", "K", "CPB",
    # Industrial / Energy
    "GE", "BA", "CAT", "DE", "LMT", "RTX", "NOC", "GD", "XOM", "CVX",
    "COP", "SLB", "HAL", "OXY", "MPC", "VLO", "PSX",
    # Telecom
    "T", "VZ", "TMUS",
    # Utilities
    "NEE", "DUK", "SO", "AEP", "EXC", "SRE",
    # ETFs / indices
    "SPY", "QQQ", "IWM", "DIA", "GLD", "SLV", "USO", "TLT", "HYG",
    "^GSPC", "^IXIC", "^DJI", "^TNX",
})

# ---------------------------------------------------------------------------
# In-process caches
# ---------------------------------------------------------------------------
_resolution_cache: dict[str, dict] = {}
_rf_rate_cache: dict[str, float] = {}

# ---------------------------------------------------------------------------
# Currency → region fallback for yfinance results
# ---------------------------------------------------------------------------
_CURRENCY_REGION: dict[str, str] = {
    "INR": "IN",
    "USD": "US",
    "GBP": "GB",
    "EUR": "EU",
    "JPY": "JP",
}

_EXCHANGE_REGION: dict[str, str] = {
    "NSI": "IN", "NSE": "IN", "BSE": "IN", "BOM": "IN",
    "NMS": "US", "NGM": "US", "NYQ": "US", "NYSE": "US",
    "NASDAQ": "US", "PCX": "US",
    "LSE": "GB", "IOB": "GB",
    "XETRA": "EU", "FRA": "EU", "AMS": "EU", "PAR": "EU",
    "TYO": "JP",
}


def _get_us_rf_rate() -> float:
    """Fetch US 10Y Treasury rate from ^TNX (cached per process run)."""
    if "US" in _rf_rate_cache:
        return _rf_rate_cache["US"]
    try:
        import yfinance as yf  # local import so module loads without yfinance
        tnx = yf.Ticker("^TNX")
        fi = tnx.fast_info
        rate_pct = getattr(fi, "last_price", None) or getattr(fi, "lastPrice", None)
        if rate_pct and 0.5 < float(rate_pct) < 15.0:
            result = float(rate_pct) / 100.0
            _rf_rate_cache["US"] = result
            logger.info(f"ticker_resolver: US rf_rate from ^TNX = {result:.4f}")
            return result
    except Exception as exc:
        logger.warning(f"ticker_resolver: ^TNX fetch failed ({exc}), using 4.2% fallback")
    _rf_rate_cache["US"] = 0.042
    return 0.042


def _build_result(
    symbol: str,
    yf_symbol: str,
    region: str,
    suffix: str = "",
) -> dict:
    meta = _REGION_META.get(region)
    if meta is None:
        logger.warning(f"ticker_resolver: unknown region '{region}' for {symbol}")
        return {
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "exchange": "UNKNOWN",
            "region": "OTHER",
            "currency": "USD",
            "currency_symbol": "$",
            "rf_rate": 0.042,
            "equity_risk_premium": 0.050,
        }

    rf = meta["rf_rate"]
    if rf is None:
        rf = _get_us_rf_rate()

    exchange = meta["default_exchange"]
    if region == "IN" and suffix == ".BO":
        exchange = "BSE"

    return {
        "symbol": symbol,
        "yf_symbol": yf_symbol,
        "exchange": exchange,
        "region": region,
        "currency": meta["currency"],
        "currency_symbol": meta["currency_symbol"],
        "rf_rate": rf,
        "equity_risk_premium": meta["equity_risk_premium"],
    }


def _resolve_impl(raw: str) -> dict:
    """Core resolution logic (no caching layer)."""
    import yfinance as yf

    t = raw.strip().upper()

    # 1. Pre-qualified: has a recognised exchange suffix
    for suffix, region in _SUFFIX_REGION.items():
        if t.endswith(suffix):
            symbol = t[: -len(suffix)]
            return _build_result(symbol, t, region, suffix)

    # 2. Known US ticker — no network call needed
    if t in _KNOWN_US:
        return _build_result(t, t, "US")

    # 3. yfinance lookup: try bare ticker first (handles most US/intl stocks)
    try:
        info = yf.Ticker(t).info or {}
        currency = info.get("currency", "")
        exchange = info.get("exchange", "")

        # Exchange takes priority over currency
        region = _EXCHANGE_REGION.get(exchange) or _CURRENCY_REGION.get(currency)

        if region == "IN":
            yf_sym = f"{t}.NS"
            return _build_result(t, yf_sym, "IN", ".NS")
        if region == "GB":
            yf_sym = f"{t}.L"
            return _build_result(t, yf_sym, "GB", ".L")
        if region in _REGION_META:
            return _build_result(t, t, region)
        if currency:
            logger.warning(
                f"ticker_resolver: fallback for {t} "
                f"(exchange={exchange!r}, currency={currency!r})"
            )
            fallback_region = _CURRENCY_REGION.get(currency, "US")
            return _build_result(t, t, fallback_region)
    except Exception as exc:
        logger.warning(f"ticker_resolver: bare yfinance lookup failed for {t}: {exc}")

    # 4. Try appending .NS — catches Indian tickers where bare lookup returns empty info
    #    (yfinance sometimes returns {currency: None} for Indian names without suffix)
    try:
        ns_sym = f"{t}.NS"
        info = yf.Ticker(ns_sym).info or {}
        currency = info.get("currency", "")
        exchange = info.get("exchange", "")
        region = _EXCHANGE_REGION.get(exchange) or _CURRENCY_REGION.get(currency)
        if region == "IN" or currency == "INR":
            return _build_result(t, ns_sym, "IN", ".NS")
    except Exception as exc:
        logger.warning(f"ticker_resolver: .NS probe failed for {t}: {exc}")

    raise ValueError(
        f"Could not resolve ticker '{raw}'. "
        "Try AAPL, RELIANCE.NS, MSFT, SHEL.L, etc."
    )


def resolve_ticker(raw_ticker: str) -> dict:
    """
    Resolve a raw ticker string to full regional metadata.

    Returns:
      {
        "symbol": "AAPL",
        "yf_symbol": "AAPL",
        "exchange": "NASDAQ",
        "region": "US",
        "currency": "USD",
        "currency_symbol": "$",
        "rf_rate": 0.042,
        "equity_risk_premium": 0.055,
      }

    Raises ValueError if the ticker cannot be resolved.
    """
    key = raw_ticker.strip().upper()
    if key not in _resolution_cache:
        _resolution_cache[key] = _resolve_impl(raw_ticker)
    return _resolution_cache[key]


def clear_cache() -> None:
    """Clear in-process resolution cache (useful for testing)."""
    _resolution_cache.clear()
    _rf_rate_cache.clear()


if __name__ == "__main__":
    import sys

    tickers = sys.argv[1:] or ["AAPL", "RELIANCE", "RELIANCE.NS", "MSFT", "SHEL.L"]
    for t in tickers:
        try:
            r = resolve_ticker(t)
            print(
                f"{t:20s} → symbol={r['symbol']}, yf={r['yf_symbol']}, "
                f"region={r['region']}, ccy={r['currency']} {r['currency_symbol']}, "
                f"rf={r['rf_rate']:.3f}, erp={r['equity_risk_premium']:.3f}"
            )
        except ValueError as e:
            print(f"{t:20s} → ERROR: {e}")
