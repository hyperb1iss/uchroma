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

    def __init__(self, name="BlackWidow Chroma", brightness=80, is_laptop=False, is_wireless=False):
        self.Name = name
        self.Brightness = brightness
        self._fx_iface = True  # Has FX support
        self._anim_iface = True
        self._led_iface = True
        self._system_iface = is_laptop  # System control for laptops
        self._is_wireless = is_wireless
        # Additional properties for dump command
        self.DeviceType = "laptop" if is_laptop else "keyboard"
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
                "color": {
                    "__class__": ("uchroma.traits", "ColorTrait"),
                    "default_value": "green",
                    "metadata": {"config": True},
                },
            }
        }
        self.CurrentRenderers = []
        self.CurrentFX = ("static", {})

        # System control properties (laptops)
        self.HasSystemControl = is_laptop
        self.FanRPM = (3500, 3500) if is_laptop else None
        self.FanMode = "auto" if is_laptop else None
        self.FanLimits = {"min": 2000, "max": 5000} if is_laptop else None
        self.PowerMode = "balanced" if is_laptop else None
        self.AvailablePowerModes = (
            ["balanced", "gaming", "creator", "custom"] if is_laptop else None
        )
        self.CPUBoost = "medium" if is_laptop else None
        self.GPUBoost = "medium" if is_laptop else None
        self.AvailableBoostModes = ["low", "medium", "high", "boost"] if is_laptop else None
        self.SupportsFanSpeed = is_laptop
        self.SupportsBoost = is_laptop

        # Battery/wireless properties
        self.IsWireless = is_wireless
        self.IsCharging = is_wireless
        self.BatteryLevel = 75 if is_wireless else 0

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
        return {"brightness": 1.0, "color": "green"}

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

        # Static effect with color via dynamic subparser
        args = cli.parse_args(["fx", "static", "--color", "red"])
        result = cmd.run(args)

        assert result == 0

    def test_fx_set_wave(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx", "wave", "--direction", "left"])
        result = cmd.run(args)

        assert result == 0

    def test_fx_list_subcommand(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = FxCommand.register(cli, subparsers)

        args = cli.parse_args(["fx", "list"])
        result = cmd.run(args)

        assert result == 0


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


class TestPowerCommand:
    """Test power command."""

    def test_power_status_no_system_control(self, mock_device_service):
        from uchroma.client.commands.power import PowerCommand

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = PowerCommand.register(cli, subparsers)

        args = cli.parse_args(["power"])
        result = cmd.run(args)

        # Should succeed but show "no system control" message
        assert result == 0

    def test_power_status_with_system_control(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.power import PowerCommand

        # Return a laptop device
        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(is_laptop=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = PowerCommand.register(cli, subparsers)

        args = cli.parse_args(["power"])
        result = cmd.run(args)

        assert result == 0

    def test_power_mode_set(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.power import PowerCommand

        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(is_laptop=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = PowerCommand.register(cli, subparsers)

        args = cli.parse_args(["power", "mode", "gaming"])
        result = cmd.run(args)

        assert result == 0

    def test_power_fan_auto(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.power import PowerCommand

        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(is_laptop=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = PowerCommand.register(cli, subparsers)

        args = cli.parse_args(["power", "fan", "auto"])
        result = cmd.run(args)

        assert result == 0

    def test_power_fan_manual(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.power import PowerCommand

        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(is_laptop=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = PowerCommand.register(cli, subparsers)

        args = cli.parse_args(["power", "fan", "manual", "3500"])
        result = cmd.run(args)

        assert result == 0

    def test_power_boost_set(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.power import PowerCommand

        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(is_laptop=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = PowerCommand.register(cli, subparsers)

        args = cli.parse_args(["power", "boost", "--cpu", "high", "--gpu", "medium"])
        result = cmd.run(args)

        assert result == 0

    def test_power_aliases(self):
        from uchroma.client.commands.power import PowerCommand

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        PowerCommand.register(cli, subparsers)

        # Test 'fan' alias
        args = cli.parse_args(["fan"])
        assert args.command == "fan"

        # Test 'boost' alias
        args = cli.parse_args(["boost"])
        assert args.command == "boost"


class TestBatteryCommand:
    """Test battery command."""

    def test_battery_not_wireless(self, mock_device_service):
        from uchroma.client.commands.battery import BatteryCommand

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = BatteryCommand.register(cli, subparsers)

        args = cli.parse_args(["battery"])
        result = cmd.run(args)

        # Should succeed (device is not wireless)
        assert result == 0

    def test_battery_wireless_device(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.battery import BatteryCommand

        # Return a wireless device
        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(name="DeathAdder V2 Pro", is_wireless=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = BatteryCommand.register(cli, subparsers)

        args = cli.parse_args(["battery"])
        result = cmd.run(args)

        assert result == 0

    def test_battery_quiet_mode(self, mock_device_service, monkeypatch):
        from uchroma.client.commands.battery import BatteryCommand

        monkeypatch.setattr(
            mock_device_service,
            "require_device",
            lambda spec: MockDeviceProxy(is_wireless=True),
        )

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        cmd = BatteryCommand.register(cli, subparsers)

        args = cli.parse_args(["battery", "-q"])
        result = cmd.run(args)

        assert result == 0

    def test_battery_aliases(self):
        from uchroma.client.commands.battery import BatteryCommand

        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        BatteryCommand.register(cli, subparsers)

        # Test 'bat' alias
        args = cli.parse_args(["bat"])
        assert args.command == "bat"

        # Test 'wireless' alias
        args = cli.parse_args(["wireless"])
        assert args.command == "wireless"
