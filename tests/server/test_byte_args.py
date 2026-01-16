#
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
#
"""Unit tests for ByteArgs class."""

from __future__ import annotations

from enum import Enum

import numpy as np
import pytest

from uchroma.colorlib import Color
from uchroma.server.byte_args import ByteArgs

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


class MockCommand(Enum):
    """Mock enum with opcode attribute for testing."""

    CMD_ONE = 0x01
    CMD_TWO = 0x02

    @property
    def opcode(self):
        return self.value


class MockStatus(Enum):
    """Mock enum without opcode (uses .value)."""

    OK = 0x00
    ERROR = 0xFF


@pytest.fixture
def byte_args_16():
    """ByteArgs with 16-byte buffer."""
    return ByteArgs(16)


@pytest.fixture
def byte_args_64():
    """ByteArgs with 64-byte buffer."""
    return ByteArgs(64)


@pytest.fixture
def byte_args_small():
    """ByteArgs with minimal 4-byte buffer."""
    return ByteArgs(4)


# ─────────────────────────────────────────────────────────────────────────────
# Initialization Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsInit:
    """Tests for ByteArgs initialization."""

    def test_init_creates_zeroed_buffer(self):
        """Buffer should be initialized with zeros."""
        ba = ByteArgs(10)
        assert all(b == 0 for b in ba.data)

    def test_init_with_size(self):
        """Buffer should have the specified size."""
        ba = ByteArgs(32)
        assert ba.size == 32

    def test_init_with_existing_data(self):
        """Should wrap existing data buffer."""
        data = bytes([0x01, 0x02, 0x03, 0x04])
        ba = ByteArgs(4, data=data)
        assert ba.size == 4
        assert ba.data[0] == 0x01
        assert ba.data[3] == 0x04

    def test_init_data_is_numpy_array(self):
        """Internal data should be numpy uint8 array."""
        ba = ByteArgs(8)
        assert isinstance(ba.data, np.ndarray)
        assert ba.data.dtype == np.uint8


# ─────────────────────────────────────────────────────────────────────────────
# Property Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsProperties:
    """Tests for ByteArgs properties."""

    def test_size_property(self, byte_args_16):
        """Size should return buffer length."""
        assert byte_args_16.size == 16

    def test_data_property_returns_array(self, byte_args_16):
        """Data property should return the internal array."""
        assert len(byte_args_16.data) == 16

    def test_data_property_reflects_puts(self, byte_args_16):
        """Data should reflect values added via put."""
        byte_args_16.put(0xAB)
        byte_args_16.put(0xCD)
        assert byte_args_16.data[0] == 0xAB
        assert byte_args_16.data[1] == 0xCD


# ─────────────────────────────────────────────────────────────────────────────
# put() Tests - Integer Values
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutIntegers:
    """Tests for putting integer values."""

    def test_put_zero(self, byte_args_16):
        """Should pack zero correctly."""
        byte_args_16.put(0)
        assert byte_args_16.data[0] == 0

    def test_put_max_byte(self, byte_args_16):
        """Should pack max byte value (255)."""
        byte_args_16.put(255)
        assert byte_args_16.data[0] == 255

    def test_put_boundary_values(self, byte_args_16):
        """Should handle boundary values correctly."""
        byte_args_16.put(0)
        byte_args_16.put(127)
        byte_args_16.put(128)
        byte_args_16.put(255)

        assert byte_args_16.data[0] == 0
        assert byte_args_16.data[1] == 127
        assert byte_args_16.data[2] == 128
        assert byte_args_16.data[3] == 255

    def test_put_advances_offset(self, byte_args_16):
        """Offset should advance after each put."""
        byte_args_16.put(0x01)
        byte_args_16.put(0x02)
        byte_args_16.put(0x03)

        assert byte_args_16.data[0] == 0x01
        assert byte_args_16.data[1] == 0x02
        assert byte_args_16.data[2] == 0x03

    def test_put_returns_self(self, byte_args_16):
        """Put should return self for chaining."""
        result = byte_args_16.put(0x01)
        assert result is byte_args_16

    def test_put_chaining(self, byte_args_16):
        """Should support method chaining."""
        byte_args_16.put(0x01).put(0x02).put(0x03)

        assert byte_args_16.data[0] == 0x01
        assert byte_args_16.data[1] == 0x02
        assert byte_args_16.data[2] == 0x03


