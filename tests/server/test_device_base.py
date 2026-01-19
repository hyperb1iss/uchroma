#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.device_base module."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from uchroma.server.device_base import BaseUChromaDevice

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_hardware():
    """Create a mock Hardware object."""
    hw = MagicMock()
    hw.name = "Test Device"
    hw.type = MagicMock()
    hw.type.value = "keyboard"
    hw.manufacturer = "Test Manufacturer"
    hw.dimensions = MagicMock()
    hw.dimensions.x = 22
    hw.dimensions.y = 6
    hw.has_matrix = True
    hw.quirks = 0
    hw.has_quirk = MagicMock(return_value=False)
    hw.key_mapping = {"KEY_A": [[0, 1]]}
    return hw


@pytest.fixture
def mock_hardware_no_matrix():
    """Create a mock Hardware without matrix support."""
    hw = MagicMock()
    hw.name = "Simple Device"
    hw.type = MagicMock()
    hw.type.value = "mouse"
    hw.manufacturer = "Test"
    hw.dimensions = None
    hw.has_matrix = False
    hw.quirks = 0
    hw.has_quirk = MagicMock(return_value=False)
    hw.key_mapping = None
    return hw


@pytest.fixture
def mock_devinfo():
    """Create a mock DeviceInfo."""
    devinfo = MagicMock()
    devinfo.path = b"/dev/hidraw0"
    devinfo.vendor_id = 0x1532
    devinfo.product_id = 0x0227
    devinfo.serial_number = "XX0000000001"
    return devinfo


@pytest.fixture
def device(mock_hardware, mock_devinfo):
    """Create a BaseUChromaDevice for testing."""
    with (
        patch("uchroma.server.device_base.AnimationManager"),
        patch("uchroma.server.device_base.PreferenceManager"),
    ):
        dev = BaseUChromaDevice(
            hardware=mock_hardware,
            devinfo=mock_devinfo,
            index=0,
            sys_path="/sys/devices/test",
            input_devices=None,
        )
        return dev


@pytest.fixture
def device_no_matrix(mock_hardware_no_matrix, mock_devinfo):
    """Create a device without matrix support."""
    with (
        patch("uchroma.server.device_base.AnimationManager"),
        patch("uchroma.server.device_base.PreferenceManager"),
    ):
        dev = BaseUChromaDevice(
            hardware=mock_hardware_no_matrix,
            devinfo=mock_devinfo,
            index=1,
            sys_path="/sys/devices/test2",
            input_devices=None,
        )
        return dev


# ─────────────────────────────────────────────────────────────────────────────
# Command Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceCommand:
    """Tests for BaseUChromaDevice.Command enum."""

    def test_get_firmware_version_command(self):
        """GET_FIRMWARE_VERSION command is defined."""
        cmd = BaseUChromaDevice.Command.GET_FIRMWARE_VERSION
        assert cmd.value == (0x00, 0x81, 0x02)

    def test_get_serial_command(self):
        """GET_SERIAL command is defined."""
        cmd = BaseUChromaDevice.Command.GET_SERIAL
        assert cmd.value == (0x00, 0x82, 0x16)


# ─────────────────────────────────────────────────────────────────────────────
# Init Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceInit:
    """Tests for BaseUChromaDevice initialization."""

    def test_init_basic_properties(self, device, mock_hardware, mock_devinfo):
        """Device initializes with basic properties."""
        assert device._hardware is mock_hardware
        assert device._devinfo is mock_devinfo
        assert device._devindex == 0
        assert device._sys_path == "/sys/devices/test"

    def test_init_not_suspended(self, device):
        """Device starts not suspended."""
        assert device._suspended is False
        assert device._offline is False

    def test_init_creates_signals(self, device):
        """Device creates power_state_changed and restore_prefs signals."""
        assert hasattr(device, "power_state_changed")
        assert hasattr(device, "restore_prefs")

    def test_init_with_input_devices(self, mock_hardware, mock_devinfo):
        """Device creates InputManager when input_devices provided."""
        with (
            patch("uchroma.server.device_base.AnimationManager"),
            patch("uchroma.server.device_base.InputManager") as mock_input,
            patch("uchroma.server.device_base.PreferenceManager"),
        ):
            dev = BaseUChromaDevice(
                hardware=mock_hardware,
                devinfo=mock_devinfo,
                index=0,
                sys_path="/sys/test",
                input_devices=["/dev/input/event0"],
            )
            mock_input.assert_called_once()
            assert dev._input_manager is not None


