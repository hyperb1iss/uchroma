#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Polling rate control mixin for mice and keyboards."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING

from .commands import Commands
from .hardware import Capability, Quirks

if TYPE_CHECKING:
    from .hardware import Hardware


class PollingRate(Enum):
    """
    Standard USB polling rates.

    Each value is a tuple of (command_code, rate_in_hz).
    """

    HZ_125 = (0x08, 125)
    HZ_500 = (0x02, 500)
    HZ_1000 = (0x01, 1000)

    def __init__(self, code: int, rate: int):
        self._code = code
        self._rate = rate

    @property
    def code(self) -> int:
        """Command code for this polling rate."""
        return self._code

    @property
    def rate(self) -> int:
        """Polling rate in Hz."""
        return self._rate

    @classmethod
    def from_code(cls, code: int) -> PollingRate | None:
        """Get PollingRate from command code."""
        for pr in cls:
            if pr.code == code:
                return pr
        return None

    @classmethod
    def from_rate(cls, hz: int) -> PollingRate | None:
        """Get PollingRate from Hz value."""
        for pr in cls:
            if pr.rate == hz:
                return pr
        return None


class HyperPollingRate(Enum):
    """
    HyperPolling rates for devices with HyperPolling dongle.

    Supports up to 8000Hz polling rates on compatible devices.
    Each value is a tuple of (command_code, rate_in_hz).
    """

    HZ_125 = (0x40, 125)
    HZ_500 = (0x10, 500)
    HZ_1000 = (0x08, 1000)
    HZ_2000 = (0x04, 2000)
    HZ_4000 = (0x02, 4000)
    HZ_8000 = (0x01, 8000)

    def __init__(self, code: int, rate: int):
        self._code = code
        self._rate = rate

    @property
    def code(self) -> int:
        """Command code for this polling rate."""
        return self._code

    @property
    def rate(self) -> int:
        """Polling rate in Hz."""
        return self._rate

    @classmethod
    def from_code(cls, code: int) -> HyperPollingRate | None:
        """Get HyperPollingRate from command code."""
        for pr in cls:
            if pr.code == code:
                return pr
        return None

    @classmethod
    def from_rate(cls, hz: int) -> HyperPollingRate | None:
        """Get HyperPollingRate from Hz value."""
        for pr in cls:
            if pr.rate == hz:
                return pr
        return None


class PollingMixin:
    """
    Mixin for polling rate control.

    Provides standard and HyperPolling rate control for mice
    and keyboards that support it.

    This mixin requires the host class to implement:
    - hardware property (Hardware)
    - has_quirk(*quirks) method
    - run_with_result(command, *args) method
    - run_command(command, *args) method
    """

    # These methods must be provided by the host class (see protocols.HasHardwareAndCommands)
    hardware: Hardware
    has_quirk: Callable[..., bool]
    run_with_result: Callable[..., bytes | None]
    run_command: Callable[..., bool]

    @property
    def supports_hyperpolling(self) -> bool:
        """
        Check if device supports HyperPolling rates.

        :return: True if device supports rates > 1000Hz
        """
        if hasattr(self, "hardware") and hasattr(self.hardware, "has_capability"):
            return self.hardware.has_capability(Capability.HYPERPOLLING)
        return self.has_quirk(Quirks.HYPERPOLLING)

    @property
    def polling_rate(self) -> int:
        """
        Get current polling rate in Hz.

        :return: Polling rate in Hz, or 0 if query failed
        """
        result = self.run_with_result(Commands.GET_POLLING_RATE)
        if result is None or len(result) < 1:
            return 0

        code = result[0]

        # Try HyperPolling rates first if supported
        if self.supports_hyperpolling:
            hp_rate = HyperPollingRate.from_code(code)
            if hp_rate is not None:
                return hp_rate.rate

        # Fall back to standard rates
        std_rate = PollingRate.from_code(code)
        if std_rate is not None:
            return std_rate.rate

        return 0

    @polling_rate.setter
    def polling_rate(self, rate: int) -> None:
        """
        Set polling rate in Hz.

        :param rate: Polling rate in Hz
        :raises ValueError: If rate is not a valid polling rate
        """
        # Try HyperPolling rates first if supported
        if self.supports_hyperpolling:
            hp_rate = HyperPollingRate.from_rate(rate)
            if hp_rate is not None:
                self.run_command(Commands.SET_POLLING_RATE, hp_rate.code)
                return

        # Fall back to standard rates
        std_rate = PollingRate.from_rate(rate)
        if std_rate is not None:
            self.run_command(Commands.SET_POLLING_RATE, std_rate.code)
            return

        valid_rates = self.get_available_rates()
        raise ValueError(f"Invalid polling rate: {rate}. Valid rates: {valid_rates}")

    def get_available_rates(self) -> list[int]:
        """
        Get list of available polling rates for this device.

        :return: List of available polling rates in Hz
        """
        if self.supports_hyperpolling:
            return [pr.rate for pr in HyperPollingRate]
        return [pr.rate for pr in PollingRate]

    def set_polling_rate_125(self) -> bool:
        """Set polling rate to 125Hz."""
        try:
            self.polling_rate = 125
            return True
        except ValueError:
            return False

    def set_polling_rate_500(self) -> bool:
        """Set polling rate to 500Hz."""
        try:
            self.polling_rate = 500
            return True
        except ValueError:
            return False

    def set_polling_rate_1000(self) -> bool:
        """Set polling rate to 1000Hz."""
        try:
            self.polling_rate = 1000
            return True
        except ValueError:
            return False

    def get_polling_info(self) -> dict[str, int | bool | list[int]]:
        """
        Get comprehensive polling rate information.

        :return: Dictionary with current rate, available rates, and HyperPolling support
        """
        return {
            "polling_rate": self.polling_rate,
            "available_rates": self.get_available_rates(),
            "supports_hyperpolling": self.supports_hyperpolling,
        }
