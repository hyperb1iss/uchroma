#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Metaballs - Organic blob fusion effect.

Soft, blobby shapes that slowly drift, merge when close,
and split apart — like a lava lamp. Classic demoscene algorithm.
"""

import math
import random
from dataclasses import dataclass

from traitlets import Float, Int, observe

from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

METABALL_COLORS = ["#ff006e", "#8338ec", "#3a86ff", "#00f5d4"]


@dataclass
class Blob:
    """A single metaball with position, velocity, and color."""

    x: float
    y: float
    vx: float
    vy: float
    radius: float
    hue_idx: int


class Metaballs(Renderer):
    """Organic lava-lamp style blobs that merge and split."""

    meta = RendererMeta(
        "Metaballs",
        "Organic blobs that merge and flow",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    blob_count = Int(default_value=4, min=2, max=8).tag(config=True)
    speed = Float(default_value=0.5, min=0.1, max=2.0).tag(config=True)
    threshold = Float(default_value=1.0, min=0.5, max=2.0).tag(config=True)
    glow_falloff = Float(default_value=2.0, min=1.0, max=4.0).tag(config=True)
    base_brightness = Float(default_value=0.2, min=0.0, max=0.4).tag(config=True)
    blob_radius = Float(default_value=3.0, min=1.5, max=5.0).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=METABALL_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._blobs: list[Blob] = []
        self._gradient = None
        self.fps = 15

    def _spawn_blob(self, idx: int) -> Blob:
        """Create a new blob with random properties."""
        angle = random.random() * math.pi * 2
        speed = self.speed * (0.5 + random.random())
        return Blob(
            x=random.random() * self.width,
            y=random.random() * self.height,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            radius=self.blob_radius * (0.8 + random.random() * 0.4),
            hue_idx=idx,
        )

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    @observe("color_scheme")
    def _scheme_changed(self, changed):
        self._gen_gradient()

    @observe("blob_count")
    def _count_changed(self, changed):
        while len(self._blobs) < self.blob_count:
            self._blobs.append(self._spawn_blob(len(self._blobs)))
        while len(self._blobs) > self.blob_count:
            self._blobs.pop()

    def init(self, frame):
        self._gen_gradient()
        self._blobs = [self._spawn_blob(i) for i in range(self.blob_count)]
        return True

    async def draw(self, layer, timestamp):
        width = layer.width
        height = layer.height
        grad_len = len(self._gradient)
        thresh = self.threshold
        falloff = self.glow_falloff
        base_bright = self.base_brightness

        # Update blob physics
        dt = 1.0 / self.fps
        for blob in self._blobs:
            blob.x += blob.vx * dt * 10
            blob.y += blob.vy * dt * 10

            # Bounce off edges
            if blob.x < 0 or blob.x >= width:
                blob.vx = -blob.vx
                blob.x = max(0, min(width - 0.1, blob.x))
            if blob.y < 0 or blob.y >= height:
                blob.vy = -blob.vy
                blob.y = max(0, min(height - 0.1, blob.y))

        # Render metaball field
        for row in range(height):
            for col in range(width):
                field = 0.0
                total_weight = 0.0
                weighted_hue = 0.0

                for blob in self._blobs:
                    dx = col - blob.x
                    dy = row - blob.y
                    dist_sq = dx * dx + dy * dy + 0.1  # Epsilon to avoid divide by zero

                    # Inverse square falloff
                    contribution = (blob.radius * blob.radius) / dist_sq
                    field += contribution

                    # Weight color by contribution
                    blob_hue = (blob.hue_idx * 60) % grad_len
                    weighted_hue += blob_hue * contribution
                    total_weight += contribution

                # Threshold creates blob boundary
                if field > thresh:
                    brightness = min(1.0, (field - thresh) * falloff * 0.5 + 0.5)
                    hue_idx = int(weighted_hue / total_weight) % grad_len
                    color = self._gradient[hue_idx]
                    r, g, b = color.rgb
                    layer.matrix[row][col] = (
                        r * brightness,
                        g * brightness,
                        b * brightness,
                        1.0,
                    )
                elif field > thresh * 0.5:
                    # Glow region
                    glow = (field - thresh * 0.5) / (thresh * 0.5)
                    brightness = base_bright + glow * 0.3
                    hue_idx = int(weighted_hue / total_weight) % grad_len
                    color = self._gradient[hue_idx]
                    r, g, b = color.rgb
                    layer.matrix[row][col] = (
                        r * brightness,
                        g * brightness,
                        b * brightness,
                        1.0,
                    )
                else:
                    # Background
                    layer.matrix[row][col] = (
                        base_bright * 0.3,
                        base_bright * 0.2,
                        base_bright * 0.4,
                        1.0,
                    )

        return True
