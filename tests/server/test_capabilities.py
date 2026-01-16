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

"""Unit tests for uchroma.server.capabilities module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from uchroma.server.capabilities import DeviceCapabilities, get_device_capabilities
from uchroma.server.hardware import Capability, Hardware, Point

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_device():
    """Create a mock device for testing."""
    device = MagicMock()
    device.hardware = MagicMock(spec=Hardware)
    device.hardware.dimensions = Point(6, 22)
    device.hardware.supported_leds = ("backlight", "logo")
    device.has_matrix = True

    # Default capability responses
    device.hardware.has_capability = MagicMock(return_value=False)
    device.hardware.has_leds = True
    device.hardware.uses_extended_fx = False
    device.hardware.get_supported_effects = MagicMock(return_value=("static", "wave", "breathe"))
    device.hardware.supports_effect = MagicMock(
        side_effect=lambda e: e.lower() in ("static", "wave", "breathe")
    )
    device.hardware.get_protocol_config = MagicMock()
    device.hardware.get_protocol_config.return_value.version.value = "legacy"
    device.hardware.get_protocol_config.return_value.transaction_id = 0xFF

    return device


@pytest.fixture
def wireless_device(mock_device):
    """Create a mock wireless device."""
    mock_device.hardware.has_capability = MagicMock(side_effect=lambda c: c == Capability.WIRELESS)
    return mock_device


@pytest.fixture
def hyperpolling_device(mock_device):
    """Create a mock HyperPolling device."""
    mock_device.hardware.has_capability = MagicMock(
        side_effect=lambda c: c == Capability.HYPERPOLLING
    )
    return mock_device


# ─────────────────────────────────────────────────────────────────────────────
# DeviceCapabilities LED Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeviceCapabilitiesLEDs:
    """Tests for LED-related capabilities."""

    def test_has_leds_true(self, mock_device):
        """Device with LEDs should return True."""
        caps = DeviceCapabilities(mock_device)
        assert caps.has_leds is True

    def test_has_leds_false_no_led_capability(self, mock_device):
        """Device with NO_LED capability should return False."""
        mock_device.hardware.has_capability = MagicMock(
            side_effect=lambda c: c == Capability.NO_LED
        )
        caps = DeviceCapabilities(mock_device)
        assert caps.has_leds is False

    def test_has_matrix_true(self, mock_device):
        """Device with matrix should return True."""
        caps = DeviceCapabilities(mock_device)
        assert caps.has_matrix is True

    def test_has_matrix_false(self, mock_device):
        """Device without matrix should return False."""
        mock_device.has_matrix = False
        caps = DeviceCapabilities(mock_device)
        assert caps.has_matrix is False

    def test_matrix_dimensions(self, mock_device):
        """Should return correct matrix dimensions."""
        caps = DeviceCapabilities(mock_device)
        dims = caps.matrix_dimensions
        assert dims == (6, 22)

    def test_matrix_dimensions_none(self, mock_device):
        """Should return None when no dimensions."""
        mock_device.hardware.dimensions = None
        caps = DeviceCapabilities(mock_device)
        assert caps.matrix_dimensions is None

    def test_is_single_led(self, mock_device):
        """Should detect single LED devices."""
        mock_device.hardware.has_capability = MagicMock(
            side_effect=lambda c: c == Capability.SINGLE_LED
        )
        caps = DeviceCapabilities(mock_device)
        assert caps.is_single_led is True


# ─────────────────────────────────────────────────────────────────────────────
# DeviceCapabilities Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeviceCapabilitiesEffects:
    """Tests for effect-related capabilities."""

    def test_has_hardware_effect_true(self, mock_device):
        """Should return True for supported effect."""
        caps = DeviceCapabilities(mock_device)
        assert caps.has_hardware_effect("static") is True
        assert caps.has_hardware_effect("wave") is True

    def test_has_hardware_effect_false(self, mock_device):
        """Should return False for unsupported effect."""
        caps = DeviceCapabilities(mock_device)
        assert caps.has_hardware_effect("unknown") is False

    def test_has_hardware_effect_caching(self, mock_device):
        """Should cache effect test results."""
        caps = DeviceCapabilities(mock_device)
        caps.has_hardware_effect("static")
        caps.has_hardware_effect("static")  # Second call
        # Should only call hardware once (caching)
        assert "static" in caps._tested_effects

    def test_requires_software_effects(self, mock_device):
        """Should detect software effect requirement."""
        mock_device.hardware.has_capability = MagicMock(
            side_effect=lambda c: c == Capability.SOFTWARE_EFFECTS
        )
        caps = DeviceCapabilities(mock_device)
        assert caps.requires_software_effects is True

    def test_supported_effects_from_config(self, mock_device):
        """Should return effects from device config."""
        caps = DeviceCapabilities(mock_device)
        effects = caps.supported_effects
        assert "static" in effects
        assert "wave" in effects
        assert "breathe" in effects

    def test_uses_extended_fx(self, mock_device):
        """Should detect extended FX usage."""
        mock_device.hardware.uses_extended_fx = True
        caps = DeviceCapabilities(mock_device)
        assert caps.uses_extended_fx is True


# ─────────────────────────────────────────────────────────────────────────────
# DeviceCapabilities Connectivity Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeviceCapabilitiesConnectivity:
    """Tests for connectivity-related capabilities."""

    def test_is_wireless(self, wireless_device):
        """Should detect wireless capability."""
        caps = DeviceCapabilities(wireless_device)
        assert caps.is_wireless is True

    def test_is_not_wireless(self, mock_device):
        """Should return False when not wireless."""
        caps = DeviceCapabilities(mock_device)
        assert caps.is_wireless is False

    def test_supports_hyperpolling(self, hyperpolling_device):
        """Should detect HyperPolling support."""
        caps = DeviceCapabilities(hyperpolling_device)
        assert caps.supports_hyperpolling is True


# ─────────────────────────────────────────────────────────────────────────────
# DeviceCapabilities Input Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeviceCapabilitiesInput:
    """Tests for input-related capabilities."""

    def test_has_analog_keys(self, mock_device):
        """Should detect analog keys."""
        mock_device.hardware.has_capability = MagicMock(
            side_effect=lambda c: c == Capability.ANALOG_KEYS
        )
        caps = DeviceCapabilities(mock_device)
        assert caps.has_analog_keys is True

    def test_has_profile_leds(self, mock_device):
        """Should detect profile LEDs."""
        mock_device.hardware.has_capability = MagicMock(
            side_effect=lambda c: c == Capability.PROFILE_LEDS
        )
        caps = DeviceCapabilities(mock_device)
        assert caps.has_profile_leds is True


# ─────────────────────────────────────────────────────────────────────────────
# DeviceCapabilities Protocol Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeviceCapabilitiesProtocol:
    """Tests for protocol-related capabilities."""

    def test_protocol_version(self, mock_device):
        """Should return protocol version string."""
        caps = DeviceCapabilities(mock_device)
        assert caps.protocol_version == "legacy"

    def test_transaction_id(self, mock_device):
        """Should return transaction ID."""
        caps = DeviceCapabilities(mock_device)
        assert caps.transaction_id == 0xFF


# ─────────────────────────────────────────────────────────────────────────────
# DeviceCapabilities.get_all_capabilities Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAllCapabilities:
    """Tests for get_all_capabilities method."""

    def test_returns_dict(self, mock_device):
        """Should return a dictionary."""
        caps = DeviceCapabilities(mock_device)
        all_caps = caps.get_all_capabilities()
        assert isinstance(all_caps, dict)

    def test_contains_all_keys(self, mock_device):
        """Should contain all expected keys."""
        caps = DeviceCapabilities(mock_device)
        all_caps = caps.get_all_capabilities()

        expected_keys = [
            "has_leds",
            "has_matrix",
            "is_single_led",
            "matrix_dimensions",
            "uses_extended_fx",
            "requires_software_effects",
            "supported_effects",
            "is_wireless",
            "supports_hyperpolling",
            "has_analog_keys",
            "has_profile_leds",
            "protocol_version",
            "transaction_id",
        ]

        for key in expected_keys:
            assert key in all_caps, f"Missing key: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# get_device_capabilities Factory Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDeviceCapabilities:
    """Tests for get_device_capabilities factory function."""

    def test_creates_device_capabilities(self, mock_device):
        """Should create DeviceCapabilities instance."""
        caps = get_device_capabilities(mock_device)
        assert isinstance(caps, DeviceCapabilities)
        assert caps.device is mock_device
