# AIR PRO v2.0 — low-level hardware setup: I2C, display, backlight, encoder.
import time
import board
import busio
import digitalio
import dotclockframebuffer
from framebufferio import FramebufferDisplay
from adafruit_seesaw import seesaw, digitalio as seesaw_digitalio
from adafruit_seesaw import rotaryio as seesaw_rotaryio

from config import (
    TFT_TIMING,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BL_I2C_ADDR,
    BL_REG_GPIO,
    BL_REG_CONFIG,
    BL_BIT,
    BL_TIMEOUT_MS,
    SEESAW_ADDR,
    ENCODER_BUTTON_PIN,
)


def release_and_init_display():
    """Release any previous displays and create the DotClock framebuffer."""
    import displayio

    # Free the shared I2C singleton so we can use a private bus for the
    # display init sequence. It will be recreated later via board.I2C().
    try:
        board.I2C().deinit()
    except Exception:
        pass

    displayio.release_displays()
    # Send the TFT IO-expander init sequence over a temporary I2C bus.
    tft_pins = dict(board.TFT_PINS)
    with busio.I2C(board.SCL, board.SDA) as i2c:
        dotclockframebuffer.ioexpander_send_init_sequence(
            i2c, bytes(), **dict(board.TFT_IO_EXPANDER)
        )
    fb = dotclockframebuffer.DotClockFramebuffer(**tft_pins, **TFT_TIMING)
    display = FramebufferDisplay(fb, auto_refresh=False)
    return display


def _i2c_lock_with_timeout(i2c, timeout_ms=BL_TIMEOUT_MS):
    """Try to lock the I2C bus; return True on success, False on timeout."""
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while not i2c.try_lock():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


def configure_backlight(i2c):
    """Set the backlight GPIO bit as an output (AW9523 on Qualia S3)."""
    if not _i2c_lock_with_timeout(i2c):
        print("BL config: lock timeout")
        return
    try:
        cfg = bytearray(1)
        i2c.writeto_then_readfrom(BL_I2C_ADDR, bytes([BL_REG_CONFIG]), cfg)
        cfg[0] &= ~(1 << BL_BIT)
        i2c.writeto(BL_I2C_ADDR, bytes([BL_REG_CONFIG, cfg[0]]))
    except Exception as e:
        print(f"BL config: {e}")
    finally:
        try:
            i2c.unlock()
        except Exception:
            pass


def set_backlight(i2c, on):
    """Turn the display backlight on or off with a lock timeout."""
    if not _i2c_lock_with_timeout(i2c):
        print("BL: lock timeout")
        return
    try:
        buf = bytearray(1)
        i2c.writeto_then_readfrom(BL_I2C_ADDR, bytes([BL_REG_GPIO]), buf)
        if on:
            buf[0] |= 1 << BL_BIT
        else:
            buf[0] &= ~(1 << BL_BIT)
        i2c.writeto(BL_I2C_ADDR, bytes([BL_REG_GPIO, buf[0]]))
    except Exception as e:
        print(f"BL: {e}")
    finally:
        try:
            i2c.unlock()
        except Exception:
            pass


def runtime_i2c():
    """Return the shared board I2C bus used at runtime."""
    return board.I2C()


def init_encoder(i2c):
    """Initialize the rotary encoder over Seesaw."""
    ss = seesaw.Seesaw(i2c, SEESAW_ADDR)
    enc_btn = seesaw_digitalio.DigitalIO(ss, ENCODER_BUTTON_PIN)
    enc_btn.direction = digitalio.Direction.INPUT
    enc_btn.pull = digitalio.Pull.UP
    encoder = seesaw_rotaryio.IncrementalEncoder(ss)
    return ss, enc_btn, encoder
