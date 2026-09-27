# AIR PRO v2.0 — sensor reading wrappers (SHT4x + SEN66).
import time

import adafruit_sht4x
import adafruit_sen6x

from config import SENSOR_STALE_AFTER_S, SHT4X_MODE, SEN66_ADDR, TREND_WINDOW_S

# Last known readings (updated by read_sensors()).
_last_tmp = None
_last_hum = None
_last_sen = {}
_last_nc = {}
_last_sht_read_at = None
_last_sen_read_at = None
_last_nc_read_at = None
_sen_history = []

_sht = None
_sen66 = None


def init_sensors(i2c):
    """Initialize SHT4x and SEN66 on the given I2C bus."""
    global _sht, _sen66
    _sht = adafruit_sht4x.SHT4x(i2c)
    _sht.mode = getattr(adafruit_sht4x.Mode, SHT4X_MODE)
    _sen66 = adafruit_sen6x.SEN66(i2c, SEN66_ADDR)
    _sen66.start_measurement()
    return _sht, _sen66


def read_sensors():
    """Poll sensors and store latest values. Exceptions are logged, not raised."""
    global _last_tmp, _last_hum, _last_sht_read_at, _last_sen_read_at
    global _last_nc_read_at
    if _sht is not None:
        try:
            _last_tmp, _last_hum = _sht.measurements
            _last_sht_read_at = time.monotonic()
        except Exception as e:
            print(f"SHT: {e}")

    if _sen66 is not None:
        try:
            ready = _sen66.data_ready
        except Exception as e:
            print(f"SEN ready: {e}")
            return

        if not ready:
            return

        try:
            measurements = _sen66.all_measurements()
            read_at = time.monotonic()
            _last_sen.clear()
            _last_sen.update(measurements)
            _last_sen_read_at = read_at
            _record_sen_history(read_at)
        except Exception as e:
            print(f"SEN values: {e}")
            return

        try:
            concentrations = _sen66.number_concentration()
            _last_nc.clear()
            _last_nc.update(concentrations)
            _last_nc_read_at = time.monotonic()
        except Exception as e:
            print(f"SEN count: {e}")


def temperature():
    return _last_tmp if sht_is_fresh() else None


def humidity():
    return _last_hum if sht_is_fresh() else None


def sen_data():
    return _last_sen if sen_status() == "FRESH" else {}


def nc_data():
    return _last_nc if _is_fresh(_last_nc_read_at) else {}


def trend_data():
    """Return current values and changes over the recent trend window."""
    if sen_status() != "FRESH" or len(_sen_history) < 2:
        return {}
    current = _sen_history[-1]
    baseline = _sen_history[0]
    return {
        "co2": _trend_pair(current[1], baseline[1]),
        "voc_index": _trend_pair(current[2], baseline[2]),
        "nox_index": _trend_pair(current[3], baseline[3]),
        "pm2_5": _trend_pair(current[4], baseline[4]),
        "pm10": _trend_pair(current[5], baseline[5]),
    }


def sht_is_fresh():
    """Return whether SHT4x data was read within the stale-data timeout."""
    return _is_fresh(_last_sht_read_at)


def sht_status():
    """Return FRESH, STALE, or NO DATA for SHT4x measurements."""
    return _status(_last_sht_read_at)


def sen_status():
    """Return FRESH, STALE, or NO DATA for SEN66 measurements."""
    return _status(_last_sen_read_at)


def nc_status():
    """Return FRESH, STALE, or NO DATA for particle-count measurements."""
    return _status(_last_nc_read_at)


def sht_age():
    return _age(_last_sht_read_at)


def sen_age():
    return _age(_last_sen_read_at)


def nc_age():
    return _age(_last_nc_read_at)


def _status(last_read_at):
    if last_read_at is None:
        return "NO DATA"
    return "FRESH" if _is_fresh(last_read_at) else "STALE"


def _age(last_read_at):
    if last_read_at is None:
        return None
    return max(0.0, time.monotonic() - last_read_at)


def _is_fresh(last_read_at):
    return (
        last_read_at is not None
        and time.monotonic() - last_read_at <= SENSOR_STALE_AFTER_S
    )


def _record_sen_history(timestamp):
    values = (
        timestamp,
        _last_sen.get("co2"),
        _last_sen.get("voc_index"),
        _last_sen.get("nox_index"),
        _last_sen.get("pm2_5"),
        _last_sen.get("pm10"),
    )
    _sen_history.append(values)
    cutoff = timestamp - TREND_WINDOW_S
    while len(_sen_history) > 1 and _sen_history[0][0] < cutoff:
        _sen_history.pop(0)


def _trend_pair(current, baseline):
    if current is None or baseline is None:
        return current, None
    return current, current - baseline
