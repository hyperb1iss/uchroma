# pylint: disable=invalid-name
import asyncio
import time

from math import cos, pi, sin, sqrt

from grapefruit import Color

from uchroma.anim import Renderer


class Plasma(Renderer):
    """
    Draws a old-school plasma effect
    """

    def __init__(self, *args, **kwargs):
        super(Plasma, self).__init__(*args, **kwargs)

        self._gradient = None
        self._start_time = 0
        self.fps = 15


    @staticmethod
    def _hue_gradient(start, length):
        step = 360 / length
        return [Color.NewFromHsl((start + (step * x)) % 360, 1, 0.5) for x in range(0, length)]


    def init(self, frame, **kwargs):
        self._gradient = Plasma._hue_gradient(0, 360)
        self._start_time = time.time()

        return True


    @asyncio.coroutine
    def draw(self, layer, timestamp):
        duration = timestamp - self._start_time

        for col in range(0, layer.width):
            for row in range(0, layer.height):
                y = row / (layer.height * (layer.width / layer.height))
                x = col / layer.width

                val = sin((x * 20) + duration)
                val = sin(2 * (x * sin(duration / 2) + y * cos(duration / 3)) + duration)
                cx = x * sin(duration / 5)
                cy = y * cos(duration / 3)
                val += sin(sqrt(20 * (cx * cx + cy * cy) + 1) + duration)

                hue = 360 * ((1 + sin(pi * val)) / 2)
                layer.matrix[row][col] = tuple(self._gradient[int(hue)])

        return True
