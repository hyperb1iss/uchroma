#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for D-Bus preparation helpers."""

import numpy as np

from uchroma.dbus_utils import dbus_prepare


def test_dbus_prepare_int_signature_stable():
    _, sig = dbus_prepare(1)
    assert sig == "i"

    _, sig = dbus_prepare(2**40)
    assert sig == "x"


def test_dbus_prepare_bytes_uses_ay():
    obj, sig = dbus_prepare(b"\x00\x01")
    assert sig == "ay"
    assert obj == b"\x00\x01"


def test_dbus_prepare_numpy_uint8_array():
    obj, sig = dbus_prepare(np.array([1, 2], dtype=np.uint8))
    assert sig == "ay"
    assert obj == [1, 2]


def test_dbus_prepare_numpy_float32_array():
    obj, sig = dbus_prepare(np.array([1.5, 2.25], dtype=np.float32))
    assert sig == "ad"
    assert obj == [1.5, 2.25]


def test_dbus_prepare_list_of_ints():
    obj, sig = dbus_prepare([1, 2, 3])
    assert sig == "ai"
    assert obj == [1, 2, 3]


def test_dbus_prepare_dict_of_ints():
    obj, sig = dbus_prepare({"a": 1, "b": 2})
    assert sig == "a{si}"
    assert obj == {"a": 1, "b": 2}
