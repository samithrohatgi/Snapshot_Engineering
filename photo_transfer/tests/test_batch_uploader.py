
import logging
from unittest.mock import Mock, call

import pytest
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError, NoCredentialsError

from src.batch_uploader import BatchUploader
from src.photo_store import PhotoStore


@pytest.fixture
def photos(tmp_path):
    file1 = tmp_path / "photo1.jpg"
    file2 = tmp_path / "photo2.jpg"

    file1.write_bytes(b"fake image 1")
    file2.write_bytes(b"fake image 2")

    return [file1, file2]


@pytest.fixture
def store(tmp_path, photos):
    return PhotoStore(tmp_path)


@pytest.fixture
def mock_s3(monkeypatch):
    client = Mock()
    factory = Mock(return_value=client)

    monkeypatch.setattr(
        "src.batch_uploader.boto3.client",
        factory
    )

    return client, factory


@pytest.fixture
def uploader(store, mock_s3):
    return BatchUploader(store, "test-photo-bucket")


def test_upload_success(uploader, photos, mock_s3):
    client, _ = mock_s3

    uploader.upload()

    expected_calls = [
        call(
            Filename=str(photo),
            Bucket="test-photo-bucket",
            Key=photo.name
        )
        for photo in photos
    ]

    client.upload_file.assert_has_calls(
        expected_calls,
        any_order=True
    )

    assert client.upload_file.call_count == 2
    assert all(not photo.exists() for photo in photos)


def test_empty_batch(uploader, photos, mock_s3):
    client, _ = mock_s3

    for photo in photos:
        photo.unlink()

    uploader.upload()

    client.upload_file.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        S3UploadFailedError("Upload failed"),
        NoCredentialsError(),
        ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "Access denied"
                }
            },
            "PutObject"
        )
    ]
)
def test_failed_upload(
    uploader, store, photos, mock_s3,
    monkeypatch, caplog, error
):
    client, _ = mock_s3
    failed_photo, successful_photo = photos

    # Ensure the failed photo is attempted first
    monkeypatch.setattr(
        store,
        "get_pending_photos",
        lambda: [failed_photo, successful_photo]
    )

    def simulate_upload(Filename, Bucket, Key):
        if Filename == str(failed_photo):
            raise error

    client.upload_file.side_effect = simulate_upload

    with caplog.at_level(logging.ERROR):
        uploader.upload()

    # Both photos should have been attempted
    assert client.upload_file.call_count == 2

    # Failed photo remains on disk for retry
    assert failed_photo.exists()

    # Successful photo is deleted
    assert not successful_photo.exists()

    # Failure was logged
    assert "UPLOAD FAILED" in caplog.text


def test_s3_client_configuration(mock_s3, store):
    _, factory = mock_s3

    BatchUploader(store, "test-photo-bucket")

    factory.assert_called_once_with(
        "s3",
        region_name="us-west-2"
    )


def test_correct_bucket(uploader, mock_s3):
    client, _ = mock_s3

    uploader.upload()

    for upload_call in client.upload_file.call_args_list:
        assert upload_call.kwargs["Bucket"] == "test-photo-bucket"
