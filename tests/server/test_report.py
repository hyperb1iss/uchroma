#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Unit tests for Rust-backed RazerReport and Status."""

from __future__ import annotations

import pytest

from uchroma.server import hid


def build_response(status: int, data: bytes | None = None) -> bytes:
    buf = bytearray(hid.REPORT_SIZE)
    buf[0] = int(status)
    if data:
        if len(data) > hid.DATA_SIZE:
            raise ValueError("data too large")
        buf[5] = len(data)
        buf[8 : 8 + len(data)] = data
    return bytes(buf)


class TestStatus:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (hid.Status.Unknown, 0x00),
            (hid.Status.Busy, 0x01),
            (hid.Status.Ok, 0x02),
            (hid.Status.Fail, 0x03),
            (hid.Status.Timeout, 0x04),
            (hid.Status.Unsupported, 0x05),
            (hid.Status.BadCrc, 0xFE),
            (hid.Status.OsError, 0xFF),
        ],
    )
    def test_status_values(self, status, expected):
        assert int(status) == expected

    def test_status_eq_int(self):
        assert hid.Status.Ok == 0x02
        assert hid.Status.Busy != 0x02


class TestReportPack:
    def test_pack_returns_bytes(self):
        report = hid.RazerReport(0x03, 0x01, 3)
        payload = report.pack()
        assert isinstance(payload, bytes)
        assert len(payload) == hid.REPORT_SIZE

    def test_pack_sets_header_fields(self):
        report = hid.RazerReport(0x03, 0x01, 3, transaction_id=0x3F)
        payload = report.pack()
        assert payload[1] == 0x3F
        assert payload[5] == 3
        assert payload[6] == 0x03
        assert payload[7] == 0x01

    def test_pack_uses_args_size_when_data_size_none(self):
        report = hid.RazerReport(0x03, 0x01, data_size=None)
        report.put_byte(0xAA)
        report.put_byte(0xBB)
        report.put_byte(0xCC)
        payload = report.pack()
        assert payload[5] == 3

    def test_pack_crc(self):
        report = hid.RazerReport(0x03, 0x01, 3)
        report.put_rgb(0x01, 0x02, 0x03)
        payload = report.pack()
        expected_crc = 0
        for idx in range(1, 88):
            expected_crc ^= payload[idx]
        assert payload[88] == expected_crc

    def test_put_methods_increment_args_size(self):
        report = hid.RazerReport(0x03, 0x01, data_size=None)
        report.put_byte(0x01)
        report.put_u16(0x0203)
        report.put_u16_be(0x0405)
        report.put_rgb(0x06, 0x07, 0x08)
        report.put_bytes(b"\x09\x0a")
        assert report.args_size == 10

    def test_put_bytes_overflow_raises(self):
        report = hid.RazerReport(0x03, 0x01, data_size=None)
        with pytest.raises(ValueError):
            report.put_bytes(bytes(hid.DATA_SIZE + 1))

    def test_clear_resets_args(self):
        report = hid.RazerReport(0x03, 0x01, data_size=None)
        report.put_byte(0x01)
        report.clear()
        assert report.args_size == 0

    def test_remaining_packets_roundtrip(self):
        report = hid.RazerReport(0x03, 0x01, 1)
        report.set_remaining_packets(12)
        assert report.get_remaining_packets() == 12


class TestReportParse:
    def test_parse_response_ok(self):
        report = hid.RazerReport(0x03, 0x01, 1)
        response = build_response(hid.Status.Ok, data=b"\x01\x02\x03")
        status, data = report.parse_response(response)
        assert status == hid.Status.Ok
        assert data[:3] == b"\x01\x02\x03"

    def test_parse_response_empty(self):
        report = hid.RazerReport(0x03, 0x01, 1)
        status, data = report.parse_response(build_response(hid.Status.Unknown))
        assert status == hid.Status.Unknown
        assert data == b""

    def test_parse_response_invalid_size_raises(self):
        report = hid.RazerReport(0x03, 0x01, 1)
        with pytest.raises(ValueError):
            report.parse_response(b"\x00" * 10)