# ─────────────────────────────────────────────────────────────────────────────
# put() Tests - Bytes and Bytearray
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutBytes:
    """Tests for putting bytes and bytearray."""

    def test_put_bytes(self, byte_args_16):
        """Should pack bytes directly."""
        byte_args_16.put(bytes([0x01, 0x02, 0x03]))

        assert byte_args_16.data[0] == 0x01
        assert byte_args_16.data[1] == 0x02
        assert byte_args_16.data[2] == 0x03

    def test_put_bytearray(self, byte_args_16):
        """Should pack bytearray directly."""
        byte_args_16.put(bytearray([0xAA, 0xBB, 0xCC]))

        assert byte_args_16.data[0] == 0xAA
        assert byte_args_16.data[1] == 0xBB
        assert byte_args_16.data[2] == 0xCC

    def test_put_empty_bytes(self, byte_args_16):
        """Should handle empty bytes gracefully."""
        byte_args_16.put(bytes([]))
        # Buffer should remain zeroed
        assert all(b == 0 for b in byte_args_16.data)

    def test_put_mixed_bytes_and_ints(self, byte_args_16):
        """Should handle mixed bytes and int operations."""
        byte_args_16.put(0x01)
        byte_args_16.put(bytes([0x02, 0x03]))
        byte_args_16.put(0x04)

        assert byte_args_16.data[0] == 0x01
        assert byte_args_16.data[1] == 0x02
        assert byte_args_16.data[2] == 0x03
        assert byte_args_16.data[3] == 0x04


# ─────────────────────────────────────────────────────────────────────────────
# put() Tests - NumPy Arrays
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutNumpy:
    """Tests for putting numpy arrays."""

    def test_put_numpy_1d(self, byte_args_16):
        """Should pack 1D numpy array."""
        arr = np.array([10, 20, 30], dtype=np.uint8)
        byte_args_16.put(arr)

        assert byte_args_16.data[0] == 10
        assert byte_args_16.data[1] == 20
        assert byte_args_16.data[2] == 30

    def test_put_numpy_2d_flattens(self, byte_args_16):
        """Should flatten 2D arrays."""
        arr = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        byte_args_16.put(arr)

        assert byte_args_16.data[0] == 1
        assert byte_args_16.data[1] == 2
        assert byte_args_16.data[2] == 3
        assert byte_args_16.data[3] == 4

    def test_put_numpy_empty(self, byte_args_16):
        """Should handle empty numpy array."""
        arr = np.array([], dtype=np.uint8)
        byte_args_16.put(arr)
        # Buffer should remain zeroed
        assert all(b == 0 for b in byte_args_16.data)


# ─────────────────────────────────────────────────────────────────────────────
# put() Tests - Color Objects
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutColor:
    """Tests for putting Color objects."""

    def test_put_red_color(self, byte_args_16):
        """Should pack red as RGB bytes."""
        red = Color.NewFromRgb(1.0, 0.0, 0.0)
        byte_args_16.put(red)

        assert byte_args_16.data[0] == 255  # R
        assert byte_args_16.data[1] == 0  # G
        assert byte_args_16.data[2] == 0  # B

    def test_put_green_color(self, byte_args_16):
        """Should pack green as RGB bytes."""
        green = Color.NewFromRgb(0.0, 1.0, 0.0)
        byte_args_16.put(green)

        assert byte_args_16.data[0] == 0  # R
        assert byte_args_16.data[1] == 255  # G
        assert byte_args_16.data[2] == 0  # B

    def test_put_blue_color(self, byte_args_16):
        """Should pack blue as RGB bytes."""
        blue = Color.NewFromRgb(0.0, 0.0, 1.0)
        byte_args_16.put(blue)

        assert byte_args_16.data[0] == 0  # R
        assert byte_args_16.data[1] == 0  # G
        assert byte_args_16.data[2] == 255  # B

    def test_put_color_ignores_alpha(self, byte_args_16):
        """Color should pack RGB only, ignoring alpha."""
        rgba = Color.NewFromRgb(1.0, 0.5, 0.25, 0.8)
        byte_args_16.put(rgba)

        # Should only write 3 bytes (RGB), not 4
        assert byte_args_16.data[0] == 255  # R
        assert byte_args_16.data[1] == 127  # G (0.5 * 255 = 127)
        assert byte_args_16.data[2] == 63  # B (0.25 * 255 = 63)
        # Position 3 should still be zero (alpha not written)
        # Verify next put would go at position 3
        byte_args_16.put(0xAB)
        assert byte_args_16.data[3] == 0xAB

    def test_put_white_color(self, byte_args_16):
        """Should pack white correctly."""
        white = Color.NewFromRgb(1.0, 1.0, 1.0)
        byte_args_16.put(white)

        assert byte_args_16.data[0] == 255
        assert byte_args_16.data[1] == 255
        assert byte_args_16.data[2] == 255

    def test_put_black_color(self, byte_args_16):
        """Should pack black correctly."""
        black = Color.NewFromRgb(0.0, 0.0, 0.0)
        byte_args_16.put(black)

        assert byte_args_16.data[0] == 0
        assert byte_args_16.data[1] == 0
        assert byte_args_16.data[2] == 0

    def test_put_multiple_colors(self, byte_args_16):
        """Should pack multiple colors sequentially."""
        red = Color.NewFromRgb(1.0, 0.0, 0.0)
        green = Color.NewFromRgb(0.0, 1.0, 0.0)

        byte_args_16.put(red).put(green)

        # Red at 0-2
        assert byte_args_16.data[0] == 255
        assert byte_args_16.data[1] == 0
        assert byte_args_16.data[2] == 0
        # Green at 3-5
        assert byte_args_16.data[3] == 0
        assert byte_args_16.data[4] == 255
        assert byte_args_16.data[5] == 0


