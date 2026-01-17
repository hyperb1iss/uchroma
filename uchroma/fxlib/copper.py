#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Copper Bars - Classic Amiga demoscene raster bar effect.

Horizontal color bands flow and warp with sine-wave displacement,
creating the iconic "copper bar" look from 80s/90s demos.
"""

import math

from traitlets import Bool, Float, Int, observe

from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait


class CopperBars(Renderer):
    """Pure Amiga-style raster bars with sine displacement."""

    meta = RendererMeta(
        "Copper Bars",
        "Classic Amiga demoscene raster ribbons",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    speed = Float(default_value=1.0, min=0.2, max=3.0).tag(config=True)
    wave_amplitude = Float(default_value=0.5, min=0.0, max=2.0).tag(config=True)
    wave_frequency = Float(default_value=0.8, min=0.2, max=2.0).tag(config=True)
    band_width = Int(default_value=40, min=10, max=100).tag(config=True)
    horizontal_wave = Bool(default_value=False).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=[*ColorScheme.Rainbow.value]).tag(
        config=True
    )
    preset = ColorPresetTrait(ColorScheme, default_value=ColorScheme.Rainbow).tag(config=False)
    gradient_length = Int(default_value=360, min=60, max=720).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None
        self._time = 0.0
        self.fps = 15

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(self.gradient_length, *self.color_scheme)

    @observe("color_scheme", "gradient_length", "preset")
    def _scheme_changed(self, changed):
        with self.hold_trait_notifications():
            if changed.name == "preset" and changed.new is not None:
                self.color_scheme = list(changed.new.value)
            self._gen_gradient()

    def init(self, frame):
        self._time = 0.0
        self._gen_gradient()
        return True

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps * self.speed

        gradient = self._gradient
        if gradient is None:
            return False

        grad_len = len(gradient)
        width = layer.width
        height = layer.height

        wave_freq = self.wave_frequency
        wave_amp = self.wave_amplitude
        band_w = self.band_width
        t = self._time

        for row in range(height):
            # Sine-based vertical displacement
            y_warp = math.sin(row * wave_freq + t * 2.0) * wave_amp * band_w

            # Base palette index from row position + warp + scroll
            base_idx = row * band_w + y_warp + t * 50

            if self.horizontal_wave:
                # Per-column variation for extra dimension
                for col in range(width):
                    h_mod = math.sin(col * 0.3 + t * 1.5) * band_w * 0.3
                    idx = int(base_idx + h_mod) % grad_len
                    layer.matrix[row][col] = (*gradient[idx].rgb, 1.0)
            else:
                # Uniform row color (classic copper bar look)
                idx = int(base_idx) % grad_len
                color = (*gradient[idx].rgb, 1.0)
                for col in range(width):
                    layer.matrix[row][col] = color

        return True
