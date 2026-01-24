#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.polling module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from uchroma.server.commands import Commands
from uchroma.server.hardware import Capability, Quirks
from uchroma.server.polling import (
    HyperPollingRate,
    PollingMixin,
    PollingRate,
)

# ─────────────────────────────────────────────────────────────────────────────
# PollingRate Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPollingRateEnum:
    """Tests for PollingRate enum."""

    def test_hz_125_values(self):
        """HZ_125 should have correct code and rate."""
        assert PollingRate.HZ_125.code == 0x08
        assert PollingRate.HZ_125.rate == 125

    def test_hz_500_values(self):
        """HZ_500 should have correct code and rate."""
        assert PollingRate.HZ_500.code == 0x02
        assert PollingRate.HZ_500.rate == 500

    def test_hz_1000_values(self):
        """HZ_1000 should have correct code and rate."""
        assert PollingRate.HZ_1000.code == 0x01
        assert PollingRate.HZ_1000.rate == 1000

    def test_from_code_found(self):
        """from_code should return correct PollingRate."""
        assert PollingRate.from_code(0x01) == PollingRate.HZ_1000
        assert PollingRate.from_code(0x02) == PollingRate.HZ_500
        assert PollingRate.from_code(0x08) == PollingRate.HZ_125

    def test_from_code_not_found(self):
        """from_code should return None for unknown code."""
        assert PollingRate.from_code(0xFF) is None

    def test_from_rate_found(self):
        """from_rate should return correct PollingRate."""
        assert PollingRate.from_rate(1000) == PollingRate.HZ_1000
        assert PollingRate.from_rate(500) == PollingRate.HZ_500
        assert PollingRate.from_rate(125) == PollingRate.HZ_125

    def test_from_rate_not_found(self):
        """from_rate should return None for unknown rate."""
        assert PollingRate.from_rate(4000) is None


# ─────────────────────────────────────────────────────────────────────────────
# HyperPollingRate Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHyperPollingRateEnum:
    """Tests for HyperPollingRate enum."""

    def test_hz_8000_values(self):
        """HZ_8000 should have correct code and rate."""
        assert HyperPollingRate.HZ_8000.code == 0x01
        assert HyperPollingRate.HZ_8000.rate == 8000

    def test_hz_4000_values(self):
        """HZ_4000 should have correct code and rate."""
        assert HyperPollingRate.HZ_4000.code == 0x02
        assert HyperPollingRate.HZ_4000.rate == 4000

    def test_hz_2000_values(self):
        """HZ_2000 should have correct code and rate."""
        assert HyperPollingRate.HZ_2000.code == 0x04
        assert HyperPollingRate.HZ_2000.rate == 2000

    def test_from_rate_hyperpolling(self):
        """from_rate should find HyperPolling rates."""
        assert HyperPollingRate.from_rate(8000) == HyperPollingRate.HZ_8000
        assert HyperPollingRate.from_rate(4000) == HyperPollingRate.HZ_4000
        assert HyperPollingRate.from_rate(2000) == HyperPollingRate.HZ_2000

    def test_all_hyperpolling_rates(self):
        """All HyperPolling rates should be present."""
        rates = [pr.rate for pr in HyperPollingRate]
        assert 125 in rates
        assert 500 in rates
        assert 1000 in rates
        assert 2000 in rates
        assert 4000 in rates
        assert 8000 in rates


# ─────────────────────────────────────────────────────────────────────────────
# Mock Device with PollingMixin
# ─────────────────────────────────────────────────────────────────────────────


class MockPollingDevice(PollingMixin):
    """Mock device for testing PollingMixin."""

    def __init__(self, has_hyperpolling: bool = False):
        self._has_hyperpolling = has_hyperpolling
        self._mock_results: dict[Commands, bytes | None] = {}
        self._last_command: tuple[Commands, tuple[int, ...]] | None = None

    @property
    def hardware(self):
        mock_hw = MagicMock()
        mock_hw.has_capability = MagicMock(
            side_effect=lambda cap: cap == Capability.HYPERPOLLING and self._has_hyperpolling
        )
        return mock_hw

    def has_quirk(self, *quirks: Quirks) -> bool:
        return Quirks.HYPERPOLLING in quirks and self._has_hyperpolling

    def run_with_result_sync(self, command: Commands, *args: int) -> bytes | None:
        return self._mock_results.get(command)

    def run_command_sync(self, command: Commands, *args: int) -> bool:
        self._last_command = (command, args)
        return True


