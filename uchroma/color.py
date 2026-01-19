#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name, no-member

import itertools
import math
import random
import re
from collections.abc import Iterable
from enum import Enum
from typing import Union

import numpy as np
from hsluv import hsluv_to_rgb, rgb_to_hsluv

from uchroma.colorlib import Color
from uchroma.drawing import img_as_ubyte
from uchroma.util import autocast_decorator, clamp, lerp, lerp_degrees

# Type hint for decorated color arguments
ColorType = Union[Color, str, Iterable[int], Iterable[float], None]
ColorList = list[ColorType]


class ColorScheme(Enum):
    """
    Predefined color schemes for animations and effects.
    """

    # ── Original schemes ──────────────────────────────────────────────────────
    Emma = ("#320d6d", "#ffbfb7", "#ffd447", "#700353", "#4c1c00")
    Best = ("#247ba0", "#70c1b3", "#b2dbbf", "#f3ffbd", "#ff1654")
    Variety = ("#db5461", "#ffd9ce", "#593c8f", "#8ef9f3", "#171738")
    Redd = ("#d7263d", "#f46036", "#2e294e", "#1b998b", "#c5d86d")
    Bluticas = ("#006ba6", "#0496ff", "#ffbc42", "#d81159", "#8f2d56")
    Newer = ("#0d0630", "#18314f", "#384e77", "#8bbeb2", "#e6f9af")
    Bright = ("#ffbe0b", "#fb5607", "#ff006e", "#8338ec", "#3a86ff")
    Qap = ("#004777", "#a30000", "#ff7700", "#efd28d", "#00afb5")
    Rainbow = ("red", "yellow", "lime", "aqua", "blue", "magenta")

    # ── Dark purple / synthwave ───────────────────────────────────────────────
    Nightshade = ("#0d0221", "#261447", "#6b2d5c", "#b33f62", "#f9564f")
    Ultraviolet = ("#1a0a2e", "#3d1e6d", "#8b2fc9", "#c86bfa", "#e9b8ff")
    DeepAmethyst = ("#120024", "#2d0a4e", "#5c1a8c", "#9b4dca", "#d4a5ff")
    Obsidian = ("#0a0014", "#1c0033", "#3d0066", "#7a00cc", "#b84dff")
    Twilight = ("#1a1423", "#2d2040", "#4a3766", "#7b5ea7", "#b794f6")
    Cosmos = ("#0f0c29", "#302b63", "#24243e", "#8b5cf6", "#c4b5fd")
    Vaporwave = ("#1a0533", "#4a0e78", "#ff00ff", "#00ffff", "#ffb6c1")
    Witching = ("#13002d", "#2e0854", "#5a108f", "#9b30ff", "#e066ff")

    # ── Cyberpunk / neon ──────────────────────────────────────────────────────
    Neon = ("#ff00ff", "#00ffff", "#ff0080", "#80ff00", "#ffff00")
    Cyberpunk = ("#0d0d0d", "#ff003c", "#00f0ff", "#f0f", "#ffe600")
    Hotline = ("#1a1a2e", "#e94560", "#0f3460", "#16213e", "#ff6b6b")
    Outrun = ("#2b1055", "#7f00ff", "#ff00ff", "#ff7300", "#ffec00")
    Glitch = ("#0d0208", "#ff2a6d", "#05d9e8", "#d1f7ff", "#01012b")

    # ── Nature / organic ──────────────────────────────────────────────────────
    Forest = ("#1b4332", "#2d6a4f", "#40916c", "#52b788", "#95d5b2")
    Ocean = ("#03045e", "#0077b6", "#00b4d8", "#48cae4", "#90e0ef")
    Sunset = ("#ff6b35", "#ff8c42", "#ffd166", "#f4845f", "#f25c54")
    Aurora = ("#004643", "#008f8c", "#00d4aa", "#c1fba4", "#fffcdc")
    Sakura = ("#ffb7c5", "#ff8fa3", "#ff5c8a", "#c9184a", "#590d22")
    Moss = ("#132a13", "#31572c", "#4f772d", "#90a955", "#ecf39e")

    # ── Cool / icy ────────────────────────────────────────────────────────────
    Arctic = ("#caf0f8", "#90e0ef", "#00b4d8", "#0077b6", "#03045e")
    Glacier = ("#e0fbfc", "#c2dfe3", "#9db4c0", "#5c6b73", "#253237")
    Frost = ("#a2d2ff", "#bde0fe", "#cdb4db", "#ffc8dd", "#ffafcc")

    # ── Warm / fire ───────────────────────────────────────────────────────────
    Ember = ("#310000", "#6b0000", "#a30000", "#d62828", "#f77f00")
    Lava = ("#1a0000", "#660000", "#cc3300", "#ff6600", "#ffcc00")
    Inferno = ("#03071e", "#370617", "#6a040f", "#d00000", "#ffba08")

    # ── Pastel / soft ─────────────────────────────────────────────────────────
    Candy = ("#fae0e4", "#f7cad0", "#e8b4bc", "#d698a8", "#c28294")
    Dreamy = ("#cdb4db", "#ffc8dd", "#ffafcc", "#bde0fe", "#a2d2ff")
    Bubblegum = ("#ff99c8", "#fcf6bd", "#d0f4de", "#a9def9", "#e4c1f9")
    Lavender = ("#e0b1cb", "#be95c4", "#9f86c0", "#5e548e", "#231942")

    # ── Monochrome gradients ──────────────────────────────────────────────────
    Grayscale = ("#1a1a1a", "#404040", "#737373", "#a6a6a6", "#d9d9d9")
    Purple = ("#1a0033", "#330066", "#660099", "#9933cc", "#cc66ff")
    Emerald = ("#002211", "#004422", "#006633", "#008844", "#22aa66")

    def gradient(self, length: int = 360) -> list:
        """
        Interpolate this ColorScheme to a gradient of the
        specified length.

        :param length: Final length of the gradient
        :return: List of all colors in the gradient
        """
        return ColorUtils.gradient(length, *tuple(self.value))


