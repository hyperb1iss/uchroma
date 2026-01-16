#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Power command — system control for laptops (fans, power modes, boost).

Works entirely through D-Bus, no server-side imports.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class PowerCommand(Command):
    """System control for laptops (fans, power modes, boost)."""

    name = "power"
    help = "Fan control, power modes, and performance boost (laptops)"
    aliases: ClassVar[list[str]] = ["fan", "boost"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="power_cmd", metavar="COMMAND")

        # status - show current state (default)
        sub.add_parser("status", help="show current power/fan/boost status")

        # mode - set power mode
        mode_p = sub.add_parser("mode", help="set power mode")
        mode_p.add_argument(
            "mode",
            nargs="?",
            metavar="MODE",
            help="power mode: balanced, gaming, creator, custom",
        )

        # fan subcommands
        fan_p = sub.add_parser("fan", help="fan control")
        fan_sub = fan_p.add_subparsers(dest="fan_cmd", metavar="COMMAND")

        fan_sub.add_parser("auto", help="set fans to automatic control")

        manual_p = fan_sub.add_parser("manual", help="set manual fan RPM")
        manual_p.add_argument("rpm", type=int, metavar="RPM", help="target RPM")
        manual_p.add_argument(
            "--fan2", type=int, default=-1, metavar="RPM", help="second fan RPM (if different)"
        )

        # boost - set CPU/GPU boost
        boost_p = sub.add_parser("boost", help="set CPU/GPU boost level")
        boost_p.add_argument(
            "--cpu", metavar="MODE", help="CPU boost mode (low, medium, high, boost)"
        )
        boost_p.add_argument("--gpu", metavar="MODE", help="GPU boost mode (low, medium, high)")

    def run(self, args: Namespace) -> int:
        cmd = getattr(args, "power_cmd", None)

        if cmd is None or cmd == "status":
            return self._status(args)
        elif cmd == "mode":
            return self._set_mode(args)
        elif cmd == "fan":
            return self._fan(args)
        elif cmd == "boost":
            return self._boost(args)

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Status display
    # ─────────────────────────────────────────────────────────────────────────

    def _status(self, args: Namespace) -> int:
        """Show current power/fan/boost status."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not service.has_system_control(device):
            self.print(self.out.muted("Device does not support system control"))
            return 0

        self.print()
        self.print(self.out.header(" System Control Status:"))
        self.print()

        key_width = 15

        # Power mode
        power_mode = service.get_power_mode(device)
        available_modes = service.get_available_power_modes(device) or []
        self.print(self.out.table_header(key_width, "power-mode", "Power profile management"))
        self.print(self.out.table_sep(key_width))
        if power_mode:
            self.print(self.out.table_row(key_width, self.out.device("current"), power_mode))
        if available_modes:
            self.print(
                self.out.table_row(
                    key_width, "available", ", ".join(m.lower() for m in available_modes)
                )
            )
        self.print()
        self.print()

        # Fan status
        if service.supports_fan_speed(device):
            self.print(self.out.table_header(key_width, "fan", "Cooling fan control"))
            self.print(self.out.table_sep(key_width))

            fan_mode = service.get_fan_mode(device)
            if fan_mode:
                self.print(self.out.table_row(key_width, self.out.device("mode"), fan_mode))

            fan_limits = service.get_fan_limits(device)
            max_rpm = fan_limits.get("max", 5000) if fan_limits else 5000

            fan_rpm = service.get_fan_rpm(device)
            if fan_rpm:
                rpm1, rpm2 = fan_rpm
                gauge1 = self.out.rpm_gauge(rpm1, max_rpm)
                if rpm2 > 0 and rpm2 != rpm1:
                    gauge2 = self.out.rpm_gauge(rpm2, max_rpm)
                    self.print(self.out.table_row(key_width, self.out.device("fan 1"), gauge1))
                    self.print(self.out.table_row(key_width, self.out.device("fan 2"), gauge2))
                else:
                    self.print(self.out.table_row(key_width, self.out.device("rpm"), gauge1))

            if fan_limits:
                min_rpm = fan_limits.get("min", 0)
                self.print(
                    self.out.table_row(
                        key_width,
                        "range",
                        f"{self.out.number(min_rpm)} - {self.out.number(max_rpm)} RPM",
                    )
                )
            self.print()
            self.print()

        # Boost status
        if service.supports_boost(device):
            self.print(self.out.table_header(key_width, "boost", "CPU/GPU performance boost"))
            self.print(self.out.table_sep(key_width))

            cpu_boost = service.get_cpu_boost(device)
            gpu_boost = service.get_gpu_boost(device)
            boost_modes = service.get_available_boost_modes(device) or []

            if cpu_boost:
                self.print(self.out.table_row(key_width, self.out.device("cpu"), cpu_boost))
            if gpu_boost:
                self.print(self.out.table_row(key_width, self.out.device("gpu"), gpu_boost))
            if boost_modes:
                self.print(
                    self.out.table_row(
                        key_width, "available", ", ".join(m.lower() for m in boost_modes)
                    )
                )
            self.print()

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Power mode
    # ─────────────────────────────────────────────────────────────────────────

    def _set_mode(self, args: Namespace) -> int:
        """Set power mode."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not service.has_system_control(device):
            self.print(self.out.error("Device does not support system control"))
            return 1

        mode = getattr(args, "mode", None)
        if not mode:
            # Show current mode
            current = service.get_power_mode(device)
            available = service.get_available_power_modes(device) or []
            if current:
                self.print(f"Current power mode: {self.out.device(current)}")
            if available:
                self.print(f"Available modes: {', '.join(m.lower() for m in available)}")
            return 0

        available = service.get_available_power_modes(device) or []
        # Case-insensitive matching
        mode_map = {m.lower(): m for m in available}
        actual_mode = mode_map.get(mode.lower())

        if not actual_mode:
            self.print(self.out.error(f"Invalid power mode: {mode}"))
            if available:
                self.print(f"Available modes: {', '.join(m.lower() for m in available)}")
            return 1

        service.set_power_mode(device, actual_mode)
        self.print(self.out.success(f"Power mode: {actual_mode}"))
        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Fan control
    # ─────────────────────────────────────────────────────────────────────────

    def _fan(self, args: Namespace) -> int:
        """Fan control subcommand."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not service.has_system_control(device):
            self.print(self.out.error("Device does not support system control"))
            return 1

        if not service.supports_fan_speed(device):
            self.print(self.out.error("Device does not support fan control"))
            return 1

        fan_cmd = getattr(args, "fan_cmd", None)

        if fan_cmd == "auto":
            if service.set_fan_auto(device):
                self.print(self.out.success("Fans set to automatic control"))
                return 0
            else:
                self.print(self.out.error("Failed to set automatic fan control"))
                return 1

        elif fan_cmd == "manual":
            rpm = args.rpm
            fan2_rpm = getattr(args, "fan2", -1)

            # Validate against limits
            limits = service.get_fan_limits(device)
            if limits:
                min_rpm = limits.get("min", 0)
                max_rpm = limits.get("max", 5000)
                if not min_rpm <= rpm <= max_rpm:
                    self.print(self.out.error(f"RPM must be {min_rpm}-{max_rpm}, got {rpm}"))
                    return 1
                if fan2_rpm > 0 and not min_rpm <= fan2_rpm <= max_rpm:
                    self.print(
                        self.out.error(f"Fan2 RPM must be {min_rpm}-{max_rpm}, got {fan2_rpm}")
                    )
                    return 1

            if service.set_fan_rpm(device, rpm, fan2_rpm):
                if fan2_rpm > 0:
                    self.print(self.out.success(f"Fan RPM: {rpm} / {fan2_rpm}"))
                else:
                    self.print(self.out.success(f"Fan RPM: {rpm}"))
                return 0
            else:
                self.print(self.out.error("Failed to set fan RPM"))
                return 1

        else:
            # Show current fan status
            mode = service.get_fan_mode(device)
            rpm = service.get_fan_rpm(device)
            if mode:
                self.print(f"Fan mode: {self.out.device(mode)}")
            if rpm:
                rpm1, rpm2 = rpm
                if rpm2 > 0 and rpm2 != rpm1:
                    self.print(f"Fan RPM: {rpm1} / {rpm2}")
                else:
                    self.print(f"Fan RPM: {rpm1}")
            return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Boost control
    # ─────────────────────────────────────────────────────────────────────────

    def _boost(self, args: Namespace) -> int:
        """Set CPU/GPU boost levels."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not service.has_system_control(device):
            self.print(self.out.error("Device does not support system control"))
            return 1

        if not service.supports_boost(device):
            self.print(self.out.error("Device does not support boost control"))
            return 1

        cpu_mode = getattr(args, "cpu", None)
        gpu_mode = getattr(args, "gpu", None)

        if not cpu_mode and not gpu_mode:
            # Show current boost levels
            cpu = service.get_cpu_boost(device)
            gpu = service.get_gpu_boost(device)
            available = service.get_available_boost_modes(device) or []
            if cpu:
                self.print(f"CPU boost: {self.out.device(cpu)}")
            if gpu:
                self.print(f"GPU boost: {self.out.device(gpu)}")
            if available:
                self.print(f"Available modes: {', '.join(m.lower() for m in available)}")
            return 0

        available = service.get_available_boost_modes(device) or []
        mode_map = {m.lower(): m for m in available}

        if cpu_mode:
            actual = mode_map.get(cpu_mode.lower())
            if not actual:
                self.print(self.out.error(f"Invalid CPU boost mode: {cpu_mode}"))
                if available:
                    self.print(f"Available: {', '.join(m.lower() for m in available)}")
                return 1
            service.set_cpu_boost(device, actual)
            self.print(self.out.success(f"CPU boost: {actual}"))

        if gpu_mode:
            actual = mode_map.get(gpu_mode.lower())
            if not actual:
                self.print(self.out.error(f"Invalid GPU boost mode: {gpu_mode}"))
                if available:
                    self.print(f"Available: {', '.join(m.lower() for m in available)}")
                return 1
            service.set_gpu_boost(device, actual)
            self.print(self.out.success(f"GPU boost: {actual}"))

        return 0
