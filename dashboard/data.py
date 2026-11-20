"""Fetch the data the dashboard shows. Every source is free and needs no API key."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

USER_AGENT = "kindle-dashboard (github.com/Napili808/kindle-dashboard)"
TIMEOUT = 20
RETRY_WAITS = (5, 20)  # seconds to wait before the 2nd and 3rd tries
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")


def _get(url: str, params: dict) -> dict:
    """GET with a couple of retries, since free APIs sometimes blip (503s, timeouts)."""
    last = None
    for attempt in range(len(RETRY_WAITS) + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last = e
            if attempt < len(RETRY_WAITS):
                time.sleep(RETRY_WAITS[attempt])
    raise last


def _get_cached(name: str, url: str, params: dict, max_age_hours: float, fresh_minutes: float = 0):
    """Fetch, saving each good answer. If the service is down, fall back to the
    last good answer (if it's recent enough). Returns (data, stale_since or None).

    If the saved answer is younger than fresh_minutes, it's used without asking
    the service again. The image redraws every minute for the clock, but the
    weather only needs checking every half hour or so."""
    path = os.path.join(CACHE_DIR, f"{name}.json")
    if fresh_minutes:
        try:
            with open(path) as f:
                cached = json.load(f)
            if time.time() - cached["fetched_at"] < fresh_minutes * 60:
                return cached["data"], None
        except (OSError, ValueError, KeyError):
            pass
    try:
        data = _get(url, params)
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path + ".tmp", "w") as f:
            json.dump({"fetched_at": time.time(), "data": data}, f)
        os.replace(path + ".tmp", path)
        return data, None
    except Exception as fetch_error:
        try:
            with open(path) as f:
                cached = json.load(f)
        except (OSError, ValueError):
            raise fetch_error from None
        if time.time() - cached["fetched_at"] > max_age_hours * 3600:
            raise fetch_error
        return cached["data"], datetime.fromtimestamp(cached["fetched_at"])


def _fresh_minutes(cfg: dict) -> float:
    return float(cfg.get("refresh", {}).get("data_minutes", 30))


def fetch_weather(cfg: dict) -> dict:
    """Current conditions, next 24 hours, and a 5-day forecast from Open-Meteo."""
    loc = cfg["location"]
    imperial = cfg.get("weather", {}).get("units", "imperial") == "imperial"
    params = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "timezone": loc["timezone"],
        "forecast_days": 5,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "weather_code,wind_speed_10m,wind_direction_10m,is_day",
        "hourly": "temperature_2m,precipitation_probability",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,sunrise,sunset",
    }
    if imperial:
        params.update(temperature_unit="fahrenheit", wind_speed_unit="mph")
    raw, stale_since = _get_cached("weather", "https://api.open-meteo.com/v1/forecast", params, 12,
                                   fresh_minutes=_fresh_minutes(cfg))

    tz = ZoneInfo(loc["timezone"])
    now = datetime.now(tz)
    cur = raw["current"]

    hourly = []
    for t, temp, pop in zip(raw["hourly"]["time"],
                            raw["hourly"]["temperature_2m"],
                            raw["hourly"]["precipitation_probability"]):
        ts = datetime.fromisoformat(t).replace(tzinfo=tz)
        if now - timedelta(hours=1) < ts <= now + timedelta(hours=24):
            hourly.append({"time": ts, "temp": temp, "pop": pop or 0})

    d = raw["daily"]
    daily = [
        {
            "date": datetime.fromisoformat(d["time"][i]).date(),
            "code": d["weather_code"][i],
            "hi": d["temperature_2m_max"][i],
            "lo": d["temperature_2m_min"][i],
            "pop": d["precipitation_probability_max"][i] or 0,
            "sunrise": datetime.fromisoformat(d["sunrise"][i]),
            "sunset": datetime.fromisoformat(d["sunset"][i]),
        }
        for i in range(len(d["time"]))
    ]

    return {
        "stale_since": stale_since.astimezone(tz) if stale_since else None,
        "units": "F" if imperial else "C",
        "wind_units": "mph" if imperial else "km/h",
        "current": {
            "temp": cur["temperature_2m"],
            "feels": cur["apparent_temperature"],
            "humidity": cur["relative_humidity_2m"],
            "code": cur["weather_code"],
            "wind": cur["wind_speed_10m"],
            "wind_dir": cur["wind_direction_10m"],
            "is_day": bool(cur.get("is_day", 1)),
        },
        "hourly": hourly,
        "daily": daily,
    }


def fetch_tides(cfg: dict) -> list[dict]:
    """Upcoming high and low tides from NOAA CO-OPS (station local time)."""
    tcfg = cfg.get("tides", {})
    if not tcfg.get("enabled", False):
        return []
    tz = ZoneInfo(cfg["location"]["timezone"])
    now = datetime.now(tz)
    params = {
        "product": "predictions",
        "application": "kindle-dashboard",
        "begin_date": (now - timedelta(hours=12)).strftime("%Y%m%d %H:%M"),
        "range": 60,
        "datum": "MLLW",
        "station": tcfg["station_id"],
        "time_zone": "lst_ldt",
        "units": "english",
        "interval": "hilo",
        "format": "json",
    }
    # Tide predictions cover 60 hours, so a cached copy stays useful for a day.
    raw, _ = _get_cached("tides", "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter", params, 24,
                         fresh_minutes=max(_fresh_minutes(cfg), 180))
    if "predictions" not in raw:
        raise RuntimeError(f"NOAA error: {raw.get('error', raw)}")
    tides = []
    for p in raw["predictions"]:
        ts = datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        tides.append({"time": ts, "height": float(p["v"]), "type": "High" if p["type"] == "H" else "Low"})
    return tides


def fetch_air(cfg: dict) -> dict | None:
    """Air quality, sulfur dioxide (for vog) and UV from Open-Meteo's air-quality service."""
    if not cfg.get("air", {}).get("enabled", True):
        return None
    loc = cfg["location"]
    params = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "timezone": loc["timezone"],
        "forecast_days": 2,
        "current": "us_aqi,pm2_5,sulphur_dioxide,uv_index",
        "hourly": "uv_index",
    }
    raw, _ = _get_cached("air", "https://air-quality-api.open-meteo.com/v1/air-quality", params, 6,
                         fresh_minutes=_fresh_minutes(cfg))
    tz = ZoneInfo(loc["timezone"])
    now = datetime.now(tz)
    cur = raw["current"]

    hours = [(datetime.fromisoformat(t).replace(tzinfo=tz), uv or 0)
             for t, uv in zip(raw["hourly"]["time"], raw["hourly"]["uv_index"])]
    # Show today's UV until the sun's done for the day, then tomorrow's.
    today = [(t, uv) for t, uv in hours if t.date() == now.date()]
    rest_of_today = [uv for t, uv in today if t >= now.replace(minute=0, second=0, microsecond=0)]
    if rest_of_today and max(rest_of_today) >= 1:
        day, which = today, "today"
    else:
        tomorrow = (now + timedelta(days=1)).date()
        day, which = [(t, uv) for t, uv in hours if t.date() == tomorrow], "tomorrow"
    uv_max = max((uv for _, uv in day), default=0)
    high = [t for t, uv in day if uv >= 6]  # "high" or worse on the UV scale

    return {
        "aqi": cur.get("us_aqi") or 0,
        "pm25": cur.get("pm2_5") or 0,
        "so2": cur.get("sulphur_dioxide") or 0,
        "uv_now": cur.get("uv_index") or 0,
        "uv_max": uv_max,
        "uv_window": (high[0], high[-1]) if high else None,
        "uv_day": which,
    }
