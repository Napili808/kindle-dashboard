"""Draw the dashboard as a grayscale PNG sized for the Kindle screen.

Everything is drawn with Pillow shapes and text, so there are no icon fonts
or browsers to install. That keeps it light enough to share a Pi 3 with Pi-hole.
"""

from __future__ import annotations

import math
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

BLACK, DARK, MID, LIGHT, WHITE = 0, 70, 140, 205, 255

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
]

# WMO weather codes used by Open-Meteo -> (label, icon kind)
WEATHER_CODES = {
    0: ("Clear", "sun"), 1: ("Mostly clear", "sun"), 2: ("Partly cloudy", "partly"),
    3: ("Overcast", "cloud"), 45: ("Fog", "fog"), 48: ("Fog", "fog"),
    51: ("Light drizzle", "rain"), 53: ("Drizzle", "rain"), 55: ("Heavy drizzle", "rain"),
    56: ("Freezing drizzle", "rain"), 57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"), 63: ("Rain", "rain"), 65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"), 67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"), 73: ("Snow", "snow"), 75: ("Heavy snow", "snow"), 77: ("Snow grains", "snow"),
    80: ("Showers", "rain"), 81: ("Showers", "rain"), 82: ("Heavy showers", "rain"),
    85: ("Snow showers", "snow"), 86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"), 96: ("Thunderstorm", "storm"), 99: ("Thunderstorm", "storm"),
}


def _font_path(bold: bool) -> str | None:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def font(size: int, bold: bool = False):
    path = _font_path(bold)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def fmt_hour(dt: datetime) -> str:
    return dt.strftime("%I%p").lstrip("0").lower()


def compass(deg: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((deg % 360) / 45 + 0.5) % 8]


# ---------- icons ----------

def _sun(d: ImageDraw.ImageDraw, cx, cy, r, fill=WHITE):
    for i in range(8):
        a = math.radians(i * 45)
        d.line([(cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35),
                (cx + math.cos(a) * r * 1.8, cy + math.sin(a) * r * 1.8)],
               fill=BLACK, width=max(2, int(r * 0.16)))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=BLACK, width=max(2, int(r * 0.14)))


def _cloud(d: ImageDraw.ImageDraw, cx, cy, s, fill=WHITE):
    w = max(2, int(s * 0.07))
    parts = [
        (cx - s * 0.55, cy - s * 0.05, s * 0.32),
        (cx - s * 0.1, cy - s * 0.25, s * 0.42),
        (cx + s * 0.4, cy - s * 0.02, s * 0.32),
    ]
    for x, y, r in parts:  # outlines
        d.ellipse([x - r - w, y - r - w, x + r + w, y + r + w], fill=BLACK)
    d.rounded_rectangle([cx - s * 0.87 - w, cy - s * 0.05 - w, cx + s * 0.72 + w, cy + s * 0.3 + w],
                        radius=int(s * 0.17), fill=BLACK)
    for x, y, r in parts:  # fills
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
    d.rounded_rectangle([cx - s * 0.87, cy - s * 0.05, cx + s * 0.72, cy + s * 0.3],
                        radius=int(s * 0.17), fill=fill)


def draw_icon(d: ImageDraw.ImageDraw, kind: str, cx: float, cy: float, size: float):
    s = size / 2
    if kind == "sun":
        _sun(d, cx, cy, s * 0.5)
    elif kind == "partly":
        _sun(d, cx + s * 0.25, cy - s * 0.3, s * 0.35)
        _cloud(d, cx - s * 0.1, cy + s * 0.2, s * 0.85)
    elif kind == "cloud":
        _cloud(d, cx, cy, s, fill=LIGHT)
    elif kind == "fog":
        for i in range(4):
            y = cy - s * 0.45 + i * s * 0.3
            d.line([(cx - s * 0.8, y), (cx + s * 0.8, y)], fill=BLACK, width=max(3, int(s * 0.1)))
    elif kind in ("rain", "snow", "storm"):
        _cloud(d, cx, cy - s * 0.25, s * 0.9, fill=LIGHT)
        if kind == "rain":
            for i in range(4):
                x = cx - s * 0.5 + i * s * 0.33
                d.line([(x, cy + s * 0.3), (x - s * 0.12, cy + s * 0.7)], fill=BLACK, width=max(3, int(s * 0.08)))
        elif kind == "snow":
            for i in range(3):
                x = cx - s * 0.4 + i * s * 0.4
                r = s * 0.08
                d.ellipse([x - r, cy + s * 0.5 - r, x + r, cy + s * 0.5 + r], fill=BLACK)
        else:
            d.polygon([(cx, cy + s * 0.2), (cx - s * 0.25, cy + s * 0.55), (cx - s * 0.02, cy + s * 0.55),
                       (cx - s * 0.15, cy + s * 0.9), (cx + s * 0.25, cy + s * 0.45), (cx + s * 0.03, cy + s * 0.45),
                       (cx + s * 0.15, cy + s * 0.2)], fill=BLACK)
    else:
        _cloud(d, cx, cy, s, fill=LIGHT)


