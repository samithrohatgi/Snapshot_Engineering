
import pytest
from src.photo_store import PhotoStore


@pytest.fixture
def photo_dir(tmp_path):
    directory = tmp_path / "photos"
    directory.mkdir()

    (directory / "photo1.jpg").write_bytes(b"fake image 1")
    (directory / "photo2.jpg").write_bytes(b"fake image 2")
    (directory / "notes.txt").write_text("not an image")

    return directory


@pytest.fixture
def store(photo_dir):
    return PhotoStore(photo_dir)


def test_get_pending_photos(store, photo_dir):
    expected = {
        photo_dir / "photo1.jpg",
        photo_dir / "photo2.jpg"
    }

    assert set(store.get_pending_photos()) == expected


def test_delete_valid_photo(store, photo_dir):
    file = photo_dir / "photo1.jpg"

    store.delete_photo(file)

    assert not file.exists()
    assert (photo_dir / "photo2.jpg").exists()


def test_delete_nonexistent_photo(store, photo_dir):
    missing_file = photo_dir / "nonexistent.jpg"

    with pytest.raises(FileNotFoundError):
        store.delete_photo(missing_file)


def test_delete_outside_directory(store, photo_dir):
    outside_file = photo_dir.parent / "outside.jpg"
    outside_file.write_bytes(b"fake image")

    with pytest.raises(ValueError):
        store.delete_photo(outside_file)

    assert outside_file.exists()
