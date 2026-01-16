#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Kaleidoscope - Rotating symmetric patterns.

Symmetric patterns that rotate and morph, creating hypnotic
geometric shapes using polar coordinate transforms and n-fold symmetry.
"""

import math

from traitlets import Float, Int, observe

from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait, DefaultCaselessStrEnum

KALEIDOSCOPE_COLORS = ["#ff006e", "#ffbe0b", "#00f5d4", "#8338ec"]


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
        self._gradient = None
        self._polar_map = None
        self._time = 0.0
        self.fps = 15

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    def _compute_polar_map(self):
        """Precompute polar coordinates for each pixel."""
        width = self.width
        height = self.height
        cx = width / 2.0
        cy = height / 2.0

        self._polar_map = []
        for row in range(height):
            for col in range(width):
                dx = col - cx
                dy = (row - cy) * (width / height)  # Aspect ratio correction
                angle = math.atan2(dy, dx)
                radius = math.sqrt(dx * dx + dy * dy)
                self._polar_map.append((angle, radius))

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

        gradient = self._gradient
        if gradient is None:
            return False

        width = layer.width
        grad_len = len(gradient)

        t = self._time
        sym = self.symmetry
        rot_spd = self.rotation_speed
        ring_freq = self.ring_frequency
        spiral_tw = self.spiral_twist
        hue_rot = self.hue_rotation
        mode = self.pattern_mode

        # Symmetry wedge angle
        wedge = 2.0 * math.pi / sym

        assert self._polar_map is not None
        for idx, (angle, radius) in enumerate(self._polar_map):
            row = idx // width
            col = idx % width

            # Apply rotation
            rotated_angle = angle - t * rot_spd

            # Apply n-fold symmetry (fold into first wedge)
            sym_angle = rotated_angle % wedge
            # Mirror for kaleidoscope effect
            if int(rotated_angle / wedge) % 2 == 1:
                sym_angle = wedge - sym_angle

            # Pattern value based on mode
            if mode == "rings":
                value = math.sin(radius * ring_freq * 3.0 + t * 2.0)
            elif mode == "spiral":
                value = math.sin(radius * ring_freq + sym_angle * spiral_tw + t)
            else:  # waves
                value = math.sin(sym_angle * 4.0 + t * 2.0) * math.cos(radius * ring_freq)

            # Color from symmetric angle + time rotation
            hue_idx = int((sym_angle / wedge) * grad_len * 0.5 + t * hue_rot) % grad_len
            color = gradient[hue_idx]
            r, g, b = color.rgb

            # Brightness: never fully dark (0.3 to 1.0)
            brightness = (value + 1.0) / 2.0 * 0.7 + 0.3

            layer.matrix[row][col] = (
                r * brightness,
                g * brightness,
                b * brightness,
                1.0,
            )

        return True
