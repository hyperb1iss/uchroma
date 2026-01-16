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


# =============================================================================
# max_keylen() tests
# =============================================================================
class TestMaxKeylen:
    """Tests for the max_keylen function."""

    def test_max_keylen_basic(self):
        """Test max_keylen with basic dict."""
        from uchroma.util import max_keylen

        d = {"a": 1, "bb": 2, "ccc": 3}
        assert max_keylen(d) == 3

    def test_max_keylen_single_key(self):
        """Test max_keylen with single key."""
        from uchroma.util import max_keylen

        d = {"hello": 1}
        assert max_keylen(d) == 5

    def test_max_keylen_equal_lengths(self):
        """Test max_keylen when all keys same length."""
        from uchroma.util import max_keylen

        d = {"aa": 1, "bb": 2, "cc": 3}
        assert max_keylen(d) == 2


# =============================================================================
# smart_delay() tests
# =============================================================================
class TestSmartDelay:
    """Tests for the smart_delay function."""

    def test_smart_delay_returns_timestamp(self):
        """smart_delay returns a monotonic timestamp."""

        from uchroma.util import smart_delay

        result = smart_delay(0.0, None)
        assert isinstance(result, float)
        assert result > 0

    def test_smart_delay_skips_when_remain_nonzero(self):
        """smart_delay skips delay when remain > 0."""
        import time

        from uchroma.util import smart_delay

        start = time.monotonic()
        smart_delay(1.0, start - 0.5, remain=1)  # Would sleep if remain=0
        elapsed = time.monotonic() - start
        # Should not have slept
        assert elapsed < 0.1

    def test_smart_delay_sleeps_when_needed(self):
        """smart_delay sleeps for remaining time."""
        import time

        from uchroma.util import smart_delay

        delay = 0.02  # 20ms delay
        last_cmd = time.monotonic()
        time.sleep(0.005)  # Sleep 5ms
        start = time.monotonic()
        smart_delay(delay, last_cmd, remain=0)
        elapsed = time.monotonic() - start
        # Should have slept for ~15ms (20ms - 5ms elapsed)
        assert elapsed >= 0.01

    def test_smart_delay_no_sleep_when_enough_time_passed(self):
        """smart_delay doesn't sleep if enough time already passed."""
        import time

        from uchroma.util import smart_delay

        delay = 0.01  # 10ms
        last_cmd = time.monotonic() - 0.1  # 100ms ago
        start = time.monotonic()
        smart_delay(delay, last_cmd, remain=0)
        elapsed = time.monotonic() - start
        # Should not have slept
        assert elapsed < 0.005


# =============================================================================
# ArgsDict tests
# =============================================================================
class TestArgsDict:
    """Tests for the ArgsDict class."""

    def test_argsdict_removes_none_values(self):
        """ArgsDict removes keys with None values."""
        from uchroma.util import ArgsDict

        d = ArgsDict({"a": 1, "b": None, "c": 3})
        assert "a" in d
        assert "b" not in d
        assert "c" in d

    def test_argsdict_keeps_non_none(self):
        """ArgsDict keeps all non-None values."""
        from uchroma.util import ArgsDict

        d = ArgsDict({"a": 0, "b": "", "c": False})
        assert "a" in d  # 0 is not None
        assert "b" in d  # empty string is not None
        assert "c" in d  # False is not None

    def test_argsdict_empty(self):
        """ArgsDict works with empty dict."""
        from uchroma.util import ArgsDict

        d = ArgsDict()
        assert len(d) == 0


# =============================================================================
# Signal tests
# =============================================================================
class TestSignal:
    """Tests for the Signal class."""

    def test_signal_connect_and_fire(self):
        """Signal connects handlers and fires them."""
        from uchroma.util import Signal

        results = []
        signal = Signal()
        signal.connect(lambda x: results.append(x))

        signal.fire(42)
        assert results == [42]

    def test_signal_multiple_handlers(self):
        """Signal fires all connected handlers."""
        from uchroma.util import Signal

        results = []
        signal = Signal()
        signal.connect(lambda x: results.append(f"a:{x}"))
        signal.connect(lambda x: results.append(f"b:{x}"))

        signal.fire("test")
        assert "a:test" in results
        assert "b:test" in results

    def test_signal_fire_with_kwargs(self):
        """Signal passes kwargs to handlers."""
        from uchroma.util import Signal

        results = []
        signal = Signal()
        signal.connect(lambda a, b=None: results.append((a, b)))

        signal.fire(1, b=2)
        assert results == [(1, 2)]


