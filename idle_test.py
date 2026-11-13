import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT  = 144
LED_PIN    = 18
BRIGHTNESS = 60          # 0-255, keep low while testing

FLASH_EVERY = 10.0       # seconds between flash sequences
FLASH_COUNT = 3
FLASH_ON    = 0.15       # seconds white is on
FLASH_OFF   = 0.15       # seconds between flashes
FRAME_DELAY = 0.02       # lower = faster scrolling

strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, BRIGHTNESS, 0, ws.SK6812_STRIP_GRBW)
strip.begin()

# Precompute a blue -> green -> blue gradient that wraps around the strip
palette = []
for i in range(LED_COUNT):
    phase = i / LED_COUNT                  # 0 to 1 along the strip
    t = 1 - abs(2 * phase - 1)             # 0 < t < 1 (triangle wave)
    palette.append(Color(0, int(255 * t), int(255 * (1 - t)), 0))  # r, g, b, w

def fill(r, g, b, w=0):
    c = Color(r, g, b, w)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, c)
    strip.show()

def idle_frame(shift):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, palette[(i + shift) % LED_COUNT])
    strip.show()

def flash_white():
    for _ in range(FLASH_COUNT):
        fill(0, 0, 0, 255)                 # white flash
        time.sleep(FLASH_ON)
        fill(0, 0, 0, 0)
        time.sleep(FLASH_OFF)

try:
    shift = 0
    last_flash = time.monotonic()
    while True:
        idle_frame(shift)
        shift = (shift + 1) % LED_COUNT
        time.sleep(FRAME_DELAY)

        if time.monotonic() - last_flash >= FLASH_EVERY:
            flash_white()
            last_flash = time.monotonic()   # restart timer
except KeyboardInterrupt:
    fill(0, 0, 0, 0)                       # lights off on Ctrl+C