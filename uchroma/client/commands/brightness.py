#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Brightness command — get/set device brightness.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class BrightnessCommand(Command):
    """Get or set device brightness."""

    name = "brightness"
    help = "Get or set brightness"
    aliases: ClassVar[list[str]] = ["bright", "br"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "value",
            type=int,
            nargs="?",
            metavar="PERCENT",
            help="brightness level (0-100), omit to query",
        )
        parser.add_argument(
            "--led",
            type=str,
            metavar="NAME",
            help="specific LED (backlight, logo, scroll)",
        )

    def run(self, args: Namespace) -> int:
        service = get_device_service()

        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            return self.error(str(e))

        if args.value is None:
            return self._get_brightness(device, args.led)
        else:
            return self._set_brightness(device, args.value, args.led)

    def _get_brightness(self, device, led: str | None) -> int:
        """Query and display brightness."""
        service = get_device_service()
        brightness = service.get_brightness(device, led)

        if led:
            self.print(
                f"{self.out.device(device.Name)} {self.out.key(led)}: "
                f"{self.out.value(f'{brightness}%')}"
            )
        else:
            self.print(f"{self.out.device(device.Name)}: {self.out.value(f'{brightness}%')}")

        return 0

    def _set_brightness(self, device, value: int, led: str | None) -> int:
        """Set brightness level."""
        service = get_device_service()

        try:
            service.set_brightness(device, value, led)
        except ValueError as e:
            return self.error(str(e))

        if led:
            return self.success(f"{device.Name} {led} brightness set to {value}%")
        else:
            return self.success(f"{device.Name} brightness set to {value}%")
