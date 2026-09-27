# AIR PRO v2.0 — display helpers, night mode, and both screens.
import gc
import time

import terminalio
import displayio
from adafruit_display_text import label
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.rect import Rect
from adafruit_bitmap_font import bitmap_font

from config import (
    FONT_BIG,
    FONT_XL,
    FONT_SM,
    BG,
    CARD,
    BORDER,
    PIP,
    PIP_DIM,
    PIP_LO,
    S_GOOD,
    S_WARN,
    S_BAD,
    S_CRIT,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    DIM_FACTOR,
)
from utils import (
    dim,
    tcol,
    co2col,
    co2txt,
    voccol,
    noxcol,
    pm1col,
    pm25col,
    pm4col,
    pm10col,
    nccol,
    dew_point,
    dewcol,
    eaqi_level,
    EAQI_COLORS,
    EAQI_NAMES,
    aq_score,
    aq_label_and_color,
    main_threat_and_action,
)
import wifi_sync
from wifi_sync import clock_str
import sensors
import hardware

font_big = bitmap_font.load_font(FONT_BIG)
font_xl = bitmap_font.load_font(FONT_XL)
font_sm = terminalio.FONT if FONT_SM is None else FONT_SM

_night_mode = False
_all_labels = []

# Background bitmap (shared across screens).
_bg_bm = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1)
_bg_pal = displayio.Palette(1)
_bg_pal[0] = BG


def make_label(*args, **kwargs):
    """Create a label and register it for night-mode dimming."""
    lbl = label.Label(*args, **kwargs)
    lbl._orig_color = kwargs.get("color", PIP)
    _all_labels.append(lbl)
    return lbl


def set_color(lbl, color):
    """Set a label's base color and apply night-mode dimming if active."""
    lbl._orig_color = color
    lbl.color = dim(color, DIM_FACTOR) if _night_mode else color


def make_bg(group):
    """Append the shared background to a group."""
    group.append(displayio.TileGrid(_bg_bm, pixel_shader=_bg_pal))


# ── Gradient bar (green -> yellow -> orange -> red) ──
BAR_H = 18
N_PAL = 64
_bar_pal = displayio.Palette(N_PAL)
_bar_orig = []
_stops = [S_GOOD, 0x88DD00, 0xFFAA00, S_BAD, S_CRIT]

for _i in range(N_PAL):
    _t = _i / (N_PAL - 1) * (len(_stops) - 1)
    _si = min(int(_t), len(_stops) - 2)
    _f = _t - _si
    _c1, _c2 = _stops[_si], _stops[_si + 1]
    _r = int(((_c1 >> 16) & 0xFF) * (1 - _f) + ((_c2 >> 16) & 0xFF) * _f)
    _g = int(((_c1 >> 8) & 0xFF) * (1 - _f) + ((_c2 >> 8) & 0xFF) * _f)
    _b = int((_c1 & 0xFF) * (1 - _f) + (_c2 & 0xFF) * _f)
    _c = (_r << 16) | (_g << 8) | _b
    _bar_pal[_i] = _c
    _bar_orig.append(_c)


def make_gradient_bar(width, x, y):
    """Create a horizontal gradient bar and a pointer sprite."""
    bm = displayio.Bitmap(width, BAR_H, N_PAL)
    for px in range(width):
        ci = int(px / (width - 1) * (N_PAL - 1))
        for py in range(BAR_H):
            bm[px, py] = ci
    tg = displayio.TileGrid(bm, pixel_shader=_bar_pal, x=x, y=y)
    ptr = displayio.Group()
    ptr.append(Rect(0, 0, 4, BAR_H + 8, fill=PIP))
    ptr.x = x
    ptr.y = y - 4
    return tg, ptr


def apply_night_mode(on, i2c):
    """Toggle night mode: dim labels, gradient bar, and backlight."""
    global _night_mode
    _night_mode = on
    hardware.set_backlight(i2c, not on)
    for lbl in _all_labels:
        c = getattr(lbl, "_orig_color", lbl.color)
        lbl.color = dim(c, DIM_FACTOR) if on else c
    for i in range(N_PAL):
        _bar_pal[i] = dim(_bar_orig[i], DIM_FACTOR) if on else _bar_orig[i]


def is_night_mode():
    return _night_mode


