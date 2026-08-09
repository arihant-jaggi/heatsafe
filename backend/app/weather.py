"""Weather + heat-index helpers backed by the free Open-Meteo API.

Miami Beach is humid, not dry, so the raw air temperature badly understates how
hot it *feels*. We pull temperature **and** relative humidity from Open-Meteo
and combine them into the NWS heat index. The same call also returns the solar
radiation components (direct beam + diffuse) that the MRT model needs, so a
single hourly fetch feeds every downstream calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests

from .cache import TTLCache
from .settings import (
    OPEN_METEO_URL,
    FALLBACK_AIR_TEMP_C,
    FALLBACK_RH_PCT,
    FALLBACK_DIRECT_RAD,
    FALLBACK_DIFFUSE_RAD,
)

# Cache Open-Meteo responses for an hour; keyed by (lat, lon, date).
_weather_cache = TTLCache(ttl_seconds=3600)


@dataclass
class Conditions:
    """Weather + derived heat metrics for a single hour at one location."""
    air_temp_c: float
    rh_pct: float
    direct_rad: float   # direct (beam) shortwave on a horizontal surface, W/m^2
    diffuse_rad: float  # diffuse shortwave, W/m^2
    heat_index_c: float
    heat_index_f: float
    source: str         # "open-meteo" or "fallback"

    @property
    def global_rad(self) -> float:
        return self.direct_rad + self.diffuse_rad


def c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def heat_index_f(temp_f: float, rh: float) -> float:
    """NWS Rothfusz heat index (apparent temperature) in degrees Fahrenheit.

    Uses the simple Steadman regression below 80 F and the full Rothfusz
    regression (with the low-RH and high-RH adjustments) at/above it.
    """
    # Steadman simple form; also the value we average with for the low band.
    simple = 0.5 * (temp_f + 61.0 + (temp_f - 68.0) * 1.2 + rh * 0.094)
    if (simple + temp_f) / 2.0 < 80.0:
        return simple

    t, r = temp_f, rh
    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * r
        - 0.22475541 * t * r
        - 6.83783e-3 * t * t
        - 5.481717e-2 * r * r
        + 1.22874e-3 * t * t * r
        + 8.5282e-4 * t * r * r
        - 1.99e-6 * t * t * r * r
    )

    # Adjustments near the edges of the regression's valid range.
    if r < 13.0 and 80.0 <= t <= 112.0:
        hi -= ((13.0 - r) / 4.0) * ((17.0 - abs(t - 95.0)) / 17.0) ** 0.5
    elif r > 85.0 and 80.0 <= t <= 87.0:
        hi += ((r - 85.0) / 10.0) * ((87.0 - t) / 5.0)

    return hi


def _fallback() -> Conditions:
    hi_f = heat_index_f(c_to_f(FALLBACK_AIR_TEMP_C), FALLBACK_RH_PCT)
    return Conditions(
        air_temp_c=FALLBACK_AIR_TEMP_C,
        rh_pct=FALLBACK_RH_PCT,
        direct_rad=FALLBACK_DIRECT_RAD,
        diffuse_rad=FALLBACK_DIFFUSE_RAD,
        heat_index_c=f_to_c(hi_f),
        heat_index_f=hi_f,
        source="fallback",
    )


def _fetch_hourly(lat: float, lon: float, date_str: str) -> Optional[dict]:
    key = ("wx", round(lat, 3), round(lon, 3), date_str)
    cached = _weather_cache.get(key)
    if cached is not None:
        return cached
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,direct_radiation,diffuse_radiation",
        "timezone": "auto",
        "start_date": date_str,
        "end_date": date_str,
    }
    try:
        r = requests.get(OPEN_METEO_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("hourly")
        if data:
            _weather_cache.set(key, data)
        return data
    except Exception:
        return None


def get_conditions(when_local: datetime, lat: float, lon: float) -> Conditions:
    """Return weather + heat metrics for the hour of ``when_local`` at (lat, lon).

    ``when_local`` should be a timezone-aware local datetime. Falls back to hot,
    humid Miami defaults if the network call fails, so routing always works.
    """
    date_str = when_local.strftime("%Y-%m-%d")
    hourly = _fetch_hourly(lat, lon, date_str)
    if not hourly:
        return _fallback()

    times = hourly.get("time", [])
    target = when_local.strftime("%Y-%m-%dT%H:00")
    idx = None
    if target in times:
        idx = times.index(target)
    elif times:
        idx = min(range(len(times)), key=lambda i: abs(i - when_local.hour))

    if idx is None:
        return _fallback()

    def pick(field: str, default: float) -> float:
        arr = hourly.get(field) or []
        if idx < len(arr) and arr[idx] is not None:
            return float(arr[idx])
        return default

    ta = pick("temperature_2m", FALLBACK_AIR_TEMP_C)
    rh = pick("relative_humidity_2m", FALLBACK_RH_PCT)
    direct = pick("direct_radiation", 0.0)
    diffuse = pick("diffuse_radiation", 0.0)

    hi_f = heat_index_f(c_to_f(ta), rh)
    return Conditions(
        air_temp_c=ta,
        rh_pct=rh,
        direct_rad=direct,
        diffuse_rad=diffuse,
        heat_index_c=f_to_c(hi_f),
        heat_index_f=hi_f,
        source="open-meteo",
    )
