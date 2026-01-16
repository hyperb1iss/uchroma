#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Unit tests for RazerReport class."""

from __future__ import annotations

import struct
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from uchroma.server.report import RazerReport, Status

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_logger():
    """Mock logger for driver."""
    logger = MagicMock()
    logger.isEnabledFor = MagicMock(return_value=False)
    logger.debug = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_hid():
    """Mock HID device."""
    hid = MagicMock()
    hid.send_feature_report = MagicMock(return_value=90)
    hid.get_feature_report = MagicMock(return_value=bytes(90))
    return hid


@pytest.fixture
def mock_driver(mock_logger, mock_hid):
    """Mock driver with HID device."""
    driver = MagicMock()
    driver.logger = mock_logger
    driver.hid = mock_hid
    driver.last_cmd_time = 0.0
    driver.device_open = MagicMock(return_value=nullcontext())
    driver.has_quirk = MagicMock(return_value=False)
    return driver


@pytest.fixture
def basic_report(mock_driver):
    """Basic report with minimal configuration."""
    return RazerReport(
        driver=mock_driver,
        command_class=0x03,
        command_id=0x01,
        data_size=3,
    )


@pytest.fixture
def report_with_data(mock_driver):
    """Report with pre-populated data."""
    report = RazerReport(
        driver=mock_driver,
        command_class=0x0F,
        command_id=0x02,
        data_size=5,
    )
    report.args.put(0xAA).put(0xBB).put(0xCC)
    return report


def build_response(
    status: int = Status.OK.value,
    transaction_id: int = 0xFF,
    remaining_packets: int = 0x00,
    protocol_type: int = 0x00,
    data_size: int = 0,
    command_class: int = 0x00,
    command_id: int = 0x00,
    data: bytes | None = None,
    crc: int | None = None,
) -> bytes:
    """Build a valid 90-byte HID response."""
    buf = bytearray(90)
    struct.pack_into(
        "=BBHBBBB",
        buf,
        0,
        status,
        transaction_id,
        remaining_packets,
        protocol_type,
        data_size,
        command_class,
        command_id,
    )
    if data:
        for i, byte in enumerate(data[:80]):
            buf[8 + i] = byte
    if crc is None:
        crc = 0
        for i in range(1, 87):
            crc ^= buf[i]
    buf[88] = crc
    # reserved at 89
    return bytes(buf)


