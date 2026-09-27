# AIR PRO v2.0 — pure helper functions (no hardware state).
from config import (
    BLUE_G,
    S_GOOD,
    S_OK,
    S_WARN,
    S_BAD,
    S_CRIT,
    PIP_LO,
    AMBER,
    RED,
    TEMP_LIMITS,
    CO2_LIMITS,
    VOC_LIMITS,
    NOX_LIMITS,
    PM_THRESHOLDS,
    EAQI_PM25_BREAKS,
    EAQI_PM10_BREAKS,
    EAQI_NAMES,
    EAQI_COLORS,
    NC_LIMITS,
    DEWPOINT_LIMITS,
    AQ_LABELS,
    AQ_GRAD,
)


def dim(color, factor=4):
    """Dim an RGB color by an integer factor."""
    r = ((color >> 16) & 0xFF) // factor
    g = ((color >> 8) & 0xFF) // factor
    b = (color & 0xFF) // factor
    return (r << 16) | (g << 8) | b


def tcol(t):
    """Color for temperature value."""
    if t is None:
        return PIP_LO
    if t < TEMP_LIMITS["cold"] or t > TEMP_LIMITS["hot"]:
        return RED
    if t < TEMP_LIMITS["cool"]:
        return BLUE_G
    if t < TEMP_LIMITS["warm"]:
        return S_GOOD
    return AMBER


def _step_color(value, limits, colors):
    """Map a numeric value to a color using ascending limits."""
    if value is None:
        return PIP_LO
    for limit, color in zip(limits, colors):
        if value <= limit:
            return color
    return colors[-1]


def co2col(v):
    if v is None:
        return PIP_LO
    return _step_color(v, CO2_LIMITS.values(), [S_GOOD, S_OK, S_WARN, S_BAD, S_CRIT])


def co2txt(v):
    if v is None:
        return ""
    if v <= CO2_LIMITS["good"]:
        return "OPTIMAL"
    if v <= CO2_LIMITS["ok"]:
        return "NORMAL"
    if v <= CO2_LIMITS["warn"]:
        return "CAUTION"
    return "WARNING"


def voccol(v):
    if v is None:
        return PIP_LO
    return _step_color(v, VOC_LIMITS.values(), [S_GOOD, S_OK, S_WARN, S_BAD, S_CRIT])


def noxcol(v):
    if v is None:
        return PIP_LO
    return _step_color(v, NOX_LIMITS.values(), [S_GOOD, S_OK, S_WARN, S_BAD, S_CRIT])


def pmcol(v, thresholds):
    if v is None:
        return PIP_LO
    return _step_color(v, thresholds, [S_GOOD, S_OK, S_WARN, S_BAD, S_CRIT])


def pm1col(v):
    return pmcol(v, PM_THRESHOLDS["pm1_0"])


def pm25col(v):
    return pmcol(v, PM_THRESHOLDS["pm2_5"])


def pm4col(v):
    return pmcol(v, PM_THRESHOLDS["pm4_0"])


def pm10col(v):
    return pmcol(v, PM_THRESHOLDS["pm10"])


def _eaqi_level(value, breaks):
    if value is None:
        return 0
    for level, limit in enumerate(breaks, start=1):
        if value <= limit:
            return level
    return len(breaks) + 1


def eaqi_pm25(v):
    return _eaqi_level(v, EAQI_PM25_BREAKS)


def eaqi_pm10(v):
    return _eaqi_level(v, EAQI_PM10_BREAKS)


def eaqi_level(pm25, pm10):
    return max(eaqi_pm25(pm25), eaqi_pm10(pm10))


def dew_point(t, rh):
    """Simple dew point approximation (no math module needed)."""
    if t is None or rh is None:
        return None
    return t - (100 - rh) / 5.0


def dewcol(dp):
    """Color for dew point."""
    if dp is None:
        return PIP_LO
    if dp < DEWPOINT_LIMITS["dry"]:
        return BLUE_G
    if dp < DEWPOINT_LIMITS["comfy"]:
        return S_GOOD
    if dp < DEWPOINT_LIMITS["humid"]:
        return S_WARN
    return S_BAD


def nccol(v):
    if v is None:
        return PIP_LO
    if v <= NC_LIMITS["good"]:
        return S_GOOD
    if v <= NC_LIMITS["ok"]:
        return S_OK
    if v <= NC_LIMITS["warn"]:
        return S_WARN
    return S_BAD


def aq_score(sen_data):
    """Composite air-quality score in [0.0, 1.0]."""
    scores = []
    if not sen_data:
        return 0.0

    co2 = sen_data.get("co2")
    if co2 is not None:
        scores.append(max(0.0, min(1.0, (co2 - 400) / 1600)))

    voc = sen_data.get("voc_index")
    if voc is not None:
        scores.append(max(0.0, min(1.0, voc / 300)))

    nox = sen_data.get("nox_index")
    if nox is not None:
        scores.append(max(0.0, min(1.0, nox / 150)))

    pm25 = sen_data.get("pm2_5")
    pm10 = sen_data.get("pm10")
    lvl = eaqi_level(pm25, pm10)
    if lvl > 0:
        scores.append((lvl - 1) / 5)

    return max(scores) if scores else 0.0


def aq_label_and_color(score):
    """Return (label, color) for a composite AQ score."""
    idx = min(int(score * 5), 5)
    return AQ_LABELS[idx], AQ_GRAD[idx]


def main_threat_and_action(sen_data, trends=None):
    """Return the most actionable air-quality issue and a short response."""
    if not sen_data:
        return "NO DATA", "WAIT FOR SENSOR DATA"

    threats = []
    _add_threat(threats, "CO2", "VENTILATE ROOM", sen_data.get("co2"), 900, 1200, trends, "co2", 100)
    _add_threat(
        threats, "VOC", "CHECK VOC SOURCE", sen_data.get("voc_index"), 120, 200, trends, "voc_index", 30
    )
    _add_threat(
        threats, "NOx", "VENTILATE ROOM", sen_data.get("nox_index"), 30, 120, trends, "nox_index", 20
    )
    _add_threat(
        threats, "PM2.5", "CHECK DUST / WINDOW", sen_data.get("pm2_5"), 10, 90, trends, "pm2_5", 5
    )
    _add_threat(
        threats, "PM10", "CHECK DUST / WINDOW", sen_data.get("pm10"), 30, 195, trends, "pm10", 10
    )
    if not threats:
        return "NONE", "VAULT SECURE"
    _, threat, action = max(threats)
    return threat, action


def _add_threat(threats, name, action, value, trigger, scale, trends, key, rise_trigger):
    if value is None:
        return
    score = 0.0
    if value > trigger:
        score = (value - trigger) / scale
    trend = trends.get(key) if trends else None
    rise = trend[1] if trend else None
    if rise is not None and rise > rise_trigger:
        score = max(score, 0.35 + rise / scale)
    if score > 0:
        threats.append((score, name, action))
