#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

from traitlets import Int, observe

from uchroma.colorlib import Color
from uchroma.renderer import Renderer, RendererMeta

DEFAULT_SPEED = 8


class Rainbow(Renderer):
    # meta
    meta = RendererMeta("Rainflow", "Simple flowing colors", "Stefanie Jane", "1.0")

    # configurable traits
    speed = Int(default_value=DEFAULT_SPEED, min=0, max=20).tag(config=True)
    stagger = Int(default_value=4, min=0, max=100).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._gradient = None
        self._offset = 0

        self.fps = 5

    @staticmethod
    def _hue_gradient(start, length):
        step = 360 / length
        return [Color.NewFromHsv((start + (step * x)) % 360, 1, 1) for x in range(length)]

    @observe("speed", "stagger")
    def _create_gradient(self, change=None):
        self._offset = 0
        length = max(1, self.speed * self.width + (self.height * self.stagger))
        self._gradient = Rainbow._hue_gradient(0, length)

    def init(self, frame):
        self._create_gradient()
        return True

    async def draw(self, layer, timestamp):
        gradient = self._gradient
        if gradient is None:
            return False

        data = []
        for row in range(layer.height):
            data.append(
                [
                    gradient[(self._offset + (row * self.stagger) + col) % len(gradient)]
                    for col in range(layer.width)
                ]
            )

        layer.put_all(data)
        self._offset = (self._offset + 1) % len(gradient)

        return True
