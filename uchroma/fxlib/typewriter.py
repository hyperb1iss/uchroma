#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Typewriter - Reactive key glow effect.

Keys illuminate with warm incandescent glow when pressed and
slowly fade like old typewriter keys. Creates a trailing
"heat map" of your typing.
"""

import numpy as np
from traitlets import Float, observe

from uchroma.color import to_color
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait


class Typewriter(Renderer):
    """Warm reactive glow that fades after keypress."""

    meta = RendererMeta(
        "Typewriter",
        "Keys glow warmly when pressed",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    glow_color = ColorTrait(default_value="#ffaa44").tag(config=True)
    decay_time = Float(default_value=1.5, min=0.5, max=5.0).tag(config=True)
    spread = Float(default_value=0.3, min=0.0, max=0.6).tag(config=True)
    base_brightness = Float(default_value=0.15, min=0.0, max=0.3).tag(config=True)
    peak_brightness = Float(default_value=1.0, min=0.7, max=1.0).tag(config=True)
    warmth = Float(default_value=0.3, min=0.0, max=0.6).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._brightness = None
        self._decay_factor = 0.92
        self._glow_rgb = (1.0, 0.67, 0.27)  # Default warm amber
        self.fps = 30

    def _compute_decay(self):
        """Compute per-frame decay factor from decay_time."""
        # decay_time is seconds to reach ~10% brightness
        # brightness = decay_factor ^ (fps * decay_time) = 0.1
        # decay_factor = 0.1 ^ (1 / (fps * decay_time))
        frames = self.fps * self.decay_time
        self._decay_factor = 0.1 ** (1.0 / frames)

    @observe("decay_time")
    def _decay_changed(self, change):
        self._compute_decay()

    @observe("glow_color")
    def _color_changed(self, change):
        color = to_color(self.glow_color)
        if color:
            self._glow_rgb = color.rgb

    def init(self, frame) -> bool:
        if not self.has_key_input:
            return False

        self._brightness = np.zeros((frame.height, frame.width), dtype=np.float64)
        self._compute_decay()

        color = to_color(self.glow_color)
        if color:
            self._glow_rgb = color.rgb

        return True

    async def draw(self, layer, timestamp):
        events = await self.get_input_events()
        height = layer.height
        width = layer.width
        spread = self.spread
        peak = self.peak_brightness

        # Process new key events
        for event in events:
            if event.coords is None:
                continue
            for coord in event.coords:
                row, col = coord.y, coord.x
                if 0 <= row < height and 0 <= col < width:
                    self._brightness[row, col] = peak

                    # Spread to neighbors
                    if spread > 0:
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dy == 0 and dx == 0:
                                    continue
                                ny, nx = row + dy, col + dx
                                if 0 <= ny < height and 0 <= nx < width:
                                    self._brightness[ny, nx] = max(
                                        self._brightness[ny, nx],
                                        peak * spread,
                                    )

        # Decay all brightness values
        self._brightness *= self._decay_factor

        # Render
        base = self.base_brightness
        warmth = self.warmth
        glow_r, glow_g, glow_b = self._glow_rgb

        for row in range(height):
            for col in range(width):
                b = max(base, self._brightness[row, col])

                # Color temperature: brighter = warmer (shift toward white)
                if b > 0.7 and warmth > 0:
                    warm_mix = (b - 0.7) / 0.3 * warmth
                    r = glow_r + (1.0 - glow_r) * warm_mix
                    g = glow_g + (1.0 - glow_g) * warm_mix
                    bl = glow_b + (1.0 - glow_b) * warm_mix
                else:
                    r, g, bl = glow_r * b, glow_g * b, glow_b * b

                layer.matrix[row][col] = (r * b, g * b, bl * b, 1.0)

        return True
