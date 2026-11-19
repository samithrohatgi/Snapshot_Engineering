PHOTO_DIRECTORY = "photos/"
NETWORK = "UCLA_WEB"
SYSTEM = "Pi"
BUCKET = "snapshot-photo"

LED_COUNT  = 144
LED_PIN    = 18
BRIGHTNESS = 60          # 0-255, keep low while testing

FLASH_COUNT = 3
FLASH_ON    = 0.15       # seconds white is on
FLASH_OFF   = 0.15       # seconds between flashes
FRAME_DELAY = 0.02

PRINTER_VENDOR_ID  = 0x0416   # tested POS80 thermal printer
PRINTER_PRODUCT_ID = 0x5011
PRINTER_TIMEOUT_MS = 10000    # longest one USB write may block, e.g. out of paper
PRINT_WIDTH_PX     = 576      # printable dots: 576 for 80mm paper, 384 for 58mm
