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

"""Unit tests for MockHIDDevice."""

from __future__ import annotations

import pytest

from .mock_hid import MockHIDContext, MockHIDDevice

# ─────────────────────────────────────────────────────────────────────────────
# MockHIDDevice Basic Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDDeviceBasics:
    """Tests for MockHIDDevice basic functionality."""

    def test_default_values(self):
        """MockHIDDevice should have sensible defaults."""
        mock = MockHIDDevice()
        assert mock.vendor_id == 0x1532
        assert mock.product_id == 0x0001
        assert mock.transaction_id == 0xFF

    def test_custom_values(self):
        """MockHIDDevice should accept custom vendor/product IDs."""
        mock = MockHIDDevice(vendor_id=0x1234, product_id=0x5678)
        assert mock.vendor_id == 0x1234
        assert mock.product_id == 0x5678

    def test_open_device(self):
        """open() should succeed with matching IDs."""
        mock = MockHIDDevice()
        mock.open()
        assert mock._is_open is True

    def test_open_wrong_vendor(self):
        """open() should raise on wrong vendor ID."""
        mock = MockHIDDevice(vendor_id=0x1532)
        with pytest.raises(OSError, match="Device not found"):
            mock.open(vendor_id=0x9999)

    def test_open_wrong_product(self):
        """open() should raise on wrong product ID."""
        mock = MockHIDDevice(product_id=0x0001)
        with pytest.raises(OSError, match="Device not found"):
            mock.open(product_id=0x9999)

    def test_close_device(self):
        """close() should close the device."""
        mock = MockHIDDevice()
        mock.open()
        mock.close()
        assert mock._is_open is False


# ─────────────────────────────────────────────────────────────────────────────
# MockHIDDevice Send/Receive Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDDeviceSendReceive:
    """Tests for MockHIDDevice send/receive functionality."""

    def test_send_report_not_open(self):
        """send_feature_report should raise when device not open."""
        mock = MockHIDDevice()
        with pytest.raises(OSError, match="Device not open"):
            mock.send_feature_report(bytes(90))

    def test_send_report_records_data(self):
        """send_feature_report should record sent data."""
        mock = MockHIDDevice()
        mock.open()
        data = bytes([0x00, 0xFF, 0x00, 0x00, 0x02, 0x00, 0x81])
        mock.send_feature_report(data)
        assert len(mock._received) == 1
        assert mock._received[0] == data

    def test_get_report_not_open(self):
        """get_feature_report should raise when device not open."""
        mock = MockHIDDevice()
        with pytest.raises(OSError, match="Device not open"):
            mock.get_feature_report(0, 90)

    def test_get_report_default_response(self):
        """get_feature_report should return success response by default."""
        mock = MockHIDDevice()
        mock.open()
        # Send a command
        request = bytes([0x00, 0xFF, 0x00, 0x00, 0x02, 0x00, 0x81] + [0] * 83)
        mock.send_feature_report(request)
        # Get response
        response = mock.get_feature_report(0, 90)
        assert response[0] == 0x02  # Success status
        assert response[5] == 0x00  # Command class echoed
        assert response[6] == 0x81  # Command ID echoed


# ─────────────────────────────────────────────────────────────────────────────
# MockHIDDevice Expected Commands Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDDeviceExpectedCommands:
    """Tests for MockHIDDevice expected command handling."""

    def test_expect_command_returns_self(self):
        """expect_command should return self for chaining."""
        mock = MockHIDDevice()
        result = mock.expect_command(0x00, 0x81)
        assert result is mock

    def test_expect_command_with_response(self):
        """expect_command should use provided response."""
        mock = MockHIDDevice()
        mock.open()
        expected_response = MockHIDDevice.firmware_response(1, 5)
        mock.expect_command(0x00, 0x81, response=expected_response)

        # Send the command
        request = bytes([0x00, 0xFF, 0x00, 0x00, 0x02, 0x00, 0x81] + [0] * 83)
        mock.send_feature_report(request)

        # Get response
        response = mock.get_feature_report(0, 90)
        assert response == expected_response

    def test_expect_command_with_handler(self):
        """expect_command should call handler to generate response."""
        mock = MockHIDDevice()
        mock.open()

        def custom_handler(request: bytes) -> bytes:
            response = bytearray(90)
            response[0] = 0x02
            response[7] = 0x42  # Custom data
            return bytes(response)

        mock.expect_command(0x00, 0x82, handler=custom_handler)

        # Send the command
        request = bytes([0x00, 0xFF, 0x00, 0x00, 0x16, 0x00, 0x82] + [0] * 83)
        mock.send_feature_report(request)

        # Get response
        response = mock.get_feature_report(0, 90)
        assert response[7] == 0x42


