# Printer test engineering handoff

Prepared October 21, 2026. Read alongside [print_test.py](print_test.py), [requirements.txt](requirements.txt), and the [README](README.md).

This guide explains the current printer test so you can run, debug, and change it yourself. It covers the Python environment, the USB connection, every function in the script, image processing, platform differences, and the fixes made during setup.

The Windows setup successfully sent a test receipt to the POS80 printer. Physical macOS printing and actual webcam capture still need testing. A successful USB write does not establish what appeared on paper.

## Contents

1. [What the project contains](#what-the-project-contains)
2. [How printing reaches the hardware](#how-printing-reaches-the-hardware)
3. [The Python environment](#the-python-environment)
4. [Running the program](#running-the-program)
5. [How Python starts the script](#how-python-starts-the-script)
6. [Command line parsing and main](#command-line-parsing-and-main)
7. [Understanding USB discovery](#understanding-usb-discovery)
8. [Connection ownership and printing](#connection-ownership-and-printing)
9. [The test receipt](#the-test-receipt)
10. [The image processing pipeline](#the-image-processing-pipeline)
11. [Webcam capture and saved files](#webcam-capture-and-saved-files)
12. [Windows and macOS differences](#windows-and-macos-differences)
13. [What broke and why the fixes work](#what-broke-and-why-the-fixes-work)
14. [Debugging without guessing](#debugging-without-guessing)
15. [Known assumptions and testing gaps](#known-assumptions-and-testing-gaps)
16. [Making changes you understand](#making-changes-you-understand)
17. [Reference material](#reference-material)

## What the project contains

This is a command line hardware test. It can print a sample receipt, print an image, or capture and print one webcam photo. It can also save and open a preview without printing.

| File or directory | Responsibility |
|---|---|
| `print_test.py` | All application logic and command line handling |
| `requirements.txt` | Python package versions and a Windows dependency condition |
| `README.md` | Setup instructions and command examples |
| `.venv/` | Local Python interpreter environment and installed packages |
| `captures/` | Generated webcam photos and prepared previews |
| `.gitignore` | Excludes generated captures; the repository also ignores virtual environments and Python caches |

The tested device is a generic POS80 with USB vendor ID `0416` and product ID `5011`. Its detected endpoints were OUT `0x01` and IN `0x81`. The script assumes a printable width of 576 dots for this printer.

The Python environment used successfully on Windows was Python 3.14.5, 64 bit. The requirements file does not select or install that Python version.

## How printing reaches the hardware

```text
Your script
  chooses content, formatting, and image preparation
    |
python-escpos
  turns printing operations into ESC/POS command bytes
    |
PyUSB
  exposes USB discovery and communication to Python
    |
libusb
  implements native USB operations using the operating system
    |
Windows WinUSB driver or the macOS USB system
    |
Physical printer
```

ESC/POS is a printer command language. Some transmitted bytes represent text; others change formatting, carry image dots, feed paper, or request a cut. USB provides the transport. A device having a USB connector does not prove that it understands ESC/POS.

The program uses a direct USB connection. It does not send a document through the normal Windows or macOS print queue.

| Package | Python import | Role in this project |
|---|---|---|
| `python-escpos` | `escpos` | Printer commands and USB printer abstraction |
| `pyusb` | `usb.core`, `usb.util` | USB devices, descriptors, and resource management |
| `libusb-package` | `libusb_package` | Bundled native USB library used on Windows |
| `pillow` | `PIL.Image`, `PIL.ImageOps` | Image loading, transformation, and saving |
| `opencv-python` | `cv2` | Camera access and color conversion |
| `numpy` | Used through OpenCV here | Pixel arrays returned by the camera |

Other requirements support these packages. For example, installing `qrcode` and `python-barcode` does not mean this script currently contains barcode or QR printing features. This requirements file includes supporting packages as well as direct dependencies.

## The Python environment

A virtual environment gives this project a separate set of Python packages. It is not a virtual machine and does not isolate Windows drivers or USB permissions.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Read that command as follows:

- `.\.venv\Scripts\python.exe` selects the project's Python executable.
- `-m pip` asks that Python to run the `pip` module.
- `install -r requirements.txt` installs the requirements listed in the file.

Using the same explicit Python path for installation and execution avoids installing into one Python environment and running another. Activation is optional with these commands. Activation mainly changes which executable a short command such as `python` resolves to.

`pyusb==1.3.1` pins a particular package version. This line adds a platform condition:

```text
libusb-package==1.0.30.0; sys_platform == "win32"
```

It installs that package only on Windows. Python calls the Windows platform `win32` even on 64 bit Windows.

Recreate virtual environments on each computer and operating system. Do not copy the Windows `.venv` to a Mac. Keep your own source code outside `.venv`; the environment should be replaceable from the requirements. Exact package pins do not fully specify the Python interpreter or every platform-dependent transitive dependency.

### Fresh Windows setup

From the repository root, with Python installed:

```powershell
cd printer_test
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On this Windows computer, WinUSB was already installed for the POS80 during setup. Rebuilding `.venv` does not reinstall or remove that driver. A different Windows computer may still need driver setup through Zadig; follow the README and verify the exact USB device before replacing its driver.

No manual PATH adjustment is required by the updated script.

### Fresh macOS setup

From the repository root, with Python and Homebrew available:

```sh
cd printer_test
brew install libusb
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The macOS code relies on PyUSB discovering an accessible native USB backend. Homebrew is the installation route documented here; it is not part of the printing protocol itself.

## Running the program

Run the following commands from `printer_test` in PowerShell. On macOS, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

```powershell
# Show available options without accessing hardware
.\.venv\Scripts\python.exe print_test.py --help

# List connected USB devices without printing
.\.venv\Scripts\python.exe print_test.py --list

# Print the built-in sample receipt
.\.venv\Scripts\python.exe print_test.py

# Explicitly select the tested printer
.\.venv\Scripts\python.exe print_test.py --vid 0x0416 --pid 0x5011

# Prepare and view an image without printing
.\.venv\Scripts\python.exe print_test.py --image photo.jpg --preview

# Print an image
.\.venv\Scripts\python.exe print_test.py --image photo.jpg

# Capture a webcam photo and preview it
.\.venv\Scripts\python.exe print_test.py --webcam --preview

# Capture and print using camera index 1 and a five second countdown
.\.venv\Scripts\python.exe print_test.py --webcam --camera 1 --countdown 5
```

Input image paths are relative to the terminal's current directory. Quote paths containing spaces. Generated captures are saved next to the script, because `CAPTURE_DIR` is built from `Path(__file__).parent`, not from the terminal directory.

## How Python starts the script

Python executes the imports and constant assignments, then defines the functions. Defining a function does not execute its body. At the bottom:

```python
if __name__ == "__main__":
  main()
```

Running this file directly causes Python to call `main()`. Importing it from another module defines the functions without automatically starting the command line workflow. Its top-level imports still execute.

The standard library imports provide these tools:

| Import | Use |
|---|---|
| `argparse` | Parse terminal options and generate help |
| `os` | Open previews through Windows file associations |
| `subprocess` | Launch the macOS or Linux image opener |
| `sys` | Inspect the platform, identify the interpreter, and exit with a message |
| `time` | Measure countdown intervals |
| `datetime` | Receipt timestamps and capture filenames |
| `pathlib.Path` | Build and manipulate filesystem paths |

`USB_CLASS_PRINTER = 0x07` is the standard USB interface class used to recognize printers. `PRINT_WIDTH_PX = 576` is an application assumption about this printer's printable width. These constants describe different things: an interface type and an image width.

## Command line parsing and main

`main()` constructs an `ArgumentParser` and calls `parse_args()`. Its `description=__doc__` uses the file's opening docstring as help text.

| Option | Parsed value and meaning |
|---|---|
| `--vid` | Vendor ID integer; absent by default |
| `--pid` | Product ID integer; absent by default |
| `--list` | Boolean flag to list USB devices |
| `--image FILE` | Image path string; absent by default |
| `--webcam` | Boolean flag to capture a photo |
| `--camera N` | Integer camera index; default `0` |
| `--countdown N` | Integer countdown; default `3` |
| `--preview` | Boolean flag to save and open prepared content |

`action="store_true"` makes a switch Boolean. `type=int` converts a supplied string to an integer. The mutually exclusive group prevents `--image` and `--webcam` from being supplied together.

The ID parser uses `lambda s: int(s, 0)`: a small anonymous function that allows prefixes such as `0x` for hexadecimal numbers. Hexadecimal uses digits `0` through `9` and letters `A` through `F`; `0x0416` is a numeric value, not a filename or string identifier once parsed.

The branches execute in this order:

```text
Parse arguments
    |
    +-- --preview
    |     Require --image or --webcam
    |     Load image or take photo
    |     Save and open prepared preview
    |     Return
    |
    +-- Load USB backend
    |
    +-- --list
    |     Enumerate and describe devices
    |     Return
    |
    +-- Find printer and endpoint addresses
          Describe the selected printer
          Release discovery's USB connection
          Construct ESC/POS printer object
          Choose webcam, image, or sample receipt
          Request a paper cut
          Close the printing connection
```

Preview runs before USB initialization, so it does not need a connected printer or a native USB backend. It still needs the Python packages because their imports occur at startup. `return` exits the current function and prevents later steps from running.

Some combinations are not rejected: `--preview` takes precedence over `--list`; otherwise `--list` returns before printing. Supply both `--vid` and `--pid` together. Supplying only one currently falls back to automatic detection.

## Understanding USB discovery

A USB device provides structured descriptors:

```text
Device
  Configuration
    Interface
      Endpoint
```

A configuration describes an operating arrangement. An interface describes a function the device exposes. An endpoint is an address used for data transfer. A device can expose multiple interfaces, such as a camera with additional functions.

VID and PID identify the vendor and product type. They do not necessarily identify one unique physical unit. This script does not select by serial number.

### get_usb_backend

On Windows, `get_usb_backend()` imports `libusb_package` and asks it for a libusb backend. A backend is the implementation PyUSB uses to perform USB operations. Loading it explicitly avoids relying on a system DLL search.

The function exits with an explanatory message if the Windows package is missing or its native library cannot load. On other systems it returns `None`, which tells PyUSB to perform its normal backend discovery. Here, `None` is an API instruction to use automatic selection, not a usable USB implementation by itself.

The same selected backend is passed to device discovery and to the ESC/POS object through `usb_args`. Successful discovery would not be enough if the printing library subsequently searched using a different backend configuration.

### printer_interface

`printer_interface(dev)` loops over configurations and interfaces. It returns the first interface whose `bInterfaceClass` equals `0x07`, or `None` if no such interface exists.

Returning an interface gives later code access to its endpoint descriptors. The function does not send a receipt or prove ESC/POS compatibility.

### find_printer

With both IDs supplied, `find_printer()` asks PyUSB for a matching device and exits if none is found.

Without both IDs, it enumerates devices and selects:

1. The first device exposing a printer interface.
2. Otherwise, the first device whose vendor appears in `KNOWN_POS_VENDORS`.

The dictionary's descriptive strings are there for readability; selection uses membership of its numeric keys. The vendor fallback is a heuristic. Another product from a listed vendor may not be a receipt printer.

If no candidate is found, the function prints the connected devices and exits. Automatic detection can choose the wrong device when several candidates are attached.

### find_endpoints

`find_endpoints(dev)` uses the printer interface, or falls back to interface `0`, alternate setting `0` in the active configuration.

`custom_match=lambda e: ...` passes a small predicate to the descriptor search. It tests each endpoint's direction. OUT means computer to device; IN means device to computer.

The function returns two integers: the OUT and IN endpoint addresses. This is tuple unpacking in `main()`:

```python
out_ep, in_ep = find_endpoints(dev)
```

It exits if no OUT endpoint exists. If no IN endpoint exists, it returns `0x82` as a fallback because the library still accepts an IN address. That fallback does not create an endpoint or establish that reads will work.

Despite the function's bulk-endpoint docstring, its matching expressions currently check direction only, not transfer type. Different hardware may need more precise selection.

### describe

`describe(dev)` reads manufacturer and product strings, strips unnecessary whitespace, and returns a display label. Its exception handler allows the program to show IDs even when readable names cannot be obtained.

In the formatted string, `#06x` means hexadecimal output with a `0x` prefix and a minimum total width of six characters. For example, the vendor is shown as `0x0416`.

Reading these strings can open a real USB handle. That side effect is central to the Windows connection fix described below.

## Connection ownership and printing

`dev` is a PyUSB device object used for discovery and descriptors. `p` is an ESC/POS printer object offering methods such as `text()`, `image()`, and `cut()`. They represent different abstraction levels, and the library creates its own PyUSB device connection.

The script releases discovery resources after displaying the printer name:

```python
usb.util.dispose_resources(dev)
```

A handle is the operating system's reference to an open resource. This call releases the discovery connection; it does not erase the Python object, uninstall the device, or unplug the cable. Its vendor and product attributes are still used to construct `p`.

The installed ESC/POS library opens the physical connection lazily. Constructing `Usb(...)` creates the object, but the first operation needing its device can trigger USB opening. This explains why an opening failure can appear beneath a call to `p.set()` in a traceback.

```python
p = Usb(
  dev.idVendor,
  dev.idProduct,
  usb_args={"backend": backend},
  out_ep=out_ep,
  in_ep=in_ep,
)
```

The profile assignment that follows tells the library the printable pixel width:

```python
p.profile.profile_data["media"]["width"]["pixels"] = PRINT_WIDTH_PX
```

This updates a nested Python dictionary used by the library. It does not alter the physical print head or hardware resolution.

The actual printing operations run inside `try` with `p.close()` in `finally`. The cleanup is attempted even if printing raises an exception. Preserve this ownership pattern when changing the code.

The constructor does not override the library's USB timeout. In the installed version its default is `0`, meaning no timeout. A future change could expose a bounded timeout if hangs become a problem.

## The test receipt

`print_test(p)` sends formatting and text commands in sequence. For example:

```python
p.set(align="center", bold=True, double_height=True, double_width=True)
p.text("HELLO!\n")
```

The first call configures text formatting; the second sends text and a newline. The receipt demonstrates alignment, text size, bold, underline, and inverted printing. The timestamp comes from the computer's local clock.

`print("Snap!")` writes to your terminal. `p.text("HELLO!\n")` writes to the printer. These are separate outputs.

The expression `"-" * 32` repeats a string to make a separator. `strftime()` formats a date as text; `%Y-%m-%d %H:%M:%S` produces a year-month-day timestamp with time.

After any actual printing mode, `main()` calls `p.cut(feed=False)`. This requests a cut without the library's usual additional feed behavior. Physical cutting and feeding depend on the printer.

The final message `Sent to printer.` means the printing path completed without an uncaught exception. The script does not inspect the paper, confirm an image looked correct, or obtain a physical completion acknowledgment.

## The image processing pipeline

`prepare_image(source, width=PRINT_WIDTH_PX)` is the shared transformation used by both printing and preview. It accepts a path or an existing Pillow image and returns a new prepared Pillow image.

| Stage | Code or operation | Reason |
|---|---|---|
| Load | Use the supplied image or `Image.open(source)` | Accept files and camera images |
| Orient | `ImageOps.exif_transpose(img)` | Apply orientation metadata from camera files |
| Preserve alpha | Convert to `RGBA` | Keep transparency available for compositing |
| Flatten | Composite over a white background | Make transparent areas print as paper white |
| Grayscale | Convert to `L` | Reduce color to brightness |
| Contrast | `autocontrast(cutoff=1)` | Stretch tones after clipping a small portion at the histogram extremes |
| Resize | Shrink to the printable width using LANCZOS | Fit the print head while preserving proportions |
| Dither | Convert to mode `1` | Represent the image using only black and white pixels |
| Center | Paste onto a white canvas of full printable width | Center narrow images |

RGBA means red, green, blue, and alpha, where alpha describes transparency. Mode `L` is grayscale. Mode `1` is one bit per pixel: black or white. Dithering approximates gray tones with patterns of black and white dots; it does not give the printer additional gray ink levels.

The new height is calculated from the width ratio:

```python
round(img.height * width / img.width)
```

For an 800 by 400 image and a width of 576, the resized image is 576 by 288. Smaller images are not enlarged. A narrow image is centered and padded with white.

The centering offset `(width - img.width) // 2` uses integer division because pixel positions must be integers. The height is not capped, so a tall image can use a long strip of paper.

The `width` default is evaluated when the function is defined. Changing `PRINT_WIDTH_PX` in the source and rerunning the program updates it. Reassigning the constant later in an already running process does not rewrite an existing function's default argument.

`print_image(p, source)` is a short wrapper: it prepares the image and hands the result to `p.image()`. The library then encodes and sends image commands.

`preview_image(source)` prepares the same bitmap, saves it as a PNG, and opens the saved file through the operating system. A preview checks the transformation, but cannot predict physical darkness, paper quality, or every printer-specific rendering detail.

## Webcam capture and saved files

`capture_webcam(index=0, countdown=3)` opens an OpenCV camera using an integer index. Index `0` is the default choice; device numbering can change, so `1` does not permanently identify one particular external camera.

If opening fails, the function releases the camera object and exits with platform-specific permission guidance.

While counting down it repeatedly reads frames so camera exposure can settle and buffers can advance. `time.monotonic()` measures elapsed time without depending on changes to the calendar clock. The `range(countdown, -1, -1)` loop includes zero, where it reads for another half-second. The actual delay therefore includes that extra time and capture overhead.

The final `cam.read()` returns a success flag and a frame, which is a pixel array. A `finally` block releases the camera before subsequent image processing. A failed final read causes an explanatory exit.

OpenCV supplies BGR color order. `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)` converts it to RGB for Pillow. `Image.fromarray(...)` creates a Pillow image. The smaller dimension determines a centered square crop through `ImageOps.fit()`.

`take_photo(args)` calls the capture function, creates `captures/` if needed, saves a timestamped JPEG, and returns the cropped color image. `mkdir(exist_ok=True)` allows repeated runs without failing because the directory already exists.

| Operation | Generated files |
|---|---|
| Print existing image | No automatic copy or prepared preview |
| Preview existing image | A prepared black and white `*-preview.png` |
| Capture and print | A cropped color `.jpg` |
| Capture and preview | A cropped color `.jpg` and a prepared `*-preview.png` |

Filenames have one-second timestamp resolution. Rapid repeated operations can reuse a filename. Saved captures remain on disk until you remove them, even though Git ignores them.

## Windows and macOS differences

| Concern | Windows | macOS |
|---|---|---|
| Python executable | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Platform string | `win32` | `darwin` |
| Native USB library | Loaded explicitly from `libusb-package` | Discovered by PyUSB; README installs libusb through Homebrew |
| Driver setup | WinUSB was installed for the tested POS80 | No Zadig step |
| Open a preview | `os.startfile(path)` | `subprocess.run(["open", path], check=True)` |
| Camera permission | Windows camera and desktop-app access settings | Camera permission for the terminal or editor |

`subprocess.run()` starts an external program. Passing a list gives separate command arguments. `check=True` raises an error if that program reports failure. The script also has an `xdg-open` branch for other systems, but that is not evidence of tested Linux support.

On Windows, `os.startfile()` requests opening through the registered file association; it does not wait for the viewer to close.

## What broke and why the fixes work

### Native library discovery

The initial error was `usb.core.NoBackendError: No backend available`. Installing PyUSB supplies Python code, but PyUSB still needs a native USB implementation.

An earlier manual lookup used `libusb_package.find_library('usb-1.0')`. In the installed Windows package this returned `None`, because the bundled filename was `libusb-1.0.dll`. Editing PATH based on that result did not fix discovery.

The script now calls `libusb_package.get_libusb1_backend()` directly on Windows and passes that backend through discovery and printing. The old PATH commands are unnecessary.

### Windows driver binding

Once the backend loaded, discovery worked but opening the printer failed with `Operation not supported or unimplemented on this platform`.

The device was bound to Microsoft's `usbprint` service, shown as USB Printing Support. The direct libusb connection needed a compatible binding. The official Zadig 2.9 executable was downloaded, its Authenticode signature verified as Akeo Consulting, and WinUSB was installed specifically for VID `0416`, PID `5011`.

The installed device-specific package was reported as `oem69.inf`, originally named `pos80_printer_usb.inf`, with a libwdi autogenerated signer for that USB ID. These are records of this computer's setup, not identifiers to hard-code into the program or assume on another machine.

Changing the driver can affect ordinary Windows print-queue use. Restoring that behavior is a Windows driver-management task. Deleting `.venv` or checking out older source code does not restore the old driver binding.

Setup files were placed in `%TEMP%\Snapshot-POS80-WinUSB`. They are not runtime dependencies. No driver installation happens automatically when you run `print_test.py`.

### Duplicate open connections

After WinUSB was installed, printing failed with access denied. Reading the printer name during discovery had opened a handle. The ESC/POS library then attempted to open a second connection.

A targeted check established that opening a second connection failed while the first was open, and succeeded after releasing the first. The fix is `usb.util.dispose_resources(dev)` between discovery and the ESC/POS connection.

After that fix, the test receipt command exited successfully and printed `Sent to printer.` in the terminal. That validates the transmission path; physical appearance still requires looking at the receipt.

### Other portability changes

Preview opening now chooses the Windows or macOS mechanism instead of always invoking macOS `open`. Camera-open failures show settings appropriate to the platform, and the unsuccessful camera object is released. The README documents setup on both operating systems.

## Debugging without guessing

Choose a command that isolates the failing part of the system:

1. Run `--help` to check startup imports and argument parsing.
2. Preview an existing image to check filesystem access and image preparation without USB or camera access.
3. Run `--webcam --preview` to add camera access without printer access.
4. Run `--list` to check USB enumeration.
5. Print a receipt with explicit VID and PID to check opening and sending.
6. Print an image to add image command encoding and printer rendering.

| Symptom | First area to investigate |
|---|---|
| `ModuleNotFoundError` | Wrong interpreter or missing Python packages |
| `NoBackendError` | Native USB library discovery/loading |
| No printer found | Power, data cable, connection, and IDs |
| Unsupported operation while opening on Windows | USB driver binding |
| Access denied or resource busy | Open handles, another application, permissions, or OS ownership |
| Camera fails | Index, permissions, or another application using it |
| Preview fails to open but PNG exists | Image viewer association or opener command |
| Good preview but poor paper output | Printer width, command compatibility, paper, and physical quality |

Listing a device proves enumeration worked. It does not prove that the device can be opened, that USB writes will work, or that the printer understands the bytes.

Read a traceback from its final exception upward. Find the last frame in your code, then trace the library calls beneath it. `DeviceNotFoundError` can wrap a USB access error even when enumeration found the printer. Read the underlying message instead of taking the outer exception name literally.

When changing dependencies, use the environment's Python. Do not edit installed files in `.venv/Lib/site-packages` as your application fix: that change disappears when the environment is rebuilt and is not represented in the project's source.

## Known assumptions and testing gaps

### Evidence from this session

- Windows USB enumeration detected the POS80.
- WinUSB installation was confirmed for the target device.
- The duplicate-connection failure and the effect of releasing the first handle were reproduced.
- Receipt transmission succeeded after the cleanup fix.
- Temporary checks exercised image preparation, preview dispatch for Windows and macOS, camera failure messages, and backend propagation into the printing flow. Viewer launches and parts of those checks were mocked.
- No permanent automated test suite was added by this work.

### Still needing hardware verification

- Physical printing on a Mac.
- Actual webcam capture through the script on each OS.
- Real preview application opening on each OS.
- Image print appearance, cutter behavior, and other printer models.

### Implementation limits to remember

- Automatic detection can choose the wrong device; identical VID/PID devices are not distinguished by serial number.
- The endpoint fallback assumes interface zero and alternate setting zero, and endpoint selection checks direction rather than transfer type.
- Printer interface classification and known vendor membership do not establish ESC/POS compatibility.
- Most runtime failures still produce raw tracebacks.
- There is no print queue, retry policy, paper-status monitoring, or physical completion check.
- The default USB timeout is unbounded.
- A single VID or PID is not rejected, and negative countdown values are not validated.
- Image height and resulting paper use are not capped.
- The paper width is a source constant rather than a command line option.
- Filenames can collide within one second.

## Making changes you understand

Before editing a function, write down its inputs, return value, side effects, and the command you will use to check it. Side effects include opening hardware, saving files, launching a viewer, and printing paper.

| Desired change | Start reading here | A useful check |
|---|---|---|
| Receipt wording or formatting | `print_test()` | Print one receipt and inspect it |
| Image size, contrast, or dithering | `prepare_image()` | Preview a known image, then compare a physical print |
| Camera choice or crop | `capture_webcam()`, `take_photo()` | Capture and preview |
| New command line option | `main()` | Check help, invalid inputs, and the affected execution branch |
| Different printer selection | `find_printer()`, `printer_interface()` | List devices and use explicit IDs |
| Connection changes | `get_usb_backend()`, `main()`, library `Usb` behavior | Check discovery, opening, cleanup, and a small receipt |

For an image change, keep a fixed input so you can compare the result. For a connection change, preserve the release of discovery resources before printing and the `finally` cleanup. Make one change at a time and distinguish what your test proves from what still needs physical inspection.

Use Git to inspect and recover changes deliberately:

```sh
git status --short
git diff -- printer_test/print_test.py printer_test/README.md printer_test/requirements.txt
```

Run these from the repository root. A diff shows uncommitted tracked changes; a clean diff does not mean a feature was never added, because it may already have been committed. Do not use destructive restore commands until you understand which local edits they would discard.

Use these questions to check your understanding before changing the USB path:

- Why does installing `pyusb` not necessarily provide a working native backend?
- Why does rebuilding `.venv` leave the Windows device driver unchanged?
- Why can `--list` succeed while printing fails?
- What are the differences between `dev`, `backend`, and `p`?
- Why is the discovery handle released before constructing the printing connection?
- Which resources do `p.close()` and `cam.release()` own?
- Why can a preview run without initializing USB?
- What does `Sent to printer.` prove, and what does it leave unknown?

## Reference material

Prefer documentation matching the versions in `requirements.txt` when behavior differs from newer examples.

- [Python virtual environments](https://docs.python.org/3/library/venv.html): interpreter selection, activation, and environment recreation.
- [Python argparse](https://docs.python.org/3/library/argparse.html): flags, types, defaults, and mutually exclusive arguments.
- [Python pathlib](https://docs.python.org/3/library/pathlib.html): paths and file operations.
- [python-escpos USB printer](https://python-escpos.readthedocs.io/en/latest/user/printers.html#usb): constructor, USB arguments, opening, and cleanup.
- [PyUSB project](https://github.com/pyusb/pyusb): USB API and documentation.
- [libusb package](https://pypi.org/project/libusb-package/): bundled native library and explicit backend loading.
- [libusb on Windows](https://github.com/libusb/libusb/wiki/Windows): compatible drivers and Windows restrictions.
- [Zadig guide](https://github.com/pbatard/libwdi/wiki/Zadig): device-specific driver installation.
- [Pillow image conversion](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.convert): modes, grayscale, and dithering.

The installed library source is also available in `.venv/Lib/site-packages` on Windows. Read `escpos/printer/usb.py` to understand connection setup and `escpos/escpos.py` to understand lazy device opening and printer commands. Treat those files as reference implementations; keep application changes in this repository.
