"""Turn a photo into a black and white image for the thermal printer.

Pipeline: photo -> resize -> grayscale -> exposure correction -> dither -> result

Usage:
  .venv/bin/python photo_processing.py INPUT OUTPUT [floyd-steinberg|atkinson|random] [--pixel-size N]
"""

import argparse
from math import ceil

import numpy as np
from PIL import Image, ImageOps

# Printable width in dots: 576 for 80mm paper, 384 for 58mm.
# Keep in sync with PRINT_WIDTH_PX in print_test.py.
PRINT_WIDTH_PX = 576

# Exposure targets on the 0-255 scale. Every photo is shifted and scaled so
# its average brightness and contrast (standard deviation) match these.
# The mean sits well above mid-gray (128) because printed dots spread and
# come out darker than the file: 128 gave ~50% black dots but printed ~70% dark.
# 180 gives ~31% black dots. Raise it to print lighter, lower it for darker.
TARGET_MEAN = 180
TARGET_STD = 64
# Caps the contrast boost, so a near-black or flat photo comes out dim
# instead of turning into amplified sensor noise.
MAX_GAIN = 4.0

# Dither grid size: each dithered pixel prints as an N x N block of dots.
DITHER_PIXEL_SIZE = 2

# Error diffusion kernels as (dx, dy, weight) offsets from the current pixel.
# Each pixel's rounding error is pushed onto neighbors not yet visited.
KERNELS = {
  # Spreads all of the error: smooth gradients, the standard choice.
  "floyd-steinberg": [
    (1, 0, 7 / 16),
    (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16),
  ],
  # Spreads only 6/8 of the error: punchier contrast and cleaner highlights,
  # which tends to suit thermal paper.
  "atkinson": [
    (1, 0, 1 / 8), (2, 0, 1 / 8),
    (-1, 1, 1 / 8), (0, 1, 1 / 8), (1, 1, 1 / 8),
    (0, 2, 1 / 8),
  ],
}

# Every dither method: the error diffusion kernels above, plus "random", where
# each pixel is black with a probability set by how dark it is. Random gives a
# film-grain look with no patterns, but loses more fine detail.
METHODS = [*KERNELS, "random"]


def resize_to_width(photo, width=PRINT_WIDTH_PX):
  """Load a photo (file path or PIL image) and scale it to the print width.

  The EXIF rotation is applied first so the width is measured on the photo as
  it should be viewed. The aspect ratio is kept, and small photos are scaled
  up so every print fills the paper.
  """
  img = photo if isinstance(photo, Image.Image) else Image.open(photo)
  img = ImageOps.exif_transpose(img)
  height = max(1, round(img.height * width / img.width))
  return img.resize((width, height), Image.LANCZOS)


def to_grayscale(img):
  """Convert an image to grayscale (mode "L")."""
  return img.convert("L")


def correct_exposure(gray, target_mean=TARGET_MEAN, target_std=TARGET_STD):
  """Return a grayscale image whose average brightness and contrast match the targets.

  Pixels are shifted so the mean lands on target_mean, then spread out (or
  squeezed) around it so the standard deviation lands on target_std.
  Values pushed past black or white are clipped.
  """
  pixels = np.asarray(gray, dtype=np.float32)
  mean, std = pixels.mean(), pixels.std()
  gain = min(target_std / std, MAX_GAIN) if std > 0 else 1.0
  corrected = (pixels - mean) * gain + target_mean
  return Image.fromarray(np.clip(corrected, 0, 255).round().astype(np.uint8))


def dither(gray, method="floyd-steinberg", pixel_size=DITHER_PIXEL_SIZE):
  """Return a black and white (mode "1") dithered copy of a grayscale image.

  method is one of METHODS: an error diffusion kernel name or "random".
  pixel_size sets the dither grid: each dithered pixel prints as a
  pixel_size x pixel_size block of dots. 1 dithers every dot; larger values
  give a coarser, bolder pattern. The output is the same size as the input.
  """
  if pixel_size < 1:
    raise ValueError("pixel_size must be at least 1")
  # Average each block down to a single pixel; it gets scaled back up below.
  small = gray.resize(
    (ceil(gray.width / pixel_size), ceil(gray.height / pixel_size)), Image.BOX
  )
  pixels = np.asarray(small, dtype=np.float32)
  if method == "random":
    out = random_threshold(pixels)
  else:
    out = error_diffusion(pixels, KERNELS[method])

  # Blow each dithered pixel up into a solid block, trimmed to the input size.
  blocks = out.repeat(pixel_size, axis=0).repeat(pixel_size, axis=1)
  return Image.fromarray(blocks[:gray.height, :gray.width])


def random_threshold(pixels):
  """Make each pixel black with probability 1 - brightness / 255. Returns True for white.

  A pixel at brightness 64 comes out black 75% of the time, so every area
  keeps its average tone, but as random grain instead of an even pattern.
  """
  return pixels > np.random.default_rng().uniform(0, 255, pixels.shape)


def error_diffusion(pixels, kernel):
  """Round each pixel to black or white, pushing the rounding error onto its
  neighbors as weighted by kernel. Returns True for white.
  """
  same_row = [(dx, w) for dx, dy, w in kernel if dy == 0]
  later_rows = [(dx, dy, w) for dx, dy, w in kernel if dy > 0]

  # Pad the sides and bottom so error pushed off the edge lands in unused cells.
  height, width = pixels.shape
  pad = max(abs(dx) for dx, _, _ in kernel)
  extra_rows = max(dy for _, dy, _ in kernel)
  buf = np.zeros((height + extra_rows, width + 2 * pad), dtype=np.float32)
  buf[:height, pad:pad + width] = pixels
  out = np.empty((height, width), dtype=bool)

  for y in range(height):
    # The left-to-right pass is inherently sequential, so it runs on a plain
    # list (much faster than indexing numpy one element at a time).
    row = buf[y].tolist()
    errors = [0.0] * len(row)
    for x in range(pad, pad + width):
      old = row[x]
      new = 255.0 if old >= 128 else 0.0
      row[x] = new
      error = errors[x] = old - new
      for dx, w in same_row:
        row[x + dx] += error * w
    out[y] = np.array(row[pad:pad + width]) > 0
    # Error for the rows below can be added for the whole row at once.
    errors = np.array(errors, dtype=np.float32)
    for dx, dy, w in later_rows:
      buf[y + dy] += np.roll(errors, dx) * w
  return out


def process_photo(
  photo, method="floyd-steinberg", width=PRINT_WIDTH_PX, pixel_size=DITHER_PIXEL_SIZE
):
  """Run the full pipeline: photo -> resize -> grayscale -> exposure correction -> dither."""
  resized = resize_to_width(photo, width)
  gray = to_grayscale(resized)
  exposed = correct_exposure(gray)
  return dither(exposed, method, pixel_size)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Turn a photo into a print-ready black and white image.")
  parser.add_argument("input", help="photo to process")
  parser.add_argument("output", help="where to save the result, e.g. out.png")
  parser.add_argument("method", nargs="?", default="floyd-steinberg", choices=METHODS)
  parser.add_argument(
    "--pixel-size", type=int, default=DITHER_PIXEL_SIZE,
    help=f"dither grid size in dots, e.g. 2 for 2x2 blocks (default {DITHER_PIXEL_SIZE})",
  )
  args = parser.parse_args()
  process_photo(args.input, args.method, pixel_size=args.pixel_size).save(args.output)