def weather_label(code: int) -> tuple[str, str]:
    return WEATHER_CODES.get(code, ("Unknown", "cloud"))


# ---------- layout helpers ----------

def text_w(d, txt, f):
    l, t, r, b = d.textbbox((0, 0), txt, font=f)
    return r - l


def section_title(d, x, y, w, title):
    f = font(30, bold=True)
    d.text((x, y), title.upper(), font=f, fill=DARK)
    d.line([(x, y + 44), (x + w, y + 44)], fill=BLACK, width=3)
    return y + 60


# ---------- sections ----------

def draw_header(d, cfg, now, x, y, w):
    d.text((x, y), now.strftime("%A"), font=font(96, bold=True), fill=BLACK)
    d.text((x, y + 110), now.strftime("%B %-d, %Y"), font=font(48), fill=DARK)
    loc = cfg["location"]["name"]
    f = font(30)
    d.text((x + w - text_w(d, loc, f), y + 20), loc, font=f, fill=DARK)
    upd = f"Updated {fmt_time(now)}"
    d.text((x + w - text_w(d, upd, f), y + 60), upd, font=f, fill=MID)
    return y + 190


def draw_current(d, wx, x, y, w):
    cur = wx["current"]
    today = wx["daily"][0]
    label, kind = weather_label(cur["code"])
    if kind == "sun" and not cur["is_day"]:
        kind = "cloud" if cur["code"] >= 2 else "sun"
    draw_icon(d, kind, x + 130, y + 140, 230)

    tx = x + 280
    temp = f"{round(cur['temp'])}°"
    d.text((tx, y - 10), temp, font=font(190, bold=True), fill=BLACK)
    d.text((tx + 4, y + 210), label, font=font(42, bold=True), fill=BLACK)

    rx = x + w - 460
    f = font(34)
    fb = font(34, bold=True)
    rows = [
        ("High / Low", f"{round(today['hi'])}° / {round(today['lo'])}°"),
        ("Feels like", f"{round(cur['feels'])}°"),
        ("Wind", f"{round(cur['wind'])} {wx['wind_units']} {compass(cur['wind_dir'])}"),
        ("Humidity", f"{round(cur['humidity'])}%"),
        ("Rain chance", f"{round(today['pop'])}%"),
        ("Sun", f"{fmt_time(today['sunrise'])} – {fmt_time(today['sunset'])}"),
    ]
    # key on the left of the block, value right-aligned to the margin
    for i, (k, v) in enumerate(rows):
        yy = y + i * 46
        d.text((rx, yy), k, font=f, fill=MID)
        d.text((x + w - text_w(d, v, fb), yy), v, font=fb, fill=BLACK)
    return y + 290


def draw_hourly(d, wx, x, y, w, h=200):
    y = section_title(d, x, y, w, "Next 24 hours")
    hours = wx["hourly"][:24]
    if len(hours) < 2:
        return y
    pad_l, pad_r = 10, 10
    temps = [p["temp"] for p in hours]
    lo, hi = min(temps), max(temps)
    span = max(hi - lo, 4)
    step = (w - pad_l - pad_r) / (len(hours) - 1)

    def px(i):
        return x + pad_l + i * step

    def py(t):
        return y + 40 + (1 - (t - lo) / span) * (h - 80)

    # rain-chance bars along the bottom
    bar_h = 70
    base = y + h + 40
    for i, p in enumerate(hours):
        bh = bar_h * p["pop"] / 100
        if bh > 0:
            d.rectangle([px(i) - step * 0.35, base - bh, px(i) + step * 0.35, base], fill=LIGHT)
    d.line([(x, base), (x + w, base)], fill=MID, width=1)

    pts = [(px(i), py(p["temp"])) for i, p in enumerate(hours)]
    d.line(pts, fill=BLACK, width=5, joint="curve")

    fs = font(28)
    fb = font(30, bold=True)
    for i, p in enumerate(hours):
        if i % 3 == 0:
            label = f"{round(p['temp'])}°"
            cx, cy = pts[i]
            d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=BLACK)
            d.text((cx - text_w(d, label, fb) / 2, cy - 46), label, font=fb, fill=BLACK)
            hl = fmt_hour(p["time"])
            d.text((cx - text_w(d, hl, fs) / 2, base + 8), hl, font=fs, fill=DARK)
    d.text((x + w - text_w(d, "bars = rain chance", font(24)), base + 48), "bars = rain chance",
           font=font(24), fill=MID)
    return base + 90