# ─────────────────────────────────────────────────────────────────────────────
# put() Tests - Enum Values
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutEnum:
    """Tests for putting enum values."""

    def test_put_enum_with_opcode(self, byte_args_16):
        """Should use .opcode property if available."""
        byte_args_16.put(MockCommand.CMD_ONE)
        assert byte_args_16.data[0] == 0x01

    def test_put_enum_with_value(self, byte_args_16):
        """Should use .value if no opcode property."""
        byte_args_16.put(MockStatus.ERROR)
        assert byte_args_16.data[0] == 0xFF

    def test_put_multiple_enums(self, byte_args_16):
        """Should pack multiple enums sequentially."""
        byte_args_16.put(MockCommand.CMD_ONE)
        byte_args_16.put(MockCommand.CMD_TWO)
        byte_args_16.put(MockStatus.OK)

        assert byte_args_16.data[0] == 0x01
        assert byte_args_16.data[1] == 0x02
        assert byte_args_16.data[2] == 0x00


# ─────────────────────────────────────────────────────────────────────────────
# put() Tests - Struct Format Packing
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutWithPacking:
    """Tests for put() with struct format strings."""

    def test_put_byte_format(self, byte_args_16):
        """Should pack with =B format (unsigned byte)."""
        byte_args_16.put(200, packing="=B")
        assert byte_args_16.data[0] == 200

    def test_put_short_format(self, byte_args_16):
        """Should pack with =H format (unsigned short)."""
        byte_args_16.put(0x1234, packing="=H")
        # Native byte order (little-endian on most systems)
        assert byte_args_16.data[0] == 0x34
        assert byte_args_16.data[1] == 0x12

    def test_put_int_format(self, byte_args_16):
        """Should pack with =I format (unsigned int)."""
        byte_args_16.put(0x12345678, packing="=I")
        # Native byte order
        assert byte_args_16.data[0] == 0x78
        assert byte_args_16.data[1] == 0x56
        assert byte_args_16.data[2] == 0x34
        assert byte_args_16.data[3] == 0x12

    def test_put_big_endian_short(self, byte_args_16):
        """Should respect big-endian format."""
        byte_args_16.put(0x1234, packing=">H")
        assert byte_args_16.data[0] == 0x12
        assert byte_args_16.data[1] == 0x34

    def test_put_packing_overrides_type_detection(self, byte_args_16):
        """Packing format should override automatic type detection."""
        # Even though 5 fits in a byte, we force it to be a short
        byte_args_16.put(5, packing="=H")
        assert byte_args_16.data[0] == 0x05
        assert byte_args_16.data[1] == 0x00


# ─────────────────────────────────────────────────────────────────────────────
# put_all() Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutAll:
    """Tests for put_all() method."""

    def test_put_all_integers(self, byte_args_16):
        """Should pack all integers in list."""
        byte_args_16.put_all([1, 2, 3, 4])

        assert byte_args_16.data[0] == 1
        assert byte_args_16.data[1] == 2
        assert byte_args_16.data[2] == 3
        assert byte_args_16.data[3] == 4

    def test_put_all_with_packing(self, byte_args_16):
        """Should apply packing to all elements."""
        byte_args_16.put_all([0x0100, 0x0200], packing="=H")

        assert byte_args_16.data[0] == 0x00
        assert byte_args_16.data[1] == 0x01
        assert byte_args_16.data[2] == 0x00
        assert byte_args_16.data[3] == 0x02

    def test_put_all_empty_list(self, byte_args_16):
        """Should handle empty list gracefully."""
        byte_args_16.put_all([])
        assert all(b == 0 for b in byte_args_16.data)

    def test_put_all_returns_self(self, byte_args_16):
        """put_all should return self for chaining."""
        result = byte_args_16.put_all([1, 2])
        assert result is byte_args_16

    def test_put_all_mixed_with_put(self, byte_args_16):
        """Should work alongside single put() calls."""
        byte_args_16.put(0xAA)
        byte_args_16.put_all([0xBB, 0xCC])
        byte_args_16.put(0xDD)

        assert byte_args_16.data[0] == 0xAA
        assert byte_args_16.data[1] == 0xBB
        assert byte_args_16.data[2] == 0xCC
        assert byte_args_16.data[3] == 0xDD