class ColorPair(Enum):
    """
    Predefined color pairs
    """

    EARTH = ("green", "#8b4513")
    AIR = ("white", "skyblue")
    FIRE = ("red", "orange")
    WATER = ("blue", "white")
    SUN = ("white", "yellow")
    MOON = ("grey", "cyan")
    HOTPINK = ("hotpink", "purple")

    def __init__(self, first, second):
        self.first = Color.NewFromHtml(first)
        self.second = Color.NewFromHtml(second)

    @classmethod
    def get(cls, name):
        """
        Get a ColorPair by name

        TODO: Implement support for ColourLovers

        :param name: Name of the item to get as a string
        :return: Enumerated value of the color pair
        """
        if name is None or name.upper() not in cls.__members__:
            return None
        return cls[name.upper()]


def rgb_from_tuple(arg: tuple) -> Color:
    """
    Convert a 3-tuple of ints or floats to a Grapefruit color

    :param arg: The RGB tuple to convert
    :return: The Color object
    """
    if len(arg) >= 3:
        if arg[0] is None:
            return Color.NewFromRgb(0, 0, 0)
        if all(isinstance(n, int) for n in arg):
            return Color.NewFromRgb(*Color.IntTupleToRgb(arg))
        if all(isinstance(n, float) for n in arg):
            return Color.NewFromRgb(*arg)

    raise TypeError(f"Unable to convert {arg} ({type(arg[0])}) to color")


def rgb_to_int_tuple(arg: tuple) -> tuple:
    """
    Convert/sanitize a 3-tuple of ints or floats

    :param arg: Tuple of RGB values

    :return: Tuple of RGB ints
    """
    if len(arg) >= 3:
        return tuple([clamp(round(x), 0, 255) for x in arg[:3]])

    raise TypeError(f"Unable to convert {arg} ({type(arg[0])}) to color")


COLOR_TUPLE_STR = re.compile(r"\((.*, .*, .*, .*)\)")