# ─────────────────────────────────────────────────────────────────────────────
# PollingMixin.supports_hyperpolling Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestSupportsHyperpolling:
    """Tests for PollingMixin.supports_hyperpolling property."""

    def test_supports_hyperpolling_true(self):
        """Device with HYPERPOLLING should return True."""
        device = MockPollingDevice(has_hyperpolling=True)
        assert device.supports_hyperpolling is True

    def test_supports_hyperpolling_false(self):
        """Device without HYPERPOLLING should return False."""
        device = MockPollingDevice(has_hyperpolling=False)
        assert device.supports_hyperpolling is False


# ─────────────────────────────────────────────────────────────────────────────
# PollingMixin.polling_rate Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPollingRateProperty:
    """Tests for PollingMixin.polling_rate property."""

    def test_get_polling_rate_1000(self):
        """Should return 1000Hz when code is 0x01."""
        device = MockPollingDevice()
        device._mock_results[Commands.GET_POLLING_RATE] = bytes([0x01])
        assert device.polling_rate == 1000

    def test_get_polling_rate_500(self):
        """Should return 500Hz when code is 0x02."""
        device = MockPollingDevice()
        device._mock_results[Commands.GET_POLLING_RATE] = bytes([0x02])
        assert device.polling_rate == 500

    def test_get_polling_rate_125(self):
        """Should return 125Hz when code is 0x08."""
        device = MockPollingDevice()
        device._mock_results[Commands.GET_POLLING_RATE] = bytes([0x08])
        assert device.polling_rate == 125

    def test_get_polling_rate_hyperpolling(self):
        """Should return HyperPolling rate for HP device."""
        device = MockPollingDevice(has_hyperpolling=True)
        device._mock_results[Commands.GET_POLLING_RATE] = bytes([0x01])  # 8000Hz in HP
        assert device.polling_rate == 8000

    def test_get_polling_rate_no_response(self):
        """Should return 0 when no response."""
        device = MockPollingDevice()
        device._mock_results[Commands.GET_POLLING_RATE] = None
        assert device.polling_rate == 0


# ─────────────────────────────────────────────────────────────────────────────
# PollingMixin.set_polling_rate Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestSetPollingRate:
    """Tests for PollingMixin.polling_rate setter."""

    def test_set_polling_rate_1000(self):
        """Setting 1000Hz should send correct command."""
        device = MockPollingDevice()
        device.polling_rate = 1000
        assert device._last_command is not None
        assert device._last_command[0] == Commands.SET_POLLING_RATE
        assert device._last_command[1] == (0x01,)

    def test_set_polling_rate_500(self):
        """Setting 500Hz should send correct command."""
        device = MockPollingDevice()
        device.polling_rate = 500
        assert device._last_command is not None
        assert device._last_command[0] == Commands.SET_POLLING_RATE
        assert device._last_command[1] == (0x02,)

    def test_set_polling_rate_invalid(self):
        """Setting invalid rate should raise ValueError."""
        device = MockPollingDevice()
        with pytest.raises(ValueError, match="Invalid polling rate"):
            device.polling_rate = 4000  # Not supported on non-HP device


# ─────────────────────────────────────────────────────────────────────────────
# PollingMixin.get_available_rates Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAvailableRates:
    """Tests for PollingMixin.get_available_rates method."""

    def test_standard_rates(self):
        """Standard device should return standard rates."""
        device = MockPollingDevice(has_hyperpolling=False)
        rates = device.get_available_rates()
        assert 125 in rates
        assert 500 in rates
        assert 1000 in rates
        assert 2000 not in rates
        assert 4000 not in rates

    def test_hyperpolling_rates(self):
        """HyperPolling device should return all rates."""
        device = MockPollingDevice(has_hyperpolling=True)
        rates = device.get_available_rates()
        assert 125 in rates
        assert 500 in rates
        assert 1000 in rates
        assert 2000 in rates
        assert 4000 in rates
        assert 8000 in rates


# ─────────────────────────────────────────────────────────────────────────────
# PollingMixin.get_polling_info Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetPollingInfo:
    """Tests for PollingMixin.get_polling_info method."""

    def test_get_polling_info(self):
        """Should return comprehensive polling information."""
        device = MockPollingDevice(has_hyperpolling=True)
        device._mock_results[Commands.GET_POLLING_RATE] = bytes([0x01])

        info = device.get_polling_info()
        assert info["polling_rate"] == 8000  # 0x01 = 8000Hz for HyperPolling
        assert info["supports_hyperpolling"] is True
        assert 8000 in info["available_rates"]
