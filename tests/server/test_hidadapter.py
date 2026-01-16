#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.hidadapter module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from uchroma.server.hidadapter import Device, DeviceInfo, enumerate

# ─────────────────────────────────────────────────────────────────────────────
# DeviceInfo Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeviceInfo:
    """Tests for DeviceInfo class."""

    @pytest.fixture
    def sample_info_dict(self):
        """Sample device info dictionary."""
        return {
            "path": b"/dev/hidraw0",
            "vendor_id": 0x1532,
            "product_id": 0x0227,
            "serial_number": "XX00000001",
            "release_number": 0x0200,
            "manufacturer_string": "Razer",
            "product_string": "BlackWidow Chroma",
            "usage_page": 0x0001,
            "usage": 0x0006,
            "interface_number": 2,
        }

    @pytest.fixture
    def device_info(self, sample_info_dict):
        """Create a DeviceInfo instance."""
        return DeviceInfo(sample_info_dict)

    def test_path_property(self, device_info):
        """path returns the device path."""
        assert device_info.path == b"/dev/hidraw0"

    def test_vendor_id_property(self, device_info):
        """vendor_id returns the vendor ID."""
        assert device_info.vendor_id == 0x1532

    def test_product_id_property(self, device_info):
        """product_id returns the product ID."""
        assert device_info.product_id == 0x0227

    def test_serial_number_property(self, device_info):
        """serial_number returns the serial."""
        assert device_info.serial_number == "XX00000001"

    def test_serial_number_default(self):
        """serial_number defaults to empty string."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.serial_number == ""

    def test_release_number_property(self, device_info):
        """release_number returns the release."""
        assert device_info.release_number == 0x0200

    def test_release_number_default(self):
        """release_number defaults to 0."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.release_number == 0

    def test_manufacturer_string_property(self, device_info):
        """manufacturer_string returns the manufacturer."""
        assert device_info.manufacturer_string == "Razer"

    def test_manufacturer_string_default(self):
        """manufacturer_string defaults to empty string."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.manufacturer_string == ""

    def test_product_string_property(self, device_info):
        """product_string returns the product name."""
        assert device_info.product_string == "BlackWidow Chroma"

    def test_product_string_default(self):
        """product_string defaults to empty string."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.product_string == ""

    def test_usage_page_property(self, device_info):
        """usage_page returns the HID usage page."""
        assert device_info.usage_page == 0x0001

    def test_usage_page_default(self):
        """usage_page defaults to 0."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.usage_page == 0

    def test_usage_property(self, device_info):
        """usage returns the HID usage."""
        assert device_info.usage == 0x0006

    def test_usage_default(self):
        """usage defaults to 0."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.usage == 0

    def test_interface_number_property(self, device_info):
        """interface_number returns the USB interface."""
        assert device_info.interface_number == 2

    def test_interface_number_default(self):
        """interface_number defaults to -1."""
        info = DeviceInfo({"path": b"/test", "vendor_id": 1, "product_id": 2})
        assert info.interface_number == -1

    def test_repr(self, device_info):
        """__repr__ includes key info."""
        r = repr(device_info)
        assert "DeviceInfo" in r
        assert "0x1532" in r
        assert "0x0227" in r
        assert "interface=2" in r


