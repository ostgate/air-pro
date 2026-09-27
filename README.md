# AIR PRO

A small indoor air quality monitor with a retro green "Pip-Boy" style screen.

It shows CO2, temperature, humidity, dust (PM), VOC and NOx on a 720x720 display.
You turn the knob on top to switch screens and press it to switch night mode.

![Overview screen](docs/img/screen-overview.jpg)

## What it does

- Reads CO2, particles, VOC, NOx, temperature and humidity every 2 seconds.
- Gives one simple "overall air status" (OPTIMAL, NORMAL, FAIR, CAUTION, WARNING, CRITICAL).
- Tells you the main problem, for example "MAIN THREAT: CO2, VENTILATE ROOM".
- Shows a clock. The time comes from the internet (NTP) once an hour.
- Works fully offline. WiFi is only turned on for a few seconds to get the time.

## Screens

Turn the knob to move between screens.

| # | Screen | What you see |
|---|--------|--------------|
| 1 | Environment Overview | Overall status, CO2, temperature, humidity, dew point, PM2.5, VOC |
| 2 | Air Quality Analysis | All values: PM1.0 to PM10, particle counts, NOx, VOC, CO2, dew point |
| 3 | CO2 Monitoring Station | Big CO2 number, easy to read from across the room |
| 4 | System Health | Sensor status, data age, WiFi/NTP status, uptime, free memory |

Press the knob to turn night mode on or off (dim colors, backlight off).

More photos and the full parts list are in [docs/SPECS.md](docs/SPECS.md).

## Hardware (short list)

- Adafruit Qualia ESP32-S3 for RGB666 displays
- 4 inch 720x720 square RGB666 TFT display
- Sensirion SEN66 (CO2, PM, VOC, NOx, temperature, humidity)
- Adafruit SHT45 (precise temperature and humidity)
- Adafruit I2C rotary encoder (seesaw)
- STEMMA QT / Qwiic cables

## How to install

1. Flash CircuitPython 10.x on the board. Download it here:
   [circuitpython.org/board/adafruit_qualia_s3_rgb666](https://circuitpython.org/board/adafruit_qualia_s3_rgb666/)
2. Plug the board into your computer. A drive called `CIRCUITPY` appears.
3. Copy everything from this repo to the root of `CIRCUITPY`:
   `code.py`, `*.py`, `fonts/`, `lib/`.
4. Create `settings.toml` on `CIRCUITPY` with your WiFi:

   ```toml
   CIRCUITPY_WIFI_SSID = "your-wifi"
   CIRCUITPY_WIFI_PASSWORD = "your-password"
   ```

5. The board restarts and the monitor starts by itself.

To see logs, open the serial console:

```sh
screen /dev/cu.usbmodem* 115200
```

## Settings

Everything you may want to change is in `config.py`:

- `TZ_OFFSET_HOURS` for your time zone
- `SENSOR_INTERVAL_S` for how often sensors are read
- `CO2_LIMITS`, `VOC_LIMITS`, `PM_THRESHOLDS` and others for the color levels

## Code layout

| File | Job |
|------|-----|
| `code.py` | Start up and main loop |
| `hardware.py` | Display, I2C, backlight, rotary encoder |
| `sensors.py` | Reads SEN66 and SHT45, keeps last good values |
| `ui.py` | All four screens and night mode |
| `wifi_sync.py` | WiFi on, get time from NTP, WiFi off |
| `utils.py` | Small helpers (dew point, colors, formatting) |
| `config.py` | Colors, limits, timings, pins |

## Known quirks

- The display driver needs the I2C bus during start up, so the code frees I2C,
  starts the display, then starts I2C again for the sensors.
- WiFi and the display fight over memory bandwidth on the ESP32-S3 and the screen
  can flicker. That is why WiFi is off most of the time.

## Status

Working prototype. The case is a small wooden box I had at home.
Next step: design and 3D print a proper case. See [docs/SPECS.md](docs/SPECS.md#next-step-3d-printed-case).
## License

MIT, see [LICENSE](LICENSE).

Third party files keep their own licenses:

- `lib/` has Adafruit CircuitPython libraries, MIT license.
- `fonts/` has Roboto fonts, Apache 2.0 license.