# ═══════════════════════════════════════════════════════
# SCREEN 0 — ENVIRONMENT OVERVIEW
# ═══════════════════════════════════════════════════════
def build_overview_screen():
    """Build the calm, at-a-glance environmental summary screen."""
    g = displayio.Group()
    make_bg(g)

    g.append(Rect(20, 10, 680, 2, fill=PIP))
    g.append(
        make_label(
            font_sm,
            text="ENVIRONMENT OVERVIEW",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(25, 28),
        )
    )
    clk = make_label(
        font_sm,
        text="--:--",
        color=PIP,
        scale=2,
        anchor_point=(1, 0.5),
        anchored_position=(695, 28),
    )
    g.append(clk)
    g.append(Rect(20, 42, 680, 2, fill=PIP))

    g.append(RoundRect(20, 55, 680, 170, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="OVERALL AIR STATUS",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 62),
        )
    )
    status = make_label(
        font_sm,
        text="NO DATA",
        color=PIP_LO,
        scale=4,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 120),
    )
    g.append(status)
    detail = make_label(
        font_sm,
        text="MAIN THREAT: UNKNOWN",
        color=PIP_LO,
        scale=2,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 155),
    )
    g.append(detail)
    action = make_label(
        font_sm,
        text="WAITING FOR SENSOR DATA",
        color=PIP_LO,
        scale=2,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 176),
    )
    g.append(action)
    bar_tg, ptr = make_gradient_bar(580, 70, 199)
    g.append(bar_tg)
    g.append(ptr)

    g.append(RoundRect(20, 230, 680, 170, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="CO2 CONCENTRATION",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 238),
        )
    )
    co2 = make_label(
        font_big,
        text="---",
        color=PIP,
        scale=2,
        anchor_point=(0.5, 0.5),
        anchored_position=(275, 315),
    )
    g.append(co2)
    g.append(
        make_label(
            font_sm,
            text="PPM",
            color=PIP_LO,
            scale=3,
            anchor_point=(0, 0.5),
            anchored_position=(455, 315),
        )
    )
    co2t = make_label(
        font_sm,
        text="",
        color=PIP_LO,
        scale=2,
        anchor_point=(0, 0.5),
        anchored_position=(550, 315),
    )
    g.append(co2t)

    card_x = [20, 250, 480]
    card_titles = ["TEMPERATURE", "HUMIDITY", "DEW POINT"]
    card_units = ["C", "%", "C"]
    values = []
    for index, x in enumerate(card_x):
        g.append(RoundRect(x, 415, 220, 110, r=4, fill=CARD, outline=BORDER))
        g.append(
            make_label(
                font_sm,
                text=card_titles[index],
                color=PIP_DIM,
                scale=2,
                anchor_point=(0.5, 0),
                anchored_position=(x + 110, 422),
            )
        )
        value = make_label(
            font_big,
            text="--.-",
            color=PIP,
            anchor_point=(0.5, 0.5),
            anchored_position=(x + 85, 482),
        )
        g.append(value)
        values.append(value)
        g.append(
            make_label(
                font_sm,
                text=card_units[index],
                color=PIP_LO,
                scale=2,
                anchor_point=(0, 0.5),
                anchored_position=(x + 165, 482),
            )
        )

    g.append(RoundRect(20, 545, 335, 110, r=4, fill=CARD, outline=BORDER))
    g.append(RoundRect(365, 545, 335, 110, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="PM2.5  (ug/m3)",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(187, 552),
        )
    )
    g.append(
        make_label(
            font_sm,
            text="VOC INDEX",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(532, 552),
        )
    )
    pm25 = make_label(
        font_big,
        text="--",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(187, 610),
    )
    voc = make_label(
        font_big,
        text="--",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(532, 610),
    )
    g.append(pm25)
    g.append(voc)
    g.append(
        make_label(
            font_sm,
            text="ROTATE FOR DETAIL",
            color=PIP_LO,
            scale=2,
            anchor_point=(0.5, 0.5),
            anchored_position=(360, 685),
        )
    )
    return (
        g,
        clk,
        status,
        detail,
        action,
        ptr,
        co2,
        co2t,
        values[0],
        values[1],
        values[2],
        pm25,
        voc,
    )


