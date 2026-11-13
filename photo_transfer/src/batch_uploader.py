import logging

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)

from .photo_store import PhotoStore


class BatchUploader:
    def __init__(self, batch: PhotoStore, bucket: str):
        self.batch = batch
        self.client = boto3.client("s3", region_name="us-west-2")
        self.logs = logging.getLogger(__name__);
        self.bucket = bucket

    def upload(self):
        photos = self.batch.get_pending_photos()

        for photo in photos:
            try:
                self.client.upload_file(
                    Filename=str(photo),
                    Bucket=self.bucket,
                    Key=photo.name
                )
            
            except (S3UploadFailedError, BotoCoreError, ClientError):
                self.logs.exception("UPLOAD FAILED")
                continue
            
            else:
                continue
                self.batch.delete_photo(photo)



