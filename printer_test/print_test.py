"""Print a test receipt on a USB ESC/POS thermal printer.

Usage:
  .venv/bin/python print_test.py                 # auto-detect the printer
  .venv/bin/python print_test.py --list          # show all USB devices
  .venv/bin/python print_test.py --vid 0x0416 --pid 0x5011
  .venv/bin/python print_test.py --image photo.jpg   # print an image instead
  .venv/bin/python print_test.py --webcam            # snap a webcam photo and print it
  .venv/bin/python print_test.py --webcam --preview  # show what would print, don't print
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import usb.core
import usb.util
from escpos.printer import Usb
from PIL import Image, ImageOps

USB_CLASS_PRINTER = 0x07

# Printable width in dots: 576 for 80mm paper, 384 for 58mm.
PRINT_WIDTH_PX = 576

CAPTURE_DIR = Path(__file__).parent / "captures"

# Vendor IDs commonly found on generic ESC/POS printers, used when the
# device doesn't advertise the USB printer class.
KNOWN_POS_VENDORS = {
  0x0416: "Winbond (generic POS-58/80)",
  0x04B8: "Epson",
  0x0519: "Star Micronics",
  0x0483: "STMicroelectronics (generic)",
  0x0FE6: "ICS Advent (generic)",
  0x1504: "Bixolon",
  0x154F: "SNBC",
  0x1FC9: "NXP (generic)",
  0x28E9: "GigaDevice (generic)",
  0x6868: "Generic POS",
}


def describe(dev):
  try:
    name = f"{usb.util.get_string(dev, dev.iManufacturer) or ''} {usb.util.get_string(dev, dev.iProduct) or ''}".strip()
  except (usb.core.USBError, ValueError, NotImplementedError):
    name = ""
  return f"{dev.idVendor:#06x}:{dev.idProduct:#06x}  {name or '(name unavailable)'}"


def printer_interface(dev):
  """Return the printer-class interface, or None."""
  for cfg in dev:
    for intf in cfg:
      if intf.bInterfaceClass == USB_CLASS_PRINTER:
        return intf
  return None


def find_printer(vid=None, pid=None):
  if vid is not None and pid is not None:
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
      sys.exit(f"No USB device found with {vid:#06x}:{pid:#06x}. Run with --list to see what's connected.")
    return dev

  devices = list(usb.core.find(find_all=True))
  for dev in devices:
    if printer_interface(dev) is not None:
      return dev
  for dev in devices:
    if dev.idVendor in KNOWN_POS_VENDORS:
      return dev

  print("Couldn't auto-detect a printer. Connected USB devices:")
  for dev in devices:
    print("  " + describe(dev))
  sys.exit("Plug in / power on the printer, or pass --vid and --pid explicitly.")


def find_endpoints(dev):
  """Find the bulk OUT (and IN, if any) endpoint addresses."""
  intf = printer_interface(dev) or dev.get_active_configuration()[(0, 0)]
  out_ep = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT,
  )
  in_ep = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN,
  )
  if out_ep is None:
    sys.exit("Printer has no OUT endpoint; can't send data to it.")
  # Some printers are write-only; the library still wants an IN address.
  return out_ep.bEndpointAddress, (in_ep.bEndpointAddress if in_ep else 0x82)


def print_test(p):
  p.set(align="center", bold=True, double_height=True, double_width=True)
  p.text("HELLO!\n")
  p.set(align="center", normal_textsize=True)
  p.text("ESC/POS test print\n")
  p.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
  p.text("-" * 32 + "\n")

  p.set(align="left")
  p.text("Normal text\n")
  p.set(bold=True)
  p.text("Bold text\n")
  p.set(bold=False, underline=1)
  p.text("Underlined text\n")
  p.set(underline=0, invert=True)
  p.text(" Inverted text \n")
  p.set(invert=False)
  p.text("-" * 32 + "\n")


def capture_webcam(index=0, countdown=3):
  """Grab one frame from the webcam as a PIL image, after a countdown."""
  cam = cv2.VideoCapture(index)
  if not cam.isOpened():
    sys.exit(
      f"Couldn't open camera {index}. Allow camera access for your terminal / VS Code in "
      "System Settings > Privacy & Security > Camera, then try again."
    )
  try:
    # Keep reading frames while waiting so auto-exposure settles and the
    # final frame is fresh rather than one sitting in the buffer.
    for n in range(countdown, -1, -1):
      if n:
        print(f"{n}...", flush=True)
      end = time.monotonic() + (1 if n else 0.5)
      while time.monotonic() < end:
        cam.read()
    ok, frame = cam.read()
  finally:
    cam.release()
  if not ok:
    sys.exit("Camera opened but returned no image; camera permission may be denied.")
  print("Snap!")
  photo = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
  # Center-crop to a square.
  side = min(photo.size)
  return ImageOps.fit(photo, (side, side))


def prepare_image(source, width=PRINT_WIDTH_PX):
  """Load an image (path or PIL image), fit it to the paper width, dither to 1-bit and center it."""
  img = source if isinstance(source, Image.Image) else Image.open(source)
  img = ImageOps.exif_transpose(img).convert("RGBA")
  # Flatten transparency onto white so transparent areas don't print black.
  img = Image.alpha_composite(Image.new("RGBA", img.size, "white"), img).convert("L")
  # Stretch the tonal range; thermal prints look washed out otherwise.
  img = ImageOps.autocontrast(img, cutoff=1)
  if img.width > width:
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
  img = img.convert("1")  # Floyd-Steinberg dithering
  canvas = Image.new("1", (width, img.height), 1)
  canvas.paste(img, ((width - img.width) // 2, 0))
  return canvas


def print_image(p, source):
  p.image(prepare_image(source))


def preview_image(source):
  """Save the print-ready (dithered) image and open it instead of printing."""
  CAPTURE_DIR.mkdir(exist_ok=True)
  path = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-preview.png"
  prepare_image(source).save(path)
  print(f"Saved preview {path}")
  subprocess.run(["open", path])


def take_photo(args):
  photo = capture_webcam(args.camera, args.countdown)
  CAPTURE_DIR.mkdir(exist_ok=True)
  saved = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jpg"
  photo.save(saved)
  print(f"Saved {saved}")
  return photo


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--vid", type=lambda s: int(s, 0), help="USB vendor ID, e.g. 0x0416")
  parser.add_argument("--pid", type=lambda s: int(s, 0), help="USB product ID, e.g. 0x5011")
  parser.add_argument("--list", action="store_true", help="list connected USB devices and exit")
  source = parser.add_mutually_exclusive_group()
  source.add_argument("--image", help="print this image file instead of the test receipt")
  source.add_argument("--webcam", action="store_true", help="take a webcam photo and print it")
  parser.add_argument("--camera", type=int, default=0, help="webcam index (default 0)")
  parser.add_argument("--countdown", type=int, default=3, help="seconds before the photo is taken (default 3)")
  parser.add_argument("--preview", action="store_true", help="open the print-ready image instead of printing")
  args = parser.parse_args()

  if args.preview:
    if not (args.webcam or args.image):
      parser.error("--preview needs --image or --webcam")
    preview_image(take_photo(args) if args.webcam else args.image)
    return

  if args.list:
    for dev in usb.core.find(find_all=True):
      tag = "  <- printer class" if printer_interface(dev) else ""
      print(describe(dev) + tag)
    return

  dev = find_printer(args.vid, args.pid)
  out_ep, in_ep = find_endpoints(dev)
  print(f"Using {describe(dev)}  (out_ep={out_ep:#04x}, in_ep={in_ep:#04x})")

  p = Usb(dev.idVendor, dev.idProduct, out_ep=out_ep, in_ep=in_ep)
  # The default profile doesn't know the paper width; without it, image() warns.
  p.profile.profile_data["media"]["width"]["pixels"] = PRINT_WIDTH_PX
  try:
    if args.webcam:
      print_image(p, take_photo(args))
    elif args.image:
      print_image(p, args.image)
    else:
      print_test(p)
    # Feed only as far as the cutter (GS V 66 0), not the library's default 6 lines.
    p.cut(feed=False)
  finally:
    p.close()
  print("Sent to printer.")


if __name__ == "__main__":
  main()
