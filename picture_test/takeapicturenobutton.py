#!/usr/bin/env python3
import subprocess
from datetime import datetime
from pathlib import Path

SAVE_DIR = Path.home() / "photos"
SAVE_DIR.mkdir(exist_ok=True)

filename = SAVE_DIR / f"{datetime.now():%Y-%m-%d_%H-%M-%S}.jpg"

result = subprocess.run(
    ["rpicam-still", "-n", "-t", "2000", "-o", str(filename)],
    capture_output=True, text=True,
)

if result.returncode == 0:
    print(f"Saved {filename}")
else:
    print(f"Capture failed:\n{result.stderr.strip()}")

