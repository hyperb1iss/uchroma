import itertools
import math
import random

from enum import Enum

from uchroma.util import colorarg, to_rgb

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
    def lab_gradient(color1: Color, color2: Color, steps: int=100, loop=False) -> list:
        """
        Generate a gradient between two points in Lab colorspace

        :param color1: Starting color
        :param color2: Ending color
        :param steps: Number of steps in the gradient
        :param loop: If the gradient should "loop" back around to it's starting point

        :return: List of colors in the gradient
        """
        lab1 = color1.lab
        lab2 = color2.lab
        gradient = []
        for i in range(0, steps):
            alpha = float(i) / (steps - 1)
            L = (1 - alpha) * lab1[0] + alpha * lab2[0]
            a = (1 - alpha) * lab1[1] + alpha * lab2[1]
            b = (1 - alpha) * lab1[2] + alpha * lab2[2]
            gradient.append(Color.NewFromLab(L, a, b))

        if loop:
            gradient.extend(gradient[::-1])

        return gradient


    @staticmethod
    @colorarg('color')
    def hue_gradient(color: Color, to_hue: float, steps: int=100, loop=False) -> list:
        """
        Generate a gradient by rotating the hue

        :param color: Starting color
        :param to_hue: Ending hue
        :param steps: Length of the gradient
        :param loop: If the gradient should "loop" back around to it's starting point

        :return: List of colors in the gradient
        """
        gradient = []
        from_hue = color.hue

        for i in range(0, steps):
            alpha = float(i) / (steps - 1)
            hue = (1 - alpha) * from_hue + alpha * to_hue
            gradient.append(color.ColorWithHue(hue))

        if loop:
            gradient.extend(gradient[::-1])

        return gradient


    @staticmethod
    @colorarg('color', 'base_color')
    def scheme_generator(color=None, base_color=None, randomize: bool=False,
                         steps: int=10, rgb: bool=False):
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
            c0, c1 = base_color.TriadicScheme(angle=180, mode='rgb')

        gradient = ColorUtils.hue_gradient(c0, c1.hue, steps, not randomize)

        if rgb:
            gradient = [to_rgb(x) for x in gradient]

        if randomize:
            while True:
                yield random.choice(gradient)
        else:
            cycle = itertools.cycle(gradient)
            while True:
                yield next(cycle)


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
    def rainbow_generator(steps: int=64, rgb: bool=False):
        """
        Generate a smooth rainbow gradient

        :param steps: Length or smoothness of the gradient
        :param rgb: True if RGB tuples should be generated

        :return: generator
        """
        gradient = ColorUtils.interference(steps)
        if rgb:
            gradient = [to_rgb(x) for x in gradient]

        it = itertools.cycle(gradient)

        while True:
            yield next(it)

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
