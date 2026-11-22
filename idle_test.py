import time
from rpi_ws281x import PixelStrip, Color, ws

LED_COUNT  = 30          # originally 144 changed for testing
LED_PIN    = 18
BRIGHTNESS = 60          # 0-255, keep low while testing

FLASH_EVERY = 10.0       # seconds between flash sequences
FLASH_COUNT = 3          # NOT USED ANYMORE
FLASH_ON    = 0.15       # seconds white is on NOT USED ANYMORE
FLASH_OFF   = 0.15       # seconds between flashes NOT USED ANYMORE
FRAME_DELAY = 0.02       # lower = faster scrolling 

BAR_STEP = 0.04       # seconds per LED (30 x 0.04 = ~1.2 s to fill)
BAR_HOLD = 1.0        # seconds the full bar stays lit


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
    fill(0, 0, 0, 0)                          # idle off, all LEDs dark
    for n in range(LED_COUNT):
        strip.setPixelColor(n, Color(0, 0, 0, 255))         # light the next LED
        strip.show()
        time.sleep(BAR_STEP)
    time.sleep(BAR_HOLD)                      # bar stays full

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

if __name__ == "__main__":
    flash_white()
