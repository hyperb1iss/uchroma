#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""
Unit tests for uchroma.util module.
"""

import struct

import pytest

from uchroma.util import (
    camel_to_snake,
    clamp,
    lerp,
    lerp_degrees,
    scale,
    scale_brightness,
    set_bits,
    snake_to_camel,
    test_bit as util_test_bit,
    to_byte,
)


# =============================================================================
# clamp() tests
# =============================================================================
class TestClamp:
    """Tests for the clamp function."""

    @pytest.mark.parametrize(
        "value,min_,max_,expected",
        [
            # Value within range - should return unchanged
            (5, 0, 10, 5),
            (0, 0, 10, 0),
            (10, 0, 10, 10),
            (5.5, 0.0, 10.0, 5.5),
            # Value below minimum - should clamp to min
            (-5, 0, 10, 0),
            (-100, 0, 10, 0),
            (-0.1, 0.0, 10.0, 0.0),
            # Value above maximum - should clamp to max
            (15, 0, 10, 10),
            (100, 0, 10, 10),
            (10.1, 0.0, 10.0, 10.0),
            # Negative ranges
            (-5, -10, -1, -5),
            (-15, -10, -1, -10),
            (0, -10, -1, -1),
            # Edge case: min equals max
            (5, 5, 5, 5),
            (0, 5, 5, 5),
            (10, 5, 5, 5),
        ],
    )
    def test_clamp_values(self, value, min_, max_, expected):
        """Test clamp with various values and ranges."""
        assert clamp(value, min_, max_) == expected

    def test_clamp_float_precision(self):
        """Test clamp preserves float precision."""
        result = clamp(0.123456789, 0.0, 1.0)
        assert result == 0.123456789


# =============================================================================
# scale() tests
# =============================================================================
class TestScale:
    """Tests for the scale function."""

    @pytest.mark.parametrize(
        "value,src_min,src_max,dst_min,dst_max,round_,expected",
        [
            # Basic scaling 0-100 to 0-255
            (0, 0, 100, 0, 255, False, 0.0),
            (100, 0, 100, 0, 255, False, 255.0),
            (50, 0, 100, 0, 255, False, 127.5),
            (50, 0, 100, 0, 255, True, 127),  # Python rounds 127.5 to 127 (banker's rounding)
            # Reverse scaling 0-255 to 0-100
            (0, 0, 255, 0, 100, False, 0.0),
            (255, 0, 255, 0, 100, False, 100.0),
            (127, 0, 255, 0, 100, False, pytest.approx(49.80, rel=0.01)),
            # Scaling with different ranges
            (5, 0, 10, 0, 100, False, 50.0),
            (5, 0, 10, 100, 200, False, 150.0),
            # Negative destination range
            (5, 0, 10, -100, 100, False, 0.0),
            (0, 0, 10, -100, 100, False, -100.0),
            (10, 0, 10, -100, 100, False, 100.0),
            # Value clamped to source range
            (-10, 0, 100, 0, 255, False, 0.0),
            (200, 0, 100, 0, 255, False, 255.0),
        ],
    )
    def test_scale_values(self, value, src_min, src_max, dst_min, dst_max, round_, expected):
        """Test scale with various ranges and rounding options."""
        result = scale(value, src_min, src_max, dst_min, dst_max, round_)
        if isinstance(expected, float) and not hasattr(expected, "approx"):
            assert result == pytest.approx(expected, rel=0.01)
        else:
            assert result == expected

    def test_scale_rounding(self):
        """Test that rounding produces integers."""
        result = scale(33, 0, 100, 0, 255, round_=True)
        assert isinstance(result, int)
        assert result == 84


# =============================================================================
# lerp() tests
# =============================================================================
class TestLerp:
    """Tests for the lerp (linear interpolation) function."""

    @pytest.mark.parametrize(
        "start,end,amount,expected",
        [
            # Basic interpolation
            (0.0, 100.0, 0.0, 0.0),
            (0.0, 100.0, 1.0, 100.0),
            (0.0, 100.0, 0.5, 50.0),
            (0.0, 100.0, 0.25, 25.0),
            (0.0, 100.0, 0.75, 75.0),
            # Negative ranges
            (-100.0, 100.0, 0.5, 0.0),
            (-100.0, 0.0, 0.5, -50.0),
            # Reverse interpolation (end < start)
            (100.0, 0.0, 0.5, 50.0),
            (100.0, 0.0, 0.0, 100.0),
            (100.0, 0.0, 1.0, 0.0),
            # Extrapolation (amount outside 0-1)
            (0.0, 100.0, 2.0, 200.0),
            (0.0, 100.0, -0.5, -50.0),
            # Same start and end
            (50.0, 50.0, 0.5, 50.0),
        ],
    )
    def test_lerp_values(self, start, end, amount, expected):
        """Test lerp with various start, end, and amount values."""
        assert lerp(start, end, amount) == pytest.approx(expected)


# =============================================================================
# lerp_degrees() tests
# =============================================================================
class TestLerpDegrees:
    """Tests for the lerp_degrees (circular interpolation) function."""

    @pytest.mark.parametrize(
        "start,end,amount,expected",
        [
            # Basic interpolation
            (0.0, 90.0, 0.0, 0.0),
            (0.0, 90.0, 1.0, 90.0),
            (0.0, 90.0, 0.5, 45.0),
            # Interpolation crossing 360/0 boundary
            (350.0, 10.0, 0.5, 0.0),  # Should take short path
            (10.0, 350.0, 0.5, 0.0),  # Should take short path
            # Full circle cases
            (0.0, 360.0, 0.5, 0.0),  # 360 == 0 in circular math
            (0.0, 180.0, 0.5, 90.0),
            (180.0, 0.0, 0.5, 90.0),  # Reverse direction
            # Negative angles (normalized)
            (0.0, -90.0, 0.5, 315.0),  # -45 normalized to 315
            # Large angles
            (720.0, 0.0, 0.5, 0.0),  # 720 == 0
        ],
    )
    def test_lerp_degrees_values(self, start, end, amount, expected):
        """Test lerp_degrees takes shortest path around circle."""
        result = lerp_degrees(start, end, amount)
        # Normalize both for comparison
        result_normalized = result % 360.0
        expected_normalized = expected % 360.0
        assert result_normalized == pytest.approx(expected_normalized, abs=0.1)

    def test_lerp_degrees_always_positive(self):
        """Test that lerp_degrees always returns positive angles."""
        # Test various combinations that might produce negative results
        for start in [0, 90, 180, 270, 350]:
            for end in [0, 90, 180, 270, 350]:
                for amount in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    result = lerp_degrees(start, end, amount)
                    assert 0.0 <= result < 360.0, (
                        f"lerp_degrees({start}, {end}, {amount}) = {result}"
                    )


# =============================================================================
# scale_brightness() tests
# =============================================================================
class TestScaleBrightness:
    """Tests for the scale_brightness function."""

    @pytest.mark.parametrize(
        "brightness,expected",
        [
            # Percentage to hardware (0-100 -> 0-255)
            (0.0, 0),
            (100.0, 255),
            (50.0, 127),  # Python banker's rounding: 127.5 -> 127
            (25.0, 64),
            (75.0, 191),
        ],
    )
    def test_brightness_to_hw(self, brightness, expected):
        """Test converting percentage brightness to hardware value."""
        result = scale_brightness(brightness, from_hw=False)
        assert result == expected
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "brightness,expected",
        [
            # Hardware to percentage (0-255 -> 0-100)
            (0, 0.0),
            (255, 100.0),
            (128, pytest.approx(50.20, rel=0.01)),
            (64, pytest.approx(25.10, rel=0.01)),
        ],
    )
    def test_brightness_from_hw(self, brightness, expected):
        """Test converting hardware value to percentage brightness."""
        result = scale_brightness(brightness, from_hw=True)
        assert result == expected
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "brightness",
        [-1.0, -0.1, 100.1, 200.0],
    )
    def test_brightness_to_hw_out_of_range(self, brightness):
        """Test that out-of-range percentage values raise ValueError."""
        with pytest.raises(ValueError, match="Float brightness must be between 0 and 100"):
            scale_brightness(brightness, from_hw=False)

    @pytest.mark.parametrize(
        "brightness",
        [-1, -10, 256, 1000],
    )
    def test_brightness_from_hw_out_of_range(self, brightness):
        """Test that out-of-range hardware values raise ValueError."""
        with pytest.raises(ValueError, match="Integer brightness must be between 0 and 255"):
            scale_brightness(brightness, from_hw=True)

    def test_brightness_roundtrip(self):
        """Test that converting back and forth is reasonably accurate."""
        # Note: Not perfectly reversible due to rounding
        for pct in [0.0, 25.0, 50.0, 75.0, 100.0]:
            hw_value = scale_brightness(pct, from_hw=False)
            result = scale_brightness(hw_value, from_hw=True)
            assert result == pytest.approx(pct, abs=0.5)


# =============================================================================
# test_bit() tests
# =============================================================================
class TestTestBit:
    """Tests for the test_bit function."""

    @pytest.mark.parametrize(
        "value,bit,expected",
        [
            # Single bit values
            (0b00000001, 0, True),
            (0b00000010, 1, True),
            (0b00000100, 2, True),
            (0b00001000, 3, True),
            (0b10000000, 7, True),
            # Unset bits
            (0b00000000, 0, False),
            (0b00000001, 1, False),
            (0b11111110, 0, False),
            # Multiple bits set
            (0b11111111, 0, True),
            (0b11111111, 7, True),
            (0b10101010, 1, True),
            (0b10101010, 0, False),
            # Zero value
            (0, 0, False),
            (0, 7, False),
            # Large values
            (0xFF, 7, True),
            (0x100, 8, True),
            (0x100, 0, False),
        ],
    )
    def test_bit_values(self, value, bit, expected):
        """Test test_bit with various values and bit positions."""
        assert util_test_bit(value, bit) is expected


# =============================================================================
# set_bits() tests
# =============================================================================
class TestSetBits:
    """Tests for the set_bits function."""

    @pytest.mark.parametrize(
        "value,bits,expected",
        [
            # Set single bits from zero
            (0, (True,), 0b00000001),
            (0, (False, True), 0b00000010),
            (0, (True, True), 0b00000011),
            (0, (True, False, True), 0b00000101),
            # Clear bits
            (0b11111111, (False,), 0b11111110),
            (0b11111111, (False, False), 0b11111100),
            # Mixed set and clear
            (0b00001111, (False, True, False, True), 0b00001010),
            # No change
            (0b00000001, (True,), 0b00000001),
            (0b00000000, (False,), 0b00000000),
            # Multiple bits from non-zero
            (0b10000000, (True, True, True, True), 0b10001111),
            # Empty bits tuple (no change)
            (0b10101010, (), 0b10101010),
        ],
    )
    def test_set_bits_values(self, value, bits, expected):
        """Test set_bits with various values and bit patterns."""
        assert set_bits(value, *bits) == expected

    def test_set_bits_preserves_higher_bits(self):
        """Test that set_bits only affects the specified bit positions."""
        # Set bits 0-3, should not affect bits 4-7
        result = set_bits(0b11110000, True, True, True, True)
        assert result == 0b11111111

        # Clear bits 0-3, should not affect bits 4-7
        result = set_bits(0b11111111, False, False, False, False)
        assert result == 0b11110000


# =============================================================================
# snake_to_camel() tests
# =============================================================================
class TestSnakeToCamel:
    """Tests for the snake_to_camel function."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            # Basic conversions
            ("hello_world", "HelloWorld"),
            ("snake_case_name", "SnakeCaseName"),
            ("foo", "Foo"),
            # Single word
            ("hello", "Hello"),
            # Multiple underscores with letters
            ("a_b_c_d", "ABCD"),
            # Empty string
            ("", ""),
            # Leading underscore (regex only matches _[a-z])
            ("_private", "Private"),
            # Numbers are preserved with underscores (regex matches [a-z] only)
            ("test_123", "Test_123"),
            ("test_1_2_3", "Test_1_2_3"),
            # Already capitalized letters after underscore aren't matched
            ("Hello_World", "Hello_World"),
            # Double underscore - only one gets consumed
            ("__dunder", "_Dunder"),
            # Trailing underscore preserved
            ("trailing_", "Trailing_"),
        ],
    )
    def test_snake_to_camel_values(self, name, expected):
        """Test snake_to_camel with various inputs."""
        assert snake_to_camel(name) == expected