def to_color(*color_args) -> Color | list[Color | None] | None:
    """
    Convert various color representations to grapefruit.Color

    Handles RGB triplets, hexcodes, and html color names.

    :return: The color
    """
    colors = []
    for arg in color_args:
        value = None
        if arg is not None:
            if isinstance(arg, Color):
                value = arg
            elif isinstance(arg, str):
                if arg != "":
                    # grapefruit's default str() spews a string repr of a tuple
                    strtuple = COLOR_TUPLE_STR.match(arg)
                    if strtuple:
                        value = Color.NewFromRgb(*[float(x) for x in strtuple.group(1).split(", ")])
                    else:
                        value = Color.NewFromHtml(arg)
            elif isinstance(arg, Iterable):
                value = rgb_from_tuple(arg)
            else:
                raise TypeError(f"Unable to parse color from '{arg}' ({type(arg)})")
        colors.append(value)

    if len(colors) == 0:
        return None
    if len(colors) == 1:
        return colors[0]

    return colors


def to_rgb(arg) -> tuple | list:
    """
    Convert various representations to RGB tuples

    :return: An RGB int tuple
    """
    if arg is None:
        return (0, 0, 0)
    if isinstance(arg, Color):
        return arg.intTuple[:3]
    if isinstance(arg, str):
        return Color.NewFromHtml(arg).intTuple[:3]
    if isinstance(arg, (tuple, list)):
        if arg[0] is None:
            return (0, 0, 0)

        if isinstance(arg[0], (list, tuple, str, Color)):
            return [to_rgb(item) for item in arg]
        return rgb_to_int_tuple(arg)

    raise TypeError(f"Unable to parse color from '{arg}' ({type(arg)})")


"""
Decorator to parse various color representations

Invokes to_color on any arguments listed in decls. This will cause
the listed arguments to be resolved to grapefruit.Color objects from
the various different representations that might be in use.

Example:

@colorarg
def frobizzle(self, speed, color1: ColorType=None, color2: ColorType=None)
"""
colorarg = autocast_decorator(ColorType, to_color)


