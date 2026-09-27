# AIR PRO v2.0 — configuration and constants.
# Keep this file free of hardware imports so it can be imported anywhere.

# ── Fonts ──
FONT_BIG = "/fonts/Roboto-Regular-47.pcf"
FONT_XL = "/fonts/Roboto-Clock-120.pcf"
FONT_SM = None  # terminalio.FONT is assigned at runtime

# ── Pip-Boy Color Palette ──
BG = 0x0A0A0A          # near-black background
CARD = 0x0D1A0D        # dark green card fill
BORDER = 0x1A3A1A      # subtle green border
PIP = 0x00FF41         # phosphor green (primary)
PIP_DIM = 0x00AA2A     # muted green (labels)
PIP_LO = 0x006618      # dim green (secondary)
AMBER = 0xFFAA00       # amber warning
RED = 0xFF2200         # alert red
BLUE_G = 0x00CCAA      # teal accent

# Aliases used by generic helpers — in the Pip-Boy theme "white" is green.
WHITE = PIP
GRAY = PIP_DIM

# ── Sensor status colors ──
S_GOOD = 0x00FF41
S_OK = 0x88DD00
S_WARN = 0xFFAA00
S_BAD = 0xFF4400
S_CRIT = 0xFF0000

# ── Thresholds ──
TEMP_LIMITS = {
    "cold": 0,      # below -> BLUE_G
    "cool": 18,     # below -> S_GOOD
    "warm": 27,     # above -> AMBER
    "hot": 35,      # above -> RED
}

CO2_LIMITS = {
    "good": 800,
    "ok": 1000,
    "warn": 1500,
    "bad": 2000,
}

VOC_LIMITS = {
    "good": 100,
    "ok": 150,
    "warn": 200,
    "bad": 300,
}

NOX_LIMITS = {
    "good": 20,
    "ok": 50,
    "warn": 100,
    "bad": 150,
}

# PM mass concentration thresholds (good, ok, warn, bad) in ug/m3
PM_THRESHOLDS = {
    "pm1_0": (3, 8, 25, 45),
    "pm2_5": (5, 15, 50, 90),
    "pm4_0": (10, 30, 85, 140),
    "pm10": (15, 45, 120, 195),
}

# EAQI level breakpoints
EAQI_PM25_BREAKS = (5, 15, 50, 90, 140)
EAQI_PM10_BREAKS = (15, 45, 120, 195, 270)
EAQI_COLORS = [PIP_LO, S_GOOD, S_OK, S_WARN, S_BAD, S_CRIT, S_CRIT]
EAQI_NAMES = ["---", "CLEAR", "FAIR", "MODERATE", "POOR", "HAZARDOUS", "CRITICAL"]

# Particle number concentration thresholds
NC_LIMITS = {
    "good": 100,
    "ok": 500,
    "warn": 1000,
}

# ── Dew point ──
DEWPOINT_LIMITS = {
    "dry": 10,
    "comfy": 15,
    "humid": 20,
}

# ── Air quality composite score labels ──
AQ_LABELS = ["OPTIMAL", "NORMAL", "FAIR", "CAUTION", "WARNING", "CRITICAL"]
AQ_GRAD = [S_GOOD, S_GOOD, S_OK, S_WARN, S_BAD, S_CRIT]

# ── Night mode ──
DIM_FACTOR = 4

# ── Display ──
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 720
TFT_FREQUENCY = 12_000_000
TFT_TIMING = {
    "frequency": TFT_FREQUENCY,
    "width": SCREEN_WIDTH,
    "height": SCREEN_HEIGHT,
    "hsync_pulse_width": 2,
    "hsync_front_porch": 46,
    "hsync_back_porch": 44,
    "vsync_pulse_width": 2,
    "vsync_front_porch": 16,
    "vsync_back_porch": 18,
    "hsync_idle_low": False,
    "vsync_idle_low": False,
    "de_idle_high": False,
    "pclk_active_high": False,
    "pclk_idle_high": False,
}

# ── Backlight (AW9523 GPIO expander on Qualia S3) ──
BL_I2C_ADDR = 0x3F
BL_REG_GPIO = 0x01      # GPIO output state
BL_REG_CONFIG = 0x03    # GPIO direction config
BL_BIT = 4              # backlight control bit
BL_TIMEOUT_MS = 500     # max time to wait for I2C lock

# ── Timing ──
SENSOR_INTERVAL_S = 2.0
SENSOR_STALE_AFTER_S = 10.0
HEALTH_INTERVAL_S = 0.5
TREND_WINDOW_S = 120.0
NTP_INTERVAL_S = 3600
NTP_RETRY_INTERVAL_S = 300
TZ_OFFSET_HOURS = 2
NTP_SERVER = "pool.ntp.org"

# ── Sensor startup constants ──
SHT4X_MODE = "NOHEAT_HIGHPRECISION"  # resolved in sensors.py
SEN66_ADDR = 0x6B
SEESAW_ADDR = 0x36
ENCODER_BUTTON_PIN = 24
