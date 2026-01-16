#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Battery command — battery status for wireless devices.

Works entirely through D-Bus, no server-side imports.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class BatteryCommand(Command):
    """Battery and wireless status for devices."""

    name = "battery"
    help = "Show battery level and charging status"
    aliases: ClassVar[list[str]] = ["bat", "wireless"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("-a", "--all", action="store_true", help="show all devices")
        parser.add_argument("-q", "--quiet", action="store_true", help="only show percentage")

    def run(self, args: Namespace) -> int:
        service = get_device_service()

        if getattr(args, "all", False):
            return self._show_all(args, service)

        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        return self._show_device(args, service, device)

    def _show_device(self, args: Namespace, service, device) -> int:
        """Show battery status for a single device."""
        is_wireless = service.is_wireless(device)

        if not is_wireless:
            if getattr(args, "quiet", False):
                return 0
            self.print(self.out.muted("Device is not wireless"))
            return 0

        battery = service.get_battery_level(device)
        charging = service.is_charging(device)

        if getattr(args, "quiet", False):
            self.print(f"{battery}%")
            return 0

        self.print()
        self.print(self.out.header(f" {device.Name}"))
        self.print()

        key_width = 12

        # Battery level with visual indicator
        level_str = self._format_battery_level(battery)
        status = "charging" if charging else "discharging"
        self.print(
            self.out.table_row(key_width, self.out.device("battery"), f"{level_str} ({status})")
        )

        # Visual bar
        bar = self._battery_bar(battery)
        self.print(self.out.table_row(key_width, "", bar))
        self.print()

        return 0

    def _show_all(self, args: Namespace, service) -> int:
        """Show battery status for all wireless devices."""
        devices = service.list_devices()
        wireless_count = 0

        self.print()
        self.print(self.out.header(" Wireless Device Status:"))
        self.print()

        key_width = 20

        for info in devices:
            try:
                device = service.get_device(info.key)
                if device and service.is_wireless(device):
                    wireless_count += 1
                    battery = service.get_battery_level(device)
                    charging = service.is_charging(device)

                    level_str = self._format_battery_level(battery)
                    status_icon = "⚡" if charging else ""

                    self.print(
                        self.out.table_row(
                            key_width,
                            self.out.device(info.name),
                            f"{level_str} {status_icon}".strip(),
                        )
                    )
            except Exception:
                continue

        if wireless_count == 0:
            self.print(self.out.muted("  No wireless devices found"))

        self.print()
        return 0

    def _format_battery_level(self, level: int) -> str:
        """Format battery level with color coding."""
        if level <= 20:
            return self.out.error(f"{level}%")
        elif level <= 50:
            return self.out.warning(f"{level}%")
        else:
            return self.out.success(f"{level}%")

    def _battery_bar(self, level: int, width: int = 20) -> str:
        """Create a visual battery bar."""
        filled = int(level / 100 * width)
        empty = width - filled

        if level <= 20:
            fill_char = self.out.error("█")
        elif level <= 50:
            fill_char = self.out.warning("█")
        else:
            fill_char = self.out.success("█")

        empty_char = self.out.muted("░")

        return f"[{fill_char * filled}{empty_char * empty}]"
