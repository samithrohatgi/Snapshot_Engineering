import logging
from pathlib import Path

import boto3
from dotenv import load_dotenv
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)

from .photo_store import PhotoStore


class BatchUploader:
    def __init__(self, batch: PhotoStore, bucket: str):
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        self.batch = batch
        self.client = boto3.client("s3", region_name="us-east-2")
        self.logs = logging.getLogger(__name__)
        self.bucket = bucket

    def upload(self):
        photos = self.batch.get_pending_photos()

        for photo in photos:
            try:
                self.client.upload_file(
                    Filename=str(photo),
                    Bucket=self.bucket,
                    Key=f"images/testing/{photo.name}",
                )
            
            except (S3UploadFailedError, BotoCoreError, ClientError):
                self.logs.exception("UPLOAD FAILED")
                continue
            
            else:
                self.logs.info("Uploaded %s; keeping local photo", photo.name)



