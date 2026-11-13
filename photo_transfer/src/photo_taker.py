import logging
import subprocess
import uuid
from pathlib import Path

from .constants import PHOTO_DIRECTORY


class PhotoTaker:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        self.logs = logging.getLogger(__name__);

    def take_photo(self):
        try:
            temporary_path = Path(self.storage_path) / f"{uuid.uuid4().hex}.tmp"
            subprocess.run(
                ["rpicam-still", "-n", "-t", "2000", "--encoding", "jpg", "-o", str(temporary_path)],
                capture_output=True, 
                text=True,
                check=True,
                timeout=15,
            )
            temporary_path.rename(temporary_path.with_suffix(".jpg"))

        except subprocess.CalledProcessError as error:
            self.logs.error("Camera capture failed: %s", error.stderr)
            return self._fail(temporary_path)

        except subprocess.TimeoutExpired:
            self.logs.exception("Camera capture timed out")
            return self._fail(temporary_path)

        except FileNotFoundError:
            self.logs.exception("Camera command not found")
            return self._fail(temporary_path)

        except OSError:
            self.logs.exception("Operating system error during capture")
            return self._fail(temporary_path)

        return True


    def _fail(self, temp_path: Path):
        temp_path.unlink(missing_ok = True)
        return False
        

if __name__ == "__main__":
    camera = PhotoTaker(PHOTO_DIRECTORY)
    camera.take_photo()
