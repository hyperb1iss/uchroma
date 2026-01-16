#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for CLI main entry point."""

import pytest

from uchroma.client.device_service import DeviceInfo, DeviceService
from uchroma.client.main import main


class MockDeviceProxy:
    """Mock device proxy for testing."""

    def __init__(self, name="BlackWidow Chroma", brightness=80):
        self.Name = name
        self.Brightness = brightness
        self._fx_iface = True
        # Additional properties for dump command
        self.DeviceType = "keyboard"
        self.Key = "1532:0203.00"
        self.SerialNumber = "XX1234567890"
        self.FirmwareVersion = "v1.05"
        self.Manufacturer = "Razer"
        self.VendorId = 0x1532
        self.ProductId = 0x0203
        self.HasMatrix = True
        self.Height = 6
        self.Width = 22
        self.SupportedLeds = ["backlight", "logo"]
        self.AvailableFX = {"static": {}, "wave": {}, "spectrum": {}}
        self.AvailableRenderers = {"uchroma.fxlib.plasma.Plasma": {}}
        self.CurrentFX = ("static", {})


class MockDeviceService(DeviceService):
    """Mock device service that doesn't connect to D-Bus."""

    def __init__(self):
        super().__init__()
        self._connected = True
        self._mock_devices = [
            DeviceInfo(
                name="BlackWidow Chroma",
                device_type="keyboard",
                key="1532:0203.00",
                index=0,
                serial="XX1234567890",
                firmware="v1.05",
                brightness=80,
            ),
        ]

    def list_devices(self):
        return self._mock_devices

    def require_device(self, spec):
        return MockDeviceProxy()

    def get_brightness(self, device, led=None):
        return 80

    def set_brightness(self, device, value, led=None):
        if not 0 <= value <= 100:
            raise ValueError(f"Brightness must be 0-100, got {value}")
        return True

    def set_effect(self, device, effect, **kwargs):
        return True


@pytest.fixture(autouse=True)
def mock_device_service(monkeypatch):
    """Replace the device service singleton with a mock."""
    mock = MockDeviceService()
    monkeypatch.setattr("uchroma.client.device_service._service", mock)
    monkeypatch.setattr("uchroma.client.commands.devices.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.brightness.get_device_service", lambda: mock)
    return mock


class TestMainFunction:
    """Test the main CLI entry point."""

    def test_no_args_shows_help(self, capsys):
        result = main([])

        assert result == 0
        captured = capsys.readouterr()
        assert "uchroma" in captured.out
        assert "commands" in captured.out.lower() or "usage" in captured.out.lower()

    def test_help_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])

        assert exc.value.code == 0

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])

        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "uchroma" in captured.out

    def test_list_command(self, capsys):
        result = main(["list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "Devices" in captured.out or "device" in captured.out.lower()

    def test_brightness_query(self, capsys):
        result = main(["brightness"])

        assert result == 0

    def test_fx_list(self, capsys):
        result = main(["fx", "--list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "static" in captured.out.lower()
        assert "wave" in captured.out.lower()

    def test_dump_command(self, capsys):
        result = main(["dump", "version"])

        assert result == 0
        captured = capsys.readouterr()
        assert "uchroma" in captured.out.lower()

    def test_device_spec_with_at_prefix(self, capsys):
        result = main(["@blackwidow", "brightness"])

        assert result == 0

    def test_device_spec_with_flag(self, capsys):
        result = main(["-d", "blackwidow", "brightness"])

        assert result == 0

    def test_command_alias(self, capsys):
        # 'ls' is an alias for 'list'
        result = main(["ls"])

        assert result == 0

    def test_debug_flag_exists(self, capsys):
        # Just verify --debug doesn't cause an error
        result = main(["--debug", "list"])

        assert result == 0

    def test_no_color_flag(self, capsys):
        result = main(["--no-color", "list"])

        assert result == 0
        captured = capsys.readouterr()
        # Should not have ANSI escape codes
        assert "\x1b[" not in captured.out


class TestMainErrors:
    """Test error handling in main."""

    def test_invalid_command(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["nonexistent-command"])

        assert exc.value.code == 2  # argparse error

    def test_invalid_brightness_value(self, capsys):
        result = main(["brightness", "150"])

        assert result == 1  # Error exit code