# =============================================================================
# camel_to_snake() tests
# =============================================================================
class TestCamelToSnake:
    """Tests for the camel_to_snake function."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            # Basic conversions
            ("HelloWorld", "hello_world"),
            ("CamelCaseName", "camel_case_name"),
            ("Foo", "foo"),
            # Single word lowercase
            ("hello", "hello"),
            # Consecutive capitals (acronyms)
            ("HTTPServer", "http_server"),
            ("XMLParser", "xml_parser"),
            ("getHTTPResponse", "get_http_response"),
            # Numbers
            ("Test123", "test123"),
            ("Test1Test2", "test1_test2"),
            # Already snake_case
            ("already_snake", "already_snake"),
            # Empty string
            ("", ""),
            # Single character
            ("A", "a"),
            ("a", "a"),
        ],
    )
    def test_camel_to_snake_values(self, name, expected):
        """Test camel_to_snake with various inputs."""
        assert camel_to_snake(name) == expected

    def test_roundtrip_snake_to_camel_to_snake(self):
        """Test that snake -> camel -> snake preserves the original."""
        original = "hello_world"
        camel = snake_to_camel(original)
        result = camel_to_snake(camel)
        assert result == original


# =============================================================================
# to_byte() tests
# =============================================================================
class TestToByte:
    """Tests for the to_byte function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, b"\x00"),
            (1, b"\x01"),
            (127, b"\x7f"),
            (128, b"\x80"),
            (255, b"\xff"),
            (42, b"\x2a"),
        ],
    )
    def test_to_byte_values(self, value, expected):
        """Test to_byte with various valid byte values."""
        result = to_byte(value)
        assert result == expected
        assert isinstance(result, bytes)
        assert len(result) == 1

    def test_to_byte_negative_raises(self):
        """Test that negative values raise an error."""
        with pytest.raises(struct.error):
            to_byte(-1)

    def test_to_byte_too_large_raises(self):
        """Test that values > 255 raise an error."""
        with pytest.raises(struct.error):
            to_byte(256)

    def test_to_byte_way_too_large_raises(self):
        """Test that very large values raise an error."""
        with pytest.raises(struct.error):
            to_byte(1000)
