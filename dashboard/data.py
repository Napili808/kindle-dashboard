"""Fetch the data the dashboard shows. Every source is free and needs no API key."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

USER_AGENT = "kindle-dashboard (github.com/Napili808/kindle-dashboard)"
TIMEOUT = 20


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.json()


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
    raw = _get("https://api.open-meteo.com/v1/forecast", params)

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
    raw = _get("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter", params)
    if "predictions" not in raw:
        raise RuntimeError(f"NOAA error: {raw.get('error', raw)}")
    tides = []
    for p in raw["predictions"]:
        ts = datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        tides.append({"time": ts, "height": float(p["v"]), "type": "High" if p["type"] == "H" else "Low"})
    return tides
