#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Aurora - Northern lights curtain effect.

Shimmering vertical curtains of light that undulate horizontally,
with colors flowing through greens, teals, and purples.
"""

import math

from traitlets import Float, observe

from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

# Default aurora palette: green -> teal -> purple
AURORA_COLORS = ["#00ff87", "#00d9ff", "#bf00ff", "#00ff87"]


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Smooth interpolation between edges."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


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

    color_scheme = ColorSchemeTrait(minlen=2, default_value=AURORA_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        # Must set gradient_length BEFORE super().__init__ because the
        # color_scheme observer fires during init and needs this value
        self.gradient_length = 180
        self._gradient = None
        self._time = 0.0
        super().__init__(*args, **kwargs)
        self.fps = 15

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(self.gradient_length, *self.color_scheme)

    @observe("color_scheme")
    def _scheme_changed(self, changed):
        self._gen_gradient()

    def init(self, frame):
        self._time = 0.0
        self._gen_gradient()
        return True

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps

        gradient = self._gradient
        if gradient is None:
            return False

        width = layer.width
        height = layer.height
        grad_len = len(gradient)

        t = self._time
        speed = self.speed
        drift = self.drift
        base_height = self.curtain_height
        shimmer = self.shimmer
        color_drift = self.color_drift

        for col in range(width):
            # Curtain height oscillates via layered sines
            wave1 = math.sin(col * 0.4 + t * speed)
            wave2 = math.sin(t * drift * 0.7) * 0.5
            curtain_h = base_height + wave1 * wave2 * 0.3

            # Convert to row threshold (0 = top, height-1 = bottom)
            curtain_row = (1.0 - curtain_h) * height

            # Color shifts across columns and time
            hue_offset = col * 3 + t * color_drift * 20
            base_color_idx = int(hue_offset) % grad_len

            for row in range(height):
                # Intensity falls off below curtain edge
                intensity = smoothstep(curtain_row + 2, curtain_row - 1, row)

                # High-frequency shimmer
                if shimmer > 0:
                    shimmer_val = math.sin(col * 2.1 + row * 1.3 + t * 8) * shimmer * 0.15
                    intensity = max(0.0, min(1.0, intensity + shimmer_val))

                if intensity > 0.01:
                    # Gradient shifts slightly per row for depth
                    color_idx = (base_color_idx + row * 2) % grad_len
                    color = gradient[color_idx]
                    layer.matrix[row][col] = (*color.rgb, intensity)
                else:
                    layer.matrix[row][col] = (0.0, 0.0, 0.0, 0.0)

        return True
