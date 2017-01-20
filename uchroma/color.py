import itertools
import math
import random

from enum import Enum

import numpy as np

from uchroma.util import colorarg, lerp, lerp_degrees, to_rgb
from skimage.util import dtype

from grapefruit import Color


class Splotch(Enum):
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


class ColorUtils(object):
    """
    Various helpers and utilities for working with colors
    """


    @staticmethod
    def _interpolate(start, end, amount: float) -> tuple:
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
    def _hsva(color: Color) -> Color:
        return (*color.hsv, color.alpha)


    @staticmethod
    @colorarg('color1', 'color2')
    def hsv_blend(color1: Color, color2: Color, amount: float) -> Color:
        return Color.NewFromHsv(*ColorUtils._interpolate(
            ColorUtils._hsva(color1), ColorUtils._hsva(color2), amount))


    @staticmethod
    @colorarg('color1', 'color2')
    def hsv_gradient(color1: Color, color2: Color, steps: int) -> list:
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
            gradient.append(Color.NewFromHsv(*ColorUtils._interpolate(start, end, amount)))

        return gradient


    @staticmethod
    def _generator(gradient: list, randomize: bool=False, alternate: bool=False, rgb: bool=False):
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
    @colorarg('color', 'base_color')
    def color_scheme(color=None, base_color=None, steps: int=11):
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

        return ColorUtils.hsv_gradient(c0, c1, steps)


    @staticmethod
    @colorarg('color', 'base_color')
    def scheme_generator(color=None, base_color=None, randomize: bool=False,
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
        return ColorUtils._generator(gradient, randomize, alternate, rgb)


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

        return ColorUtils._generator(gradient, randomize, alternate, rgb)


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
    @colorarg('color')
    def increase_contrast(color: Color) -> Color:
        hsl = list(color.hsl)
        if hsl[2] < 0.1 or hsl[2] > 0.7:
            hsl[2] = 1.0 - hsl[2]
            color = Color.NewFromHsl(*hsl, color.alpha)
        return color


    @staticmethod
    @colorarg('bg_color')
    def rgba2rgb(arr, bg_color=None):
        if bg_color is None:
            bg_color = np.array([0.0, 0.0, 0.0, 1.0])
        else:
            bg_color = np.array([*bg_color.rgb, bg_color.alpha])

        alpha = arr[..., -1]
        channels = arr[..., :-1]
        out = np.empty_like(channels)

        for ichan in range(channels.shape[-1]):
            out[..., ichan] = np.clip(
                (1 - alpha) * bg_color[ichan] + alpha * channels[..., ichan],
                a_min=0, a_max=1)

        return dtype.img_as_ubyte(out)
