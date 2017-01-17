import itertools
import math
import random

from enum import Enum

from uchroma.util import colorarg, lerp, lerp_degrees, to_rgb

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
        start = color1.hsv
        end = color2.hsv

        gradient = []
        for x in range(0, steps):
            pos = float(x) / float(steps - 1)
            h = lerp_degrees(start[0], end[0], pos)
            s = lerp(start[1], end[1], pos)
            v = lerp(start[2], end[2], pos)
            a = lerp(color1.alpha, color2.alpha, pos)

            gradient.append(Color.NewFromHsv(h, s, v, alpha=a))

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
    def scheme_generator(color=None, base_color=None, randomize: bool=False,
                         alternate: bool=False, steps: int=11, rgb: bool=False):
        """
        Generator which produces a continuous stream of colors based on a
        color scheme of two overlapping colors.

        :param color: The "top" color
        :param base_color: The base or background color
        :param randomize: True if values should be chosen at random instead of sequential
        :param steps: Number of steps used for the gradient
        :param rgb: True if we should return RGB tuples

        :return: generator
        """
        c0 = c1 = None
        if base_color is not None and color is not None:
            c0, c1 = color.AnalogousScheme(angle=15, mode='rgb')
        elif base_color is not None:
            c0, c1 = base_color.TriadicScheme(angle=160, mode='rgb')

        gradient = ColorUtils.hsv_gradient(c0, c1, steps)

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
    def composite_alpha(fg_alpha: float, bg_alpha: float) -> float:
        """
        Blend alpha
        """
        return 1.0 - (((1.0 - bg_alpha) * (1.0 - fg_alpha)))


    @staticmethod
    def composite_value(fg_color: float, fg_alpha: float, bg_color: float,
                        bg_alpha: float, a: float) -> float:
        """
        Blend component
        """
        if a == 0:
            return 0
        return ((fg_color * fg_alpha) + (bg_color * bg_alpha * (1.0 - fg_alpha))) / (a)


    @staticmethod
    @colorarg('fg', 'bg')
    def composite(fg: Color, bg: Color) -> Color:
        """
        Blends two colors, including alpha

        :param fg: Foreground color
        :param bg: Background color

        :return: The blended color
        """
        alpha = ColorUtils.composite_alpha(fg.alpha, bg.alpha)

        rgb = [ColorUtils.composite_value(fg_rgb, fg.alpha, bg_rgb, bg.alpha, alpha) \
            for fg_rgb, bg_rgb in zip(fg.rgb, bg.rgb)]

        return Color.NewFromRgb(*rgb, alpha)
