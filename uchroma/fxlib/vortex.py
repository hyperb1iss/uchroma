#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Vortex - Hypnotic spiral tunnel effect.

A swirling vortex centered on the keyboard with spiral arms
flowing inward or outward, creating a tunnel effect.
"""

import math

from traitlets import Float, Int, observe

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
        arms = self.arm_count
        twist = self.twist
        flow_spd = self.flow_speed
        flow_dir = self.flow_direction
        rot_spd = self.rotation_speed
        center_g = self.center_glow
        ring_dens = self.ring_density

        for idx, (angle, radius) in enumerate(self._polar_map):
            row = idx // width
            col = idx % width

            # Spiral: angle offset by radius creates twist
            spiral_angle = angle - radius * twist - t * rot_spd

            # Multiple spiral arms
            arm_value = math.sin(spiral_angle * arms)

            # Radial "depth" rings
            depth_value = math.sin(radius * ring_dens * 2.0 - t * flow_spd * flow_dir)

            # Combine spiral and depth
            value = arm_value * 0.5 + depth_value * 0.5

            # Color: hue from angle
            hue_idx = int((angle / math.pi + 1.0) * 180 + t * 30) % grad_len
            color = gradient[hue_idx]
            r, g, b = color.rgb

            # Brightness from combined value (0.4 to 1.0)
            brightness = (value + 1.0) / 2.0 * 0.6 + 0.4

            # Center glow boost
            if radius < center_g:
                center_boost = math.exp(-(radius**2) / (2 * (center_g / 2) ** 2))
                brightness = min(1.0, brightness + center_boost * 0.4)

            layer.matrix[row][col] = (
                r * brightness,
                g * brightness,
                b * brightness,
                1.0,
            )

        return True