# ─────────────────────────────────────────────────────────────────────────────
# Property Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceProperties:
    """Tests for BaseUChromaDevice properties."""

    def test_name_property(self, device):
        """name returns hardware name."""
        assert device.name == "Test Device"

    def test_device_index_property(self, device):
        """device_index returns the index."""
        assert device.device_index == 0

    def test_sys_path_property(self, device):
        """sys_path returns the sysfs path."""
        assert device.sys_path == "/sys/devices/test"

    def test_key_property(self, device):
        """key returns unique identifier."""
        key = device.key
        assert "1532" in key
        assert "0227" in key

    def test_hardware_property(self, device, mock_hardware):
        """hardware returns the Hardware object."""
        assert device.hardware is mock_hardware

    def test_product_id_property(self, device):
        """product_id returns USB product ID."""
        assert device.product_id == 0x0227

    def test_vendor_id_property(self, device):
        """vendor_id returns USB vendor ID."""
        assert device.vendor_id == 0x1532

    def test_manufacturer_property(self, device):
        """manufacturer returns device manufacturer."""
        assert device.manufacturer == "Test Manufacturer"

    def test_device_type_property(self, device):
        """device_type returns hardware type."""
        assert device.device_type.value == "keyboard"

    def test_width_property(self, device):
        """width returns matrix width."""
        assert device.width == 22

    def test_height_property(self, device):
        """height returns matrix height."""
        assert device.height == 6

    def test_width_no_matrix(self, device_no_matrix):
        """width returns 0 without matrix."""
        assert device_no_matrix.width == 0

    def test_height_no_matrix(self, device_no_matrix):
        """height returns 0 without matrix."""
        assert device_no_matrix.height == 0

    def test_has_matrix_property(self, device):
        """has_matrix returns hardware has_matrix."""
        assert device.has_matrix is True

    def test_has_quirk_method(self, device, mock_hardware):
        """has_quirk delegates to hardware."""
        device.has_quirk("SOME_QUIRK")
        mock_hardware.has_quirk.assert_called_with("SOME_QUIRK")

    def test_key_mapping_property(self, device):
        """key_mapping returns hardware key_mapping."""
        assert device.key_mapping == {"KEY_A": [[0, 1]]}

    def test_hid_property_initially_none(self, device):
        """hid property is None when not opened."""
        assert device.hid is None

    def test_is_offline_property(self, device):
        """is_offline returns offline state."""
        assert device.is_offline is False

    def test_driver_version_property(self, device):
        """driver_version returns uchroma version."""
        version = device.driver_version
        assert version is not None

    def test_last_cmd_time_property(self, device):
        """last_cmd_time getter and setter work."""
        assert device.last_cmd_time is None
        device.last_cmd_time = 12345.0
        assert device.last_cmd_time == 12345.0


# ─────────────────────────────────────────────────────────────────────────────
# Animation Manager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceAnimationManager:
    """Tests for animation manager integration."""

    def test_animation_manager_property(self, device):
        """animation_manager returns the manager."""
        assert device.animation_manager is not None

    def test_animation_manager_none_without_matrix(self, device_no_matrix):
        """animation_manager is None without matrix."""
        assert device_no_matrix.animation_manager is None

    def test_is_animating_false_when_not_running(self, device):
        """is_animating returns False when not running."""
        device._animation_manager.running = False
        assert device.is_animating is False

    def test_is_animating_true_when_running(self, device):
        """is_animating returns True when running."""
        device._animation_manager.running = True
        assert device.is_animating is True


