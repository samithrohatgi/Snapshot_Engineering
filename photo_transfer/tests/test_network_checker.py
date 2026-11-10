
import subprocess
from unittest.mock import Mock

import pytest
from src.network_checker import NetworkChecker


@pytest.fixture
def mock_run(monkeypatch):
    def setup(stdout="", exception=None):
        if exception is not None:
            mocked = Mock(side_effect=exception)
        else:
            result = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr=""
            )
            mocked = Mock(return_value=result)

        monkeypatch.setattr(
            "src.network_checker.subprocess.run",
            mocked
        )
        return mocked

    return setup


@pytest.mark.parametrize(
    "system, output, expected",
    [
        (
            "Windows",
            "State : connected\nSSID : UCLA_WEB",
            True
        ),
        (
            "Windows",
            "State : connected\nSSID : eduroam",
            False
        ),
        (
            "Windows",
            "State : disconnected",
            False
        ),
        (
            "Pi",
            "*:UCLA_WEB\n:eduroam",
            True
        ),
        (
            "Pi",
            "*:eduroam\n:UCLA_WEB",
            False
        ),
        (
            "Pi",
            ":UCLA_WEB\n:eduroam",
            False
        ),
        (
            "Pi",
            "",
            False
        ),
    ]
)
def test_poll(mock_run, system, output, expected):
    mock_run(stdout=output)

    checker = NetworkChecker("UCLA_WEB", system)

    assert checker.poll() is expected


@pytest.mark.parametrize(
    "system, expected_command",
    [
        (
            "Windows",
            ["netsh", "wlan", "show", "interfaces"]
        ),
        (
            "Pi",
            [
                "nmcli", "-t", "-f", "IN-USE,SSID",
                "device", "wifi", "list",
                "--rescan", "no"
            ]
        ),
    ]
)
def test_correct_command(mock_run, system, expected_command):
    mocked = mock_run()

    checker = NetworkChecker("UCLA_WEB", system)
    checker.poll()

    mocked.assert_called_once_with(
        expected_command,
        capture_output=True,
        text=True,
        check=True,
        timeout=5
    )


def test_custom_network(mock_run):
    mock_run(stdout="*:eduroam\n:UCLA_WEB")

    checker = NetworkChecker("eduroam", "Pi")

    assert checker.poll() is True


def test_unsupported_system():
    checker = NetworkChecker("UCLA_WEB", "MacOS")

    with pytest.raises(ValueError):
        checker.poll()


@pytest.mark.parametrize(
    "exception",
    [
        subprocess.CalledProcessError(1, ["nmcli"]),
        subprocess.TimeoutExpired(["nmcli"], 5),
        FileNotFoundError("nmcli not found"),
    ]
)
def test_subprocess_errors(mock_run, exception):
    mock_run(exception=exception)

    checker = NetworkChecker("UCLA_WEB", "Pi")

    with pytest.raises(type(exception)):
        checker.poll()