def draw_forecast(d, wx, x, y, w, compact=False):
    y = section_title(d, x, y, w, "5-day forecast")
    days = wx["daily"][:5]
    col = w / len(days)
    for i, day in enumerate(days):
        cx = x + col * i + col / 2
        name = "Today" if i == 0 else day["date"].strftime("%a")
        f = font(36, bold=True)
        d.text((cx - text_w(d, name, f) / 2, y), name, font=f, fill=BLACK)
        _, kind = weather_label(day["code"])
        draw_icon(d, kind, cx, y + 115, 110)
        hl = f"{round(day['hi'])}° / {round(day['lo'])}°"
        f2 = font(28 if compact else 34, bold=True)
        d.text((cx - text_w(d, hl, f2) / 2, y + 190), hl, font=f2, fill=BLACK)
        pop = f"{round(day['pop'])}% rain"
        f3 = font(25 if compact else 28)
        d.text((cx - text_w(d, pop, f3) / 2, y + 236), pop, font=f3, fill=DARK)
        if i:
            d.line([(x + col * i, y + 10), (x + col * i, y + 270)], fill=LIGHT, width=2)
    return y + 300


def draw_tides(d, cfg, tides, now, x, y, w):
    station = cfg.get("tides", {}).get("station_name", "")
    y = section_title(d, x, y, w, f"Tides · {station}" if station else "Tides")
    upcoming = [t for t in tides if t["time"] >= now][:4]
    if not upcoming:
        d.text((x, y), "Tide data unavailable", font=font(34), fill=MID)
        return y + 60
    col = w / len(upcoming)
    for i, t in enumerate(upcoming):
        cx = x + col * i + col / 2
        is_next = i == 0
        typ = t["type"] + (" (next)" if is_next else "")
        f = font(32, bold=True)
        d.text((cx - text_w(d, typ, f) / 2, y), typ, font=f, fill=BLACK if is_next else DARK)
        # arrow: up for high, down for low
        ay = y + 75
        if t["type"] == "High":
            d.polygon([(cx, ay - 22), (cx - 20, ay + 12), (cx + 20, ay + 12)], fill=BLACK)
        else:
            d.polygon([(cx, ay + 12), (cx - 20, ay - 22), (cx + 20, ay - 22)], fill=BLACK)
        tm = fmt_time(t["time"])
        day = "" if t["time"].date() == now.date() else t["time"].strftime(" %a")
        f2 = font(40, bold=True)
        txt = tm + day
        d.text((cx - text_w(d, txt, f2) / 2, y + 105), txt, font=f2, fill=BLACK)
        ht = f"{t['height']:.1f} ft"
        f3 = font(32)
        d.text((cx - text_w(d, ht, f3) / 2, y + 155), ht, font=f3, fill=DARK)
    return y + 210


def render_portrait(cfg: dict, weather: dict | None, tides: list[dict], now: datetime, errors: list[str]) -> Image.Image:
    disp = cfg["display"]
    W, H = disp["width"], disp["height"]
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    margin = 60
    x, w = margin, W - 2 * margin

    y = draw_header(d, cfg, now, x, 50, w)
    d.line([(x, y), (x + w, y)], fill=BLACK, width=5)
    y += 40

    if weather:
        y = draw_current(d, weather, x, y, w)
        y = draw_hourly(d, weather, x, y + 10, w)
        y = draw_forecast(d, weather, x, y + 10, w)
    else:
        d.text((x, y), "Weather unavailable", font=font(48, bold=True), fill=BLACK)
        y += 100

    if cfg.get("tides", {}).get("enabled"):
        y = draw_tides(d, cfg, tides, now, x, y + 10, w)

    if errors:
        f = font(24)
        msg = "Note: " + "; ".join(errors)
        d.text((x, H - 50), msg[:110], font=f, fill=DARK)

    return img


# ---------- landscape ----------

