# pylint: disable=invalid-name
import asyncio
import time

from enum import Enum
from math import cos, pi, sin, sqrt

from traitlets import observe, Int
from grapefruit import Color

from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait



class Plasma(Renderer):
    """
    Draws a old-school plasma effect
    """

    # meta
    meta = RendererMeta('Plasma', 'Colorful moving blobs of plasma',
                        'Steve Kondik', 'v1.0')

    # configurable traits
    color_scheme = ColorSchemeTrait(minlen=2, default_value=['black', 'white'])
    preset = ColorPresetTrait(ColorScheme, default_value=None)
    gradient_length = Int(default_value=360)


    def __init__(self, *args, **kwargs):
        super(Plasma, self).__init__(*args, **kwargs)

        self._gradient = None
        self._start_time = 0
        self.preset = ColorScheme.Qap
        self.fps = 15


    @observe('color_scheme', 'gradient_length', 'preset')
    def _scheme_changed(self, changed):
        if changed.name == 'preset':
            self.color_scheme.clear()
            self.color_scheme = list(changed.new.value)

        self._gradient = ColorUtils.gradient(self.gradient_length, *self.color_scheme)


    def init(self, frame):
        self._start_time = time.time()
    #    self.color_scheme = list(self.preset.value)
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

                pos = len(self._gradient) * ((1 + sin(pi * val)) / 2)
                layer.matrix[row][col] = tuple(self._gradient[int(pos)])

        return True
