#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Nebula - Flowing space clouds effect.

Soft, colorful clouds drifting slowly, like looking at a nebula.
Uses layered noise for organic shapes with rich color gradients.
"""

import random

from traitlets import Float, Int, observe

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
        self._noise_table = None
        self._time = 0.0
        self.fps = 12

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    def _init_noise_table(self, size: int = 64):
        """Generate a simple value noise lookup table."""
        self._noise_table = [[random.random() for _ in range(size)] for _ in range(size)]
        self._noise_size = size

    def _sample_noise(self, x: float, y: float) -> float:
        """Bilinear interpolation of noise table."""
        size = self._noise_size
        table = self._noise_table

        # Wrap coordinates
        x = x % size
        y = y % size

        # Integer and fractional parts
        x0 = int(x) % size
        y0 = int(y) % size
        x1 = (x0 + 1) % size
        y1 = (y0 + 1) % size
        fx = x - int(x)
        fy = y - int(y)

        # Smoothstep for smoother interpolation
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)

        # Bilinear interpolation
        v00 = table[y0][x0]
        v10 = table[y0][x1]
        v01 = table[y1][x0]
        v11 = table[y1][x1]

        v0 = v00 + (v10 - v00) * fx
        v1 = v01 + (v11 - v01) * fx

        return v0 + (v1 - v0) * fy

    def _fbm(self, x: float, y: float, octaves: int) -> float:
        """Fractal Brownian Motion - layered noise."""
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            value += self._sample_noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2.0

        return value / max_value

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

        width = layer.width
        height = layer.height
        grad_len = len(self._gradient)

        t = self._time * self.drift_speed
        scale = self.scale * 10  # Scale up for noise table sampling
        octaves = self.detail
        contrast = self.contrast
        base_bright = self.base_brightness
        color_shift = self.color_shift

        for row in range(height):
            for col in range(width):
                # Sample noise with time offset for animation
                nx = col * scale + t * 3
                ny = row * scale + t * 2

                # Primary noise for cloud shape
                n1 = self._fbm(nx, ny, octaves)

                # Secondary noise for color variation
                n2 = self._fbm(nx * 0.7 + 100, ny * 0.7 + 100, octaves)

                # Map to gradient position
                grad_pos = n1 * contrast + (1 - contrast) * 0.5
                grad_pos = max(0.0, min(1.0, grad_pos))
                color_idx = int(grad_pos * (grad_len - 1))

                # Color shift from secondary noise
                if color_shift > 0:
                    shift = int((n2 - 0.5) * color_shift * grad_len * 0.5)
                    color_idx = (color_idx + shift) % grad_len

                color = self._gradient[color_idx]
                r, g, b = color.rgb

                # Brightness modulated by noise
                brightness = base_bright + n2 * 0.3
                brightness = max(0.3, min(1.0, brightness))

                layer.matrix[row][col] = (
                    r * brightness,
                    g * brightness,
                    b * brightness,
                    1.0,
                )

        return True
