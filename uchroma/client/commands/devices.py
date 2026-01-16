#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
List command — show available devices.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class ListCommand(Command):
    """List available Razer devices."""

    name = "list"
    help = "List connected devices"
    aliases: ClassVar[list[str]] = ["ls", "devices"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="show all details",
        )
        parser.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="only show device keys (for scripting)",
        )

    def run(self, args: Namespace) -> int:
        service = get_device_service()
        devices = service.list_devices()

        # Show connection error if any
        if not devices and service.connection_error:
            self.print(self.out.warning(service.connection_error))
            return 0

        if not devices:
            self.print(self.out.muted("No devices found"))
            return 0

        if args.quiet:
            for d in devices:
                self.print(d.key)
            return 0

        self.print(self.out.header(f"Devices ({len(devices)})"))
        self.print()

        for device in devices:
            # Index marker
            index = self.out.muted(f"[{device.index}]")

            # Device line
            line = self.out.device_line(
                device.name,
                device.device_type,
                device.key,
            )
            self.print(f"{index} {line}")

            if args.all:
                # Show additional details
                details = [
                    ("serial", device.serial or "unknown"),
                    ("firmware", device.firmware or "unknown"),
                    ("brightness", f"{device.brightness}%"),
                ]
                for key, value in details:
                    self.print(f"     {self.out.kv(key, value)}")
                self.print()

        return 0
