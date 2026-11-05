#!/usr/bin/env python3
"""Build the dashboard image.

    python3 make_dashboard.py            # fetch live data, write output/dashboard.png
    python3 make_dashboard.py --sample   # use made-up data (no internet needed)
"""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dashboard.render import render

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        fallback = os.path.join(HERE, "config.example.toml")
        print(f"No {os.path.basename(path)} found, using config.example.toml", file=sys.stderr)
        path = fallback
    with open(path, "rb") as f:
        return tomllib.load(f)


def sample_data(cfg: dict, now: datetime):
    tz = now.tzinfo
    base = now.replace(minute=0, second=0, microsecond=0)
    hourly = []
    for i in range(24):
        t = base + timedelta(hours=i + 1)
        temp = 76 + 7 * __import__("math").sin((t.hour - 9) / 24 * 6.283)
        hourly.append({"time": t, "temp": temp, "pop": [0, 0, 10, 20, 40, 30, 10, 0][i % 8]})
    daily = []
    codes = [2, 0, 61, 3, 80]
    for i in range(5):
        dt = (now + timedelta(days=i)).date()
        daily.append({
            "date": dt, "code": codes[i], "hi": 84 - i, "lo": 70 + (i % 2), "pop": [10, 0, 60, 20, 40][i],
            "sunrise": datetime(dt.year, dt.month, dt.day, 6, 41, tzinfo=tz),
            "sunset": datetime(dt.year, dt.month, dt.day, 17, 49, tzinfo=tz),
        })
    weather = {
        "units": "F", "wind_units": "mph",
        "current": {"temp": 81.4, "feels": 84.0, "humidity": 62, "code": 2, "wind": 14,
                    "wind_dir": 60, "is_day": True},
        "hourly": hourly, "daily": daily,
    }
    tides = []
    t = base - timedelta(hours=2)
    for i in range(6):
        tides.append({"time": t + timedelta(hours=6 * i, minutes=13 * i),
                      "height": [1.9, 0.2, 1.4, 0.5][i % 4], "type": "High" if i % 2 == 0 else "Low"})
    return weather, tides


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(HERE, "config.toml"))
    ap.add_argument("--sample", action="store_true", help="use made-up data instead of fetching")
    ap.add_argument("--out", help="override output path")
    args = ap.parse_args()

    cfg = load_config(args.config)
    now = datetime.now(ZoneInfo(cfg["location"]["timezone"]))
    errors: list[str] = []

    if args.sample:
        weather, tides = sample_data(cfg, now)
    else:
        from dashboard.data import fetch_tides, fetch_weather
        try:
            weather = fetch_weather(cfg)
        except Exception as e:  # keep drawing even if one source is down
            weather = None
            errors.append(f"weather: {e}"[:80])
        try:
            tides = fetch_tides(cfg)
        except Exception as e:
            tides = []
            errors.append(f"tides: {e}"[:80])

    img = render(cfg, weather, tides, now, errors)

    out = args.out or cfg["display"]["output_path"]
    if not os.path.isabs(out):
        out = os.path.join(HERE, out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp.png"
    img.save(tmp, optimize=True)
    os.replace(tmp, out)  # atomic swap so the Kindle never grabs a half-written file
    print(f"Wrote {out}" + (f" ({len(errors)} problem(s))" if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
