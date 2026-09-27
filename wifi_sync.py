# AIR PRO v2.0 — WiFi + NTP time sync.
import os
import struct
import time

from config import TZ_OFFSET_HOURS, NTP_SERVER

_clock_synced = False
_last_attempt_ok = None
_last_error = None


def wifi_ntp_sync():
    """Sync RTC from NTP and return whether this attempt succeeded."""
    global _clock_synced, _last_attempt_ok, _last_error
    sock = None
    try:
        import wifi
        import socketpool
        import rtc

        ssid = os.getenv("CIRCUITPY_WIFI_SSID")
        if not ssid:
            print("No WiFi SSID")
            _last_attempt_ok = False
            _last_error = "NO CONFIG"
            return False
        pwd = os.getenv("CIRCUITPY_WIFI_PASSWORD")

        print(f"WiFi: {ssid}...")
        wifi.radio.enabled = True
        wifi.radio.connect(ssid, pwd)
        print(f"WiFi: IP={wifi.radio.ipv4_address}")

        pool = socketpool.SocketPool(wifi.radio)
        pkt = bytearray(48)
        pkt[0] = 0x23
        sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(pkt, (NTP_SERVER, 123))
        sock.recvfrom_into(pkt)
        sock.close()
        sock = None

        ts = struct.unpack_from("!I", pkt, 40)[0] - 2208988800 + TZ_OFFSET_HOURS * 3600
        rtc.RTC().datetime = time.localtime(ts)
        _clock_synced = True
        _last_attempt_ok = True
        _last_error = None
        t = time.localtime()
        print(f"NTP: {t.tm_hour:02d}:{t.tm_min:02d}")
        return True
    except Exception as e:
        _last_attempt_ok = False
        _last_error = str(e)
        print(f"NTP: {e}")
        return False
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

        # Disable WiFi radio to prevent DMA conflicts with DotClock display.
        try:
            import wifi

            wifi.radio.enabled = False
            print("WiFi: radio off (display stability)")
        except Exception:
            pass


def clock_str():
    if not _clock_synced:
        return "--:--"
    t = time.localtime()
    return f"{t.tm_hour:02d}:{t.tm_min:02d}"


def is_synced():
    return _clock_synced


def sync_status():
    """Return a compact health-screen status for WiFi/NTP."""
    if _clock_synced:
        return "SYNCED" if _last_attempt_ok is not False else "RETRYING"
    if _last_error == "NO CONFIG":
        return "NO CONFIG"
    if _last_attempt_ok is False:
        return "RETRYING"
    return "WAITING"
