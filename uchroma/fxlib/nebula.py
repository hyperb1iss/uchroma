#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Nebula - Flowing space clouds effect.

Soft, colorful clouds drifting slowly, like looking at a nebula.
Uses layered noise for organic shapes with rich color gradients.
"""

import numpy as np
from traitlets import Float, Int, observe

from uchroma._native import draw_nebula as _rust_draw_nebula
from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

NEBULA_COLORS = ["#4a0080", "#ff006e", "#00d4ff", "#00ff88"]


class Nebula(Renderer):
    """Flowing cosmic clouds using procedural noise."""

    meta = RendererMeta(
        "Nebula",
        "Flowing cosmic cloud formations",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    drift_speed = Float(default_value=0.3, min=0.1, max=1.0).tag(config=True)
    scale = Float(default_value=0.15, min=0.05, max=0.4).tag(config=True)
    detail = Int(default_value=2, min=1, max=3).tag(config=True)
    contrast = Float(default_value=0.6, min=0.3, max=1.0).tag(config=True)
    base_brightness = Float(default_value=0.5, min=0.3, max=0.7).tag(config=True)
    color_shift = Float(default_value=0.3, min=0.0, max=1.0).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=NEBULA_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None
        self._gradient_array = None
        self._noise_table = None
        self._time = 0.0
        self.fps = 12

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)
        # Pre-convert to numpy array for Rust
        self._gradient_array = np.array([c.rgb for c in self._gradient], dtype=np.float64)

    def _init_noise_table(self, size: int = 64):
        """Generate a simple value noise lookup table as numpy array."""
        self._noise_table = np.random.rand(size, size).astype(np.float64)

    @observe("color_scheme")
    def _scheme_changed(self, changed):
        self._gen_gradient()

    def init(self, frame):
        self._time = 0.0
        self._gen_gradient()
        self._init_noise_table(64)
        return True

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps

        if self._gradient_array is None or self._noise_table is None:
            return False

        _rust_draw_nebula(
            width=layer.width,
            height=layer.height,
            matrix=layer.matrix,
            gradient=self._gradient_array,
            noise_table=self._noise_table,
            time=self._time,
            drift_speed=self.drift_speed,
            scale=self.scale,
            octaves=self.detail,
            contrast=self.contrast,
            base_brightness=self.base_brightness,
            color_shift=self.color_shift,
        )

        return True