# ─────────────────────────────────────────────────────────────────────────────
# Status Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestStatusEnum:
    """Tests for Status enum values."""

    @pytest.mark.parametrize(
        ("status", "expected_value"),
        [
            (Status.UNKNOWN, 0x00),
            (Status.BUSY, 0x01),
            (Status.OK, 0x02),
            (Status.FAIL, 0x03),
            (Status.TIMEOUT, 0x04),
            (Status.UNSUPPORTED, 0x05),
            (Status.BAD_CRC, 0xFE),
            (Status.OSERROR, 0xFF),
        ],
    )
    def test_status_enum_values(self, status, expected_value):
        """Verify all Status enum values are correct."""
        assert status.value == expected_value

    def test_status_from_value(self):
        """Status enum should be constructible from value."""
        assert Status(0x02) == Status.OK
        assert Status(0x01) == Status.BUSY

    def test_status_name(self):
        """Status enum should have correct names."""
        assert Status.OK.name == "OK"
        assert Status.BUSY.name == "BUSY"
        assert Status.FAIL.name == "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# Report Initialization Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReportInit:
    """Tests for RazerReport initialization."""

    def test_init_sets_command_class(self, mock_driver):
        """Report should store command class."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._command_class == 0x03

    def test_init_sets_command_id(self, mock_driver):
        """Report should store command id."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._command_id == 0x01

    def test_init_sets_data_size(self, mock_driver):
        """Report should store data size."""
        report = RazerReport(mock_driver, 0x03, 0x01, 5)
        assert report._data_size == 5

    def test_init_default_status(self, mock_driver):
        """Report should have default status of 0x00."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._status == 0x00

    def test_init_default_transaction_id(self, mock_driver):
        """Report should have default transaction_id of 0xFF."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._transaction_id == 0xFF

    def test_init_custom_transaction_id(self, mock_driver):
        """Report should accept custom transaction_id."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3, transaction_id=0x3F)
        assert report._transaction_id == 0x3F

    def test_init_default_remaining_packets(self, mock_driver):
        """Report should have default remaining_packets of 0x00."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._remaining_packets == 0x00

    def test_init_default_protocol_type(self, mock_driver):
        """Report should have default protocol_type of 0x00."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._protocol_type == 0x00

    def test_init_creates_buffer(self, mock_driver):
        """Report should create 90-byte buffer."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert len(report._buf) == 90
        assert isinstance(report._buf, np.ndarray)
        assert report._buf.dtype == np.uint8

    def test_init_creates_data_buffer(self, mock_driver):
        """Report should create 80-byte data buffer via ByteArgs."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._data.size == 80

    def test_init_with_existing_data(self, mock_driver):
        """Report should accept existing data bytes."""
        data = bytes([0x01, 0x02, 0x03])
        report = RazerReport(mock_driver, 0x03, 0x01, 3, data=data)
        assert report._data.data[0] == 0x01
        assert report._data.data[1] == 0x02
        assert report._data.data[2] == 0x03

    def test_init_crc_default(self, mock_driver):
        """Report should have default CRC of 0."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._crc == 0

    def test_init_crc_custom(self, mock_driver):
        """Report should accept custom CRC."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3, crc=0x42)
        assert report._crc == 0x42

    def test_init_reserved_default(self, mock_driver):
        """Report should have default reserved of 0."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        assert report._reserved == 0

    def test_init_reserved_custom(self, mock_driver):
        """Report should accept custom reserved."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3, reserved=0x99)
        assert report._reserved == 0x99


# ─────────────────────────────────────────────────────────────────────────────
# Report Constants Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReportConstants:
    """Tests for RazerReport class constants."""

    def test_buf_size(self):
        """Buffer size should be 90 bytes."""
        assert RazerReport.BUF_SIZE == 90

    def test_data_buf_size(self):
        """Data buffer size should be 80 bytes."""
        assert RazerReport.DATA_BUF_SIZE == 80

    def test_req_report_id(self):
        """Request report ID should be 0x00."""
        assert RazerReport.REQ_REPORT_ID == b"\x00"

    def test_rsp_report_id(self):
        """Response report ID should be 0x00."""
        assert RazerReport.RSP_REPORT_ID == b"\x00"

    def test_cmd_delay_time(self):
        """Command delay time should be 0.007 seconds."""
        assert RazerReport.CMD_DELAY_TIME == 0.007


# ─────────────────────────────────────────────────────────────────────────────
# Properties Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReportProperties:
    """Tests for RazerReport properties."""

    def test_args_property(self, basic_report):
        """args property should return ByteArgs instance."""
        assert basic_report.args is not None
        assert hasattr(basic_report.args, "put")
        assert hasattr(basic_report.args, "data")

    def test_status_property_initial(self, basic_report):
        """status property should return initial status."""
        assert basic_report.status == 0x00

    def test_status_property_after_unpack(self, mock_driver):
        """status property should return Status enum after unpack."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        response = build_response(status=Status.OK.value)
        report._unpack_response(response)
        assert report.status == Status.OK

    def test_remaining_packets_property_get(self, basic_report):
        """remaining_packets property should be gettable."""
        assert basic_report.remaining_packets == 0x00

    def test_remaining_packets_property_set(self, basic_report):
        """remaining_packets property should be settable."""
        basic_report.remaining_packets = 5
        assert basic_report.remaining_packets == 5


