# pylint: disable=invalid-name, no-member
import itertools
import math
import random

from enum import Enum

import numpy as np

from grapefruit import Color
from hsluv import hsluv_to_rgb, rgb_to_hsluv
from skimage.util import dtype

from uchroma.util import colorarg, ColorType, lerp, lerp_degrees, MagicalEnum, to_color, to_rgb


class ColorScheme(Enum):
    Emma = ('#320d6d', '#ffbfb7', '#ffd447', '#700353', '#4c1c00')
    Best = ('#247ba0', '#70c1b3', '#b2dbbf', '#f3ffbd', '#ff1654')
    Variety = ('#db5461', '#ffd9ce', '#593c8f', '#8ef9f3', '#171738')
    Redd = ('#d7263d', '#f46036', '#2e294e', '#1b998b', '#c5d86d')
    Bluticas = ('#006ba6', '#0496ff', '#ffbc42', '#d81159', '#8f2d56')
    Newer = ('#0d0630', '#18314f', '#384e77', '#8bbeb2', '#e6f9af')
    Bright = ('#ffbe0b', '#fb5607', '#ff006e', '#8338ec', '#3a86ff')
    Qap = ('#004777', '#a30000', '#ff7700', '#efd28d', '#00afb5')
    Rainbow = ('red', 'yellow', 'lime', 'aqua', 'blue', 'magenta')

    def gradient(self, length: int=360) -> list:
        return ColorUtils.gradient(length, *self.value)


class ColorPair(MagicalEnum, Enum):
    """
    Predefined color pairs
    """

    EARTH = ('green', '#8b4513')
    AIR = ('white', 'skyblue')
    FIRE = ('red', 'orange')
    WATER = ('blue', 'white')
    SUN = ('white', 'yellow')
    MOON = ('grey', 'cyan')
    HOTPINK = ('hotpink', 'purple')

    def __init__(self, first, second):
        self.first = Color.NewFromHtml(first)
        self.second = Color.NewFromHtml(second)

    @classmethod
    def get(cls, name):
        if name is None or name.upper() not in cls.__members__:
            return None
        return cls[name.upper()]


class ColorUtils(object):
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
    def hue_gradient(start, length):
        step = 360 / length
        return [Color.NewFromHsv((start + (step * x)) % 360, 1, 1) for x in range(0, length)]


    @staticmethod
    def _hsva(color: Color) -> Color:
        return (*rgb_to_hsluv(color.rgb), color.alpha)


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
        start = ColorUtils._hsva(color1)
        end = ColorUtils._hsva(color2)

        gradient = []
        for x in range(0, steps):
            amount = float(x) / float(steps - 1)
            i = ColorUtils._circular_interp(start, end, amount)
            gradient.append(Color.NewFromRgb(*hsluv_to_rgb([i[0], i[1], i[2]])))

        return gradient


    @staticmethod
    def gradient(length: int, *colors) -> list:
        """
        Generate a looped gradient from multiple evenly-spaced colors

        Uses the new HSLUV colorspace
        :param length: Total number of entries in the final gradient
        :param colors: Color stops, varargs

        :return: List of colors in the gradient
        """

        luv_colors = [rgb_to_hsluv(to_color(x).rgb) for x in colors]
        luv_colors.append(luv_colors[0])

        steps = max(len(luv_colors), math.floor(length / (len(luv_colors))))
        gradient = []
        for color_idx in range(0, len(luv_colors) - 1):
            start = luv_colors[color_idx]
            end = luv_colors[(color_idx + 1)]

            for interp in range(0, steps):
                amount = float(interp) / float(steps)
                i = ColorUtils._circular_interp(start, end, amount)
                gradient.append(Color.NewFromRgb(*hsluv_to_rgb([i[0], i[1], i[2]])))

        return gradient


    @staticmethod
    def color_generator(gradient: list, randomize: bool=False, alternate: bool=False, rgb: bool=False):
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
                if alternate:
                    yield next(cycle2)


    @staticmethod
    @colorarg
    def color_scheme(color: ColorType=None, base_color: ColorType=None, steps: int=11):
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
    def scheme_generator(color: ColorType=None, base_color: ColorType=None, randomize: bool=False,
                         alternate: bool=False, steps: int=11, rgb: bool=False):
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
    def interference(length, freq1: float=0.3, freq2: float=0.3, freq3: float=0.3,
                     phase1: float=0.0, phase2: float=2.0, phase3: float=4.0,
                     center: float=128.0, width: float=127.0):
        """
        Creates an interference pattern of three sine waves
        """
        phase1 = phase1 * math.pi / 3
        phase2 = phase2 * math.pi / 3
        phase3 = phase3 * math.pi / 3

        center /= 255.0
        width /= 255.0

        gradient = []

        for i in range(0, length):
            r = math.sin(freq1 * i + phase1) * width + center
            g = math.sin(freq2 * i + phase2) * width + center
            b = math.sin(freq3 * i + phase3) * width + center
            gradient.append(Color.NewFromRgb(r, g, b))

        return gradient


    @staticmethod
    def rainbow_generator(randomize: bool=False, alternate: bool=False,
                          steps: int=33, rgb: bool=False):
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
    def random_generator(rgb: bool=False):
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
    def increase_contrast(color: ColorType) -> Color:
        """
        Performs contrast inversion if a hue rotation would result in
        white-on-white or black-on-black.

        :param color: The color to check

        :return: The new color with adjusted contrast
        """
        hsl = list(color.hsl)
        if hsl[2] < 0.1 or hsl[2] > 0.7:
            hsl[2] = 1.0 - hsl[2]
            color = Color.NewFromHsl(*hsl, color.alpha)
        return color


    @staticmethod
    @colorarg
    def rgba2rgb(arr: np.ndarray, bg_color: ColorType=None) -> np.ndarray:
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
            bg_color = np.array(tuple(bg_color), dtype=np.float)

        alpha = arr[..., -1]
        channels = arr[..., :-1]

        out_buf = np.empty_like(channels)

        for ichan in range(channels.shape[-1]):
            out_buf[..., ichan] = np.clip(
                (1 - alpha) * bg_color[ichan] + alpha * channels[..., ichan],
                a_min=0, a_max=1)

        return dtype.img_as_ubyte(out_buf)
