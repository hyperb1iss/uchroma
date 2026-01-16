#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Watch command — live monitoring of device status.

Shows real-time updates for fans, battery, brightness, etc.
"""

import sys
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service
from uchroma.client.output import BOX_V, strip_ansi


class WatchCommand(Command):
    """Live monitoring of device status."""

    name = "watch"
    help = "Live monitoring of device status (fans, battery, etc.)"
    aliases: ClassVar[list[str]] = ["monitor", "live"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-i",
            "--interval",
            type=float,
            default=1.0,
            metavar="SEC",
            help="update interval in seconds (default: 1.0)",
        )
        parser.add_argument(
            "-n",
            "--count",
            type=int,
            default=0,
            metavar="N",
            help="stop after N updates (0 = infinite)",
        )
        parser.add_argument(
            "--fan",
            action="store_true",
            help="show fan speed only",
        )
        parser.add_argument(
            "--battery",
            action="store_true",
            help="show battery only",
        )
        parser.add_argument(
            "--compact",
            action="store_true",
            help="compact single-line output",
        )

    def run(self, args: Namespace) -> int:
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        interval = args.interval
        max_count = args.count
        compact = args.compact

        # Determine what to show
        show_fan = args.fan or (not args.fan and not args.battery)
        show_battery = args.battery or (not args.fan and not args.battery)

        has_system = service.has_system_control(device)
        is_wireless = service.is_wireless(device)

        if args.fan and not has_system:
            self.print(self.out.error("Device does not support fan monitoring"))
            return 1

        if args.battery and not is_wireless:
            self.print(self.out.error("Device is not wireless"))
            return 1

        if not has_system and not is_wireless:
            self.print(self.out.error("No monitorable features available"))
            return 1

        try:
            if compact:
                return self._watch_compact(
                    service, device, interval, max_count, show_fan, show_battery
                )
            else:
                return self._watch_panel(
                    service, device, interval, max_count, show_fan, show_battery
                )
        except KeyboardInterrupt:
            self.print()
            self.print(self.out.muted("Monitoring stopped"))
            return 0

    def _watch_compact(
        self, service, device, interval: float, max_count: int, show_fan: bool, show_battery: bool
    ) -> int:
        """Compact single-line watch mode."""
        count = 0
        history: list[float] = []

        while max_count == 0 or count < max_count:
            parts = []
            timestamp = datetime.now().strftime("%H:%M:%S")
            parts.append(self.out.timestamp(timestamp))

            if (
                show_fan
                and service.has_system_control(device)
                and service.supports_fan_speed(device)
            ):
                rpm = service.get_fan_rpm(device)
                if rpm:
                    rpm1, rpm2 = rpm
                    history.append(rpm1)
                    if len(history) > 20:
                        history = history[-20:]
                    spark = self.out.sparkline(history, width=10)
                    if rpm2 > 0 and rpm2 != rpm1:
                        parts.append(
                            f"Fan: {self.out.number(rpm1)}/{self.out.number(rpm2)} RPM {spark}"
                        )
                    else:
                        parts.append(f"Fan: {self.out.number(rpm1)} RPM {spark}")

            if show_battery and service.is_wireless(device):
                level = service.get_battery_level(device)
                charging = service.is_charging(device)
                icon = self.out.accent("⚡") if charging else ""
                bar = self.out.progress_bar(level, 100, width=10, show_percent=False)
                parts.append(f"Bat: {bar} {self.out.number(level)}% {icon}")

            # Clear line and print
            sys.stdout.write("\r\033[K")
            sys.stdout.write(" │ ".join(parts))
            sys.stdout.flush()

            count += 1
            if max_count == 0 or count < max_count:
                time.sleep(interval)

        self.print()
        return 0

    def _watch_panel(
        self, service, device, interval: float, max_count: int, show_fan: bool, show_battery: bool
    ) -> int:
        """Panel-style watch mode with visual gauges."""
        count = 0
        panel_width = 50
        rpm_history: list[float] = []

        # Hide cursor
        sys.stdout.write("\033[?25l")

        try:
            while max_count == 0 or count < max_count:
                lines = []

                # Header
                timestamp = datetime.now().strftime("%H:%M:%S")
                title = f"{device.Name} - {timestamp}"
                lines.append(self.out.panel_top(title, panel_width))

                # Fan section
                if (
                    show_fan
                    and service.has_system_control(device)
                    and service.supports_fan_speed(device)
                ):
                    lines.append(self._panel_row("", panel_width))

                    mode = service.get_fan_mode(device) or "unknown"
                    lines.append(
                        self._panel_row(
                            f"  {self.out.key('Fan Mode')}  {self.out.value(mode)}", panel_width
                        )
                    )

                    limits = service.get_fan_limits(device)
                    max_rpm = limits.get("max", 5000) if limits else 5000

                    rpm = service.get_fan_rpm(device)
                    if rpm:
                        rpm1, rpm2 = rpm
                        rpm_history.append(rpm1)
                        if len(rpm_history) > 30:
                            rpm_history = rpm_history[-30:]

                        gauge = self.out.rpm_gauge(rpm1, max_rpm)
                        lines.append(
                            self._panel_row(f"  {self.out.key('RPM')}      {gauge}", panel_width)
                        )

                        if rpm2 > 0 and rpm2 != rpm1:
                            gauge2 = self.out.rpm_gauge(rpm2, max_rpm)
                            lines.append(
                                self._panel_row(
                                    f"  {self.out.key('RPM 2')}    {gauge2}", panel_width
                                )
                            )

                        # Sparkline history
                        spark = self.out.sparkline(rpm_history, width=30)
                        lines.append(
                            self._panel_row(f"  {self.out.muted('History')} {spark}", panel_width)
                        )

                # Battery section
                if show_battery and service.is_wireless(device):
                    if show_fan and service.has_system_control(device):
                        lines.append(self.out.panel_divider(panel_width))

                    lines.append(self._panel_row("", panel_width))

                    level = service.get_battery_level(device)
                    charging = service.is_charging(device)

                    bar = self.out.battery_bar(level, charging, width=20)
                    status = (
                        self.out.accent("Charging") if charging else self.out.muted("Discharging")
                    )
                    lines.append(
                        self._panel_row(
                            f"  {self.out.key('Battery')} {bar} {self.out.number(level)}%",
                            panel_width,
                        )
                    )
                    lines.append(
                        self._panel_row(f"  {self.out.key('Status')}  {status}", panel_width)
                    )

                lines.append(self._panel_row("", panel_width))
                lines.append(self.out.panel_bottom(panel_width))
                lines.append(self.out.muted(f"  Press Ctrl+C to stop • Interval: {interval}s"))

                # Move cursor to start and redraw
                if count > 0:
                    sys.stdout.write(f"\033[{len(lines)}A")

                for line in lines:
                    sys.stdout.write(f"\033[K{line}\n")
                sys.stdout.flush()

                count += 1
                if max_count == 0 or count < max_count:
                    time.sleep(interval)

        finally:
            # Show cursor
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

        return 0

    def _panel_row(self, content: str, width: int) -> str:
        """Format a panel row with proper padding."""
        visible_len = len(strip_ansi(content))
        padding = width - visible_len - 4
        return f"{self.out.muted(BOX_V)} {content}{' ' * max(0, padding)} {self.out.muted(BOX_V)}"
