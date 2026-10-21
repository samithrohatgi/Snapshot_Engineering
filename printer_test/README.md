# printer_test (coded with Claude)

Prints text, images, or webcam photos on a USB ESC/POS thermal receipt printer (tested with a generic POS80, USB ID `0416:5011`).

Supports macOS and Windows, including image previews and webcam capture.

## Setup

Run setup commands from the `printer_test` directory.

### Windows (PowerShell)

Install Python from [python.org](https://www.python.org/downloads/windows/), then run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The requirements install `libusb-package` on Windows. The script loads its bundled USB library directly from the virtual environment; Homebrew and manual PATH changes are unnecessary.

Plug in the printer, power it on, and list devices:

```powershell
.\.venv\Scripts\python.exe print_test.py --list
```

If the printer cannot be accessed, use [Zadig](https://zadig.akeo.ie/) to install WinUSB for the printer: choose **Options > List All Devices**, select the printer (the tested model has USB ID `0416:5011`), select **WinUSB**, and install or replace the driver. Verify the selected device before replacing its driver. This may affect printing through the normal Windows print queue.

Print a test receipt:

```powershell
.\.venv\Scripts\python.exe print_test.py
```

For the usage examples below, replace `.venv/bin/python` with `.\.venv\Scripts\python.exe` on Windows.

### macOS

```sh
brew install libusb
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Plug in the printer, power it on, and check it shows up:

```sh
.venv/bin/python print_test.py --list
```

The printer should be marked `<- printer class`.

## Usage

```sh
# Print a test receipt
.venv/bin/python print_test.py

# Print an image file
.venv/bin/python print_test.py --image photo.jpg

# Take a webcam photo (3 second countdown) and print it
.venv/bin/python print_test.py --webcam

# Preview what would print, without printing
.venv/bin/python print_test.py --webcam --preview
.venv/bin/python print_test.py --image photo.jpg --preview
```

| Option | Description |
|---|---|
| `--list` | List connected USB devices and exit |
| `--image FILE` | Print an image file |
| `--webcam` | Take a webcam photo and print it |
| `--preview` | Open the print-ready image instead of printing (needs `--image` or `--webcam`) |
| `--camera N` | Webcam index, default `0` (try `1` for an external or iPhone camera) |
| `--countdown N` | Seconds before the webcam photo is taken, default `3` |
| `--vid`, `--pid` | Use a specific printer if auto-detection picks the wrong device, e.g. `--vid 0x0416 --pid 0x5011` |

Images are scaled to the paper width (576 dots for 80mm paper), contrast-boosted, and dithered to black and white. Webcam photos are center-cropped to a square. Webcam photos and previews are saved to `captures/`.

Previews open in the default image viewer on either OS and do not require a connected printer or USB backend.

For 58mm paper, set `PRINT_WIDTH_PX = 384` in `print_test.py`.

## Troubleshooting

- **`NoBackendError: No backend available` on Windows:** install the requirements using the same virtual environment's Python and use the updated script, which explicitly loads the bundled libusb backend. Installing a device driver alone does not fix library discovery.
- **Printer not listed:** make sure it's powered from its own supply, the cable carries data, and you allowed the accessory to connect if macOS asked.
- **Paper feeds but prints blank:** the paper roll is upside down. Scratch it with a fingernail; the side that darkens must face the print head.
- **"Access denied" / "resource busy":** remove the printer from System Settings > Printers if macOS added it.
- **Camera won't open:** on macOS, allow camera access for your terminal or VS Code in System Settings > Privacy & Security > Camera. On Windows, enable camera access and access for desktop apps in Settings > Privacy & security > Camera (Privacy > Camera on Windows 10).
- **Images print garbled:** in `print_image`, try `p.image(..., impl="bitImageColumn")` or `impl="graphics"`.