# ═══════════════════════════════════════════════════════
# SCREEN 1 — AIR QUALITY ANALYSIS
# ═══════════════════════════════════════════════════════
def build_dashboard():
    g = displayio.Group()
    make_bg(g)

    # Header
    g.append(Rect(20, 10, 680, 2, fill=PIP))
    g.append(
        make_label(
            font_sm,
            text="AIR QUALITY ANALYSIS",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(25, 28),
        )
    )
    clk = make_label(
        font_sm,
        text="--:--",
        color=PIP,
        scale=2,
        anchor_point=(1, 0.5),
        anchored_position=(695, 28),
    )
    g.append(clk)
    g.append(Rect(20, 42, 680, 2, fill=PIP))

    # Temperature
    g.append(RoundRect(20, 52, 335, 100, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="TEMPERATURE",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(187, 57),
        )
    )
    tmp = make_label(
        font_big,
        text="--.-",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(155, 110),
    )
    g.append(tmp)
    g.append(
        make_label(
            font_big,
            text="C",
            color=PIP_LO,
            anchor_point=(0, 0.5),
            anchored_position=(260, 110),
        )
    )

    # Humidity
    g.append(RoundRect(365, 52, 335, 100, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="HUMIDITY",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(532, 57),
        )
    )
    hum = make_label(
        font_big,
        text="--.-",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(500, 110),
    )
    g.append(hum)
    g.append(
        make_label(
            font_big,
            text="%",
            color=PIP_LO,
            anchor_point=(0, 0.5),
            anchored_position=(600, 110),
        )
    )

    # EAQI
    g.append(RoundRect(20, 162, 230, 90, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="PM AIR QUALITY",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(135, 167),
        )
    )
    eaqi = make_label(
        font_sm,
        text="---",
        color=PIP_LO,
        scale=3,
        anchor_point=(0.5, 0.5),
        anchored_position=(135, 216),
    )
    g.append(eaqi)

    # CO2
    g.append(RoundRect(260, 162, 440, 90, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="CO2 LEVEL",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(480, 167),
        )
    )
    co2 = make_label(
        font_big,
        text="---",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(370, 216),
    )
    g.append(co2)
    g.append(
        make_label(
            font_sm,
            text="PPM",
            color=PIP_LO,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(440, 216),
        )
    )
    co2t = make_label(
        font_sm,
        text="",
        color=PIP_LO,
        scale=2,
        anchor_point=(0, 0.5),
        anchored_position=(540, 216),
    )
    g.append(co2t)

    # VOC
    g.append(RoundRect(20, 262, 220, 80, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="VOC INDEX",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(130, 267),
        )
    )
    voc = make_label(
        font_big,
        text="--",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(130, 310),
    )
    g.append(voc)

    # NOx
    g.append(RoundRect(250, 262, 220, 80, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="NOx INDEX",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 267),
        )
    )
    nox = make_label(
        font_big,
        text="--",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 310),
    )
    g.append(nox)

    # Dew point
    g.append(RoundRect(480, 262, 220, 80, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="DEW POINT",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(590, 267),
        )
    )
    dew = make_label(
        font_big,
        text="--",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(570, 310),
    )
    g.append(dew)
    g.append(
        make_label(
            font_sm,
            text="C",
            color=PIP_LO,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(650, 310),
        )
    )

    # PM mass
    g.append(RoundRect(20, 352, 680, 100, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="PARTICULATE MATTER (ug/m3)",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 355),
        )
    )
    pm_cx = [105, 275, 445, 615]
    pm_nms = ["PM1.0", "PM2.5", "PM4.0", "PM10"]
    pm = []
    for i in range(4):
        g.append(
            make_label(
                font_sm,
                text=pm_nms[i],
                color=PIP_LO,
                scale=2,
                anchor_point=(0.5, 0),
                anchored_position=(pm_cx[i], 380),
            )
        )
        v = make_label(
            font_sm,
            text="--",
            color=PIP,
            scale=3,
            anchor_point=(0.5, 0.5),
            anchored_position=(pm_cx[i], 422),
        )
        g.append(v)
        pm.append(v)

    # Particle count
    g.append(RoundRect(20, 462, 680, 100, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="PARTICLE COUNT (n/cm3)",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 465),
        )
    )
    nc_cx = [88, 224, 360, 496, 632]
    nc_nms = ["PM0.5", "PM1.0", "PM2.5", "PM4.0", "PM10"]
    nc = []
    for i in range(5):
        g.append(
            make_label(
                font_sm,
                text=nc_nms[i],
                color=PIP_LO,
                scale=2,
                anchor_point=(0.5, 0),
                anchored_position=(nc_cx[i], 490),
            )
        )
        v = make_label(
            font_sm,
            text="--",
            color=PIP,
            scale=2,
            anchor_point=(0.5, 0.5),
            anchored_position=(nc_cx[i], 533),
        )
        g.append(v)
        nc.append(v)

    # Status bar
    g.append(Rect(20, 572, 680, 2, fill=PIP))
    g.append(RoundRect(20, 580, 680, 130, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="OVERALL AIR STATUS",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 585),
        )
    )
    aq_txt = make_label(
        font_sm,
        text="---",
        color=PIP_LO,
        scale=3,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 620),
    )
    g.append(aq_txt)
    bar_tg, ptr = make_gradient_bar(620, 50, 645)
    g.append(bar_tg)
    g.append(ptr)
    g.append(
        make_label(
            font_sm,
            text="SAFE",
            color=S_GOOD,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(50, 678),
        )
    )
    g.append(
        make_label(
            font_sm,
            text="DANGER",
            color=S_CRIT,
            scale=2,
            anchor_point=(1, 0.5),
            anchored_position=(670, 678),
        )
    )

    return (
        g,
        clk,
        tmp,
        hum,
        eaqi,
        co2,
        co2t,
        dew,
        voc,
        nox,
        pm[0],
        pm[1],
        pm[2],
        pm[3],
        nc[0],
        nc[1],
        nc[2],
        nc[3],
        nc[4],
        aq_txt,
        ptr,
    )