# =============================================================================
# Singleton tests
# =============================================================================
class TestSingleton:
    """Tests for the Singleton metaclass."""

    def test_singleton_returns_same_instance(self):
        """Singleton metaclass returns same instance."""
        from uchroma.util import Singleton

        class MySingleton(metaclass=Singleton):
            def __init__(self):
                self.value = 42

        a = MySingleton()
        b = MySingleton()
        assert a is b

    def test_singleton_preserves_state(self):
        """Singleton preserves state across calls."""
        from uchroma.util import Singleton

        class Counter(metaclass=Singleton):
            def __init__(self):
                self.count = 0

        c1 = Counter()
        c1.count = 10
        c2 = Counter()
        assert c2.count == 10


# =============================================================================
# Ticker tests
# =============================================================================
class TestTicker:
    """Tests for the Ticker class."""

    def test_ticker_interval_property(self):
        """Ticker interval property works."""
        from uchroma.util import Ticker

        ticker = Ticker(0.1)
        assert ticker.interval == 0.1

    def test_ticker_interval_setter(self):
        """Ticker interval can be changed."""
        from uchroma.util import Ticker

        ticker = Ticker(0.1)
        ticker.interval = 0.2
        assert ticker.interval == 0.2

    def test_ticker_context_manager(self):
        """Ticker works as sync context manager."""

        from uchroma.util import Ticker

        ticker = Ticker(0.01)
        with ticker:
            pass  # Do nothing
        # Should have recorded next tick time
        assert ticker._next_tick >= 0

    def test_ticker_handles_overrun(self):
        """Ticker handles interval overrun."""
        import time

        from uchroma.util import Ticker

        ticker = Ticker(0.001)  # 1ms interval
        with ticker:
            time.sleep(0.01)  # Sleep 10ms (overrun)
        # Should sync to next interval
        assert ticker._next_tick >= 0

    def test_ticker_async_context_manager(self):
        """Ticker works as async context manager."""
        import asyncio

        from uchroma.util import Ticker

        async def test_async():
            ticker = Ticker(0.001)
            async with ticker:
                pass
            return True

        result = asyncio.run(test_async())
        assert result is True


# =============================================================================
# autocast_decorator tests
# =============================================================================
class TestAutocastDecorator:
    """Tests for the autocast_decorator function."""

    def test_autocast_decorator_basic(self):
        """autocast_decorator applies fix_arg_func to hinted args."""

        from uchroma.util import autocast_decorator

        MyType = str

        def to_upper(val):
            if val is not None:
                return val.upper()
            return val

        decorator = autocast_decorator(MyType, to_upper)

        @decorator
        def test_func(name: MyType):
            return name

        result = test_func("hello")
        assert result == "HELLO"

    def test_autocast_decorator_kwargs(self):
        """autocast_decorator handles kwargs."""

        from uchroma.util import autocast_decorator

        MyType = int

        def double(val):
            return val * 2

        decorator = autocast_decorator(MyType, double)

        @decorator
        def test_func(value: MyType = 5):
            return value

        result = test_func(value=10)
        assert result == 20

    def test_autocast_decorator_no_hints_raises(self):
        """autocast_decorator raises if no matching hints."""
        from uchroma.util import AUTOCAST_CACHE, autocast_decorator

        MyType = float

        def identity(val):
            return val

        decorator = autocast_decorator(MyType, identity)

        @decorator
        def test_func(x: int):  # No MyType hints
            return x

        # Clear cache to ensure fresh check
        AUTOCAST_CACHE.clear()

        with pytest.raises(ValueError, match="No arguments with"):
            test_func(5)
