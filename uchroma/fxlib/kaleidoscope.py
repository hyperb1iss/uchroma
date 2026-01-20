#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Kaleidoscope - Rotating symmetric patterns.

Symmetric patterns that rotate and morph, creating hypnotic
geometric shapes using polar coordinate transforms and n-fold symmetry.
"""

import numpy as np
from traitlets import Float, Int, observe

from uchroma._native import (
    compute_polar_map as _rust_compute_polar_map,
    draw_kaleidoscope as _rust_draw_kaleidoscope,
)
from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait, DefaultCaselessStrEnum

KALEIDOSCOPE_COLORS = ["#ff006e", "#ffbe0b", "#00f5d4", "#8338ec"]

# Pattern mode mapping: string -> u8 for Rust
_PATTERN_MODES = {"spiral": 0, "rings": 1, "waves": 2}


class Kaleidoscope(Renderer):
    """Rotating kaleidoscope with n-fold symmetry."""

    meta = RendererMeta(
        "Kaleidoscope",
        "Rotating symmetric patterns",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    symmetry = Int(default_value=6, min=3, max=12).tag(config=True)
    rotation_speed = Float(default_value=0.5, min=0.1, max=2.0).tag(config=True)
    pattern_mode = DefaultCaselessStrEnum(["spiral", "rings", "waves"], default_value="spiral").tag(
        config=True
    )
    ring_frequency = Float(default_value=0.5, min=0.2, max=1.5).tag(config=True)
    spiral_twist = Float(default_value=2.0, min=0.5, max=5.0).tag(config=True)
    hue_rotation = Float(default_value=30.0, min=0.0, max=120.0).tag(config=True)
    saturation = Float(default_value=0.9, min=0.5, max=1.0).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=KALEIDOSCOPE_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient_array: np.ndarray | None = None
        self._polar_map: np.ndarray | None = None
        self._time = 0.0
        self.fps = 15

    def _gen_gradient(self):
        """Generate gradient and convert to numpy array for Rust."""
        gradient = ColorUtils.gradient(360, *self.color_scheme)
        if self.saturation < 1.0:
            gradient = [c.ColorWithSaturation(self.saturation) for c in gradient]
        # Pre-convert to numpy array for Rust
        self._gradient_array = np.array([c.rgb for c in gradient], dtype=np.float64)

    def _compute_polar_map(self):
        """Precompute polar coordinates using Rust."""
        self._polar_map = _rust_compute_polar_map(self.width, self.height)

    @observe("color_scheme", "saturation")
    def _scheme_changed(self, changed):
        self.logger.debug("color_scheme changed: %s -> %s", changed.old, changed.new)
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

        _rust_draw_kaleidoscope(
            width=layer.width,
            height=layer.height,
            matrix=layer.matrix,
            gradient=self._gradient_array,
            polar_map=self._polar_map,
            time=self._time,
            symmetry=self.symmetry,
            rotation_speed=self.rotation_speed,
            pattern_mode=_PATTERN_MODES.get(self.pattern_mode, 0),
            ring_frequency=self.ring_frequency,
            spiral_twist=self.spiral_twist,
            hue_rotation=self.hue_rotation,
        )

        return True