# ─────────────────────────────────────────────────────────────────────────────
# Request Packing Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPackRequest:
    """Tests for _pack_request method."""

    def test_pack_request_returns_bytes(self, basic_report):
        """_pack_request should return bytes."""
        result = basic_report._pack_request()
        assert isinstance(result, bytes)

    def test_pack_request_length(self, basic_report):
        """_pack_request should return 90 bytes."""
        result = basic_report._pack_request()
        assert len(result) == 90

    def test_pack_request_status_is_zero(self, basic_report):
        """Request status byte should always be 0x00."""
        result = basic_report._pack_request()
        assert result[0] == 0x00

    def test_pack_request_transaction_id(self, mock_driver):
        """Transaction ID should be packed correctly."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3, transaction_id=0x3F)
        result = report._pack_request()
        assert result[1] == 0x3F

    def test_pack_request_remaining_packets(self, basic_report):
        """Remaining packets should be packed as 2-byte value."""
        basic_report.remaining_packets = 0x1234
        result = basic_report._pack_request()
        # Little-endian 16-bit
        assert result[2] == 0x34
        assert result[3] == 0x12

    def test_pack_request_protocol_type(self, mock_driver):
        """Protocol type should be packed correctly."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3, protocol_type=0x05)
        result = report._pack_request()
        # Protocol is at offset 4 (after remaining_packets which is 2 bytes)
        # Header: status(1) + trans_id(1) + remaining(2) + proto(1) + size(1) + class(1) + cmd(1)
        # Looking at struct format "=BBHBBBB":
        # B(status) + B(trans_id) + H(remaining, 2 bytes) + B(proto) + B(size) + B(class) + B(cmd)
        # Offset: 0, 1, 2-3, 4, 5, 6, 7
        assert result[4] == 0x05

    def test_pack_request_data_size(self, mock_driver):
        """Data size should be packed correctly."""
        report = RazerReport(mock_driver, 0x03, 0x01, 10)
        result = report._pack_request()
        assert result[5] == 10

    def test_pack_request_command_class(self, mock_driver):
        """Command class should be packed correctly."""
        report = RazerReport(mock_driver, 0x0F, 0x01, 3)
        result = report._pack_request()
        assert result[6] == 0x0F

    def test_pack_request_command_id(self, mock_driver):
        """Command ID should be packed correctly."""
        report = RazerReport(mock_driver, 0x03, 0x42, 3)
        result = report._pack_request()
        assert result[7] == 0x42

    def test_pack_request_data_at_offset_8(self, report_with_data):
        """Data should be packed starting at offset 8."""
        result = report_with_data._pack_request()
        assert result[8] == 0xAA
        assert result[9] == 0xBB
        assert result[10] == 0xCC

    def test_pack_request_crc_at_offset_88(self, basic_report):
        """CRC should be at offset 88."""
        result = basic_report._pack_request()
        # CRC is XOR of bytes 1-86
        expected_crc = 0
        for i in range(1, 87):
            expected_crc ^= result[i]
        assert result[88] == expected_crc

    def test_pack_request_reserved_at_offset_89(self, basic_report):
        """Reserved byte at offset 89 should be zero."""
        result = basic_report._pack_request()
        assert result[89] == 0

    def test_pack_request_none_data_size_uses_ptr(self, mock_driver):
        """If data_size is None, use actual args size."""
        report = RazerReport(mock_driver, 0x03, 0x01, data_size=None)
        report.args.put(0x01).put(0x02).put(0x03)  # 3 bytes
        result = report._pack_request()
        assert result[5] == 3  # data_size should be 3


class TestPackRequestCRC:
    """Tests for CRC calculation in _pack_request."""

    def test_crc_calculation_simple(self, mock_driver):
        """CRC should XOR bytes 1-86."""
        report = RazerReport(mock_driver, 0x00, 0x00, 0)
        result = report._pack_request()

        # Manual CRC calculation
        expected_crc = 0
        for i in range(1, 87):
            expected_crc ^= result[i]
        assert result[88] == expected_crc

    def test_crc_changes_with_data(self, mock_driver):
        """CRC should change when data changes."""
        report1 = RazerReport(mock_driver, 0x03, 0x01, 1)
        report1.args.put(0x00)
        result1 = report1._pack_request()

        report2 = RazerReport(mock_driver, 0x03, 0x01, 1)
        report2.args.put(0xFF)
        result2 = report2._pack_request()

        assert result1[88] != result2[88]


