import time

from .batch_uploader import BatchUploader
from .constants import BUCKET, NETWORK, PHOTO_DIRECTORY, SYSTEM
from .network_checker import NetworkChecker
from .photo_store import PhotoStore

if __name__ == "__main__":

    path = "placeholder/path"

    photos = PhotoStore(PHOTO_DIRECTORY)
    poller = NetworkChecker(NETWORK, SYSTEM)
    uploader = BatchUploader(photos, BUCKET)

    while True:
        if poller.poll():
            uploader.upload()

        time.sleep(10)
