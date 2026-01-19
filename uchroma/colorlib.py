#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Extended Color class with grapefruit-compatible API.

This extends ColorAide's Color with the factory methods and properties
that the uchroma codebase expects from grapefruit.
"""

from coloraide import Color as _BaseColor
from coloraide.spaces.hsluv import HSLuv
from coloraide.spaces.luv import Luv


class Color(_BaseColor):
    """Color class with grapefruit-compatible API."""

    # Factory methods (grapefruit style)
    @classmethod
    def NewFromHtml(cls, html: str) -> "Color":
        """Create color from HTML hex or named color."""
        return cls(html)

    @classmethod
    def NewFromRgb(cls, r: float, g: float, b: float, a: float = 1.0) -> "Color":
        """Create color from RGB floats (0-1 range)."""
        c = cls("srgb", [r, g, b])
        c["alpha"] = a
        return c

    @classmethod
    def NewFromHsv(cls, h: float, s: float, v: float, a: float = 1.0) -> "Color":
        """Create color from HSV (h: 0-360, s/v: 0-1)."""
        c = cls("hsv", [h, s * 100, v * 100])
        c["alpha"] = a
        return c

    @classmethod
    def NewFromHsl(cls, h: float, s: float, l: float, a: float = 1.0) -> "Color":
        """Create color from HSL (h: 0-360, s/l: 0-1)."""
        c = cls("hsl", [h, s * 100, l * 100])
        c["alpha"] = a
        return c

    @classmethod
    def NewFromHsluv(cls, h: float, s: float, l: float, a: float = 1.0) -> "Color":
        """Create color from HSLuv (h: 0-360, s/l: 0-100)."""
        c = cls("hsluv", [h, s, l])
        c["alpha"] = a
        return c

    @staticmethod
    def IntTupleToRgb(t: tuple) -> tuple:
        """Convert int tuple (0-255) to float tuple (0-1)."""
        return (t[0] / 255.0, t[1] / 255.0, t[2] / 255.0)

    @staticmethod
    def RgbToIntTuple(t: tuple) -> tuple:
        """Convert float tuple (0-1) to int tuple (0-255)."""
        return (int(t[0] * 255), int(t[1] * 255), int(t[2] * 255))

    # Properties (grapefruit style)
    @property
    def rgb(self) -> tuple:
        """Get RGB as float tuple (0-1)."""
        srgb = self.convert("srgb")
        return (srgb["red"], srgb["green"], srgb["blue"])

    @property
    def rgba(self) -> tuple:
        """Get RGBA as float tuple (0-1)."""
        srgb = self.convert("srgb")
        return (srgb["red"], srgb["green"], srgb["blue"], self.alpha())

    @property
    def hsl(self) -> tuple:
        """Get HSL tuple (h: 0-360, s/l: 0-1)."""
        hsl = self.convert("hsl")
        h = hsl["hue"] if hsl["hue"] == hsl["hue"] else 0  # Handle NaN
        return (h, hsl["saturation"] / 100, hsl["lightness"] / 100)

    @property
    def hsla(self) -> tuple:
        """Get HSLA tuple."""
        h, s, l = self.hsl
        return (h, s, l, self.alpha())

    @property
    def hsv(self) -> tuple:
        """Get HSV tuple (h: 0-360, s/v: 0-1)."""
        hsv = self.convert("hsv")
        h = hsv["hue"] if hsv["hue"] == hsv["hue"] else 0
        return (h, hsv["saturation"] / 100, hsv["value"] / 100)

    @property
    def hsluv(self) -> tuple:
        """Get HSLuv tuple (h: 0-360, s/l: 0-100)."""
        luv = self.convert("hsluv")
        h = luv["hue"] if luv["hue"] == luv["hue"] else 0  # Handle NaN
        return (h, luv["saturation"], luv["lightness"])

    @property
    def intTuple(self) -> tuple:
        """Get RGBA as int tuple (0-255)."""
        r, g, b = self.rgb
        return (int(r * 255), int(g * 255), int(b * 255), int(self.alpha() * 255))

    @property
    def html(self) -> str:
        """Get HTML hex color string."""
        return self.convert("srgb").to_string(hex=True)

    # Color manipulation (grapefruit style)
    def ColorWithHue(self, hue: float) -> "Color":
        """Return new color with modified hue."""
        hsl = self.convert("hsl").clone()
        hsl["hue"] = hue
        return Color(hsl.convert("srgb"))

    def ColorWithSaturation(self, saturation: float) -> "Color":
        """Return new color with modified saturation (0-1)."""
        hsl = self.convert("hsl").clone()
        hsl["saturation"] = saturation * 100
        return Color(hsl.convert("srgb"))

    def ColorWithLightness(self, lightness: float) -> "Color":
        """Return new color with modified lightness (0-1)."""
        hsl = self.convert("hsl").clone()
        hsl["lightness"] = lightness * 100
        return Color(hsl.convert("srgb"))

    def ColorWithAlpha(self, alpha: float) -> "Color":
        """Return new color with modified alpha."""
        c = self.clone()
        c["alpha"] = alpha
        return Color(c)

    def AnalogousScheme(self, angle: float = 30) -> tuple:
        """Generate analogous color scheme."""
        h, s, l = self.hsl
        c1 = Color.NewFromHsl((h - angle) % 360, s, l, self.alpha())
        c2 = Color.NewFromHsl((h + angle) % 360, s, l, self.alpha())
        return (c1, c2)

    def TriadicScheme(self, angle: float = 120) -> tuple:
        """Generate triadic color scheme."""
        h, s, l = self.hsl
        c1 = Color.NewFromHsl((h + angle) % 360, s, l, self.alpha())
        c2 = Color.NewFromHsl((h - angle) % 360, s, l, self.alpha())
        return (c1, c2)

    def ComplementaryScheme(self) -> "Color":
        """Get complementary color."""
        h, s, l = self.hsl
        return Color.NewFromHsl((h + 180) % 360, s, l, self.alpha())

    def blend(self, other: "Color", percent: float = 0.5) -> "Color":
        """Blend with another color."""
        return Color(self.interpolate([other], space="srgb")(percent))

    def __iter__(self):
        """Allow unpacking as RGB tuple."""
        return iter(self.rgb)


# Register Luv and HSLuv for perceptually uniform gradient interpolation
Color.register(Luv())
Color.register(HSLuv())