# ═══════════════════════════════════════════════════════
# SCREEN 1 — CO2 MONITORING STATION
# ═══════════════════════════════════════════════════════
def build_co2_screen():
    g = displayio.Group()
    make_bg(g)

    # Header
    g.append(Rect(20, 10, 680, 2, fill=PIP))
    g.append(
        make_label(
            font_sm,
            text="CO2 MONITORING STATION",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(25, 28),
        )
    )
    clk = make_label(
        font_sm,
        text="--:--",
        color=PIP,
        scale=2,
        anchor_point=(1, 0.5),
        anchored_position=(695, 28),
    )
    g.append(clk)
    g.append(Rect(20, 42, 680, 2, fill=PIP))

    # Big CO2
    co2 = make_label(
        font_xl,
        text="---",
        color=PIP,
        scale=2,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 175),
    )
    g.append(co2)
    g.append(
        make_label(
            font_sm,
            text="CO2 CONCENTRATION (PPM)",
            color=PIP_DIM,
            scale=3,
            anchor_point=(0.5, 0),
            anchored_position=(360, 275),
        )
    )
    co2t = make_label(
        font_sm,
        text="",
        color=PIP_LO,
        scale=3,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 350),
    )
    g.append(co2t)

    # Temperature
    g.append(RoundRect(20, 395, 220, 100, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="TEMP",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(130, 400),
        )
    )
    tmp = make_label(
        font_big,
        text="--.-",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(105, 455),
    )
    g.append(tmp)
    g.append(
        make_label(
            font_sm,
            text="C",
            color=PIP_LO,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(180, 455),
        )
    )

    # Humidity
    g.append(RoundRect(480, 395, 220, 100, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="HUMIDITY",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(590, 400),
        )
    )
    hum = make_label(
        font_big,
        text="--.-",
        color=PIP,
        anchor_point=(0.5, 0.5),
        anchored_position=(565, 455),
    )
    g.append(hum)
    g.append(
        make_label(
            font_sm,
            text="%",
            color=PIP_LO,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(640, 455),
        )
    )

    # Overall status (separate from the CO2-specific status above)
    g.append(Rect(20, 508, 680, 2, fill=PIP))
    g.append(
        make_label(
            font_sm,
            text="OVERALL AIR STATUS",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 515),
        )
    )
    aq_txt = make_label(
        font_sm,
        text="---",
        color=PIP_LO,
        scale=3,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 560),
    )
    g.append(aq_txt)
    bar_tg, ptr = make_gradient_bar(520, 100, 590)
    g.append(bar_tg)
    g.append(ptr)
    g.append(
        make_label(
            font_sm,
            text="SAFE",
            color=S_GOOD,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(100, 625),
        )
    )
    g.append(
        make_label(
            font_sm,
            text="DANGER",
            color=S_CRIT,
            scale=2,
            anchor_point=(1, 0.5),
            anchored_position=(620, 625),
        )
    )

    return g, clk, co2, co2t, tmp, hum, aq_txt, ptr