# ─────────────────────────────────────────────────────────────────────────────
# put_short() Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutShort:
    """Tests for put_short() convenience method."""

    def test_put_short_value(self, byte_args_16):
        """Should pack as 16-bit value."""
        byte_args_16.put_short(0xABCD)

        # Native byte order (little-endian)
        assert byte_args_16.data[0] == 0xCD
        assert byte_args_16.data[1] == 0xAB

    def test_put_short_zero(self, byte_args_16):
        """Should pack zero correctly."""
        byte_args_16.put_short(0)

        assert byte_args_16.data[0] == 0
        assert byte_args_16.data[1] == 0

    def test_put_short_max(self, byte_args_16):
        """Should pack max short value."""
        byte_args_16.put_short(0xFFFF)

        assert byte_args_16.data[0] == 0xFF
        assert byte_args_16.data[1] == 0xFF

    def test_put_short_returns_self(self, byte_args_16):
        """put_short should return self for chaining."""
        result = byte_args_16.put_short(100)
        assert result is byte_args_16

    def test_put_short_advances_offset_by_two(self, byte_args_16):
        """Offset should advance by 2 bytes."""
        byte_args_16.put_short(0x1234)
        byte_args_16.put(0x56)

        assert byte_args_16.data[2] == 0x56


# ─────────────────────────────────────────────────────────────────────────────
# put_int() Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsPutInt:
    """Tests for put_int() convenience method."""

    def test_put_int_value(self, byte_args_16):
        """Should pack as 32-bit value."""
        byte_args_16.put_int(0x12345678)

        # Native byte order (little-endian)
        assert byte_args_16.data[0] == 0x78
        assert byte_args_16.data[1] == 0x56
        assert byte_args_16.data[2] == 0x34
        assert byte_args_16.data[3] == 0x12

    def test_put_int_zero(self, byte_args_16):
        """Should pack zero correctly."""
        byte_args_16.put_int(0)

        assert byte_args_16.data[0] == 0
        assert byte_args_16.data[1] == 0
        assert byte_args_16.data[2] == 0
        assert byte_args_16.data[3] == 0

    def test_put_int_max(self, byte_args_16):
        """Should pack max int value."""
        byte_args_16.put_int(0xFFFFFFFF)

        assert byte_args_16.data[0] == 0xFF
        assert byte_args_16.data[1] == 0xFF
        assert byte_args_16.data[2] == 0xFF
        assert byte_args_16.data[3] == 0xFF

    def test_put_int_returns_self(self, byte_args_16):
        """put_int should return self for chaining."""
        result = byte_args_16.put_int(100)
        assert result is byte_args_16

    def test_put_int_advances_offset_by_four(self, byte_args_16):
        """Offset should advance by 4 bytes."""
        byte_args_16.put_int(0x12345678)
        byte_args_16.put(0xAB)

        assert byte_args_16.data[4] == 0xAB


