from pathlib import Path


class PhotoStore:

    def __init__(self, path: str) -> None:
        self.photos = Path(path)

    def get_pending_photos(self) -> list[Path]:
        return list(self.photos.glob("*.jpg"))

    def delete_photo(self, path: Path) -> None:
        path = path.resolve()

        if path.is_relative_to(self.photos.resolve()):
            path.unlink()
        elif path.is_file():
            raise ValueError("File is outside the managed directory")
        else:
            raise FileNotFoundError("Provided path is not a file")