# ─────────────────────────────────────────────────────────────────────────────
# FX Manager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceFxManager:
    """Tests for FX manager integration."""

    def test_fx_manager_property(self, device):
        """fx_manager returns the manager."""
        # Initially None in base class
        assert device.fx_manager is None

    def test_has_fx_false_without_manager(self, device):
        """has_fx returns False without fx_manager."""
        assert device.has_fx("wave") is False

    def test_has_fx_with_manager(self, device):
        """has_fx checks fx_manager.available_fx."""
        device._fx_manager = MagicMock()
        device._fx_manager.available_fx = ["wave", "static"]
        assert device.has_fx("wave") is True
        assert device.has_fx("spectrum") is False


# ─────────────────────────────────────────────────────────────────────────────
# Input Manager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceInputManager:
    """Tests for input manager integration."""

    def test_input_manager_property(self, device):
        """input_manager returns None when not configured."""
        assert device.input_manager is None

    def test_input_devices_property(self, device):
        """input_devices returns None without input_manager."""
        assert device.input_devices is None

    def test_input_devices_with_manager(self, device):
        """input_devices returns devices from manager."""
        device._input_manager = MagicMock()
        device._input_manager.input_devices = ["/dev/input/event0"]
        assert device.input_devices == ["/dev/input/event0"]


# ─────────────────────────────────────────────────────────────────────────────
# Suspend/Resume Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceSuspendResume:
    """Tests for suspend/resume functionality."""

    def test_suspended_property(self, device):
        """suspended property returns state."""
        assert device.suspended is False
        device._suspended = True
        assert device.suspended is True

    def test_suspend_fast(self, device):
        """suspend(fast=True) sets brightness to 0 immediately."""
        device._prefs = MagicMock()
        device._prefs.brightness = None
        device._set_brightness = MagicMock()

        device.suspend(fast=True)

        device._set_brightness.assert_called_with(0)
        assert device._suspended is True

    def test_suspend_already_suspended(self, device):
        """suspend does nothing if already suspended."""
        device._suspended = True
        device._set_brightness = MagicMock()

        device.suspend()

        device._set_brightness.assert_not_called()

    def test_resume_restores_brightness(self, device):
        """resume restores saved brightness."""
        device._suspended = True
        device._prefs = MagicMock()
        device._prefs.brightness = 75.0

        with patch.object(device, "set_brightness") as mock_set_brightness:
            device.resume()
            mock_set_brightness.assert_called_once()
            args, _kwargs = mock_set_brightness.call_args
            assert args[0] == 75.0

        assert device._suspended is False

    def test_resume_not_suspended(self, device):
        """resume does nothing if not suspended."""
        device._suspended = False
        device._prefs = MagicMock()

        device.resume()

        # Should not have tried to set brightness


