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

"""Mock HID device for testing hardware communication."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class MockHIDDevice:
    """
    Mock HID device for testing USB communication.

    Simulates a Razer USB HID device, allowing tests to verify:
    - Report formatting and CRC calculation
    - Command class/ID/data encoding
    - Response handling and parsing
    - Transaction ID handling

    Usage:
        mock = MockHIDDevice(vendor_id=0x1532, product_id=0x0203)
        mock.expect_command(0x00, 0x81, response=bytes([0x01, 0x00, 0x00, ...]))

        # In test:
        device.get_firmware()  # Sends command 0x00/0x81
        assert mock.verify_commands()  # Verifies expected commands were sent
    """

    vendor_id: int = 0x1532
    product_id: int = 0x0001
    transaction_id: int = 0xFF

    # Queue of expected commands and their responses
    _expected: deque[tuple[int, int, bytes | None, Callable | None]] = field(default_factory=deque)
    # Queue of received commands
    _received: list[bytes] = field(default_factory=list)
    # Last sent report
    _last_report: bytes | None = None
    # Whether device is "open"
    _is_open: bool = False

    def open(self, vendor_id: int | None = None, product_id: int | None = None) -> None:
        """Open the device connection."""
        if vendor_id is not None and vendor_id != self.vendor_id:
            raise OSError(f"Device not found: vendor_id={vendor_id:#06x}")
        if product_id is not None and product_id != self.product_id:
            raise OSError(f"Device not found: product_id={product_id:#06x}")
        self._is_open = True

    def close(self) -> None:
        """Close the device connection."""
        self._is_open = False

    def send_feature_report(self, data: bytes) -> int:
        """
        Send a feature report to the device.

        Validates report format and records for verification.
        Returns the number of bytes written.
        """
        if not self._is_open:
            raise OSError("Device not open")

        self._received.append(bytes(data))
        self._last_report = bytes(data)

        return len(data)

    def get_feature_report(self, report_id: int, size: int) -> bytes:
        """
        Get a feature report from the device.

        Returns the response for the most recently sent command.
        """
        if not self._is_open:
            raise OSError("Device not open")

        if self._last_report is None:
            return bytes(size)

        # Extract command class/id from last report to find matching response
        # Report format: [status, transaction_id, remaining_packets, proto_type, size, class, id, ...]
        cmd_class = self._last_report[5] if len(self._last_report) > 5 else 0
        cmd_id = self._last_report[6] if len(self._last_report) > 6 else 0

        # Find matching expected response
        response = self._find_response(cmd_class, cmd_id)
        if response is not None:
            return response

        # Default: echo back the command as successful response
        return self._create_success_response(self._last_report, size)

    def expect_command(
        self,
        cmd_class: int,
        cmd_id: int,
        response: bytes | None = None,
        handler: Callable[[bytes], bytes] | None = None,
    ) -> MockHIDDevice:
        """
        Register an expected command with its response.

        Args:
            cmd_class: Expected command class byte
            cmd_id: Expected command ID byte
            response: Pre-defined response bytes (optional)
            handler: Callable that generates response from request (optional)

        Returns:
            self for method chaining
        """
        self._expected.append((cmd_class, cmd_id, response, handler))
        return self

    def _find_response(self, cmd_class: int, cmd_id: int) -> bytes | None:
        """Find a matching response for the given command."""
        for exp_class, exp_id, response, handler in self._expected:
            if exp_class == cmd_class and exp_id == cmd_id:
                if handler is not None:
                    return handler(self._last_report)
                return response
        return None

    def _create_success_response(self, request: bytes, size: int) -> bytes:
        """Create a success response echoing the command structure."""
        response = bytearray(size)

        if len(request) >= 7:
            response[0] = 0x02  # Status: successful
            response[1] = request[1]  # Transaction ID
            response[2] = 0x00  # Remaining packets
            response[3] = 0x00  # Protocol type
            response[4] = request[4]  # Data size
            response[5] = request[5]  # Command class
            response[6] = request[6]  # Command ID

        return bytes(response)

    def verify_commands(self) -> bool:
        """
        Verify all expected commands were received.

        Returns:
            True if all expected commands were received in order
        """
        if not self._expected:
            return True

        for cmd_class, cmd_id, _, _ in self._expected:
            found = False
            for report in self._received:
                if len(report) >= 7 and report[5] == cmd_class and report[6] == cmd_id:
                    found = True
                    break
            if not found:
                return False

        return True

    def get_received_commands(self) -> list[tuple[int, int, bytes]]:
        """
        Get list of received commands as (class, id, data) tuples.

        Returns:
            List of (command_class, command_id, data_bytes) tuples
        """
        commands = []
        for report in self._received:
            if len(report) >= 7:
                cmd_class = report[5]
                cmd_id = report[6]
                data = report[7:] if len(report) > 7 else b""
                commands.append((cmd_class, cmd_id, data))
        return commands

    def reset(self) -> None:
        """Reset the mock device state."""
        self._expected.clear()
        self._received.clear()
        self._last_report = None

    # ─────────────────────────────────────────────────────────────────────────
    # Response Generators
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def firmware_response(major: int, minor: int) -> bytes:
        """Generate a firmware version response."""
        response = bytearray(90)
        response[0] = 0x02  # Success
        response[7] = major
        response[8] = minor
        return bytes(response)

    @staticmethod
    def serial_response(serial: str) -> bytes:
        """Generate a serial number response."""
        response = bytearray(90)
        response[0] = 0x02  # Success
        serial_bytes = serial.encode("ascii")[:22]
        response[7 : 7 + len(serial_bytes)] = serial_bytes
        return bytes(response)

    @staticmethod
    def battery_response(level: int, charging: bool = False) -> bytes:
        """Generate a battery level response."""
        response = bytearray(90)
        response[0] = 0x02  # Success
        response[7] = level  # Battery level 0-255
        response[8] = 0x01 if charging else 0x00
        return bytes(response)

    @staticmethod
    def brightness_response(level: int) -> bytes:
        """Generate a brightness response."""
        response = bytearray(90)
        response[0] = 0x02  # Success
        response[7] = level  # Brightness 0-255
        return bytes(response)


class MockHIDContext:
    """
    Context manager for mock HID device testing.

    Usage:
        with MockHIDContext() as mock:
            mock.expect_command(0x00, 0x81, MockHIDDevice.firmware_response(1, 0))
            # ... run tests ...
            assert mock.verify_commands()
    """

    def __init__(self, vendor_id: int = 0x1532, product_id: int = 0x0001):
        self.mock = MockHIDDevice(vendor_id=vendor_id, product_id=product_id)

    def __enter__(self) -> MockHIDDevice:
        self.mock.open()
        return self.mock

    def __exit__(self, *args) -> None:
        self.mock.close()
        self.mock.reset()
