#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Vortex - Hypnotic spiral tunnel effect.

A swirling vortex centered on the keyboard with spiral arms
flowing inward or outward, creating a tunnel effect.
"""

import numpy as np
from traitlets import Float, Int, observe

from uchroma._native import (
    compute_polar_map as _rust_compute_polar_map,
    draw_vortex as _rust_draw_vortex,
)
from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

VORTEX_COLORS = ["#ff006e", "#8338ec", "#3a86ff", "#00f5d4"]


class Vortex(Renderer):
    """Hypnotic swirling spiral tunnel."""

    meta = RendererMeta(
        "Vortex",
        "Swirling spiral tunnel effect",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    arm_count = Int(default_value=3, min=1, max=6).tag(config=True)
    twist = Float(default_value=0.3, min=0.1, max=1.0).tag(config=True)
    flow_speed = Float(default_value=1.0, min=0.3, max=3.0).tag(config=True)
    flow_direction = Int(default_value=1, min=-1, max=1).tag(config=True)
    rotation_speed = Float(default_value=0.5, min=0.1, max=2.0).tag(config=True)
    center_glow = Float(default_value=3.0, min=1.0, max=5.0).tag(config=True)
    ring_density = Float(default_value=0.5, min=0.2, max=1.5).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=VORTEX_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient_array: np.ndarray | None = None
        self._polar_map: np.ndarray | None = None
        self._time = 0.0
        self.fps = 15

    def _gen_gradient(self):
        """Generate gradient and convert to numpy array for Rust."""
        gradient = ColorUtils.gradient(360, *self.color_scheme)
        # Pre-convert to numpy array for Rust
        self._gradient_array = np.array([c.rgb for c in gradient], dtype=np.float64)

    def _compute_polar_map(self):
        """Precompute polar coordinates using Rust."""
        self._polar_map = _rust_compute_polar_map(self.width, self.height)

    @observe("color_scheme")
    def _scheme_changed(self, changed):
        self._gen_gradient()

    def init(self, frame):
        self._time = 0.0
        self._gen_gradient()
        self._compute_polar_map()
        return True

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps

        if self._gradient_array is None or self._polar_map is None:
            return False

        _rust_draw_vortex(
            width=layer.width,
            height=layer.height,
            matrix=layer.matrix,
            gradient=self._gradient_array,
            polar_map=self._polar_map,
            time=self._time,
            arm_count=self.arm_count,
            twist=self.twist,
            flow_speed=self.flow_speed,
            flow_direction=self.flow_direction,
            rotation_speed=self.rotation_speed,
            center_glow=self.center_glow,
            ring_density=self.ring_density,
        )

        return True