# ─────────────────────────────────────────────────────────────────────────────
# Device Open/Close Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceOpenClose:
    """Tests for device open/close functionality."""

    def test_device_open_increments_ref_count(self, device):
        """_device_open increments ref count."""
        with patch.object(device, "_ensure_open", return_value=True):
            device._device_open()
            assert device._ref_count == 1

    def test_device_close_decrements_ref_count(self, device):
        """_device_close decrements ref count."""
        device._ref_count = 2
        device._device_close()
        assert device._ref_count == 1

    def test_close_not_forced_with_ref_count(self, device):
        """close without force doesn't close if ref_count > 0."""
        device._ref_count = 1
        device._dev = MagicMock()

        device.close(force=False)

        device._dev.close.assert_not_called()

    def test_close_forced(self, device):
        """close with force closes regardless."""
        device._ref_count = 1
        mock_dev = MagicMock()
        device._dev = mock_dev

        device.close(force=True)

        mock_dev.close.assert_called_once()
        assert device._dev is None

    def test_device_open_context_manager(self, device):
        """device_open context manager handles open/close."""
        with (
            patch.object(device, "_device_open", return_value=True) as mock_open,
            patch.object(device, "_device_close") as mock_close,
        ):
            with device.device_open():
                mock_open.assert_called_once()
            mock_close.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Report Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceReports:
    """Tests for report creation and execution."""

    def test_get_report_creates_report(self, device):
        """get_report creates a RazerReport."""
        with (
            patch("uchroma.server.device_base.RazerReport") as mock_report,
            patch("uchroma.server.device_base.get_transaction_id", return_value=0xFF),
        ):
            device.get_report(0x03, 0x00, 0x08)
            mock_report.assert_called_once()

    def test_get_report_with_args(self, device):
        """get_report passes args to report."""
        with (
            patch("uchroma.server.device_base.RazerReport") as mock_report,
            patch("uchroma.server.device_base.get_transaction_id", return_value=0xFF),
        ):
            mock_instance = MagicMock()
            mock_report.return_value = mock_instance

            device.get_report(0x03, 0x00, 0x08, 0x01, 0x02)

            # Args should have been put
            assert mock_instance.args.put.call_count == 2

    def test_get_timeout_cb_returns_none(self, device):
        """_get_timeout_cb returns None by default."""
        assert device._get_timeout_cb() is None


# ─────────────────────────────────────────────────────────────────────────────
# Serial/Firmware Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceSerialFirmware:
    """Tests for serial number and firmware version."""

    def test_decode_serial_valid(self, device):
        """_decode_serial decodes valid bytes."""
        result = device._decode_serial(b"SERIAL123")
        assert result == "SERIAL123"

    def test_decode_serial_none(self, device):
        """_decode_serial returns None for None input."""
        result = device._decode_serial(None)
        assert result is None

    def test_decode_serial_invalid_returns_key(self, device):
        """_decode_serial returns key on decode error."""
        result = device._decode_serial(b"\xff\xfe\x00")
        # Should return device key instead
        assert result == device.key

    def test_serial_number_caches(self, device):
        """serial_number caches the result."""
        device._serial_number = "CACHED"
        assert device.serial_number == "CACHED"

    def test_firmware_version_formats(self, device):
        """firmware_version formats version correctly."""
        with patch.object(device, "_get_firmware_version", return_value=bytes([1, 5])):
            version = device.firmware_version
            assert version == "v1.5"

    def test_firmware_version_unknown(self, device):
        """firmware_version returns unknown if None."""
        with patch.object(device, "_get_firmware_version", return_value=None):
            version = device.firmware_version
            assert version == "(unknown)"


# ─────────────────────────────────────────────────────────────────────────────
# Repr Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDeviceRepr:
    """Tests for string representation."""

    def test_repr(self, device):
        """__repr__ includes key info."""
        r = repr(device)
        assert "BaseUChromaDevice" in r
        assert "Test Device" in r
        assert "0x0227" in r


# ─────────────────────────────────────────────────────────────────────────────
# Reset/Preferences Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseUChromaDevicePreferences:
    """Tests for preferences and reset."""

    def test_reset_returns_true(self, device):
        """reset returns True by default."""
        assert device.reset() is True

    def test_fire_restore_prefs(self, device):
        """fire_restore_prefs fires signal with preferences."""
        device._prefs = MagicMock()
        device._prefs.brightness = 50.0
        device._prefs.observers_paused = MagicMock()

        # Mock the Signal.fire method
        with (
            patch.object(device.restore_prefs, "fire") as mock_fire,
            patch.object(BaseUChromaDevice, "brightness", new_callable=PropertyMock),
        ):
            device.fire_restore_prefs()

        mock_fire.assert_called_once_with(device._prefs)