# ─────────────────────────────────────────────────────────────────────────────
# MockHIDDevice Verification Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDDeviceVerification:
    """Tests for MockHIDDevice command verification."""

    def test_verify_no_expectations(self):
        """verify_commands should succeed with no expectations."""
        mock = MockHIDDevice()
        assert mock.verify_commands() is True

    def test_verify_received_command(self):
        """verify_commands should succeed when expected command received."""
        mock = MockHIDDevice()
        mock.open()
        mock.expect_command(0x00, 0x81)

        # Send the expected command
        request = bytes([0x00, 0xFF, 0x00, 0x00, 0x02, 0x00, 0x81] + [0] * 83)
        mock.send_feature_report(request)

        assert mock.verify_commands() is True

    def test_verify_missing_command(self):
        """verify_commands should fail when expected command not received."""
        mock = MockHIDDevice()
        mock.expect_command(0x00, 0x81)
        assert mock.verify_commands() is False

    def test_get_received_commands(self):
        """get_received_commands should return command details."""
        mock = MockHIDDevice()
        mock.open()

        # Send a command
        request = bytes([0x00, 0xFF, 0x00, 0x00, 0x02, 0x00, 0x81, 0x01, 0x02] + [0] * 81)
        mock.send_feature_report(request)

        commands = mock.get_received_commands()
        assert len(commands) == 1
        assert commands[0][0] == 0x00  # Class
        assert commands[0][1] == 0x81  # ID


# ─────────────────────────────────────────────────────────────────────────────
# MockHIDDevice Response Generator Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDDeviceResponseGenerators:
    """Tests for MockHIDDevice response generator methods."""

    def test_firmware_response(self):
        """firmware_response should create valid firmware response."""
        response = MockHIDDevice.firmware_response(1, 5)
        assert response[0] == 0x02  # Success
        assert response[7] == 1  # Major version
        assert response[8] == 5  # Minor version

    def test_serial_response(self):
        """serial_response should create valid serial response."""
        response = MockHIDDevice.serial_response("XX1234567890")
        assert response[0] == 0x02  # Success
        assert response[7:19] == b"XX1234567890"

    def test_battery_response(self):
        """battery_response should create valid battery response."""
        response = MockHIDDevice.battery_response(200, charging=True)
        assert response[0] == 0x02  # Success
        assert response[7] == 200  # Battery level
        assert response[8] == 0x01  # Charging

    def test_battery_response_not_charging(self):
        """battery_response should handle not charging state."""
        response = MockHIDDevice.battery_response(100, charging=False)
        assert response[8] == 0x00  # Not charging

    def test_brightness_response(self):
        """brightness_response should create valid brightness response."""
        response = MockHIDDevice.brightness_response(128)
        assert response[0] == 0x02  # Success
        assert response[7] == 128  # Brightness


# ─────────────────────────────────────────────────────────────────────────────
# MockHIDDevice Reset Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDDeviceReset:
    """Tests for MockHIDDevice reset functionality."""

    def test_reset_clears_state(self):
        """reset() should clear all state."""
        mock = MockHIDDevice()
        mock.open()
        mock.expect_command(0x00, 0x81)
        mock.send_feature_report(bytes(90))

        mock.reset()

        assert len(mock._expected) == 0
        assert len(mock._received) == 0
        assert mock._last_report is None


# ─────────────────────────────────────────────────────────────────────────────
# MockHIDContext Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMockHIDContext:
    """Tests for MockHIDContext context manager."""

    def test_context_opens_device(self):
        """Context should open device on entry."""
        with MockHIDContext() as mock:
            assert mock._is_open is True

    def test_context_closes_device(self):
        """Context should close device on exit."""
        ctx = MockHIDContext()
        with ctx as mock:
            pass
        assert mock._is_open is False

    def test_context_resets_device(self):
        """Context should reset device on exit."""
        with MockHIDContext() as mock:
            mock.expect_command(0x00, 0x81)
            mock.send_feature_report(bytes(90))

        # After exit, mock should be reset
        assert len(mock._expected) == 0
        assert len(mock._received) == 0

    def test_context_custom_ids(self):
        """Context should accept custom vendor/product IDs."""
        with MockHIDContext(vendor_id=0x1234, product_id=0x5678) as mock:
            assert mock.vendor_id == 0x1234
            assert mock.product_id == 0x5678