class ColorUtils:
    """
    Various helpers and utilities for working with colors
    """

    @staticmethod
    def _circular_interp(start, end, amount: float) -> tuple:
        h = lerp_degrees(start[0], end[0], amount)
        s = lerp(start[1], end[1], amount)
        v = lerp(start[2], end[2], amount)
        a1 = a2 = 1.0
        if len(start) > 3:
            a1 = start[3]
        if len(end) > 3:
            a2 = end[3]
        a = lerp(a1, a2, amount)
        return (h, s, v, a)

    @staticmethod
    def hue_gradient(start: float = 0.0, length: int = 360) -> list:
        """
        Generate a gradient which spans all hues

        :param start: starting hue
        :param length: number of colors which should be produced
        :return: list of colors
        """
        step = 360 / length
        return [Color.NewFromHsv((start + (step * x)) % 360, 1, 1) for x in range(length)]

    @staticmethod
    def _hsva(color: Color) -> tuple[float, float, float, float]:
        return (*rgb_to_hsluv(color.rgb), color.alpha())

    @staticmethod
    @colorarg
    def hsv_gradient(color1: ColorType, color2: ColorType, steps: int) -> list:
        """
        Generate a gradient between two points in HSV colorspace

        :param color1: Starting color
        :param color2: Ending color
        :param steps: Number of steps in the gradient
        :param loop: If the gradient should "loop" back around to it's starting point

        :return: List of colors in the gradient
        """
        # colorarg decorator ensures these are Color objects at runtime
        assert isinstance(color1, Color)
        assert isinstance(color2, Color)
        start = ColorUtils._hsva(color1)
        end = ColorUtils._hsva(color2)

        gradient = []
        for x in range(steps):
            amount = float(x) / float(steps - 1)
            i = ColorUtils._circular_interp(start, end, amount)
            rgb = hsluv_to_rgb([i[0], i[1], i[2]])
            gradient.append(Color.NewFromRgb(rgb[0], rgb[1], rgb[2], i[3]))

        return gradient

    @staticmethod
    def gradient(length: int, *colors, loop=True) -> list:
        """
        Generate a looped gradient from multiple evenly-spaced colors

        Uses the new HSLUV colorspace
        :param length: Total number of entries in the final gradient
        :param colors: Color stops, varargs

        :return: List of colors in the gradient
        """

        luv_colors = [rgb_to_hsluv(to_color(x).rgb) for x in colors]
        if loop:
            luv_colors.append(luv_colors[0])

        steps = max(len(luv_colors), math.floor(length / (len(luv_colors) - 1)))
        gradient = []
        for color_idx in range(len(luv_colors) - 1):
            start = luv_colors[color_idx]
            end = luv_colors[(color_idx + 1)]

            for interp in range(steps):
                amount = float(interp) / float(steps)
                i = ColorUtils._circular_interp(start, end, amount)
                rgb = hsluv_to_rgb([i[0], i[1], i[2]])
                gradient.append(Color.NewFromRgb(rgb[0], rgb[1], rgb[2], i[3]))

        return gradient

    @staticmethod
    def color_generator(
        gradient: list, randomize: bool = False, alternate: bool = False, rgb: bool = False
    ):
        """
        Create a generator which returns colors from the given gradient,
        optionally randomizing, or moving across the gradient in alternating
        directions.

        :param gradient: a list of colors
        :param randomize: true if colors should be chosen randomly instead of
                          sequentially
        :param alternate: true if two iterators should move sequentially
                          thru the gradient in opposite directions
        :param rgb: true if RGB int tuples should be returned
        :return: generator
        """
        grad = gradient[:]

        if not randomize:
            grad.extend(grad[::-1])

        if rgb:
            grad = [to_rgb(x) for x in grad]

        if randomize:
            while True:
                yield random.choice(grad)
        else:
            cycle = itertools.cycle(grad)
            cycle2 = None
            if alternate:
                mid = int(len(grad) / 2)
                grad2 = grad[mid:]
                grad2.extend(grad[:mid])
                cycle2 = itertools.cycle(grad2)

            while True:
                yield next(cycle)
                if alternate and cycle2 is not None:
                    yield next(cycle2)

    @staticmethod
    @colorarg
    def color_scheme(color: ColorType = None, base_color: ColorType = None, steps: int = 11):
        """
        Generator which produces a continuous stream of colors based on a
        color scheme of two overlapping colors.

        :param color: The "top" color
        :param base_color: The base or bg_color color
        :param randomize: True if values should be chosen at random instead of sequential
        :param steps: Number of steps used for the gradient
        :param rgb: True if we should return RGB tuples

        :return: generator
        """
        c0 = c1 = None
        if base_color is not None and color is not None:
            c0, c1 = color.AnalogousScheme(angle=15)

        elif base_color is not None:
            c0, c1 = ColorUtils.increase_contrast(base_color).TriadicScheme(angle=150)

        return ColorUtils.gradient(steps, c0, c1)

    @staticmethod
    @colorarg
    def scheme_generator(
        color: ColorType = None,
        base_color: ColorType = None,
        randomize: bool = False,
        alternate: bool = False,
        steps: int = 11,
        rgb: bool = False,
    ):
        """
        Generator which produces a continuous stream of colors based on a
        color scheme of two overlapping colors.

        :param color: The "top" color
        :param base_color: The base or bg_color color
        :param randomize: True if values should be chosen at random instead of sequential
        :param steps: Number of steps used for the gradient
        :param rgb: True if we should return RGB tuples

        :return: generator
        """
        gradient = ColorUtils.color_scheme(color, base_color, steps)
        return ColorUtils.color_generator(gradient, randomize, alternate, rgb)

    @staticmethod
    def interference(
        length,
        freq1: float = 0.3,
        freq2: float = 0.3,
        freq3: float = 0.3,
        phase1: float = 0.0,
        phase2: float = 2.0,
        phase3: float = 4.0,
        center: float = 128.0,
        width: float = 127.0,
    ):
        """
        Creates an interference pattern of three sine waves
        """
        phase1 = phase1 * math.pi / 3
        phase2 = phase2 * math.pi / 3
        phase3 = phase3 * math.pi / 3

        center /= 255.0
        width /= 255.0

        gradient = []

        for i in range(length):
            r = math.sin(freq1 * i + phase1) * width + center
            g = math.sin(freq2 * i + phase2) * width + center
            b = math.sin(freq3 * i + phase3) * width + center
            gradient.append(Color.NewFromRgb(r, g, b))

        return gradient

    @staticmethod
    def rainbow_generator(
        randomize: bool = False, alternate: bool = False, steps: int = 33, rgb: bool = False
    ):
        """
        Generate a smooth rainbow gradient

        :param steps: Length or smoothness of the gradient
        :param rgb: True if RGB tuples should be generated
        :param alternate: If alternating values (moving in opposite directions
                          should be returned on subsequent calls

        :return: generator
        """
        gradient = ColorUtils.interference(steps)

        return ColorUtils.color_generator(gradient, randomize, alternate, rgb)

    @staticmethod
    def random_generator(rgb: bool = False):
        """
        Generate random colors using the golden ratio conjugate

        :param rgb: True if RGB tuples should be generated

        :return: generator:
        """
        golden_ratio_conjugate = (1 + math.sqrt(5)) / 2
        hue = random.random()
        c0 = Color.NewFromHsv(0, 1.0, 1.0)
        while True:
            hue += golden_ratio_conjugate
            hue %= 1
            value = c0.ColorWithHue(hue * 360)
            if rgb:
                yield to_rgb(value)
            else:
                yield value

    @staticmethod
    @colorarg
    def luminance(color: ColorType) -> float:
        """
        Calculate the relative luminance (as defined by WCAG 2.0) of
        the given color.

        :param color: a color
        :return: the calculated relative luminance between 0.0 and 10
        """
        rgb = color.rgb
        vals = []
        for c in rgb:
            if c <= 0.03928:
                c /= 12.92
            else:
                c = math.pow((c + 0.055) / 1.055, 2.4)
            vals.append(c)
        L = 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]
        return L

    @staticmethod
    @colorarg
    def contrast_ratio(color1: ColorType, color2: ColorType) -> float:
        """
        Calculate the contrast ratio (as defined by WCAG 2.0) between
        two colors. If the two colors have the same relative luminance,
        the result is 1.0. For black/white, the result is 21.0.

        :param color1: a color
        :param color2: a color
        :return: the calculated contrast ratio
        """
        ratio = (0.05 + ColorUtils.luminance(color1)) / (0.05 + ColorUtils.luminance(color2))
        if ratio < 1:
            return 1 / ratio
        return ratio

    @staticmethod
    @colorarg
    def inverse(color: ColorType) -> Color:
        """
        Get the RGB inverse of this color (1 - component)

        :param color: a color
        :return: Inverse of the given color
        """
        assert isinstance(color, Color)
        rgb = color.rgb
        return Color.NewFromRgb(1.0 - rgb[0], 1.0 - rgb[1], 1.0 - rgb[2], color.alpha())

    @staticmethod
    @colorarg
    def increase_contrast(color: ColorType) -> Color:
        """
        Performs contrast inversion if a hue rotation would result in
        white-on-white or black-on-black.

        :param color: The color to check

        :return: The new color with adjusted contrast
        """
        assert isinstance(color, Color)
        hsl = list(color.hsl)
        if hsl[2] < 0.1 or hsl[2] > 0.7:
            hsl[2] = 1.0 - hsl[2]
            color = Color.NewFromHsl(hsl[0], hsl[1], hsl[2], color.alpha())
        return color

    @staticmethod
    @colorarg
    def rgba2rgb(arr: np.ndarray, bg_color: ColorType = None) -> np.ndarray:
        """
        Alpha-composites data in the numpy array against the given
        background color and returns a new buffer without the
        alpha component.

        :param arr: The input array of RGBA data
        :param bg_color: The background color
        :param out_buf: Optional buffer to render into

        :return: Array of composited RGB data
        """
        if bg_color is None:
            bg_color = np.array([0.0, 0.0, 0.0, 1.0])
        else:
            bg_color = np.array(tuple(bg_color), dtype=np.float64)

        alpha = arr[..., -1]
        channels = arr[..., :-1]

        out_buf = np.empty_like(channels)

        for ichan in range(channels.shape[-1]):
            out_buf[..., ichan] = np.clip(
                (1 - alpha) * bg_color[ichan] + alpha * channels[..., ichan], a_min=0, a_max=1
            )

        return img_as_ubyte(out_buf)