# ─────────────────────────────────────────────────────────────────────────────
# Response Unpacking Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestUnpackResponse:
    """Tests for _unpack_response method."""

    def test_unpack_response_ok_returns_true(self, basic_report):
        """Unpacking OK response should return True."""
        response = build_response(status=Status.OK.value)
        result = basic_report._unpack_response(response)
        assert result is True

    def test_unpack_response_ok_zero_crc_skips_validation(self, basic_report):
        response = build_response(status=Status.OK.value, crc=0x00)
        result = basic_report._unpack_response(response)
        assert result is True
        assert basic_report.status == Status.OK

    def test_unpack_response_mismatched_crc_fails(self, basic_report):
        good = build_response(status=Status.OK.value)
        response = build_response(status=Status.OK.value, crc=(good[88] ^ 0x01))
        result = basic_report._unpack_response(response)
        assert result is False
        assert basic_report.status == Status.BAD_CRC

    def test_unpack_response_fail_returns_false(self, basic_report):
        """Unpacking FAIL response should return False."""
        response = build_response(status=Status.FAIL.value)
        result = basic_report._unpack_response(response)
        assert result is False

    def test_unpack_response_busy_returns_false(self, basic_report):
        """Unpacking BUSY response should return False."""
        response = build_response(status=Status.BUSY.value)
        result = basic_report._unpack_response(response)
        assert result is False

    def test_unpack_response_unsupported_returns_false(self, basic_report):
        """Unpacking UNSUPPORTED response should return False."""
        response = build_response(status=Status.UNSUPPORTED.value)
        result = basic_report._unpack_response(response)
        assert result is False

    def test_unpack_response_timeout_returns_false(self, basic_report):
        """Unpacking TIMEOUT response should return False."""
        response = build_response(status=Status.TIMEOUT.value)
        result = basic_report._unpack_response(response)
        assert result is False

    def test_unpack_response_sets_status(self, basic_report):
        """Unpacking should set status property."""
        response = build_response(status=Status.OK.value)
        basic_report._unpack_response(response)
        assert basic_report.status == Status.OK

    def test_unpack_response_extracts_data(self, basic_report):
        """Unpacking should extract data based on data_size."""
        data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        response = build_response(status=Status.OK.value, data_size=4, data=data)
        basic_report._unpack_response(response)
        result = basic_report.result
        assert result[:4] == data

    def test_unpack_response_result_length_matches_data_size(self, basic_report):
        """Result should match data_size from response."""
        response = build_response(status=Status.OK.value, data_size=10)
        basic_report._unpack_response(response)
        assert len(basic_report.result) == 10

    def test_unpack_response_wrong_size_raises(self, basic_report):
        """Unpacking wrong-sized buffer should raise AssertionError."""
        with pytest.raises(AssertionError):
            basic_report._unpack_response(bytes(50))

    @pytest.mark.parametrize(
        "status",
        [
            Status.BUSY,
            Status.FAIL,
            Status.TIMEOUT,
            Status.BAD_CRC,
        ],
    )
    def test_unpack_response_logs_error_on_failure(self, basic_report, status):
        """Unpacking error status (not UNSUPPORTED) should log error."""
        response = build_response(status=status.value)
        basic_report._unpack_response(response)
        basic_report._logger.error.assert_called()

    def test_unpack_response_logs_debug_on_unsupported(self, basic_report):
        """Unpacking UNSUPPORTED status should log debug, not error."""
        response = build_response(status=Status.UNSUPPORTED.value)
        basic_report._unpack_response(response)
        # UNSUPPORTED is expected behavior, logged at debug level
        basic_report._logger.debug.assert_called()
        basic_report._logger.error.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# clear() Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestClear:
    """Tests for clear() method."""

    def test_clear_zeros_buffer(self, report_with_data):
        """clear() should zero the buffer."""
        report_with_data._pack_request()  # Populate buffer
        report_with_data.clear()
        assert all(b == 0 for b in report_with_data._buf)

    def test_clear_resets_data(self, report_with_data):
        """clear() should reset args data."""
        report_with_data.clear()
        assert all(b == 0 for b in report_with_data.args.data)

    def test_clear_resets_status(self, mock_driver):
        """clear() should reset status to 0x00."""
        report = RazerReport(mock_driver, 0x03, 0x01, 3)
        report._status = Status.OK
        report.clear()
        assert report._status == 0x00

    def test_clear_resets_remaining_packets(self, basic_report):
        """clear() should reset remaining_packets to 0x00."""
        basic_report.remaining_packets = 5
        basic_report.clear()
        assert basic_report.remaining_packets == 0x00

    def test_clear_resets_result(self, basic_report):
        """clear() should reset result to None."""
        response = build_response(status=Status.OK.value, data_size=3)
        basic_report._unpack_response(response)
        basic_report.clear()
        assert basic_report._result is None


