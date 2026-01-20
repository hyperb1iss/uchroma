#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Ocean - Rolling wave caustics effect.
"""

import numpy as np
from traitlets import Float, observe

from uchroma._native import draw_ocean as _rust_draw_ocean
from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

OCEAN_COLORS = ["#001f3f", "#0074D9", "#7FDBFF", "#ffffff"]


class Ocean(Renderer):
    """Rolling ocean waves with foam and caustics."""

    meta = RendererMeta(
        "Ocean",
        "Rolling waves with caustic highlights",
        "uchroma",
        "1.0",
    )

    wave_speed = Float(default_value=1.0, min=0.3, max=2.5).tag(config=True)
    wave_height = Float(default_value=0.5, min=0.2, max=1.0).tag(config=True)
    foam_threshold = Float(default_value=0.5, min=0.2, max=0.8).tag(config=True)
    caustic_intensity = Float(default_value=0.3, min=0.0, max=0.6).tag(config=True)
    saturation = Float(default_value=0.8, min=0.4, max=1.0).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=OCEAN_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None
        self._gradient_array = None
        self._time = 0.0
        self.fps = 15

    def _gen_gradient(self):
        gradient = ColorUtils.gradient(100, *self.color_scheme, loop=False)
        if self.saturation < 1.0:
            gradient = [c.ColorWithSaturation(self.saturation) for c in gradient]
        self._gradient = gradient
        self._gradient_array = np.array([c.rgb for c in gradient], dtype=np.float64)

    @observe("color_scheme", "saturation")
    def _scheme_changed(self, changed):
        self._gen_gradient()

    def init(self, frame):
        self._time = 0.0
        self._gen_gradient()
        return True

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps

        if self._gradient_array is None:
            return False

        _rust_draw_ocean(
            width=layer.width,
            height=layer.height,
            matrix=layer.matrix,
            gradient=self._gradient_array,
            time=self._time,
            wave_speed=self.wave_speed,
            wave_height=self.wave_height,
            foam_threshold=self.foam_threshold,
            caustic_intensity=self.caustic_intensity,
        )

        return True
