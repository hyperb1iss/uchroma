#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Ocean - Rolling wave caustics effect.

Horizontal waves with bright "caustic" highlights on wave crests,
creating the effect of light playing on water.
"""

import math

from traitlets import Float, observe

from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

# Deep blue to teal to white foam
OCEAN_COLORS = ["#001f3f", "#0074D9", "#7FDBFF", "#ffffff"]


class Ocean(Renderer):
    """Rolling ocean waves with foam and caustics."""

    meta = RendererMeta(
        "Ocean",
        "Rolling waves with caustic highlights",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    wave_speed = Float(default_value=1.0, min=0.3, max=2.5).tag(config=True)
    wave_height = Float(default_value=0.5, min=0.2, max=1.0).tag(config=True)
    foam_threshold = Float(default_value=0.5, min=0.2, max=0.8).tag(config=True)
    caustic_intensity = Float(default_value=0.3, min=0.0, max=0.6).tag(config=True)
    saturation = Float(default_value=0.8, min=0.4, max=1.0).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=OCEAN_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None
        self._time = 0.0
        self.fps = 15

    def _gen_gradient(self):
        gradient = ColorUtils.gradient(100, *self.color_scheme, loop=False)
        if self.saturation < 1.0:
            gradient = [c.ColorWithSaturation(self.saturation) for c in gradient]
        self._gradient = gradient

    @observe("color_scheme", "saturation")
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

        t = self._time * self.wave_speed
        wave_h = self.wave_height
        foam_thresh = self.foam_threshold
        caustic = self.caustic_intensity
        surface_rows = min(3, height)
        surface_scale = 1.0 / surface_rows if surface_rows > 0 else 0.0

        # Wave components (Gerstner-inspired)
        waves = [
            (0.3, 0.4, 1.0, 0.0),  # (freq, amp, speed, phase)
            (0.5, 0.25, 1.3, 2.1),
            (0.8, 0.15, 0.7, 4.2),
        ]

        for col in range(width):
            # Sum wave heights at this column
            height_val = 0.0
            slope = 0.0
            for freq, amp, spd, phase in waves:
                height_val += amp * math.sin(col * freq - t * spd + phase)
                slope += amp * freq * math.cos(col * freq - t * spd + phase)

            height_val *= wave_h
            slope *= wave_h

            for row in range(height):
                # Depth: 0 = surface (top), 1 = deep (bottom)
                depth = row / (height - 1) if height > 1 else 0

                # Base color from gradient (deep to surface)
                grad_idx = int((1.0 - depth) * (grad_len - 1))
                color = gradient[grad_idx]
                r, g, b = color.rgb

                # Brightness: surface is brighter
                brightness = 0.5 + (1.0 - depth) * 0.4

                # Wave height affects surface brightness (caustics)
                if row < surface_rows:
                    wave_effect = (height_val + 1.0) / 2.0
                    surface_factor = (surface_rows - row) * surface_scale
                    brightness += wave_effect * caustic * surface_factor

                # Foam on steep slopes at surface
                if abs(slope) > foam_thresh and row < surface_rows:
                    surface_factor = (surface_rows - row) * surface_scale
                    r = r + (1.0 - r) * surface_factor
                    g = g + (1.0 - g) * surface_factor
                    b = b + (1.0 - b) * surface_factor
                    brightness = min(1.0, brightness + surface_factor * 0.3)

                # Apply brightness
                brightness = min(1.0, brightness)
                layer.matrix[row][col] = (
                    r * brightness,
                    g * brightness,
                    b * brightness,
                    1.0,
                )

        return True