# ─────────────────────────────────────────────────────────────────────────────
# run() Method Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRun:
    """Tests for run() method."""

    def test_run_sends_feature_report(self, basic_report, mock_hid):
        """run() should send feature report."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        basic_report.run()
        mock_hid.send_feature_report.assert_called()

    def test_run_gets_feature_report(self, basic_report, mock_hid):
        """run() should get feature report response."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        basic_report.run()
        mock_hid.get_feature_report.assert_called_with(
            RazerReport.RSP_REPORT_ID, RazerReport.BUF_SIZE
        )

    def test_run_ok_returns_true(self, basic_report, mock_hid):
        """run() should return True on OK status."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        result = basic_report.run()
        assert result is True

    def test_run_fail_returns_false(self, basic_report, mock_hid):
        """run() should return False on FAIL status."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.FAIL.value)
        result = basic_report.run()
        assert result is False

    def test_run_unsupported_returns_false(self, basic_report, mock_hid):
        """run() should return False on UNSUPPORTED status."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.UNSUPPORTED.value)
        result = basic_report.run()
        assert result is False

    def test_run_timeout_returns_false(self, basic_report, mock_hid):
        """run() should return False on TIMEOUT with callback."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.TIMEOUT.value)
        callback = MagicMock()
        result = basic_report.run(timeout_cb=callback)
        assert result is False

    def test_run_timeout_invokes_callback(self, basic_report, mock_hid):
        """run() should invoke timeout callback on TIMEOUT."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.TIMEOUT.value)
        callback = MagicMock()
        basic_report.run(timeout_cb=callback)
        callback.assert_called_once()

    def test_run_ok_invokes_timeout_callback(self, basic_report, mock_hid):
        """run() should invoke timeout callback on OK (if provided)."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        callback = MagicMock()
        basic_report.run(timeout_cb=callback)
        callback.assert_called_once_with(Status.OK, None)

    def test_run_uses_device_open_context(self, basic_report, mock_driver, mock_hid):
        """run() should use device_open context manager."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        basic_report.run()
        mock_driver.device_open.assert_called_once()

    def test_run_default_delay(self, basic_report, mock_hid):
        """run() should use default delay of CMD_DELAY_TIME."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        with patch("uchroma.server.report.smart_delay") as mock_delay:
            mock_delay.return_value = 0.0
            basic_report.run()
            # smart_delay is called with CMD_DELAY_TIME
            mock_delay.assert_called()

    def test_run_custom_delay(self, basic_report, mock_hid):
        """run() should respect custom delay parameter."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        with patch("uchroma.server.report.smart_delay") as mock_delay:
            mock_delay.return_value = 0.0
            basic_report.run(delay=0.05)
            # Verify delay parameter was passed
            call_args = mock_delay.call_args_list[0]
            assert call_args[0][0] == 0.05


class TestRunRetryLogic:
    """Tests for retry logic in run() method."""

    def test_run_retries_on_busy(self, basic_report, mock_hid):
        """run() should retry on BUSY status."""
        mock_hid.get_feature_report.side_effect = [
            build_response(status=Status.BUSY.value),
            build_response(status=Status.BUSY.value),
            build_response(status=Status.OK.value),
        ]
        with patch("time.sleep"):
            result = basic_report.run()
        assert result is True
        assert mock_hid.get_feature_report.call_count == 3

    def test_run_max_retries(self, basic_report, mock_hid):
        """run() should fail after max retries."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.BUSY.value)
        with patch("time.sleep"):
            result = basic_report.run()
        assert result is False
        # 3 retries = 3 attempts
        assert mock_hid.get_feature_report.call_count == 3

    def test_run_no_retry_on_fail(self, basic_report, mock_hid):
        """run() should not retry on FAIL status."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.FAIL.value)
        result = basic_report.run()
        assert result is False
        assert mock_hid.get_feature_report.call_count == 1

    def test_run_no_retry_on_unsupported(self, basic_report, mock_hid):
        """run() should not retry on UNSUPPORTED status."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.UNSUPPORTED.value)
        result = basic_report.run()
        assert result is False
        assert mock_hid.get_feature_report.call_count == 1

    def test_run_logs_warning_on_retry(self, basic_report, mock_hid, mock_logger):
        """run() should log warning when retrying."""
        mock_hid.get_feature_report.side_effect = [
            build_response(status=Status.BUSY.value),
            build_response(status=Status.OK.value),
        ]
        with patch("time.sleep"):
            basic_report.run()
        mock_logger.warning.assert_called()


