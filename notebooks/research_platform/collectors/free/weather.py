"""
collectors/free/weather.py
───────────────────────────
Weather data for agri commodities and energy demand.
Source: OpenWeatherMap free API → Open-Meteo (no key needed) fallback
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import requests
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from config.settings import OPENWEATHER_API_KEY
from database.connection import get_session
from database.models import MacroIndicator
from database.queries import upsert_macro_indicator

# Key Indian cities + agri hubs
LOCATIONS = [
    {"name": "Mumbai",    "lat": 19.076, "lon": 72.877},
    {"name": "Delhi",     "lat": 28.679, "lon": 77.069},
    {"name": "Nashik",    "lat": 19.997, "lon": 73.789},   # Onion hub
    {"name": "Vidarbha",  "lat": 20.700, "lon": 78.400},   # Cotton belt
    {"name": "Punjab",    "lat": 30.733, "lon": 76.779},   # Wheat belt
]

class WeatherCollector(BaseCollector):
    source_name = "weather"
    fallback_chain = ["api", "scrape", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        """Open-Meteo — free, no API key required."""
        records = []
        today = target_date or date.today()
        for loc in LOCATIONS:
            try:
                url = (f"https://api.open-meteo.com/v1/forecast?"
                       f"latitude={loc['lat']}&longitude={loc['lon']}"
                       f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
                       f"&timezone=Asia%2FKolkata&forecast_days=1")
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                daily = data.get("daily", {})
                temps_max = daily.get("temperature_2m_max", [None])
                precip    = daily.get("precipitation_sum", [None])
                if temps_max[0] is not None:
                    records.append(MacroIndicator(
                        indicator=f"Weather/{loc['name']}/MaxTemp",
                        date=today, value=temps_max[0],
                        source="OpenMeteo"
                    ))
                if precip[0] is not None:
                    records.append(MacroIndicator(
                        indicator=f"Weather/{loc['name']}/Precipitation",
                        date=today, value=precip[0],
                        source="OpenMeteo"
                    ))
            except Exception as e:
                logger.debug(f"[weather] {loc['name']} failed: {e}")

        if not records:
            return None
        with get_session() as s:
            for r in records:
                upsert_macro_indicator(s, r)
        logger.info(f"[weather] {len(records)} weather records stored")
        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
