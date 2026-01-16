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
        self._anim_iface = True
        self._led_iface = True
        self._system_iface = False  # No system control by default
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
        # FX with trait dicts (matching real D-Bus format)
        self.AvailableFX = {
            "static": {
                "description": {
                    "__class__": ("traitlets", "Unicode"),
                    "default_value": "Static color",
                    "metadata": {},
                },
                "color": {
                    "__class__": ("uchroma.traits", "ColorTrait"),
                    "default_value": "green",
                    "metadata": {"config": True},
                },
            },
            "wave": {
                "description": {
                    "__class__": ("traitlets", "Unicode"),
                    "default_value": "Waves of color",
                    "metadata": {},
                },
                "direction": {
                    "__class__": ("traitlets", "CaselessStrEnum"),
                    "values": ["right", "left"],
                    "default_value": "right",
                    "metadata": {"config": True},
                },
            },
            "spectrum": {
                "description": {
                    "__class__": ("traitlets", "Unicode"),
                    "default_value": "Cycle thru all colors",
                    "metadata": {},
                },
            },
        }
        self.AvailableRenderers = {
            "uchroma.fxlib.plasma.Plasma": {
                "meta": {
                    "display_name": "Color Plasma",
                    "description": "Colorful plasma effect",
                    "author": "UChroma",
                    "version": "1.0",
                },
                "traits": {},
            }
        }
        self.AvailableLEDs = {
            "logo": {
                "brightness": {
                    "__class__": ("traitlets", "Float"),
                    "min": 0.0,
                    "max": 1.0,
                    "default_value": 1.0,
                    "metadata": {"config": True},
                },
            }
        }
        self.CurrentRenderers = []
        self.CurrentFX = ("static", {})

        # System control properties (not a laptop by default)
        self.HasSystemControl = False
        self.FanRPM = None
        self.FanMode = None
        self.FanLimits = None
        self.PowerMode = None
        self.AvailablePowerModes = None
        self.CPUBoost = None
        self.GPUBoost = None
        self.AvailableBoostModes = None
        self.SupportsFanSpeed = False
        self.SupportsBoost = False

        # Battery/wireless properties (not wireless by default)
        self.IsWireless = False
        self.IsCharging = False
        self.BatteryLevel = 0

    def AddRenderer(self, name, zindex, traits):
        return f"/io/uchroma/device/0/layer/{len(self.CurrentRenderers)}"

    def RemoveRenderer(self, zindex):
        return True

    def PauseAnimation(self):
        return True

    def StopAnimation(self):
        return True

    def SetLayerTraits(self, zindex, traits):
        return True

    def SetFX(self, name, props):
        return True

    def GetLED(self, led_name):
        return {"brightness": 1.0}

    def SetLED(self, led_name, props):
        return True

    def SetFanAuto(self):
        return True

    def SetFanRPM(self, rpm, fan2_rpm=-1):
        return True


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

    def get_available_renderers(self, device):
        return device.AvailableRenderers

    def get_current_renderers(self, device):
        return device.CurrentRenderers

    def add_renderer(self, device, name, zindex=-1, traits=None):
        return device.AddRenderer(name, zindex, traits or {})

    def remove_renderer(self, device, zindex):
        return device.RemoveRenderer(zindex)

    def pause_animation(self, device):
        return device.PauseAnimation()

    def stop_animation(self, device):
        return device.StopAnimation()

    def set_layer_traits(self, device, zindex, traits):
        return device.SetLayerTraits(zindex, traits)

    # System control methods
    def has_system_control(self, device):
        return device.HasSystemControl

    def get_fan_rpm(self, device):
        return device.FanRPM

    def get_fan_mode(self, device):
        return device.FanMode

    def get_fan_limits(self, device):
        return device.FanLimits

    def set_fan_auto(self, device):
        return device.SetFanAuto()

    def set_fan_rpm(self, device, rpm, fan2_rpm=-1):
        return device.SetFanRPM(rpm, fan2_rpm)

    def get_power_mode(self, device):
        return device.PowerMode

    def set_power_mode(self, device, mode):
        device.PowerMode = mode
        return True

    def get_available_power_modes(self, device):
        return device.AvailablePowerModes

    def get_cpu_boost(self, device):
        return device.CPUBoost

    def set_cpu_boost(self, device, mode):
        device.CPUBoost = mode
        return True

    def get_gpu_boost(self, device):
        return device.GPUBoost

    def set_gpu_boost(self, device, mode):
        device.GPUBoost = mode
        return True

    def get_available_boost_modes(self, device):
        return device.AvailableBoostModes

    def supports_fan_speed(self, device):
        return device.SupportsFanSpeed

    def supports_boost(self, device):
        return device.SupportsBoost

    # Battery/wireless methods
    def is_wireless(self, device):
        return device.IsWireless

    def is_charging(self, device):
        return device.IsCharging

    def get_battery_level(self, device):
        return device.BatteryLevel


@pytest.fixture(autouse=True)
def mock_device_service(monkeypatch):
    """Replace the device service singleton with a mock."""
    mock = MockDeviceService()
    monkeypatch.setattr("uchroma.client.device_service._service", mock)
    monkeypatch.setattr("uchroma.client.commands.devices.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.brightness.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.anim.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.fx.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.led.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.power.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.battery.get_device_service", lambda: mock)
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
