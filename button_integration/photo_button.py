import subprocess
from datetime import datetime
from pathlib import Path

import RPi.GPIO as GPIO

BUTTON_PIN = 10  # BOARD numbering
SAVE_DIR = Path.home() / "photos"


def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    try:
        while True:
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.RISING, bouncetime=300)
            filename = SAVE_DIR / f"{datetime.now():%Y-%m-%d_%H-%M-%S-%f}.jpg"

            result = subprocess.run(
                ["rpicam-still", "-n", "-t", "2000", "-o", str(filename)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"Saved {filename}")
            else:
                print(f"Capture failed:\n{result.stderr.strip()}")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()