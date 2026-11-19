import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
import usb.core
from escpos.exceptions import DeviceNotFoundError
from PIL import Image
from src.constants import PRINT_WIDTH_PX, PRINTER_TIMEOUT_MS
from src.receipt_printer import ReceiptPrinter, _find_endpoints


class FakeInterface(list):
  """A USB interface: a list of endpoints with the given addresses."""

  def __init__(self, interface_class, *addresses):
    super().__init__(SimpleNamespace(bEndpointAddress=address) for address in addresses)
    self.bInterfaceClass = interface_class


class FakeDevice(list):
  """A USB device with one configuration holding the given interfaces."""

  def __init__(self, *interfaces):
    super().__init__([list(interfaces)])

  def get_active_configuration(self):
    return {(0, 0): self[0][0]}


@pytest.fixture
def device():
  # Printer class interface with OUT endpoint 0x03 and IN endpoint 0x81.
  return FakeDevice(FakeInterface(0x07, 0x03, 0x81))


@pytest.fixture
def mock_usb(monkeypatch, device):
  find = Mock(return_value=device)
  dispose = Mock()
  printer = MagicMock()
  usb_class = Mock(return_value=printer)

  monkeypatch.setattr("src.receipt_printer.usb.core.find", find)
  monkeypatch.setattr("src.receipt_printer.usb.util.dispose_resources", dispose)
  monkeypatch.setattr("src.receipt_printer.Usb", usb_class)

  return SimpleNamespace(find=find, dispose=dispose, usb_class=usb_class, printer=printer)


@pytest.fixture
def receipt_printer():
  return ReceiptPrinter(0x0416, 0x5011)


@pytest.fixture
def photo(tmp_path):
  path = tmp_path / "photo.jpg"
  Image.radial_gradient("L").resize((800, 600)).convert("RGB").save(path)
  return path


def test_print_image(receipt_printer, mock_usb, device, photo):
  assert receipt_printer.print_image(photo) is True

  mock_usb.find.assert_called_once_with(idVendor=0x0416, idProduct=0x5011, backend=None)
  mock_usb.dispose.assert_called_once_with(device)
  mock_usb.usb_class.assert_called_once_with(
    0x0416, 0x5011,
    usb_args={"backend": None},
    timeout=PRINTER_TIMEOUT_MS,
    out_ep=0x03,
    in_ep=0x81,
  )

  printed = mock_usb.printer.image.call_args.args[0]
  assert printed.mode == "1"
  assert printed.width == PRINT_WIDTH_PX
  assert printed.height == 432  # 600 * 576 / 800

  mock_usb.printer.cut.assert_called_once_with(feed=False)
  mock_usb.printer.close.assert_called_once()


def test_print_image_accepts_pil_image(receipt_printer, mock_usb, photo):
  assert receipt_printer.print_image(Image.open(photo)) is True
  mock_usb.printer.image.assert_called_once()


def test_print_text(receipt_printer, mock_usb):
  assert receipt_printer.print_text("hello") is True

  mock_usb.printer.text.assert_called_once_with("hello\n")
  mock_usb.printer.cut.assert_called_once_with(feed=False)
  mock_usb.printer.close.assert_called_once()


def test_print_text_keeps_existing_newline(receipt_printer, mock_usb):
  receipt_printer.print_text("hello\n")

  mock_usb.printer.text.assert_called_once_with("hello\n")


def test_printer_not_found(receipt_printer, mock_usb, photo, caplog):
  mock_usb.find.return_value = None

  with caplog.at_level(logging.ERROR):
    assert receipt_printer.print_image(photo) is False

  mock_usb.usb_class.assert_not_called()
  assert "0416:5011 not found" in caplog.text


@pytest.mark.parametrize(
  "error",
  [
    usb.core.USBError("Resource busy"),
    usb.core.USBTimeoutError("Operation timed out"),
    DeviceNotFoundError("Unable to open USB printer"),
  ],
)
def test_print_error_closes_connection(receipt_printer, mock_usb, photo, caplog, error):
  mock_usb.printer.image.side_effect = error

  with caplog.at_level(logging.ERROR):
    assert receipt_printer.print_image(photo) is False

  mock_usb.printer.cut.assert_not_called()
  mock_usb.printer.close.assert_called_once()
  assert "Printing failed" in caplog.text


def test_no_usb_backend(receipt_printer, mock_usb, caplog):
  mock_usb.find.side_effect = usb.core.NoBackendError("No backend available")

  with caplog.at_level(logging.ERROR):
    assert receipt_printer.print_text("hello") is False

  assert "No USB library" in caplog.text


@pytest.mark.parametrize("contents", [None, b"not a jpeg"])
def test_unreadable_image(receipt_printer, mock_usb, tmp_path, caplog, contents):
  path = tmp_path / "photo.jpg"
  if contents is not None:
    path.write_bytes(contents)

  with caplog.at_level(logging.ERROR):
    assert receipt_printer.print_image(path) is False

  mock_usb.find.assert_not_called()
  assert "Could not read image" in caplog.text


def test_endpoints_fall_back_to_first_interface():
  device = FakeDevice(FakeInterface(0xFF, 0x02))

  assert _find_endpoints(device) == (0x02, 0x82)


def test_endpoints_require_out_endpoint():
  device = FakeDevice(FakeInterface(0x07, 0x81))

  with pytest.raises(usb.core.USBError):
    _find_endpoints(device)
