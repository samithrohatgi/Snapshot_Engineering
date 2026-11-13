import time

from .batch_uploader import BatchUploader
from .constants import BUCKET, NETWORK, PHOTO_DIRECTORY, SYSTEM
from .network_checker import NetworkChecker
from .photo_store import PhotoStore
from .photo_taker import PhotoTaker

if __name__ == "__main__":

    path = "placeholder/path"

    photos = PhotoStore(PHOTO_DIRECTORY)
    poller = NetworkChecker(NETWORK, SYSTEM)
    uploader = BatchUploader(photos, BUCKET)
    camera = PhotoTaker(PHOTO_DIRECTORY)

    while True:
        camera.take_photo()
        if poller.poll():
            uploader.upload()

        time.sleep(10)