# ═══════════════════════════════════════════════════════
# SCREEN 3 — SYSTEM HEALTH
# ═══════════════════════════════════════════════════════
def build_health_screen():
    """Build a diagnostic screen for connectivity, sensors, and runtime."""
    g = displayio.Group()
    make_bg(g)

    g.append(Rect(20, 10, 680, 2, fill=PIP))
    g.append(
        make_label(
            font_sm,
            text="SYSTEM HEALTH",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(25, 28),
        )
    )
    clk = make_label(
        font_sm,
        text="--:--",
        color=PIP,
        scale=2,
        anchor_point=(1, 0.5),
        anchored_position=(695, 28),
    )
    g.append(clk)
    g.append(Rect(20, 42, 680, 2, fill=PIP))

    g.append(RoundRect(20, 55, 680, 105, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="OVERALL SYSTEM STATUS",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0.5, 0),
            anchored_position=(360, 63),
        )
    )
    overall = make_label(
        font_sm,
        text="STARTING",
        color=PIP_LO,
        scale=4,
        anchor_point=(0.5, 0.5),
        anchored_position=(360, 120),
    )
    g.append(overall)

    rows = []
    row_specs = [
        ("WIFI / NTP", "RADIO OFF BY DESIGN"),
        ("SHT4X", "TEMPERATURE + HUMIDITY"),
        ("SEN66 CORE", "CO2 + VOC + NOx + PM"),
        ("SEN66 PARTICLE COUNT", "5 SIZE CHANNELS"),
    ]
    for index, (title, detail_text) in enumerate(row_specs):
        y = 175 + index * 95
        g.append(RoundRect(20, y, 680, 82, r=4, fill=CARD, outline=BORDER))
        g.append(
            make_label(
                font_sm,
                text=title,
                color=PIP_DIM,
                scale=2,
                anchor_point=(0, 0.5),
                anchored_position=(35, y + 24),
            )
        )
        status = make_label(
            font_sm,
            text="WAITING",
            color=PIP_LO,
            scale=2,
            anchor_point=(1, 0.5),
            anchored_position=(680, y + 24),
        )
        detail = make_label(
            font_sm,
            text=detail_text,
            color=PIP_LO,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(35, y + 57),
        )
        g.append(status)
        g.append(detail)
        rows.append((status, detail))

    g.append(RoundRect(20, 565, 680, 90, r=4, fill=CARD, outline=BORDER))
    g.append(
        make_label(
            font_sm,
            text="RUNTIME",
            color=PIP_DIM,
            scale=2,
            anchor_point=(0, 0.5),
            anchored_position=(35, 588),
        )
    )
    runtime = make_label(
        font_sm,
        text="UPTIME --:--:--  /  FREE MEM --- KB",
        color=PIP,
        scale=2,
        anchor_point=(0, 0.5),
        anchored_position=(35, 628),
    )
    g.append(runtime)
    g.append(
        make_label(
            font_sm,
            text="DISPLAY ONLINE  /  ROTATE TO EXIT",
            color=PIP_LO,
            scale=2,
            anchor_point=(0.5, 0.5),
            anchored_position=(360, 685),
        )
    )
    return g, clk, overall, rows, runtime


# Build all screens once at import time.
(
    overview_g,
    o_clk,
    o_status,
    o_detail,
    o_action,
    o_ptr,
    o_co2,
    o_co2t,
    o_tmp,
    o_hum,
    o_dew,
    o_pm25,
    o_voc,
) = build_overview_screen()

(
    dash_g,
    d_clk,
    d_tmp,
    d_hum,
    d_eaqi,
    d_co2,
    d_co2t,
    d_dew,
    d_voc,
    d_nox,
    d_pm1,
    d_pm25,
    d_pm4,
    d_pm10,
    d_nc05,
    d_nc1,
    d_nc25,
    d_nc4,
    d_nc10,
    d_aq_txt,
    d_ptr,
) = build_dashboard()

(co2_g, s_clk, s_co2, s_co2t, s_tmp, s_hum, s_aq_txt, s_ptr) = build_co2_screen()