def draw_current_compact(d, wx, x, y, w):
    """Icon + big temp + condition on top, details in a 2-column grid below."""
    cur = wx["current"]
    today = wx["daily"][0]
    label, kind = weather_label(cur["code"])
    draw_icon(d, kind, x + 115, y + 125, 210)
    tx = x + 255
    d.text((tx, y - 10), f"{round(cur['temp'])}°", font=font(170, bold=True), fill=BLACK)
    d.text((tx + 4, y + 190), label, font=font(40, bold=True), fill=BLACK)
    y += 270

    items = [
        ("High / Low", f"{round(today['hi'])}° / {round(today['lo'])}°"),
        ("Feels like", f"{round(cur['feels'])}°"),
        ("Wind", f"{round(cur['wind'])} {wx['wind_units']} {compass(cur['wind_dir'])}"),
        ("Humidity", f"{round(cur['humidity'])}%"),
        ("Rain", f"{round(today['pop'])}%"),
        ("Sun", f"{fmt_time(today['sunrise'])}–{fmt_time(today['sunset'])}"),
    ]
    col = w / 2
    fk, fv = font(26), font(32, bold=True)
    for i, (k, v) in enumerate(items):
        cx = x + (i % 2) * col
        cy = y + (i // 2) * 78
        d.text((cx, cy), k, font=fk, fill=MID)
        d.text((cx, cy + 30), v, font=fv, fill=BLACK)
    return y + 3 * 78 + 10


def draw_tides_list(d, cfg, tides, now, x, y, w):
    station = cfg.get("tides", {}).get("station_name", "")
    y = section_title(d, x, y, w, f"Tides · {station}" if station else "Tides")
    upcoming = [t for t in tides if t["time"] >= now][:4]
    if not upcoming:
        d.text((x, y), "Tide data unavailable", font=font(32), fill=MID)
        return y + 60
    for i, t in enumerate(upcoming):
        yy = y + i * 62
        ay = yy + 22
        if t["type"] == "High":
            d.polygon([(x + 18, ay - 16), (x + 2, ay + 10), (x + 34, ay + 10)], fill=BLACK)
        else:
            d.polygon([(x + 18, ay + 10), (x + 2, ay - 16), (x + 34, ay - 16)], fill=BLACK)
        bold = i == 0
        d.text((x + 55, yy), t["type"], font=font(34, bold=bold), fill=BLACK if bold else DARK)
        day = "" if t["time"].date() == now.date() else t["time"].strftime("%a ")
        tm = day + fmt_time(t["time"])
        ft = font(36, bold=True)
        d.text((x + 210, yy - 2), tm, font=ft, fill=BLACK)
        ht = f"{t['height']:.1f} ft"
        fh = font(32)
        d.text((x + w - text_w(d, ht, fh), yy), ht, font=fh, fill=DARK)
    return y + len(upcoming) * 62


def render_landscape(cfg, weather, tides, now, errors) -> Image.Image:
    disp = cfg["display"]
    W, H = max(disp["width"], disp["height"]), min(disp["width"], disp["height"])
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    margin, gap = 50, 70
    x, w = margin, W - 2 * margin

    y = draw_header(d, cfg, now, x, 35, w)
    d.line([(x, y), (x + w, y)], fill=BLACK, width=5)
    top = y + 35

    left_w = 700
    rx = x + left_w + gap
    right_w = x + w - rx
    d.line([(x + left_w + gap / 2, top), (x + left_w + gap / 2, H - 70)], fill=LIGHT, width=2)

    # left column: now + tides
    if weather:
        ly = draw_current_compact(d, weather, x, top, left_w)
    else:
        d.text((x, top), "Weather unavailable", font=font(44, bold=True), fill=BLACK)
        ly = top + 100
    if cfg.get("tides", {}).get("enabled"):
        draw_tides_list(d, cfg, tides, now, x, ly + 10, left_w)

    # right column: 24h + 5-day
    if weather:
        ry = draw_hourly(d, weather, rx, top - 10, right_w, h=290)
        draw_forecast(d, weather, rx, ry + 5, right_w, compact=True)

    if errors:
        d.text((x, H - 45), ("Note: " + "; ".join(errors))[:140], font=font(24), fill=DARK)
    return img


def render(cfg, weather, tides, now, errors) -> Image.Image:
    """Returns the image upright for viewing. make_dashboard rotates it for the Kindle."""
    if cfg.get("display", {}).get("orientation", "landscape") == "portrait":
        return render_portrait(cfg, weather, tides, now, errors)
    return render_landscape(cfg, weather, tides, now, errors)
