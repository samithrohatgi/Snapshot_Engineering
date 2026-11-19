import time

from .batch_uploader import BatchUploader
from .constants import (
    BUCKET,
    NETWORK,
    PHOTO_DIRECTORY,
    PRINTER_PRODUCT_ID,
    PRINTER_VENDOR_ID,
    SYSTEM,
)
from .idle_lights import IdleLights
from .network_checker import NetworkChecker
from .photo_store import PhotoStore
from .photo_taker import PhotoTaker
from .receipt_printer import ReceiptPrinter

if __name__ == "__main__":

    photos = PhotoStore(PHOTO_DIRECTORY)
    poller = NetworkChecker(NETWORK, SYSTEM)
    uploader = BatchUploader(photos, BUCKET)
    camera = PhotoTaker(PHOTO_DIRECTORY)
    #printer = ReceiptPrinter(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID)

    while True:
        if True:
            photo = camera.take_photo()
            #if photo is not None:
                # print_image dithers the photo for thermal paper, then prints it.
                #printer.print_image(photo)

        if poller.poll():
            uploader.upload()

        time.sleep(30)
