"""
collectors/free/gdelt.py
────────────────────────
Fetches GDELT 2.0 global event data.

BUG FIX:
  - Uses upsert_event() instead of session.add() — no duplicates on re-run
  - Tracks last downloaded file URL in cache to avoid re-downloading
    the same 50-200MB file every day
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime
from typing import Optional

import pandas as pd
import requests
from loguru import logger

from collectors.base import BaseCollector, CollectionResult
from config.settings import GDELT_BASE_URL
from database.connection import get_session
from database.models import Event
from database.queries import upsert_event

TIMEOUT: int = 30
MAX_EVENTS_PER_RUN: int = 500

GDELT_COLUMNS = [
    "GlobalEventID", "Day", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
    "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
    "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
    "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode",
    "QuadClass", "GoldsteinScale", "NumMentions", "NumSources",
    "NumArticles", "AvgTone", "Actor1Geo_Type", "Actor1Geo_FullName",
    "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code", "Actor1Geo_ADM2Code",
    "Actor1Geo_Lat", "Actor1Geo_Long", "Actor1Geo_FeatureID",
    "Actor2Geo_Type", "Actor2Geo_FullName", "Actor2Geo_CountryCode",
    "Actor2Geo_ADM1Code", "Actor2Geo_ADM2Code", "Actor2Geo_Lat",
    "Actor2Geo_Long", "Actor2Geo_FeatureID", "ActionGeo_Type",
    "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
    "ActionGeo_ADM2Code", "ActionGeo_Lat", "ActionGeo_Long",
    "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL",
]


class GdeltCollector(BaseCollector):
    source_name: str = "gdelt"
    fallback_chain: list[str] = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        file_url = self._resolve_file_url(target_date)
        if not file_url:
            return None

        # Skip re-download if we already processed this exact file
        last_url_key = f"{self.source_name}:last_file_url"
        last_url = self._cache.get(last_url_key)
        if last_url == file_url and target_date is None:
            logger.info(f"[{self.source_name}] Already processed {file_url} — skipping download.")
            # Return cached events
            cached = self._cache.get(self._cache_key(target_date))
            if cached:
                return CollectionResult(
                    source_name=self.source_name,
                    records=cached,
                    status="partial",
                    method_used="cache",
                )

        try:
            logger.info(f"[{self.source_name}] Downloading GDELT: {file_url}")
            resp = requests.get(file_url, timeout=TIMEOUT * 3)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csv_name = zf.namelist()[0]
                with zf.open(csv_name) as f:
                    df = pd.read_csv(
                        f, sep="\t", header=None,
                        names=GDELT_COLUMNS,
                        on_bad_lines="skip",
                        low_memory=False,
                    )
        except Exception as exc:
            logger.warning(f"[{self.source_name}] GDELT download/parse failed: {exc}")
            return None

        events = self._parse_events(df)
        if not events:
            return None

        with get_session() as session:
            for ev in events:
                upsert_event(session, ev)

        # Remember this file URL so we don't re-download it
        self._cache.set(last_url_key, file_url, expire=86400)
        self._store_cache(events, target_date=target_date)

        logger.info(f"[{self.source_name}] Upserted {len(events)} GDELT events.")
        return CollectionResult(
            source_name=self.source_name,
            records=events,
            status="ok",
        )

    def _resolve_file_url(self, target_date: Optional[date]) -> Optional[str]:
        """Get the latest GDELT export URL from masterfilelist."""
        masterfile_url = f"{GDELT_BASE_URL}/masterfilelist-translation.txt"
        try:
            resp = requests.get(masterfile_url, timeout=TIMEOUT)
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
            if lines:
                parts = lines[-1].split()
                if parts:
                    return parts[-1]
        except Exception as exc:
            logger.warning(f"[{self.source_name}] Masterfile fetch failed: {exc}")

        if target_date:
            return f"{GDELT_BASE_URL}/{target_date.strftime('%Y%m%d')}000000.export.CSV.zip"
        return f"{GDELT_BASE_URL}/{date.today().strftime('%Y%m%d')}000000.export.CSV.zip"

    def _parse_events(self, df: pd.DataFrame) -> list[Event]:
        events: list[Event] = []
        for _, row in df.iterrows():
            try:
                day_str = str(row.get("Day", ""))
                if len(day_str) != 8:
                    continue
                ev_date = date(int(day_str[:4]), int(day_str[4:6]), int(day_str[6:8]))
                tone = float(row.get("AvgTone", 0) or 0)
                impact = round(abs(tone) / 10, 2)
                source_url = str(row.get("SOURCEURL", "") or "")[:1000] or None
                actor = str(row.get("Actor1Name", "") or "")[:200]
                geo = str(row.get("ActionGeo_FullName", "") or "")[:200]
                title = f"{actor} — {geo}" if (actor or geo) else "GDELT Event"

                events.append(Event(
                    type="regulatory",
                    title=title[:1000],
                    date=ev_date,
                    impact_score=impact,
                    source_url=source_url,
                    entity_type="gdelt",
                ))
            except Exception:
                continue
            if len(events) >= MAX_EVENTS_PER_RUN:
                break
        return events
