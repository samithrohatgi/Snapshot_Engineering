"""Print photos and text on a USB ESC/POS thermal receipt printer."""

import logging
import sys

import usb.core
import usb.util
from escpos.exceptions import Error as EscposError
from escpos.printer import Usb

from .constants import (
  PRINT_WIDTH_PX,
  PRINTER_PRODUCT_ID,
  PRINTER_TIMEOUT_MS,
  PRINTER_VENDOR_ID,
)
from .photo_processing import process_photo

if sys.platform == "win32":
  import libusb_package

USB_CLASS_PRINTER = 0x07


class ReceiptPrinter:
  """Print receipts on one USB printer, cutting the paper after each one.

  Every receipt opens a fresh USB connection and closes it afterward, so the
  printer can be unplugged or power cycled between prints.
  """

  def __init__(self, vendor_id: int, product_id: int):
    self.vendor_id = vendor_id
    self.product_id = product_id
    self.logs = logging.getLogger(__name__)
    # Windows can't find libusb on its own, so use the copy bundled with
    # libusb-package. Elsewhere None lets PyUSB pick the system libusb.
    self.backend = libusb_package.get_libusb1_backend() if sys.platform == "win32" else None

  def print_image(self, image) -> bool:
    """Print a photo, given as a file path or PIL image.

    The photo is scaled to the paper width, exposure corrected and dithered
    to black and white first. Returns True once the receipt is sent.
    """
    try:
      bitmap = process_photo(image)
    except OSError:
      self.logs.exception("Could not read image %s", image)
      return False

    return self._print(lambda printer: printer.image(bitmap))

  def print_text(self, text: str) -> bool:
    """Print plain text. Returns True once the receipt is sent."""
    if not text.endswith("\n"):
      text += "\n"
    return self._print(lambda printer: printer.text(text))

  def _print(self, job) -> bool:
    """Connect to the printer, run job(printer), then cut the paper."""
    try:
      device = usb.core.find(
        idVendor=self.vendor_id, idProduct=self.product_id, backend=self.backend
      )
      if device is None:
        self.logs.error(
          "Printer %04x:%04x not found. Is it plugged in and powered on?",
          self.vendor_id, self.product_id,
        )
        return False

      out_ep, in_ep = _find_endpoints(device)
      # Finding endpoints opens a USB handle. Release it before python-escpos
      # opens its own, because WinUSB allows only one connection at a time.
      usb.util.dispose_resources(device)

      printer = Usb(
        self.vendor_id,
        self.product_id,
        usb_args={"backend": self.backend},
        timeout=PRINTER_TIMEOUT_MS,
        out_ep=out_ep,
        in_ep=in_ep,
      )
      # The default profile doesn't know the paper width; without it, image() warns.
      printer.profile.profile_data["media"]["width"]["pixels"] = PRINT_WIDTH_PX
      try:
        job(printer)
        # Feed only as far as the cutter (GS V 66 0), not the library's default 6 lines.
        printer.cut(feed=False)
      finally:
        printer.close()

    except usb.core.NoBackendError:
      self.logs.exception("No USB library found. Install libusb for this system.")
      return False

    except (usb.core.USBError, EscposError):
      self.logs.exception("Printing failed")
      return False

    return True


def _find_endpoints(device):
  """Return the printer's (OUT, IN) endpoint addresses.

  Uses the printer class interface, or interface 0 if the printer doesn't
  advertise one. Write-only printers get 0x82 for IN, since python-escpos
  still expects an address.
  """
  interface = None
  for config in device:
    for candidate in config:
      if candidate.bInterfaceClass == USB_CLASS_PRINTER:
        interface = candidate
        break
    if interface is not None:
      break
  if interface is None:
    interface = device.get_active_configuration()[(0, 0)]

  def endpoint(direction):
    return usb.util.find_descriptor(
      interface,
      custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == direction,
    )

  out_ep = endpoint(usb.util.ENDPOINT_OUT)
  in_ep = endpoint(usb.util.ENDPOINT_IN)
  if out_ep is None:
    raise usb.core.USBError("Printer has no OUT endpoint to send data to")
  return out_ep.bEndpointAddress, (in_ep.bEndpointAddress if in_ep else 0x82)


if __name__ == "__main__":
  # From photo_transfer/: python -m src.receipt_printer [PHOTO]
  # Prints PHOTO if given, otherwise a line of test text.
  printer = ReceiptPrinter(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID)
  if len(sys.argv) > 1:
    sent = printer.print_image(sys.argv[1])
  else:
    sent = printer.print_text("Snapshot printer test")
  sys.exit(0 if sent else 1)