(health_g, h_clk, h_overall, h_rows, h_runtime) = build_health_screen()

screens = [overview_g, dash_g, co2_g, health_g]


# ═══════════════════════════════════════════════════════
# Updaters
# ═══════════════════════════════════════════════════════
def update_overview():
    try:
        o_clk.text = clock_str()
        t = sensors.temperature()
        h = sensors.humidity()
        dp = dew_point(t, h)

        o_tmp.text = f"{t:.1f}" if t is not None else "--.-"
        set_color(o_tmp, tcol(t))
        o_hum.text = f"{h:.1f}" if h is not None else "--.-"
        set_color(o_hum, PIP if h is not None else PIP_LO)
        o_dew.text = f"{dp:.1f}" if dp is not None else "--.-"
        set_color(o_dew, dewcol(dp))

        sd = sensors.sen_data()
        co2v = sd.get("co2")
        pm25v = sd.get("pm2_5")
        vocv = sd.get("voc_index")
        o_co2.text = str(int(co2v)) if co2v is not None else "---"
        set_color(o_co2, co2col(co2v))
        o_co2t.text = co2txt(co2v)
        set_color(o_co2t, co2col(co2v))
        o_pm25.text = f"{pm25v:.1f}" if pm25v is not None else "--"
        set_color(o_pm25, pm25col(pm25v))
        o_voc.text = str(int(vocv)) if vocv is not None else "--"
        set_color(o_voc, voccol(vocv))

        status = sensors.sen_status()
        if status == "FRESH":
            score = aq_score(sd)
            text, color = aq_label_and_color(score)
            try:
                trends = sensors.trend_data()
            except AttributeError:
                trends = {}
            threat, action = main_threat_and_action(sd, trends)
            o_detail.text = "MAIN THREAT: " + threat
            o_action.text = action
        elif status == "STALE":
            score = 0.0
            text, color = "STALE", S_BAD
            o_detail.text = "MAIN THREAT: UNKNOWN"
            o_action.text = "SENSOR UPDATE OVERDUE"
        else:
            score = 0.0
            text, color = "NO DATA", PIP_LO
            o_detail.text = "MAIN THREAT: UNKNOWN"
            o_action.text = "WAITING FOR SENSOR DATA"
        o_status.text = text
        set_color(o_status, color)
        set_color(o_detail, color if status != "FRESH" else PIP_LO)
        set_color(o_action, color if status != "FRESH" else PIP_LO)
        o_ptr.x = 70 + int(score * 576)
    except Exception as e:
        print(f"OVERVIEW: {e}")


def update_dashboard():
    try:
        d_clk.text = clock_str()
        t = sensors.temperature()
        h = sensors.humidity()
        d_tmp.text = f"{t:.1f}" if t is not None else "--.-"
        set_color(d_tmp, tcol(t))
        d_hum.text = f"{h:.1f}" if h is not None else "--.-"
        set_color(d_hum, PIP if h is not None else PIP_LO)

        dp = dew_point(t, h)
        d_dew.text = f"{dp:.1f}" if dp is not None else "--"
        set_color(d_dew, dewcol(dp))

        sd = sensors.sen_data()
        nc = sensors.nc_data()

        pm25v = sd.get("pm2_5")
        pm10v = sd.get("pm10")
        lvl = eaqi_level(pm25v, pm10v)
        d_eaqi.text = EAQI_NAMES[lvl]
        set_color(d_eaqi, EAQI_COLORS[lvl])

        co2v = sd.get("co2")
        d_co2.text = str(int(co2v)) if co2v is not None else "---"
        set_color(d_co2, co2col(co2v))
        d_co2t.text = co2txt(co2v)
        set_color(d_co2t, co2col(co2v))

        vocv = sd.get("voc_index")
        d_voc.text = str(int(vocv)) if vocv is not None else "--"
        set_color(d_voc, voccol(vocv))

        noxv = sd.get("nox_index")
        d_nox.text = str(int(noxv)) if noxv is not None else "--"
        set_color(d_nox, noxcol(noxv))

        pm1v = sd.get("pm1_0")
        d_pm1.text = f"{pm1v:.1f}" if pm1v is not None else "--"
        set_color(d_pm1, pm1col(pm1v))

        d_pm25.text = f"{pm25v:.1f}" if pm25v is not None else "--"
        set_color(d_pm25, pm25col(pm25v))

        pm4v = sd.get("pm4_0")
        d_pm4.text = f"{pm4v:.1f}" if pm4v is not None else "--"
        set_color(d_pm4, pm4col(pm4v))

        d_pm10.text = f"{pm10v:.1f}" if pm10v is not None else "--"
        set_color(d_pm10, pm10col(pm10v))

        keys = ["nc_pm0_5", "nc_pm1_0", "nc_pm2_5", "nc_pm4_0", "nc_pm10"]
        lbls = [d_nc05, d_nc1, d_nc25, d_nc4, d_nc10]
        for i, k in enumerate(keys):
            v = nc.get(k)
            lbls[i].text = f"{v:.0f}" if v is not None else "--"
            set_color(lbls[i], nccol(v))

        status = sensors.sen_status()
        if status == "FRESH":
            score = aq_score(sd)
            txt, color = aq_label_and_color(score)
        elif status == "STALE":
            score = 0.0
            txt, color = "STALE", S_BAD
        else:
            score = 0.0
            txt, color = "NO DATA", PIP_LO
        d_aq_txt.text = txt
        set_color(d_aq_txt, color)
        d_ptr.x = 50 + int(score * 616)
    except Exception as e:
        print(f"UPD: {e}")