# ─────────────────────────────────────────────────────────────────────────────
# clear() Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsClear:
    """Tests for clear() method."""

    def test_clear_zeros_buffer(self, byte_args_16):
        """Clear should zero out the buffer."""
        byte_args_16.put_all([0xFF, 0xAB, 0xCD, 0xEF])
        byte_args_16.clear()

        assert all(b == 0 for b in byte_args_16.data)

    def test_clear_resets_offset(self, byte_args_16):
        """Clear should reset the write offset."""
        byte_args_16.put_all([1, 2, 3, 4])
        byte_args_16.clear()
        byte_args_16.put(0xAA)

        # Should write at position 0
        assert byte_args_16.data[0] == 0xAA
        assert byte_args_16.data[1] == 0

    def test_clear_returns_self(self, byte_args_16):
        """clear should return self for chaining."""
        result = byte_args_16.clear()
        assert result is byte_args_16

    def test_clear_chaining(self, byte_args_16):
        """Should support chaining after clear."""
        byte_args_16.put(0xFF).clear().put(0xAA)

        assert byte_args_16.data[0] == 0xAA
        assert byte_args_16.data[1] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Buffer Overflow Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsOverflow:
    """Tests for buffer overflow handling."""

    def test_overflow_single_put(self, byte_args_small):
        """Should raise when single put exceeds buffer."""
        byte_args_small.put_all([1, 2, 3])
        with pytest.raises(ValueError, match="No space left"):
            byte_args_small.put(4)
            byte_args_small.put(5)  # This would exceed 4-byte buffer

    def test_overflow_bytes(self, byte_args_small):
        """Should raise when bytes exceed buffer."""
        with pytest.raises(ValueError, match="No space left"):
            byte_args_small.put(bytes([1, 2, 3, 4, 5]))

    def test_overflow_put_short(self, byte_args_small):
        """Should raise when short exceeds buffer."""
        byte_args_small.put_all([1, 2, 3])
        with pytest.raises(ValueError, match="No space left"):
            byte_args_small.put_short(0x1234)

    def test_overflow_put_int(self, byte_args_small):
        """Should raise when int exceeds buffer."""
        byte_args_small.put(1)
        with pytest.raises(ValueError, match="No space left"):
            byte_args_small.put_int(0x12345678)

    def test_exact_fit_no_overflow(self, byte_args_small):
        """Should not raise when filling buffer exactly."""
        byte_args_small.put_all([1, 2, 3])
        # Buffer is now full (3 bytes used of 4)
        # One more byte should fit
        byte_args_small.put(4)
        # Verify all bytes written
        assert list(byte_args_small.data) == [1, 2, 3, 4]

    def test_overflow_color(self):
        """Should raise when color (3 bytes) exceeds remaining space."""
        ba = ByteArgs(4)
        ba.put_all([1, 2])
        with pytest.raises(ValueError, match="No space left"):
            ba.put(Color.NewFromRgb(1.0, 0.0, 0.0))


# ─────────────────────────────────────────────────────────────────────────────
# Offset Tracking Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsOffset:
    """Tests for offset tracking after multiple operations."""

    def test_offset_after_mixed_operations(self, byte_args_64):
        """Verify offset is correctly tracked through various operations."""
        # 1 byte
        byte_args_64.put(0x01)
        # 2 bytes
        byte_args_64.put_short(0x0203)
        # 4 bytes
        byte_args_64.put_int(0x04050607)
        # 3 bytes (Color)
        byte_args_64.put(Color.NewFromRgb(0.0, 1.0, 0.0))
        # 3 bytes (bytes)
        byte_args_64.put(bytes([0x0A, 0x0B, 0x0C]))

        # Total: 1 + 2 + 4 + 3 + 3 = 13 bytes
        # Next put should go at position 13
        byte_args_64.put(0xFF)
        assert byte_args_64.data[13] == 0xFF

    def test_offset_resets_after_clear(self, byte_args_16):
        """Offset should reset to 0 after clear."""
        byte_args_16.put_all([1, 2, 3, 4, 5])
        byte_args_16.clear()
        byte_args_16.put(0xAB)

        assert byte_args_16.data[0] == 0xAB
        assert byte_args_16.data[1] == 0  # Not 2


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestByteArgsEdgeCases:
    """Tests for edge cases."""

    def test_empty_buffer(self):
        """Zero-size buffer should still be creatable."""
        ba = ByteArgs(0)
        assert ba.size == 0
        assert len(ba.data) == 0

    def test_single_byte_buffer(self):
        """Single-byte buffer should work for a single byte."""
        ba = ByteArgs(1)
        ba.put(0x42)
        assert ba.data[0] == 0x42

    def test_single_byte_buffer_overflow(self):
        """Single-byte buffer should overflow on second put."""
        ba = ByteArgs(1)
        ba.put(0x42)
        with pytest.raises(ValueError, match="No space left"):
            ba.put(0x43)

    def test_large_buffer(self):
        """Large buffer should work."""
        ba = ByteArgs(1024)
        for i in range(1000):
            ba.put(i % 256)
        assert ba.data[999] == 999 % 256

    def test_data_view_modification(self, byte_args_16):
        """Data property returns array that can be inspected."""
        byte_args_16.put_all([0xDE, 0xAD, 0xBE, 0xEF])

        # Can iterate over data
        data_list = list(byte_args_16.data[:4])
        assert data_list == [0xDE, 0xAD, 0xBE, 0xEF]

    def test_init_with_bytes_preserves_data(self):
        """Init with existing data should preserve it."""
        original = bytes([0x11, 0x22, 0x33, 0x44])
        ba = ByteArgs(4, data=original)

        assert ba.data[0] == 0x11
        assert ba.data[1] == 0x22
        assert ba.data[2] == 0x33
        assert ba.data[3] == 0x44
