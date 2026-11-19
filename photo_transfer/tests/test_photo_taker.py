import subprocess
from pathlib import Path

import pytest
from src.photo_taker import PhotoTaker


@pytest.fixture
def camera(tmp_path):
  return PhotoTaker(tmp_path)


def fake_rpicam(error=None):
  """Stand-in for subprocess.run that writes a file where rpicam-still would."""
  def run(command, **kwargs):
    Path(command[command.index("-o") + 1]).write_bytes(b"fake jpeg")
    if error is not None:
      raise error
    return subprocess.CompletedProcess(command, 0, "", "")
  return run


def test_take_photo_returns_path(camera, tmp_path, monkeypatch):
  monkeypatch.setattr("src.photo_taker.subprocess.run", fake_rpicam())

  photo = camera.take_photo()

  assert photo.suffix == ".jpg"
  assert photo.read_bytes() == b"fake jpeg"
  # The temporary file was renamed, not left behind.
  assert list(tmp_path.iterdir()) == [photo]


@pytest.mark.parametrize(
  "error",
  [
    subprocess.CalledProcessError(1, ["rpicam-still"], stderr="no cameras available"),
    subprocess.TimeoutExpired(["rpicam-still"], 15),
    FileNotFoundError("rpicam-still"),
  ],
)
def test_failed_capture_returns_none(camera, tmp_path, monkeypatch, error):
  monkeypatch.setattr("src.photo_taker.subprocess.run", fake_rpicam(error))

  assert camera.take_photo() is None
  # The partial capture was cleaned up.
  assert list(tmp_path.iterdir()) == []