class TestRunRemainingPackets:
    """Tests for remaining_packets behavior in run()."""

    def test_run_skips_response_when_remaining_packets(self, basic_report, mock_hid):
        """run() should skip response read when remaining_packets > 0."""
        basic_report.remaining_packets = 5
        result = basic_report.run()
        assert result is True
        mock_hid.send_feature_report.assert_called_once()
        mock_hid.get_feature_report.assert_not_called()

    def test_run_reads_response_when_no_remaining_packets(self, basic_report, mock_hid):
        """run() should read response when remaining_packets == 0."""
        basic_report.remaining_packets = 0
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        basic_report.run()
        mock_hid.get_feature_report.assert_called()


class TestRunOSError:
    """Tests for OSError handling in run()."""

    def test_run_oserror_sets_status(self, basic_report, mock_hid):
        """run() should set OSERROR status on OSError."""
        mock_hid.send_feature_report.side_effect = OSError("HID error")
        with pytest.raises(OSError):
            basic_report.run()
        assert basic_report.status == Status.OSERROR

    def test_run_oserror_reraises(self, basic_report, mock_hid):
        """run() should re-raise OSError."""
        mock_hid.send_feature_report.side_effect = OSError("HID error")
        with pytest.raises(OSError, match="HID error"):
            basic_report.run()


# ─────────────────────────────────────────────────────────────────────────────
# result Property Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestResultProperty:
    """Tests for result property."""

    def test_result_returns_bytes(self, basic_report, mock_hid):
        """result property should return bytes."""
        response = build_response(status=Status.OK.value, data_size=4, data=bytes([1, 2, 3, 4]))
        mock_hid.get_feature_report.return_value = response
        basic_report.run()
        assert isinstance(basic_report.result, bytes)

    def test_result_contains_response_data(self, basic_report, mock_hid):
        """result should contain data from response."""
        data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        response = build_response(status=Status.OK.value, data_size=4, data=data)
        mock_hid.get_feature_report.return_value = response
        basic_report.run()
        assert basic_report.result[:4] == data


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReportIntegration:
    """Integration tests for complete report workflows."""

    def test_full_request_response_cycle(self, mock_driver, mock_hid):
        """Test complete request/response cycle."""
        # Create report
        report = RazerReport(
            mock_driver,
            command_class=0x03,
            command_id=0x0A,
            data_size=3,
        )
        report.args.put(0x01).put(0x02).put(0x03)

        # Mock response
        response_data = bytes([0xAA, 0xBB, 0xCC])
        mock_hid.get_feature_report.return_value = build_response(
            status=Status.OK.value,
            data_size=3,
            data=response_data,
        )

        # Execute
        result = report.run()

        # Verify
        assert result is True
        assert report.status == Status.OK
        assert report.result[:3] == response_data

    def test_multiple_reports_same_driver(self, mock_driver, mock_hid):
        """Multiple reports can use the same driver."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)

        report1 = RazerReport(mock_driver, 0x03, 0x01, 1)
        report2 = RazerReport(mock_driver, 0x03, 0x02, 2)

        assert report1.run() is True
        assert report2.run() is True

    def test_report_reuse_after_clear(self, basic_report, mock_hid):
        """Report can be reused after clear()."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)

        # First use
        basic_report.args.put(0x01)
        basic_report.run()

        # Clear and reuse
        basic_report.clear()
        basic_report.args.put(0x02)
        result = basic_report.run()

        assert result is True
        assert basic_report.args.data[0] == 0x02


# ─────────────────────────────────────────────────────────────────────────────
# Edge Cases Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_data_size(self, mock_driver, mock_hid):
        """Report with zero data_size should work."""
        report = RazerReport(mock_driver, 0x03, 0x01, 0)
        mock_hid.get_feature_report.return_value = build_response(
            status=Status.OK.value, data_size=0
        )
        result = report.run()
        assert result is True

    def test_max_data_size(self, mock_driver, mock_hid):
        """Report with max data_size (80) should work."""
        report = RazerReport(mock_driver, 0x03, 0x01, 80)
        data = bytes(range(80))
        for b in data:
            report.args.put(b)
        mock_hid.get_feature_report.return_value = build_response(
            status=Status.OK.value, data_size=80, data=data
        )
        result = report.run()
        assert result is True

    def test_all_transaction_ids(self, mock_driver, mock_hid):
        """Various transaction IDs should work."""
        mock_hid.get_feature_report.return_value = build_response(status=Status.OK.value)
        for tid in [0x00, 0x1F, 0x3F, 0xFF]:
            report = RazerReport(mock_driver, 0x03, 0x01, 1, transaction_id=tid)
            result = report.run()
            assert result is True
