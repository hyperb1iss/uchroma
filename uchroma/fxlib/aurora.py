#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Aurora - Northern lights curtain effect.

Shimmering vertical curtains of light that undulate horizontally,
with colors flowing through greens, teals, and purples.
"""

import numpy as np
from traitlets import Float, observe

from uchroma._native import draw_aurora as _rust_draw_aurora
from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

# Default aurora palette: green -> teal -> purple
AURORA_COLORS = ["#00ff87", "#00d9ff", "#bf00ff", "#00ff87"]


class Aurora(Renderer):
    """Northern lights with undulating curtains of color."""

    meta = RendererMeta(
        "Aurora",
        "Shimmering northern lights curtains",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    speed = Float(default_value=1.0, min=0.2, max=3.0).tag(config=True)
    drift = Float(default_value=0.3, min=0.1, max=1.0).tag(config=True)
    curtain_height = Float(default_value=0.7, min=0.3, max=1.0).tag(config=True)
    shimmer = Float(default_value=0.3, min=0.0, max=1.0).tag(config=True)
    color_drift = Float(default_value=0.5, min=0.1, max=2.0).tag(config=True)
    floor_glow = Float(default_value=0.15, min=0.0, max=0.4).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=AURORA_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        self.gradient_length = 180
        self._gradient = None
        self._gradient_array = None
        self._time = 0.0
        super().__init__(*args, **kwargs)
        self.fps = 15

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(self.gradient_length, *self.color_scheme)
        # Pre-convert to numpy array for Rust
        self._gradient_array = np.array([c.rgb for c in self._gradient], dtype=np.float64)

    @observe("color_scheme")
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

        _rust_draw_aurora(
            width=layer.width,
            height=layer.height,
            matrix=layer.matrix,
            gradient=self._gradient_array,
            time=self._time,
            speed=self.speed,
            drift=self.drift,
            curtain_height=self.curtain_height,
            shimmer=self.shimmer,
            color_drift=self.color_drift,
            floor_glow=self.floor_glow,
        )

        return True
