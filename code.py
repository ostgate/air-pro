# AIR PRO v2.0 — VAULT-TEC ENVIRONMENTAL MONITOR
# Entry point. Keep this file small: hardware setup + main loop.
# Encoder rotate = switch screen | Encoder press = night mode

import gc
import time

import hardware
import sensors
import wifi_sync

print("[VAULT-TEC] Initializing...")
display = hardware.release_and_init_display()

# Import UI after the display is initialized so displayio bitmaps are created
# against the correct framebuffer state.
print("[VAULT-TEC] Building interface...")
import ui

gc.collect()

# Runtime I2C bus and peripherals
i2c = hardware.runtime_i2c()
hardware.configure_backlight(i2c)
sensors.init_sensors(i2c)
ss, enc_btn, encoder = hardware.init_encoder(i2c)

cur_scr = 0
display.root_group = ui.screens[cur_scr]
display.auto_refresh = True
print("[VAULT-TEC] Interface ready")

# Sync clock, then keep WiFi radio off for display stability.
last_ntp_ok = wifi_sync.wifi_ntp_sync()
gc.collect()
print("[VAULT-TEC] Systems operational")

# Main loop state
last_pos = encoder.position
prev_btn = True
last_upd = 0
last_health_upd = 0
last_ntp_attempt = time.monotonic()

from config import HEALTH_INTERVAL_S, SENSOR_INTERVAL_S, NTP_INTERVAL_S, NTP_RETRY_INTERVAL_S

while True:
    now = time.monotonic()

    # Encoder: switch screen on rotation
    try:
        pos = encoder.position
        if pos != last_pos:
            delta = pos - last_pos
            last_pos = pos
            cur_scr = (cur_scr + delta) % len(ui.screens)
            display.root_group = ui.screens[cur_scr]
    except Exception as e:
        print(f"Enc: {e}")

    # Encoder button: toggle night mode
    try:
        b = enc_btn.value
        if prev_btn and not b:
            ui.apply_night_mode(not ui.is_night_mode(), i2c)
        prev_btn = b
    except Exception as e:
        print(f"Btn: {e}")

    # Sensor update
    if now - last_upd >= SENSOR_INTERVAL_S:
        sensors.read_sensors()
        if cur_scr == 0:
            ui.update_overview()
        elif cur_scr == 1:
            ui.update_dashboard()
        elif cur_scr == 2:
            ui.update_co2_screen()
        last_upd = now

    # Keep diagnostic ages moving independently of the sensor poll cadence.
    if cur_scr == 3 and now - last_health_upd >= HEALTH_INTERVAL_S:
        ui.update_health_screen()
        last_health_upd = now

    # Re-sync hourly after success; retry sooner after a failed attempt.
    ntp_interval = NTP_INTERVAL_S if last_ntp_ok else NTP_RETRY_INTERVAL_S
    if now - last_ntp_attempt >= ntp_interval:
        last_ntp_ok = wifi_sync.wifi_ntp_sync()
        last_ntp_attempt = time.monotonic()

    time.sleep(0.05)
