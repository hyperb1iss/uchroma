#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Unit tests for ByteArgs class."""

from __future__ import annotations

import numpy as np
import pytest

from uchroma.colorlib import Color
from uchroma.server.byte_args import ByteArgs


def test_init_creates_zeroed_buffer():
    ba = ByteArgs(10)
    assert all(b == 0 for b in ba.data)
    assert isinstance(ba.data, np.ndarray)
    assert ba.data.dtype == np.uint8


def test_init_with_size():
    ba = ByteArgs(32)
    assert len(ba.data) == 32


def test_init_with_existing_data():
    data = bytes([0x01, 0x02, 0x03, 0x04])
    ba = ByteArgs(4, data=data)
    assert len(ba.data) == 4
    assert ba.data[0] == 0x01
    assert ba.data[3] == 0x04


def test_put_int():
    ba = ByteArgs(4)
    ba.put(0xAA)
    ba.put(0xBB)
    assert ba.data[0] == 0xAA
    assert ba.data[1] == 0xBB


def test_put_bytes():
    ba = ByteArgs(4)
    ba.put(bytes([0x01, 0x02, 0x03]))
    assert list(ba.data[:3]) == [1, 2, 3]


def test_put_bytearray():
    ba = ByteArgs(4)
    ba.put(bytearray([0x10, 0x20]))
    assert list(ba.data[:2]) == [0x10, 0x20]


def test_put_numpy_array():
    ba = ByteArgs(4)
    arr = np.array([7, 8, 9], dtype=np.uint8)
    ba.put(arr)
    assert list(ba.data[:3]) == [7, 8, 9]


def test_put_color():
    ba = ByteArgs(4)
    color = Color.NewFromRgb(1.0, 0.5, 0.0)
    ba.put(color)
    assert list(ba.data[:3]) == [255, 127, 0]


def test_put_with_packing():
    ba = ByteArgs(4)
    ba.put(0x1234, packing=">H")
    assert list(ba.data[:2]) == [0x12, 0x34]


def test_put_returns_self():
    ba = ByteArgs(4)
    assert ba.put(0x01) is ba


def test_put_empty_bytes_noop():
    ba = ByteArgs(4)
    ba.put(b"")
    assert all(b == 0 for b in ba.data)


def test_put_accepts_numpy_non_uint8():
    ba = ByteArgs(4)
    arr = np.array([1, 2, 3], dtype=np.int16)
    ba.put(arr)
    assert list(ba.data[:3]) == [1, 2, 3]


def test_put_packing_overflow_raises():
    ba = ByteArgs(1)
    with pytest.raises(ValueError):
        ba.put(0xFFFF, packing=">H")
