#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Dump command — show debug information.
"""

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.version import __version__


class DumpCommand(Command):
    """Dump debug information."""

    name = "dump"
    help = "Show debug information"
    aliases: ClassVar[list[str]] = ["debug", "info"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "what",
            nargs="?",
            choices=["device", "hardware", "version", "all"],
            default="all",
            help="what to dump (default: all)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="output as JSON",
        )

    def run(self, args: Namespace) -> int:
        if args.json:
            return self._dump_json(args)

        what = args.what

        if what in ("version", "all"):
            self._dump_version()

        if what in ("device", "all"):
            self._dump_device(args)

        if what in ("hardware", "all"):
            self._dump_hardware()

        return 0

    def _dump_version(self) -> None:
        """Dump version info."""
        self.print(self.out.header("Version"))
        self.print()

        info = [
            ("uchroma", __version__),
            ("python", sys.version.split()[0]),
        ]

        # Try to get optional dependency versions
        try:
            import traitlets  # noqa: PLC0415

            info.append(("traitlets", traitlets.__version__))
        except (ImportError, AttributeError):
            pass

        try:
            import coloraide  # noqa: PLC0415

            info.append(("coloraide", coloraide.__version__))
        except (ImportError, AttributeError):
            pass

        for key, value in info:
            self.print(f"  {self.out.kv(key, value)}")
        self.print()

    def _dump_device(self, args: Namespace) -> None:
        """Dump device info."""
        from uchroma.client.device_service import get_device_service  # noqa: PLC0415

        self.print(self.out.header("Device"))
        self.print()

        service = get_device_service()
        devices = service.list_devices()

        if not devices:
            if service.connection_error:
                self.print(f"  {self.out.warning(service.connection_error)}")
            else:
                self.print(self.out.muted("  No devices connected"))
            self.print()
            return

        # If spec given, show just that device in detail
        # Otherwise show all devices
        if args.device_spec:
            try:
                proxy = service.require_device(args.device_spec)
                self._dump_single_device(proxy)
            except ValueError as e:
                self.print(f"  {self.out.error(str(e))}")
        else:
            for info in devices:
                try:
                    proxy = service.require_device(info.key)
                    self._dump_single_device(proxy)
                except ValueError:
                    # Fallback to basic info
                    self._dump_device_info(info)

        self.print()

    def _dump_single_device(self, proxy) -> None:
        """Dump detailed info for a single device proxy."""
        from uchroma.client.device_service import get_device_service  # noqa: PLC0415

        service = get_device_service()

        self.print(f"  {self.out.device(proxy.Name)}")
        self.print()

        # Basic info
        info = [
            ("type", proxy.DeviceType),
            ("key", proxy.Key),
            ("serial", proxy.SerialNumber or "unknown"),
            ("firmware", proxy.FirmwareVersion or "unknown"),
            ("manufacturer", proxy.Manufacturer or "Razer"),
            ("usb", f"{proxy.VendorId:04x}:{proxy.ProductId:04x}"),
        ]

        # Matrix info
        if proxy.HasMatrix:
            info.append(("matrix", f"{proxy.Height}x{proxy.Width}"))

        # Brightness
        info.append(("brightness", f"{int(proxy.Brightness)}%"))

        # Supported LEDs
        leds = proxy.SupportedLeds
        if leds:
            info.append(("leds", ", ".join(leds)))

        # Available effects
        fx = proxy.AvailableFX
        if fx:
            info.append(("effects", ", ".join(sorted(fx.keys()))))

        # Available renderers (animations) - show short names
        renderers = proxy.AvailableRenderers
        if renderers:
            short_names = [k.split(".")[-1] for k in sorted(renderers.keys())]
            info.append(("renderers", ", ".join(short_names)))

        # Current state
        current_fx = proxy.CurrentFX
        if current_fx and isinstance(current_fx, tuple) and len(current_fx) >= 1:
            info.append(("current_fx", current_fx[0]))

        # Battery/Wireless info
        try:
            if service.is_wireless(proxy):
                info.append(("wireless", "yes"))
                battery = service.get_battery_level(proxy)
                charging = service.is_charging(proxy)
                status = f"{battery}% {'(charging)' if charging else ''}"
                info.append(("battery", status.strip()))
        except Exception:
            pass

        # System control info (laptops)
        try:
            if service.has_system_control(proxy):
                info.append(("system_control", "yes"))
                power_mode = service.get_power_mode(proxy)
                if power_mode:
                    info.append(("power_mode", power_mode))
                if service.supports_fan_speed(proxy):
                    fan_rpm = service.get_fan_rpm(proxy)
                    if fan_rpm:
                        rpm1, rpm2 = fan_rpm
                        if rpm2 > 0 and rpm2 != rpm1:
                            info.append(("fan_rpm", f"{rpm1} / {rpm2}"))
                        else:
                            info.append(("fan_rpm", str(rpm1)))
                if service.supports_boost(proxy):
                    cpu = service.get_cpu_boost(proxy)
                    gpu = service.get_gpu_boost(proxy)
                    if cpu:
                        info.append(("cpu_boost", cpu))
                    if gpu:
                        info.append(("gpu_boost", gpu))
        except Exception:
            pass

        for key, value in info:
            self.print(f"    {self.out.kv(key, str(value))}")

    def _dump_device_info(self, info) -> None:
        """Dump basic device info from DeviceInfo object."""
        self.print(f"  {self.out.device(info.name)}")
        self.print()
        for key, value in [
            ("type", info.device_type),
            ("key", info.key),
            ("serial", info.serial or "unknown"),
            ("firmware", info.firmware or "unknown"),
            ("brightness", f"{info.brightness}%"),
        ]:
            self.print(f"    {self.out.kv(key, value)}")

    def _dump_hardware(self) -> None:
        """Dump hardware database info (optional - requires server deps)."""
        self.print(self.out.header("Hardware Database"))
        self.print()

        try:
            from uchroma.server.hardware import Hardware  # noqa: PLC0415

            counts = {}
            for hw_type in Hardware.Type:
                try:
                    config = Hardware.get_type(hw_type)
                    if config:
                        count = self._count_devices(config)
                        if count > 0:
                            counts[hw_type.name.lower()] = count
                except (ValueError, KeyError):
                    # Skip types with YAML parsing issues
                    pass

            for device_type, count in counts.items():
                self.print(f"  {self.out.kv(device_type, str(count))}")
        except ImportError:
            self.print(self.out.muted("  Hardware module not available"))

        self.print()

    def _count_devices(self, config) -> int:
        """Recursively count devices in a config tree."""
        count = 0
        if config.product_id is not None:
            count = 1
        if config.children:
            for child in config.children:
                count += self._count_devices(child)
        return count

    def _dump_json(self, args: Namespace) -> int:
        """Dump all info as JSON."""
        data = {
            "version": {
                "uchroma": __version__,
                "python": sys.version.split()[0],
            },
        }

        if args.device_spec:
            data["device"] = {
                "spec": args.device_spec,
                # TODO: Actual device info
            }

        self.print(json.dumps(data, indent=2))
        return 0
