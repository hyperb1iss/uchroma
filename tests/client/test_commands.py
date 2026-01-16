#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for CLI commands."""

import pytest

from uchroma.client.cli_base import UChromaCLI
from uchroma.client.commands import COMMANDS, Command
from uchroma.client.commands.brightness import BrightnessCommand
from uchroma.client.commands.devices import ListCommand
from uchroma.client.commands.dump import DumpCommand
from uchroma.client.commands.fx import FxCommand
from uchroma.client.device_service import DeviceInfo, DeviceService


class MockDeviceProxy:
    """Mock device proxy for testing."""

    def __init__(self, name="BlackWidow Chroma", brightness=80):
        self.Name = name
        self.Brightness = brightness
        self._fx_iface = True  # Has FX support
        self._anim_iface = True
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
        self.CurrentRenderers = []
        self.CurrentFX = ("static", {})

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
            DeviceInfo(
                name="DeathAdder Chroma",
                device_type="mouse",
                key="1532:0043.01",
                index=1,
                serial="DA9876543210",
                firmware="v2.00",
                brightness=100,
            ),
        ]

    def list_devices(self):
        return self._mock_devices

    def require_device(self, spec):
        if not self._mock_devices:
            raise ValueError("No devices found")
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


@pytest.fixture(autouse=True)
def mock_device_service(monkeypatch):
    """Replace the device service singleton with a mock."""
    mock = MockDeviceService()
    monkeypatch.setattr("uchroma.client.device_service._service", mock)
    monkeypatch.setattr("uchroma.client.commands.devices.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.brightness.get_device_service", lambda: mock)
    monkeypatch.setattr("uchroma.client.commands.anim.get_device_service", lambda: mock)
    return mock


class TestCommandRegistry:
    """Test command registration."""

    def test_commands_list_not_empty(self):
        assert len(COMMANDS) > 0

    def test_all_commands_are_command_subclasses(self):
        for cmd_cls in COMMANDS:
            assert issubclass(cmd_cls, Command)

    def test_all_commands_have_name(self):
        for cmd_cls in COMMANDS:
            assert hasattr(cmd_cls, "name")
            assert isinstance(cmd_cls.name, str)
            assert len(cmd_cls.name) > 0

    def test_all_commands_have_help(self):
        for cmd_cls in COMMANDS:
            assert hasattr(cmd_cls, "help")
            assert isinstance(cmd_cls.help, str)


class TestCommandRegistration:
    """Test registering commands with CLI."""

    def test_register_command(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()

        instance = ListCommand.register(cli, subparsers)

        assert instance is not None
        assert isinstance(instance, ListCommand)

    def test_register_all_commands(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()

        instances = []
        for cmd_cls in COMMANDS:
            instance = cmd_cls.register(cli, subparsers)
            instances.append(instance)

        assert len(instances) == len(COMMANDS)

    def test_command_aliases_work(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        ListCommand.register(cli, subparsers)

        # Should be able to parse alias
        args = cli.parse_args(["ls"])
        assert args.command == "ls"


class TestListCommand:
    """Test list command."""

    def test_list_returns_zero(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = ListCommand.register(cli, subparsers)

        args = cli.parse_args(["list"])
        result = cmd.run(args)

        assert result == 0

    def test_list_quiet_mode(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        ListCommand.register(cli, subparsers)

        args = cli.parse_args(["list", "-q"])

        assert args.quiet is True

    def test_list_all_mode(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        ListCommand.register(cli, subparsers)

        args = cli.parse_args(["list", "-a"])

        assert args.all is True


class TestBrightnessCommand:
    """Test brightness command."""

    def test_brightness_query(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = BrightnessCommand.register(cli, subparsers)

        args = cli.parse_args(["brightness"])
        result = cmd.run(args)

        assert result == 0

    def test_brightness_set_valid(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = BrightnessCommand.register(cli, subparsers)

        args = cli.parse_args(["brightness", "80"])
        result = cmd.run(args)

        assert result == 0
        assert args.value == 80

    def test_brightness_set_invalid_high(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = BrightnessCommand.register(cli, subparsers)

        args = cli.parse_args(["brightness", "150"])
        result = cmd.run(args)

        assert result == 1  # Error

    def test_brightness_with_led(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        BrightnessCommand.register(cli, subparsers)

        args = cli.parse_args(["brightness", "--led", "logo", "50"])

        assert args.led == "logo"
        assert args.value == 50


class TestFxCommand:
    """Test fx command."""

    def test_fx_list_effects(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx", "--list"])
        result = cmd.run(args)

        assert result == 0

    def test_fx_no_args_lists_effects(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx"])
        result = cmd.run(args)

        assert result == 0

    def test_fx_set_static(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx", "static", "-c", "red"])
        result = cmd.run(args)

        assert result == 0
        assert args.effect == "static"
        assert args.color == "red"

    def test_fx_set_wave(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx", "wave", "--direction", "left"])

        assert args.effect == "wave"
        assert args.direction == "left"

    def test_fx_speed_options(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx", "reactive", "--speed", "3"])

        assert args.speed == 3


class TestDumpCommand:
    """Test dump command."""

    def test_dump_all(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = DumpCommand.register(cli, subparsers)

        args = cli.parse_args(["dump"])
        result = cmd.run(args)

        assert result == 0

    def test_dump_version(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        DumpCommand.register(cli, subparsers)

        args = cli.parse_args(["dump", "version"])

        assert args.what == "version"

    def test_dump_json(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = DumpCommand.register(cli, subparsers)

        args = cli.parse_args(["dump", "--json"])
        result = cmd.run(args)

        assert result == 0

    def test_dump_aliases(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        DumpCommand.register(cli, subparsers)

        # Test 'debug' alias
        args = cli.parse_args(["debug"])
        assert args.command == "debug"

        # Test 'info' alias
        args = cli.parse_args(["info"])
        assert args.command == "info"
