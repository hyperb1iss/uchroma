#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name

import time

import numpy as np
from traitlets import Float, Int, observe

from uchroma._native import draw_plasma
from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait


class Plasma(Renderer):
    """
    Draws a old-school plasma effect
    """

    # meta
    meta = RendererMeta("Plasma", "Colorful moving blobs of plasma", "Stefanie Jane", "v1.0")

    # configurable traits
    color_scheme = ColorSchemeTrait(minlen=2, default_value=[*ColorScheme.Qap.value]).tag(
        config=True
    )
    preset = ColorPresetTrait(ColorScheme, default_value=ColorScheme.Qap).tag(config=False)
    gradient_length = Int(default_value=360, min=0).tag(config=True)

    # ✨ fun knobs
    speed = Float(default_value=1.0, min=0.1, max=2.0).tag(config=True)
    scale = Float(default_value=1.0, min=0.2, max=4.0).tag(config=True)
    complexity = Int(default_value=2, min=1, max=4).tag(config=True)
    turbulence = Float(default_value=0.0, min=0.0, max=1.0).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._gradient = None
        self._gradient_array = None  # Numpy array for Rust
        self._start_time = 0
        self.fps = 15

    def _gen_gradient(self):
        length = max(2, self.gradient_length)
        self._gradient = ColorUtils.gradient(length, *self.color_scheme)
        # Convert Color objects to numpy array for Rust
        self._gradient_array = np.array([c.rgb for c in self._gradient], dtype=np.float64)

    @observe("color_scheme", "gradient_length", "preset")
    def _scheme_changed(self, changed):
        with self.hold_trait_notifications():
            self.logger.debug("Parameters changed: %s", changed)
            if changed.name == "preset":
                self.color_scheme.clear()
                self.color_scheme = list(changed.new.value)
            self._gen_gradient()

    def init(self, frame):
        self._start_time = time.time()
        self._gen_gradient()
        return True

    async def draw(self, layer, timestamp):
        duration = (timestamp - self._start_time) * self.speed

        if self._gradient_array is not None:
            draw_plasma(
                layer.width,
                layer.height,
                layer.matrix,
                duration,
                self._gradient_array,
                self.scale,
                self.complexity,
                self.turbulence,
            )

        return True
