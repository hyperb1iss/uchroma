#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.wireless module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from uchroma.server.commands import Commands
from uchroma.server.hardware import Capability, Quirks
from uchroma.server.wireless import WirelessMixin

# ─────────────────────────────────────────────────────────────────────────────
# Mock Device with WirelessMixin
# ─────────────────────────────────────────────────────────────────────────────


class MockWirelessDevice(WirelessMixin):
    """Mock device for testing WirelessMixin."""

    def __init__(self, is_wireless: bool = True):
        self._is_wireless = is_wireless
        self._mock_results: dict[Commands, bytes | None] = {}

    @property
    def hardware(self):
        mock_hw = MagicMock()
        mock_hw.has_capability = MagicMock(
            side_effect=lambda cap: cap == Capability.WIRELESS and self._is_wireless
        )
        return mock_hw

    def has_quirk(self, *quirks: Quirks) -> bool:
        return Quirks.WIRELESS in quirks and self._is_wireless

    def run_with_result(self, command: Commands, *args: int) -> bytes | None:
        return self._mock_results.get(command)

    def run_command(self, command: Commands, *args: int) -> bool:
        return True


# ─────────────────────────────────────────────────────────────────────────────
# WirelessMixin.is_wireless Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIsWireless:
    """Tests for WirelessMixin.is_wireless property."""

    def test_is_wireless_true(self):
        """Device with WIRELESS capability should return True."""
        device = MockWirelessDevice(is_wireless=True)
        assert device.is_wireless is True

    def test_is_wireless_false(self):
        """Device without WIRELESS capability should return False."""
        device = MockWirelessDevice(is_wireless=False)
        assert device.is_wireless is False


# ─────────────────────────────────────────────────────────────────────────────
# WirelessMixin.battery_level Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBatteryLevel:
    """Tests for WirelessMixin.battery_level property."""

    def test_battery_level_full(self):
        """Full battery should return 100%."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_BATTERY_LEVEL] = bytes([0x00, 0xFF])
        assert device.battery_level == pytest.approx(100.0)

    def test_battery_level_half(self):
        """Half battery should return ~50%."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_BATTERY_LEVEL] = bytes([0x00, 0x80])
        assert device.battery_level == pytest.approx(50.196, rel=0.01)

    def test_battery_level_empty(self):
        """Empty battery should return 0%."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_BATTERY_LEVEL] = bytes([0x00, 0x00])
        assert device.battery_level == pytest.approx(0.0)

    def test_battery_level_not_wireless(self):
        """Non-wireless device should return -1."""
        device = MockWirelessDevice(is_wireless=False)
        assert device.battery_level == -1.0

    def test_battery_level_no_response(self):
        """No response should return -1."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_BATTERY_LEVEL] = None
        assert device.battery_level == -1.0


# ─────────────────────────────────────────────────────────────────────────────
# WirelessMixin.is_charging Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIsCharging:
    """Tests for WirelessMixin.is_charging property."""

    def test_is_charging_true(self):
        """Device charging should return True."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_CHARGING_STATUS] = bytes([0x00, 0x01])
        assert device.is_charging is True

    def test_is_charging_false(self):
        """Device not charging should return False."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_CHARGING_STATUS] = bytes([0x00, 0x00])
        assert device.is_charging is False

    def test_is_charging_not_wireless(self):
        """Non-wireless device should return False."""
        device = MockWirelessDevice(is_wireless=False)
        assert device.is_charging is False


# ─────────────────────────────────────────────────────────────────────────────
# WirelessMixin.idle_timeout Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIdleTimeout:
    """Tests for WirelessMixin.idle_timeout property."""

    def test_idle_timeout_get(self):
        """Should return idle timeout in seconds."""
        device = MockWirelessDevice()
        # 300 seconds = 0x012C big-endian
        device._mock_results[Commands.GET_IDLE_TIME] = bytes([0x01, 0x2C])
        assert device.idle_timeout == 300

    def test_idle_timeout_not_wireless(self):
        """Non-wireless device should return 0."""
        device = MockWirelessDevice(is_wireless=False)
        assert device.idle_timeout == 0


# ─────────────────────────────────────────────────────────────────────────────
# WirelessMixin.get_battery_info Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetBatteryInfo:
    """Tests for WirelessMixin.get_battery_info method."""

    def test_get_battery_info(self):
        """Should return comprehensive battery information."""
        device = MockWirelessDevice()
        device._mock_results[Commands.GET_BATTERY_LEVEL] = bytes([0x00, 0xFF])
        device._mock_results[Commands.GET_CHARGING_STATUS] = bytes([0x00, 0x01])
        device._mock_results[Commands.GET_IDLE_TIME] = bytes([0x01, 0x2C])

        info = device.get_battery_info()
        assert info["is_wireless"] is True
        assert info["battery_level"] == pytest.approx(100.0)
        assert info["is_charging"] is True
        assert info["idle_timeout"] == 300
