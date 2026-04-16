"""
collectors/free/coingecko.py
────────────────────────────
Fetches top-20 crypto prices, 24h change, and market cap from CoinGecko.
Primary: pycoingecko library.
Fallback: direct CoinGecko REST API (no library dependency).
Stores into commodity_prices table with metadata JSONB field.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import COINGECKO_API_URL
from database.connection import get_session
from database.models import Commodity, CommodityPrice
from database.queries import upsert_commodity_price
from sqlalchemy import select

TOP_N: int = 20
VS_CURRENCY: str = "usd"
TIMEOUT: int = 15

# In-memory cache: coin_id → commodity.id (avoids repeated DB lookups per run)
_COIN_ID_CACHE: dict[str, Optional[int]] = {}


class CoinGeckoCollector(BaseCollector):
    """CoinGecko top-20 crypto price collector."""

    source_name: str = "coingecko"
    fallback_chain: list[str] = ["api", "scrape", "cache"]

    # ── Primary: pycoingecko library ──────────────────────────────────────────

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            from pycoingecko import CoinGeckoAPI  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                f"[{self.source_name}] pycoingecko not installed — falling back to REST."
            )
            return None  # triggers _try_scrape (REST fallback)

        cg = CoinGeckoAPI()
        try:
            raw = cg.get_coins_markets(
                vs_currency=VS_CURRENCY,
                order="market_cap_desc",
                per_page=TOP_N,
                page=1,
                sparkline=False,
                price_change_percentage="24h",
            )
        except Exception as exc:
            logger.warning(f"[{self.source_name}] pycoingecko call failed: {exc}")
            return None

        return self._process(raw, target_date)

    # ── Fallback: direct REST ─────────────────────────────────────────────────

    def _try_scrape(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Direct CoinGecko REST call without the library."""
        url = f"{COINGECKO_API_URL}/coins/markets"
        params = {
            "vs_currency": VS_CURRENCY,
            "order": "market_cap_desc",
            "per_page": TOP_N,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            raw = resp.json()
        except Exception as exc:
            logger.warning(f"[{self.source_name}] Direct REST call failed: {exc}")
            return None

        return self._process(raw, target_date)

    # ── Shared processing ─────────────────────────────────────────────────────

    def _process(
        self, raw: list[dict[str, Any]], target_date: Optional[date]
    ) -> Optional[CollectionResult]:
        run_date = target_date or date.today()
        records: list[CommodityPrice] = []

        for coin in raw:
            try:
                coin_id: str = coin["id"]
                current_price: Optional[float] = coin.get("current_price")
                if current_price is None:
                    continue

                commodity_id = self._resolve_or_create_commodity(coin)

                record = CommodityPrice(
                    commodity_id=commodity_id,
                    date=run_date,
                    price=float(current_price),
                    currency=VS_CURRENCY.upper(),
                    exchange="CoinGecko",
                    extra_data={
                        "coin_id": coin_id,
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name", ""),
                        "market_cap": coin.get("market_cap"),
                        "market_cap_rank": coin.get("market_cap_rank"),
                        "total_volume": coin.get("total_volume"),
                        "price_change_24h": coin.get("price_change_24h"),
                        "price_change_pct_24h": coin.get(
                            "price_change_percentage_24h_in_currency",
                            coin.get("price_change_percentage_24h"),
                        ),
                        "circulating_supply": coin.get("circulating_supply"),
                        "fetched_at": datetime.utcnow().isoformat(),
                    },
                )
                records.append(record)

            except Exception as exc:
                logger.debug(f"[{self.source_name}] Coin parse error ({coin.get('id', '?')}): {exc}")
                continue

        if not records:
            return None

        self._persist(records)
        self._store_cache(records, target_date=run_date)
        logger.info(
            f"[{self.source_name}] Collected {len(records)} crypto prices for {run_date}."
        )
        return CollectionResult(
            source_name=self.source_name,
            records=records,
            status="ok",
        )

    # ── Database ──────────────────────────────────────────────────────────────

    def _persist(self, records: list[CommodityPrice]) -> None:
        with get_session() as session:
            for r in records:
                upsert_commodity_price(session, r)

    def _resolve_or_create_commodity(self, coin: dict[str, Any]) -> Optional[int]:
        """Get or create a Commodity row for this crypto coin."""
        coin_id = coin["id"]
        if coin_id in _COIN_ID_CACHE:
            return _COIN_ID_CACHE[coin_id]

        try:
            with get_session() as session:
                commodity = session.scalar(
                    select(Commodity).where(
                        Commodity.name == coin_id,
                        Commodity.type == "crypto",
                    )
                )
                if not commodity:
                    commodity = Commodity(
                        name=coin_id,
                        type="crypto",
                        exchange="CoinGecko",
                        base_currency=VS_CURRENCY.upper(),
                    )
                    session.add(commodity)
                    session.flush()

                cid = commodity.id
                _COIN_ID_CACHE[coin_id] = cid
                return cid
        except Exception as exc:
            logger.warning(
                f"[{self.source_name}] Could not resolve commodity for {coin_id}: {exc}"
            )
            _COIN_ID_CACHE[coin_id] = None
            return None
