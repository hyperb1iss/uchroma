#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

"""Wireless device support mixin for battery and charging status."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .commands import Commands
from .hardware import Capability, Quirks

if TYPE_CHECKING:
    from .hardware import Hardware


class HasHardwareAndCommands(Protocol):
    """Protocol defining the interface required by WirelessMixin."""

    @property
    def hardware(self) -> Hardware: ...

    def has_quirk(self, *quirks: Quirks) -> bool: ...

    def run_with_result(self, command: Commands, *args: int) -> bytes | None: ...

    def run_command(self, command: Commands, *args: int) -> bool: ...


class WirelessMixin:
    """
    Mixin for wireless device capabilities.

    Provides battery level, charging status, and idle timeout control
    for devices with the WIRELESS quirk or wireless capability.

    This mixin requires the host class to implement:
    - hardware property (Hardware)
    - has_quirk(*quirks) method
    - run_with_result(command, *args) method
    - run_command(command, *args) method
    """

    # Type hints for mixin methods (implemented by host class)
    hardware: Hardware
    has_quirk: HasHardwareAndCommands.has_quirk
    run_with_result: HasHardwareAndCommands.run_with_result
    run_command: HasHardwareAndCommands.run_command

    @property
    def is_wireless(self) -> bool:
        """
        Check if device has wireless capabilities.

        Checks both the new capabilities field and legacy WIRELESS quirk.

        :return: True if device supports wireless features
        """
        if hasattr(self, "hardware") and hasattr(self.hardware, "has_capability"):
            return self.hardware.has_capability(Capability.WIRELESS)
        return self.has_quirk(Quirks.WIRELESS)

    @property
    def battery_level(self) -> float:
        """
        Get battery level as percentage (0-100).

        :return: Battery percentage, or -1.0 if not supported/available
        """
        if not self.is_wireless:
            return -1.0

        result = self.run_with_result(Commands.GET_BATTERY_LEVEL)
        if result is None or len(result) < 2:
            return -1.0

        # Battery is returned as 0-255 in the second byte, convert to percentage
        raw_level = result[1]
        return (raw_level / 255.0) * 100.0

    @property
    def is_charging(self) -> bool:
        """
        Check if device is currently charging.

        :return: True if charging, False otherwise
        """
        if not self.is_wireless:
            return False

        result = self.run_with_result(Commands.GET_CHARGING_STATUS)
        if result is None or len(result) < 2:
            return False

        # 0x01 = charging, 0x00 = not charging
        return result[1] == 0x01

    @property
    def idle_timeout(self) -> int:
        """
        Get idle timeout in seconds.

        The device will enter sleep mode after this many seconds of inactivity.

        :return: Idle timeout in seconds, or 0 if not supported
        """
        if not self.is_wireless:
            return 0

        result = self.run_with_result(Commands.GET_IDLE_TIME)
        if result is None or len(result) < 2:
            return 0

        # Timeout is returned as big-endian 16-bit value
        return (result[0] << 8) | result[1]

    @idle_timeout.setter
    def idle_timeout(self, seconds: int) -> None:
        """
        Set idle timeout in seconds.

        Valid range is 60-900 seconds (1-15 minutes).

        :param seconds: Idle timeout in seconds (clamped to valid range)
        """
        if not self.is_wireless:
            return

        # Clamp to valid range
        seconds = max(60, min(900, seconds))

        # Pack as big-endian 16-bit
        high = (seconds >> 8) & 0xFF
        low = seconds & 0xFF

        self.run_command(Commands.SET_IDLE_TIME, high, low)

    @property
    def low_battery_threshold(self) -> int:
        """
        Get low battery warning threshold percentage.

        :return: Threshold percentage, or 0 if not supported
        """
        if not self.is_wireless:
            return 0

        result = self.run_with_result(Commands.GET_LOW_BATTERY_THRESHOLD)
        if result is None or len(result) < 1:
            return 0

        return result[0]

    @low_battery_threshold.setter
    def low_battery_threshold(self, percent: int) -> None:
        """
        Set low battery warning threshold percentage.

        :param percent: Threshold percentage (clamped to 5-50%)
        """
        if not self.is_wireless:
            return

        # Clamp to valid range
        percent = max(5, min(50, percent))
        self.run_command(Commands.SET_LOW_BATTERY_THRESHOLD, percent)

    def get_battery_info(self) -> dict[str, float | bool | int]:
        """
        Get comprehensive battery information.

        :return: Dictionary with battery_level, is_charging, idle_timeout
        """
        return {
            "battery_level": self.battery_level,
            "is_charging": self.is_charging,
            "idle_timeout": self.idle_timeout,
            "is_wireless": self.is_wireless,
        }
