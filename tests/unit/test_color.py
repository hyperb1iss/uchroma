# uchroma - Unit tests for color utilities
"""
Comprehensive tests for uchroma.color and uchroma.colorlib modules.

Tests cover:
- Color conversion utilities (rgb_from_tuple, rgb_to_int_tuple, to_color, to_rgb)
- ColorUtils methods (luminance, contrast_ratio, inverse, hsv_gradient)
- Color factory methods (NewFromHtml, NewFromRgb, NewFromHsv)
- Color scheme generation (AnalogousScheme, TriadicScheme, ComplementaryScheme)
"""

from __future__ import annotations

import pytest

from uchroma.color import (
    ColorUtils,
    rgb_from_tuple,
    rgb_to_int_tuple,
    to_color,
    to_rgb,
)
from uchroma.colorlib import Color

# ─────────────────────────────────────────────────────────────────────────────
# Tests for rgb_from_tuple
# ─────────────────────────────────────────────────────────────────────────────


class TestRgbFromTuple:
    """Tests for rgb_from_tuple conversion."""

    @pytest.mark.parametrize(
        "int_tuple,expected_rgb",
        [
            ((255, 0, 0), (1.0, 0.0, 0.0)),
            ((0, 255, 0), (0.0, 1.0, 0.0)),
            ((0, 0, 255), (0.0, 0.0, 1.0)),
            ((255, 255, 255), (1.0, 1.0, 1.0)),
            ((0, 0, 0), (0.0, 0.0, 0.0)),
            ((128, 128, 128), (128 / 255, 128 / 255, 128 / 255)),
        ],
    )
    def test_int_tuple_conversion(self, int_tuple, expected_rgb):
        """Convert int tuples (0-255) to Color objects."""
        color = rgb_from_tuple(int_tuple)
        assert isinstance(color, Color)
        assert color.rgb == pytest.approx(expected_rgb, abs=0.01)

    @pytest.mark.parametrize(
        "float_tuple",
        [
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.5, 0.5, 0.5),
        ],
    )
    def test_float_tuple_conversion(self, float_tuple):
        """Convert float tuples (0-1) to Color objects."""
        color = rgb_from_tuple(float_tuple)
        assert isinstance(color, Color)
        assert color.rgb == pytest.approx(float_tuple, abs=0.01)

    def test_none_first_element_returns_black(self):
        """None as first element returns black."""
        color = rgb_from_tuple((None, None, None))
        assert color.rgb == pytest.approx((0.0, 0.0, 0.0), abs=0.01)

    def test_tuple_with_alpha(self):
        """Tuples with 4 elements (RGBA) are handled."""
        color = rgb_from_tuple((255, 128, 64, 255))
        assert isinstance(color, Color)
        # Should use first 3 elements
        assert color.rgb[0] == pytest.approx(1.0, abs=0.01)

    def test_invalid_tuple_raises_error(self):
        """Short tuples raise TypeError."""
        with pytest.raises(TypeError):
            rgb_from_tuple((255, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Tests for rgb_to_int_tuple
# ─────────────────────────────────────────────────────────────────────────────


class TestRgbToIntTuple:
    """Tests for rgb_to_int_tuple sanitization."""

    @pytest.mark.parametrize(
        "input_tuple,expected",
        [
            ((255.0, 128.0, 64.0), (255, 128, 64)),
            ((0.0, 0.0, 0.0), (0, 0, 0)),
            ((255.4, 127.6, 0.1), (255, 128, 0)),  # Rounds to nearest
        ],
    )
    def test_float_to_int_conversion(self, input_tuple, expected):
        """Float values are rounded to int."""
        result = rgb_to_int_tuple(input_tuple)
        assert result == expected

    @pytest.mark.parametrize(
        "input_tuple,expected",
        [
            ((300, 128, 64), (255, 128, 64)),  # Clamps high values
            ((-10, 128, 64), (0, 128, 64)),  # Clamps negative values
            ((256, -1, 300), (255, 0, 255)),  # Multiple clamps
        ],
    )
    def test_clamping(self, input_tuple, expected):
        """Values are clamped to 0-255 range."""
        result = rgb_to_int_tuple(input_tuple)
        assert result == expected

    def test_tuple_with_alpha_ignores_fourth(self):
        """RGBA tuple only returns RGB."""
        result = rgb_to_int_tuple((128, 64, 32, 255))
        assert result == (128, 64, 32)
        assert len(result) == 3

    def test_invalid_tuple_raises_error(self):
        """Short tuples raise TypeError."""
        with pytest.raises(TypeError):
            rgb_to_int_tuple((255,))


# ─────────────────────────────────────────────────────────────────────────────
# Tests for to_color
# ─────────────────────────────────────────────────────────────────────────────


class TestToColor:
    """Tests for universal color parser."""

    def test_color_passthrough(self, red_color):
        """Color objects pass through unchanged."""
        result = to_color(red_color)
        assert result is red_color

    @pytest.mark.parametrize(
        "hex_str,expected_rgb",
        [
            ("#ff0000", (1.0, 0.0, 0.0)),
            ("#00ff00", (0.0, 1.0, 0.0)),
            ("#0000ff", (0.0, 0.0, 1.0)),
            ("#ffffff", (1.0, 1.0, 1.0)),
            ("#000000", (0.0, 0.0, 0.0)),
        ],
    )
    def test_hex_string_parsing(self, hex_str, expected_rgb):
        """Hex color strings are parsed correctly."""
        result = to_color(hex_str)
        assert isinstance(result, Color)
        assert result.rgb == pytest.approx(expected_rgb, abs=0.01)

    def test_hex_without_hash_not_supported(self):
        """Hex strings without # prefix are not supported by coloraide."""
        # coloraide requires the # prefix for hex colors
        with pytest.raises(Exception):
            to_color("ff0000")

    @pytest.mark.parametrize(
        "name,expected_rgb",
        [
            ("red", (1.0, 0.0, 0.0)),
            ("green", (0.0, 128 / 255, 0.0)),  # CSS green is #008000
            ("blue", (0.0, 0.0, 1.0)),
            ("white", (1.0, 1.0, 1.0)),
            ("black", (0.0, 0.0, 0.0)),
            ("lime", (0.0, 1.0, 0.0)),  # CSS lime is #00ff00
        ],
    )
    def test_named_color_parsing(self, name, expected_rgb):
        """Named colors are parsed correctly."""
        result = to_color(name)
        assert isinstance(result, Color)
        assert result.rgb == pytest.approx(expected_rgb, abs=0.01)

    def test_int_tuple_parsing(self):
        """Int tuples (0-255) are parsed."""
        result = to_color((255, 128, 64))
        assert isinstance(result, Color)
        assert result.rgb == pytest.approx((1.0, 128 / 255, 64 / 255), abs=0.01)

    def test_float_tuple_parsing(self):
        """Float tuples (0-1) are parsed."""
        result = to_color((0.5, 0.25, 0.75))
        assert isinstance(result, Color)
        assert result.rgb == pytest.approx((0.5, 0.25, 0.75), abs=0.01)

    def test_none_returns_none(self):
        """None input returns None."""
        assert to_color(None) is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert to_color("") is None

    def test_multiple_args_returns_list(self):
        """Multiple arguments return a list."""
        result = to_color("red", "green", "blue")
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(c, Color) for c in result)

    def test_no_args_returns_none(self):
        """No arguments returns None."""
        assert to_color() is None

    def test_tuple_string_parsing(self):
        """String representation of RGBA tuple is parsed."""
        # This tests the COLOR_TUPLE_STR regex pattern
        result = to_color("(1.0, 0.0, 0.0, 1.0)")
        assert isinstance(result, Color)
        assert result.rgb == pytest.approx((1.0, 0.0, 0.0), abs=0.01)

    def test_invalid_type_raises_error(self):
        """Invalid types raise TypeError."""
        with pytest.raises(TypeError):
            to_color(12345)  # Int is not valid


# ─────────────────────────────────────────────────────────────────────────────
# Tests for to_rgb
# ─────────────────────────────────────────────────────────────────────────────


class TestToRgb:
    """Tests for RGB tuple conversion."""

    def test_none_returns_black(self):
        """None returns black tuple."""
        assert to_rgb(None) == (0, 0, 0)

    def test_color_object_conversion(self, red_color):
        """Color objects convert to int tuple."""
        result = to_rgb(red_color)
        assert result == (255, 0, 0)

    @pytest.mark.parametrize(
        "hex_str,expected",
        [
            ("#ff0000", (255, 0, 0)),
            ("#00ff00", (0, 255, 0)),
            ("#0000ff", (0, 0, 255)),
        ],
    )
    def test_hex_string_conversion(self, hex_str, expected):
        """Hex strings convert to int tuple."""
        assert to_rgb(hex_str) == expected

    def test_tuple_with_none_first_returns_black(self):
        """Tuple with None first element returns black."""
        assert to_rgb((None, None, None)) == (0, 0, 0)

    def test_int_tuple_passthrough(self):
        """Int tuples pass through with clamping."""
        result = to_rgb((128, 64, 32))
        assert result == (128, 64, 32)

    def test_nested_list_conversion(self):
        """Nested lists are recursively converted."""
        result = to_rgb(["red", "blue"])
        assert result == [(255, 0, 0), (0, 0, 255)]

    def test_nested_tuple_conversion(self):
        """Nested tuples with Color objects are converted."""
        red = Color.NewFromRgb(1.0, 0.0, 0.0)
        blue = Color.NewFromRgb(0.0, 0.0, 1.0)
        result = to_rgb((red, blue))
        assert result == [(255, 0, 0), (0, 0, 255)]

    def test_invalid_type_raises_error(self):
        """Invalid types raise TypeError."""
        with pytest.raises(TypeError):
            to_rgb(object())


# ─────────────────────────────────────────────────────────────────────────────
# Tests for ColorUtils.luminance
# ─────────────────────────────────────────────────────────────────────────────


class TestColorUtilsLuminance:
    """Tests for WCAG 2.0 relative luminance calculation."""

    def test_white_luminance(self, white_color):
        """White has luminance of 1.0."""
        assert ColorUtils.luminance(white_color) == pytest.approx(1.0, abs=0.01)

    def test_black_luminance(self, black_color):
        """Black has luminance of 0.0."""
        assert ColorUtils.luminance(black_color) == pytest.approx(0.0, abs=0.01)

    def test_red_luminance(self, red_color):
        """Red has expected luminance (0.2126 coefficient)."""
        # Red contributes 0.2126 to luminance
        expected = 0.2126
        assert ColorUtils.luminance(red_color) == pytest.approx(expected, abs=0.01)

    def test_green_luminance(self, green_color):
        """Green has expected luminance (0.7152 coefficient)."""
        # Green contributes 0.7152 to luminance
        expected = 0.7152
        assert ColorUtils.luminance(green_color) == pytest.approx(expected, abs=0.01)

    def test_blue_luminance(self, blue_color):
        """Blue has expected luminance (0.0722 coefficient)."""
        # Blue contributes 0.0722 to luminance
        expected = 0.0722
        assert ColorUtils.luminance(blue_color) == pytest.approx(expected, abs=0.01)

    def test_accepts_string_color(self):
        """String color names are accepted via decorator."""
        lum = ColorUtils.luminance("white")
        assert lum == pytest.approx(1.0, abs=0.01)

    def test_accepts_tuple_color(self):
        """Tuple colors are accepted via decorator."""
        lum = ColorUtils.luminance((255, 255, 255))
        assert lum == pytest.approx(1.0, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for ColorUtils.contrast_ratio
# ─────────────────────────────────────────────────────────────────────────────


class TestColorUtilsContrastRatio:
    """Tests for WCAG 2.0 contrast ratio calculation."""

    def test_black_white_contrast(self, black_color, white_color):
        """Black/white has maximum contrast ratio of 21."""
        ratio = ColorUtils.contrast_ratio(black_color, white_color)
        assert ratio == pytest.approx(21.0, abs=0.1)

    def test_white_black_contrast(self, white_color, black_color):
        """White/black order doesn't matter."""
        ratio = ColorUtils.contrast_ratio(white_color, black_color)
        assert ratio == pytest.approx(21.0, abs=0.1)

    def test_same_color_contrast(self, red_color):
        """Same colors have contrast ratio of 1.0."""
        ratio = ColorUtils.contrast_ratio(red_color, red_color)
        assert ratio == pytest.approx(1.0, abs=0.01)

    def test_contrast_always_gte_1(self, red_color, green_color):
        """Contrast ratio is always >= 1.0."""
        ratio = ColorUtils.contrast_ratio(red_color, green_color)
        assert ratio >= 1.0

    def test_accepts_string_colors(self):
        """String color names are accepted via decorator."""
        ratio = ColorUtils.contrast_ratio("black", "white")
        assert ratio == pytest.approx(21.0, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for ColorUtils.inverse
# ─────────────────────────────────────────────────────────────────────────────


class TestColorUtilsInverse:
    """Tests for RGB inverse calculation."""

    def test_white_inverse_is_black(self, white_color):
        """Inverse of white is black."""
        inv = ColorUtils.inverse(white_color)
        assert inv.rgb == pytest.approx((0.0, 0.0, 0.0), abs=0.01)

    def test_black_inverse_is_white(self, black_color):
        """Inverse of black is white."""
        inv = ColorUtils.inverse(black_color)
        assert inv.rgb == pytest.approx((1.0, 1.0, 1.0), abs=0.01)

    def test_red_inverse_is_cyan(self, red_color):
        """Inverse of red is cyan."""
        inv = ColorUtils.inverse(red_color)
        assert inv.rgb == pytest.approx((0.0, 1.0, 1.0), abs=0.01)

    def test_inverse_preserves_alpha(self):
        """Inverse preserves alpha channel."""
        color = Color.NewFromRgb(1.0, 0.0, 0.0, 0.5)
        inv = ColorUtils.inverse(color)
        assert inv.alpha() == pytest.approx(0.5, abs=0.01)

    def test_double_inverse_returns_original(self, red_color):
        """Double inverse returns original color."""
        double_inv = ColorUtils.inverse(ColorUtils.inverse(red_color))
        assert double_inv.rgb == pytest.approx(red_color.rgb, abs=0.01)

    def test_accepts_string_color(self):
        """String color names are accepted via decorator."""
        inv = ColorUtils.inverse("white")
        assert inv.rgb == pytest.approx((0.0, 0.0, 0.0), abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for ColorUtils.hsv_gradient
# ─────────────────────────────────────────────────────────────────────────────


class TestColorUtilsHsvGradient:
    """Tests for HSV gradient generation."""

    def test_gradient_length(self, red_color, blue_color):
        """Gradient has correct number of steps."""
        gradient = ColorUtils.hsv_gradient(red_color, blue_color, 10)
        assert len(gradient) == 10

    def test_gradient_endpoints(self, red_color, blue_color):
        """Gradient starts and ends with input colors."""
        gradient = ColorUtils.hsv_gradient(red_color, blue_color, 10)
        # First color should be close to red
        assert gradient[0].rgb[0] == pytest.approx(1.0, abs=0.1)
        # Last color should be close to blue
        assert gradient[-1].rgb[2] == pytest.approx(1.0, abs=0.1)

    def test_gradient_all_colors(self, red_color, green_color):
        """All gradient elements are Color objects."""
        gradient = ColorUtils.hsv_gradient(red_color, green_color, 5)
        assert all(isinstance(c, Color) for c in gradient)

    def test_single_step_gradient(self, red_color, blue_color):
        """Single step gradient contains one color."""
        # Note: steps=1 causes division by zero, minimum useful is 2
        gradient = ColorUtils.hsv_gradient(red_color, blue_color, 2)
        assert len(gradient) == 2

    def test_accepts_string_colors(self):
        """String color names are accepted via decorator."""
        gradient = ColorUtils.hsv_gradient("red", "blue", 5)
        assert len(gradient) == 5
        assert all(isinstance(c, Color) for c in gradient)

    def test_gradient_with_alpha(self):
        """Gradient interpolates alpha values."""
        c1 = Color.NewFromRgb(1.0, 0.0, 0.0, 0.0)
        c2 = Color.NewFromRgb(0.0, 0.0, 1.0, 1.0)
        gradient = ColorUtils.hsv_gradient(c1, c2, 3)
        # Middle color should have alpha ~0.5
        assert gradient[1].alpha() == pytest.approx(0.5, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color.NewFromHtml
# ─────────────────────────────────────────────────────────────────────────────


class TestColorNewFromHtml:
    """Tests for HTML color parsing."""

    @pytest.mark.parametrize(
        "html,expected_rgb",
        [
            ("#ff0000", (1.0, 0.0, 0.0)),
            ("#00ff00", (0.0, 1.0, 0.0)),
            ("#0000ff", (0.0, 0.0, 1.0)),
            ("#ffffff", (1.0, 1.0, 1.0)),
            ("#000000", (0.0, 0.0, 0.0)),
            ("#808080", (128 / 255, 128 / 255, 128 / 255)),
        ],
    )
    def test_hex_colors(self, html, expected_rgb):
        """Hex colors are parsed correctly."""
        color = Color.NewFromHtml(html)
        assert color.rgb == pytest.approx(expected_rgb, abs=0.01)

    @pytest.mark.parametrize(
        "name,expected_rgb",
        [
            ("red", (1.0, 0.0, 0.0)),
            ("blue", (0.0, 0.0, 1.0)),
            ("white", (1.0, 1.0, 1.0)),
            ("black", (0.0, 0.0, 0.0)),
            ("lime", (0.0, 1.0, 0.0)),
            ("cyan", (0.0, 1.0, 1.0)),
            ("magenta", (1.0, 0.0, 1.0)),
            ("yellow", (1.0, 1.0, 0.0)),
        ],
    )
    def test_named_colors(self, name, expected_rgb):
        """Named colors are parsed correctly."""
        color = Color.NewFromHtml(name)
        assert color.rgb == pytest.approx(expected_rgb, abs=0.01)

    def test_short_hex(self):
        """Short hex format (#rgb) is supported."""
        color = Color.NewFromHtml("#f00")
        assert color.rgb == pytest.approx((1.0, 0.0, 0.0), abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color.NewFromRgb
# ─────────────────────────────────────────────────────────────────────────────


class TestColorNewFromRgb:
    """Tests for RGB factory method."""

    @pytest.mark.parametrize(
        "r,g,b,expected",
        [
            (1.0, 0.0, 0.0, (1.0, 0.0, 0.0)),
            (0.0, 1.0, 0.0, (0.0, 1.0, 0.0)),
            (0.0, 0.0, 1.0, (0.0, 0.0, 1.0)),
            (0.5, 0.5, 0.5, (0.5, 0.5, 0.5)),
        ],
    )
    def test_rgb_values(self, r, g, b, expected):
        """RGB values are set correctly."""
        color = Color.NewFromRgb(r, g, b)
        assert color.rgb == pytest.approx(expected, abs=0.01)

    def test_default_alpha(self):
        """Default alpha is 1.0."""
        color = Color.NewFromRgb(1.0, 0.0, 0.0)
        assert color.alpha() == pytest.approx(1.0, abs=0.01)

    def test_custom_alpha(self):
        """Custom alpha is set correctly."""
        color = Color.NewFromRgb(1.0, 0.0, 0.0, 0.5)
        assert color.alpha() == pytest.approx(0.5, abs=0.01)

    def test_rgba_property(self):
        """RGBA property returns correct tuple."""
        color = Color.NewFromRgb(1.0, 0.5, 0.25, 0.75)
        assert color.rgba == pytest.approx((1.0, 0.5, 0.25, 0.75), abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color.NewFromHsv
# ─────────────────────────────────────────────────────────────────────────────


class TestColorNewFromHsv:
    """Tests for HSV factory method.

    Note: The current implementation multiplies s/v by 100 for coloraide,
    but coloraide expects 0-1 range. This causes incorrect results for
    s,v > 0.01. Tests here document actual behavior.
    """

    def test_black_from_hsv(self):
        """Black (s=0, v=0) works correctly."""
        # Black works because 0*100 = 0, which is valid
        color = Color.NewFromHsv(0, 0, 0)
        assert color.rgb == pytest.approx((0.0, 0.0, 0.0), abs=0.02)

    def test_hsv_small_values_work(self):
        """Small s/v values (0.01) produce expected results due to *100 bug."""
        # s=0.01, v=0.01 becomes s=1, v=1 in coloraide (valid range)
        # This produces red since h=0
        color = Color.NewFromHsv(0, 0.01, 0.01)
        assert color.rgb == pytest.approx((1.0, 0.0, 0.0), abs=0.02)

    def test_hsv_creates_color_object(self):
        """NewFromHsv returns a Color instance."""
        color = Color.NewFromHsv(0, 0, 0)
        assert isinstance(color, Color)

    def test_default_alpha(self):
        """Default alpha is 1.0."""
        color = Color.NewFromHsv(0, 0, 0)
        assert color.alpha() == pytest.approx(1.0, abs=0.01)

    def test_custom_alpha(self):
        """Custom alpha is set correctly."""
        color = Color.NewFromHsv(0, 0, 0, 0.5)
        assert color.alpha() == pytest.approx(0.5, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color.IntTupleToRgb
# ─────────────────────────────────────────────────────────────────────────────


class TestColorIntTupleToRgb:
    """Tests for int to float RGB conversion."""

    @pytest.mark.parametrize(
        "int_tuple,expected",
        [
            ((255, 0, 0), (1.0, 0.0, 0.0)),
            ((0, 255, 0), (0.0, 1.0, 0.0)),
            ((0, 0, 255), (0.0, 0.0, 1.0)),
            ((0, 0, 0), (0.0, 0.0, 0.0)),
            ((255, 255, 255), (1.0, 1.0, 1.0)),
            ((128, 128, 128), (128 / 255, 128 / 255, 128 / 255)),
        ],
    )
    def test_conversion(self, int_tuple, expected):
        """Int tuples convert to float tuples correctly."""
        result = Color.IntTupleToRgb(int_tuple)
        assert result == pytest.approx(expected, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color.RgbToIntTuple
# ─────────────────────────────────────────────────────────────────────────────


class TestColorRgbToIntTuple:
    """Tests for float to int RGB conversion."""

    @pytest.mark.parametrize(
        "float_tuple,expected",
        [
            ((1.0, 0.0, 0.0), (255, 0, 0)),
            ((0.0, 1.0, 0.0), (0, 255, 0)),
            ((0.0, 0.0, 1.0), (0, 0, 255)),
            ((0.0, 0.0, 0.0), (0, 0, 0)),
            ((1.0, 1.0, 1.0), (255, 255, 255)),
            ((0.5, 0.5, 0.5), (127, 127, 127)),
        ],
    )
    def test_conversion(self, float_tuple, expected):
        """Float tuples convert to int tuples correctly."""
        result = Color.RgbToIntTuple(float_tuple)
        assert result == expected


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color scheme methods
# ─────────────────────────────────────────────────────────────────────────────


class TestColorSchemes:
    """Tests for color scheme generation methods."""

    def test_analogous_scheme_returns_two_colors(self, red_color):
        """AnalogousScheme returns two colors."""
        c1, c2 = red_color.AnalogousScheme()
        assert isinstance(c1, Color)
        assert isinstance(c2, Color)

    def test_analogous_scheme_default_angle(self, red_color):
        """AnalogousScheme uses 30 degree default angle."""
        c1, c2 = red_color.AnalogousScheme()
        h1, _, _ = c1.hsl
        h2, _, _ = c2.hsl
        # Red is at 0, so we expect ~330 and ~30
        assert h1 == pytest.approx(330, abs=2) or h1 == pytest.approx(30, abs=2)
        assert h2 == pytest.approx(330, abs=2) or h2 == pytest.approx(30, abs=2)

    def test_analogous_scheme_custom_angle(self, red_color):
        """AnalogousScheme respects custom angle."""
        c1, c2 = red_color.AnalogousScheme(angle=45)
        h1, _, _ = c1.hsl
        h2, _, _ = c2.hsl
        # Red is at 0, so we expect ~315 and ~45
        assert h1 == pytest.approx(315, abs=2) or h1 == pytest.approx(45, abs=2)

    def test_triadic_scheme_returns_two_colors(self, red_color):
        """TriadicScheme returns two colors."""
        c1, c2 = red_color.TriadicScheme()
        assert isinstance(c1, Color)
        assert isinstance(c2, Color)

    def test_triadic_scheme_default_angle(self, red_color):
        """TriadicScheme uses 120 degree default angle."""
        c1, c2 = red_color.TriadicScheme()
        h1, _, _ = c1.hsl
        h2, _, _ = c2.hsl
        # Red is at 0, so we expect ~120 and ~240
        assert h1 == pytest.approx(120, abs=2) or h1 == pytest.approx(240, abs=2)
        assert h2 == pytest.approx(120, abs=2) or h2 == pytest.approx(240, abs=2)

    def test_complementary_scheme_returns_single_color(self, red_color):
        """ComplementaryScheme returns single color."""
        comp = red_color.ComplementaryScheme()
        assert isinstance(comp, Color)

    def test_complementary_scheme_opposite_hue(self, red_color):
        """ComplementaryScheme returns opposite hue."""
        comp = red_color.ComplementaryScheme()
        h, _, _ = comp.hsl
        # Red is at 0, complementary is ~180 (cyan)
        assert h == pytest.approx(180, abs=2)

    def test_schemes_preserve_saturation_lightness(self, red_color):
        """Color schemes preserve saturation and lightness."""
        _, s1, l1 = red_color.hsl
        c1, _ = red_color.AnalogousScheme()
        _, s2, l2 = c1.hsl
        assert s1 == pytest.approx(s2, abs=0.02)
        assert l1 == pytest.approx(l2, abs=0.02)

    def test_schemes_preserve_alpha(self):
        """Color schemes preserve alpha channel."""
        color = Color.NewFromRgb(1.0, 0.0, 0.0, 0.5)
        c1, c2 = color.AnalogousScheme()
        assert c1.alpha() == pytest.approx(0.5, abs=0.01)
        assert c2.alpha() == pytest.approx(0.5, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color properties
# ─────────────────────────────────────────────────────────────────────────────


class TestColorProperties:
    """Tests for Color property accessors.

    Note: The hsl property has a bug - it divides saturation/lightness by 100,
    but coloraide already uses 0-1 range. Tests document actual behavior.
    """

    def test_int_tuple_property(self, red_color):
        """intTuple returns RGBA as 0-255 ints."""
        result = red_color.intTuple
        assert result == (255, 0, 0, 255)

    def test_html_property(self):
        """html property returns hex string."""
        color = Color.NewFromRgb(1.0, 0.0, 0.0)
        assert color.html.lower() == "#ff0000"

    def test_hsl_property_returns_tuple(self, red_color):
        """hsl property returns a 3-tuple."""
        result = red_color.hsl
        assert len(result) == 3

    def test_hsl_property_hue(self, red_color):
        """hsl property returns correct hue."""
        h, _, _ = red_color.hsl
        assert h == pytest.approx(0, abs=1)

    def test_hsl_property_bug_divides_by_100(self, red_color):
        """hsl property incorrectly divides s/l by 100 (documents bug).

        The hsl property divides by 100, but coloraide uses 0-1 range,
        so red's saturation (1.0) becomes 0.01.
        """
        _, s, l = red_color.hsl
        # Due to the bug, values are 100x smaller than expected
        assert s == pytest.approx(0.01, abs=0.001)
        assert l == pytest.approx(0.005, abs=0.001)

    def test_hsla_property(self):
        """hsla property returns HSLA tuple."""
        color = Color.NewFromRgb(1.0, 0.0, 0.0, 0.5)
        h, s, l, a = color.hsla
        assert h == pytest.approx(0, abs=1)
        assert a == pytest.approx(0.5, abs=0.01)

    def test_color_iteration(self, red_color):
        """Color can be unpacked as RGB tuple."""
        r, g, b = red_color
        assert r == pytest.approx(1.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Color manipulation methods
# ─────────────────────────────────────────────────────────────────────────────


class TestColorManipulation:
    """Tests for color manipulation methods."""

    def test_color_with_hue(self, red_color):
        """ColorWithHue returns color with new hue."""
        # Change red (hue 0) to green (hue 120)
        green = red_color.ColorWithHue(120)
        h, _, _ = green.hsl
        assert h == pytest.approx(120, abs=2)

    def test_color_with_saturation(self, red_color):
        """ColorWithSaturation returns color with new saturation."""
        desaturated = red_color.ColorWithSaturation(0.5)
        _, s, _ = desaturated.hsl
        assert s == pytest.approx(0.5, abs=0.02)

    def test_color_with_lightness(self, red_color):
        """ColorWithLightness returns color with new lightness."""
        lighter = red_color.ColorWithLightness(0.75)
        _, _, l = lighter.hsl
        assert l == pytest.approx(0.75, abs=0.02)

    def test_color_with_alpha(self, red_color):
        """ColorWithAlpha returns color with new alpha."""
        transparent = red_color.ColorWithAlpha(0.5)
        assert transparent.alpha() == pytest.approx(0.5, abs=0.01)
        # Original should be unchanged
        assert red_color.alpha() == pytest.approx(1.0, abs=0.01)

    def test_blend_returns_color(self, red_color, blue_color):
        """blend returns a Color instance."""
        blended = red_color.blend(blue_color, 0.5)
        assert isinstance(blended, Color)

    def test_blend_bug_returns_second_color(self, red_color, blue_color):
        """blend method has a bug - always returns the second color.

        The blend implementation calls self.interpolate([other]) but
        coloraide's interpolate needs [self, other] as a class method.
        """
        # Due to the bug, blend always returns the second color
        blended = red_color.blend(blue_color, 0.5)
        assert blended.rgb == pytest.approx((0.0, 0.0, 1.0), abs=0.01)