# ─────────────────────────────────────────────────────────────────────────────
# Device Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDevice:
    """Tests for Device class."""

    @pytest.fixture
    def mock_hid_device(self):
        """Create a mock hid.Device."""
        mock = MagicMock()
        mock.nonblocking = False
        return mock

    @pytest.fixture
    def device_info(self):
        """Create a DeviceInfo for testing."""
        return DeviceInfo(
            {
                "path": b"/dev/hidraw0",
                "vendor_id": 0x1532,
                "product_id": 0x0227,
            }
        )

    @pytest.fixture
    def device(self, device_info, mock_hid_device):
        """Create a Device for testing."""
        with patch("uchroma.server.hidadapter.hid.Device", return_value=mock_hid_device):
            return Device(device_info, blocking=True)

    def test_init_opens_device(self, device_info):
        """Device opens HID device on init."""
        with patch("uchroma.server.hidadapter.hid.Device") as mock_hid:
            mock_hid.return_value = MagicMock()
            Device(device_info)
            mock_hid.assert_called_once_with(path=b"/dev/hidraw0")

    def test_init_sets_nonblocking(self, device_info):
        """Device sets nonblocking mode on init."""
        mock = MagicMock()
        with patch("uchroma.server.hidadapter.hid.Device", return_value=mock):
            Device(device_info, blocking=False)
            assert mock.nonblocking is True

    def test_close(self, device, mock_hid_device):
        """close closes the device."""
        device.close()
        mock_hid_device.close.assert_called_once()
        assert device._device is None

    def test_write_basic(self, device, mock_hid_device):
        """write sends data to device."""
        mock_hid_device.write.return_value = 5
        result = device.write(b"\x01\x02\x03")
        mock_hid_device.write.assert_called_once_with(b"\x01\x02\x03")
        assert result == 5

    def test_write_with_report_id_int(self, device, mock_hid_device):
        """write prepends int report_id."""
        mock_hid_device.write.return_value = 4
        device.write(b"\x01\x02\x03", report_id=0x00)
        mock_hid_device.write.assert_called_once_with(b"\x00\x01\x02\x03")

    def test_write_with_report_id_bytes(self, device, mock_hid_device):
        """write prepends bytes report_id."""
        mock_hid_device.write.return_value = 4
        device.write(b"\x01\x02\x03", report_id=b"\x00")
        mock_hid_device.write.assert_called_once_with(b"\x00\x01\x02\x03")

    def test_read_basic(self, device, mock_hid_device):
        """read returns data from device."""
        mock_hid_device.read.return_value = [0x01, 0x02, 0x03]
        result = device.read(3)
        assert result == b"\x01\x02\x03"

    def test_read_with_timeout(self, device, mock_hid_device):
        """read passes timeout to device."""
        mock_hid_device.read.return_value = [0x01]
        device.read(1, timeout_ms=100)
        mock_hid_device.read.assert_called_once_with(1, 100)

    def test_send_feature_report_basic(self, device, mock_hid_device):
        """send_feature_report sends feature report."""
        mock_hid_device.send_feature_report.return_value = 5
        result = device.send_feature_report(b"\x01\x02\x03")
        mock_hid_device.send_feature_report.assert_called_once_with(b"\x01\x02\x03")
        assert result == 5

    def test_send_feature_report_with_report_id_int(self, device, mock_hid_device):
        """send_feature_report prepends int report_id."""
        device.send_feature_report(b"\x01\x02\x03", report_id=0x00)
        mock_hid_device.send_feature_report.assert_called_once_with(b"\x00\x01\x02\x03")

    def test_send_feature_report_with_report_id_bytes(self, device, mock_hid_device):
        """send_feature_report prepends bytes report_id."""
        device.send_feature_report(b"\x01\x02\x03", report_id=b"\x00")
        mock_hid_device.send_feature_report.assert_called_once_with(b"\x00\x01\x02\x03")

    def test_get_feature_report_strips_report_id(self, device, mock_hid_device):
        """get_feature_report strips report_id from result."""
        # New API returns report ID as first byte
        mock_hid_device.get_feature_report.return_value = [0x00, 0x01, 0x02, 0x03]
        result = device.get_feature_report(0x00, 3)
        # Should strip the first byte
        assert result == b"\x01\x02\x03"

    def test_get_feature_report_bytes_report_id(self, device, mock_hid_device):
        """get_feature_report handles bytes report_id."""
        mock_hid_device.get_feature_report.return_value = [0x00, 0x01]
        result = device.get_feature_report(b"\x00", 1)
        assert result == b"\x01"

    def test_set_nonblocking(self, device, mock_hid_device):
        """set_nonblocking updates device mode."""
        device.set_nonblocking(True)
        assert device._blocking is False
        assert mock_hid_device.nonblocking is True

    def test_blocking_property(self, device):
        """blocking property returns blocking state."""
        assert device.blocking is True
        device._blocking = False
        assert device.blocking is False


# ─────────────────────────────────────────────────────────────────────────────
# enumerate Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEnumerate:
    """Tests for enumerate function."""

    def test_enumerate_returns_device_info_list(self):
        """enumerate returns list of DeviceInfo."""
        mock_devices = [
            {"path": b"/dev/hidraw0", "vendor_id": 0x1532, "product_id": 0x0227},
            {"path": b"/dev/hidraw1", "vendor_id": 0x1532, "product_id": 0x0228},
        ]
        with patch("uchroma.server.hidadapter.hid.enumerate", return_value=mock_devices):
            result = enumerate()
            assert len(result) == 2
            assert all(isinstance(d, DeviceInfo) for d in result)
            assert result[0].product_id == 0x0227
            assert result[1].product_id == 0x0228

    def test_enumerate_with_vendor_filter(self):
        """enumerate filters by vendor_id."""
        with patch("uchroma.server.hidadapter.hid.enumerate") as mock_enum:
            mock_enum.return_value = []
            enumerate(vendor_id=0x1532)
            mock_enum.assert_called_once_with(0x1532, 0)

    def test_enumerate_with_product_filter(self):
        """enumerate filters by product_id."""
        with patch("uchroma.server.hidadapter.hid.enumerate") as mock_enum:
            mock_enum.return_value = []
            enumerate(vendor_id=0x1532, product_id=0x0227)
            mock_enum.assert_called_once_with(0x1532, 0x0227)

    def test_enumerate_empty_result(self):
        """enumerate returns empty list when no devices."""
        with patch("uchroma.server.hidadapter.hid.enumerate", return_value=[]):
            result = enumerate()
            assert result == []
