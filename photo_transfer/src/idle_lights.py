"""Background LED animations for the photo transfer application."""

import threading
from queue import Empty, SimpleQueue

from rpi_ws281x import Color, PixelStrip, ws

from .constants import (
    BRIGHTNESS,
    FLASH_COUNT,
    FLASH_OFF,
    FLASH_ON,
    FRAME_DELAY,
    LED_COUNT,
    LED_PIN,
)


class IdleLights:
    """Control the LED strip with one background animation at a time."""

    def __init__(self):
        self._strip = PixelStrip(
            LED_COUNT, LED_PIN, 800000, 10, False, BRIGHTNESS,
            0, ws.SK6812_STRIP_GRBW,
        )
        self._strip.begin()
        self._palette = []
        for i in range(LED_COUNT):
            phase = i / LED_COUNT
            t = 1 - abs(2 * phase - 1)
            self._palette.append(Color(0, int(255 * t), int(255 * (1 - t)), 0))

        self._stop_event = threading.Event()
        self._flashes = SimpleQueue()
        self._thread = None
        self._lock = threading.Lock()

    def idle(self):
        """Start the scrolling blue/green gradient and return immediately.

        Calling this while the animation is running leaves it running.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._flashes = SimpleQueue()
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def flash(self):
        """Queue three white flashes, then resume the gradient.

        Call after a successful photo. Returns immediately; each call queues
        one sequence on the existing LED thread. Call idle() first.
        """
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                raise RuntimeError("Call idle() before requesting a flash")
            self._flashes.put(None)

        return True

    def stop(self):
        """Wait for the animation to stop and turn off the LEDs.

        Safe to call repeatedly. Call idle() to start again afterward.
        Any pending flash requests are discarded when restarting.
        """
        with self._lock:
            self._stop()

    def _stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self._fill(0, 0, 0, 0)

    def _run(self):
        shift = 0
        try:
            while not self._stop_event.is_set():
                try:
                    self._flashes.get_nowait()
                except Empty:
                    pass
                else:
                    self._flash_white()
                    if self._stop_event.is_set():
                        break

                self._idle_frame(shift)
                shift = (shift + 1) % LED_COUNT
                if self._stop_event.wait(FRAME_DELAY):
                    break

        finally:
            self._fill(0, 0, 0, 0)

    def _fill(self, r, g, b, w=0):
        color = Color(r, g, b, w)
        for i in range(LED_COUNT):
            self._strip.setPixelColor(i, color)
        self._strip.show()

    def _idle_frame(self, shift):
        for i in range(LED_COUNT):
            self._strip.setPixelColor(i, self._palette[(i + shift) % LED_COUNT])
        self._strip.show()

    def _flash_white(self):
        for _ in range(FLASH_COUNT):
            if self._stop_event.is_set():
                return
            self._fill(0, 0, 0, 255)
            if self._stop_event.wait(FLASH_ON):
                return
            self._fill(0, 0, 0, 0)
            if self._stop_event.wait(FLASH_OFF):
                return