def update_co2_screen():
    try:
        s_clk.text = clock_str()
        t = sensors.temperature()
        h = sensors.humidity()
        s_tmp.text = f"{t:.1f}" if t is not None else "--.-"
        set_color(s_tmp, tcol(t))
        s_hum.text = f"{h:.1f}" if h is not None else "--.-"
        set_color(s_hum, PIP if h is not None else PIP_LO)

        sd = sensors.sen_data()
        co2v = sd.get("co2")
        s_co2.text = str(int(co2v)) if co2v is not None else "---"
        set_color(s_co2, co2col(co2v))
        s_co2t.text = co2txt(co2v)
        set_color(s_co2t, co2col(co2v))

        status = sensors.sen_status()
        if status == "FRESH":
            score = aq_score(sd)
            txt, color = aq_label_and_color(score)
        elif status == "STALE":
            score = 0.0
            txt, color = "STALE", S_BAD
        else:
            score = 0.0
            txt, color = "NO DATA", PIP_LO
        s_aq_txt.text = txt
        set_color(s_aq_txt, color)
        s_ptr.x = 100 + int(score * 516)
    except Exception as e:
        print(f"CO2: {e}")


def update_health_screen():
    try:
        h_clk.text = clock_str()

        wifi_state = wifi_sync.sync_status()
        sht_state = sensors.sht_status()
        sen_state = sensors.sen_status()
        nc_state = sensors.nc_status()

        states = [wifi_state, sht_state, sen_state, nc_state]
        if all(state in ("SYNCED", "FRESH") for state in states):
            overall_text, overall_color = "NOMINAL", S_GOOD
        elif any(state in ("STALE", "NO DATA") for state in states[1:]):
            overall_text, overall_color = "SENSOR FAULT", S_BAD
        else:
            overall_text, overall_color = "DEGRADED", S_WARN
        h_overall.text = overall_text
        set_color(h_overall, overall_color)

        ages = [None, sensors.sht_age(), sensors.sen_age(), sensors.nc_age()]
        base_details = [
            "RADIO OFF BY DESIGN",
            "TEMPERATURE + HUMIDITY",
            "CO2 + VOC + NOx + PM",
            "5 SIZE CHANNELS",
        ]
        for index, state in enumerate(states):
            status_label, detail_label = h_rows[index]
            if status_label.text != state:
                status_label.text = state
            set_color(status_label, _health_color(state))
            age = ages[index]
            detail_text = base_details[index]
            if age is not None:
                detail_text += f"  /  AGE {age:.1f}S"
            if detail_label.text != detail_text:
                detail_label.text = detail_text

        uptime = int(time.monotonic())
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        free_kb = gc.mem_free() // 1024
        h_runtime.text = (
            f"UPTIME {hours:02d}:{minutes:02d}:{seconds:02d}  /  FREE MEM {free_kb} KB"
        )
    except Exception as e:
        print(f"HEALTH: {e}")


def _health_color(state):
    if state in ("SYNCED", "FRESH"):
        return S_GOOD
    if state in ("WAITING", "RETRYING"):
        return S_WARN
    return S_BAD
