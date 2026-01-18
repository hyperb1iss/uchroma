#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Embers - Glowing particle field effect.

A field of warm glowing particles that drift slowly upward,
pulse in brightness, and occasionally flare brighter.
Like embers in a dying fire — warm and well-lit.
"""

import math
import random
from dataclasses import dataclass

from traitlets import Float, Int, observe

from uchroma.color import to_color
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait


@dataclass
class Ember:
    """A single glowing ember particle."""

    x: float
    y: float
    phase: float
    velocity: float
    radius: float


class Embers(Renderer):
    """Warm glowing particles drifting upward."""

    meta = RendererMeta(
        "Embers",
        "Warm glowing particles drifting up",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    particle_count = Int(default_value=8, min=3, max=15).tag(config=True)
    drift_speed = Float(default_value=0.3, min=0.1, max=1.0).tag(config=True)
    pulse_speed = Float(default_value=1.5, min=0.5, max=4.0).tag(config=True)
    glow_radius = Float(default_value=2.0, min=1.0, max=4.0).tag(config=True)
    color = ColorTrait(default_value="#ff6b35").tag(config=True)
    base_brightness = Float(default_value=0.6, min=0.3, max=0.8).tag(config=True)
    flare_chance = Float(default_value=0.02, min=0.0, max=0.1).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._embers: list[Ember] = []
        self._time = 0.0
        self._color_rgb = (1.0, 0.42, 0.21)
        self.fps = 15

    def _spawn_ember(self) -> Ember:
        """Create a new ember with random properties."""
        return Ember(
            x=random.random() * self.width,
            y=random.random() * self.height,
            phase=random.random() * math.pi * 2,
            velocity=self.drift_speed * (0.5 + random.random()),
            radius=self.glow_radius * (0.7 + random.random() * 0.6),
        )

    @observe("particle_count")
    def _count_changed(self, changed):
        while len(self._embers) < self.particle_count:
            self._embers.append(self._spawn_ember())
        while len(self._embers) > self.particle_count:
            self._embers.pop()

    @observe("color")
    def _color_changed(self, changed):
        c = to_color(self.color)
        if c:
            self._color_rgb = c.rgb

    def init(self, frame):
        self._time = 0.0
        c = to_color(self.color)
        if c:
            self._color_rgb = c.rgb
        self._embers = [self._spawn_ember() for _ in range(self.particle_count)]
        return True

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps

        width = layer.width
        height = layer.height
        t = self._time
        pulse_spd = self.pulse_speed
        base_bright = self.base_brightness
        flare = self.flare_chance
        r, g, b = self._color_rgb

        # Clear layer with slight ambient warmth
        ambient_r = r * 0.05
        ambient_g = g * 0.03
        ambient_b = b * 0.02
        layer.matrix[:, :, 0] = ambient_r
        layer.matrix[:, :, 1] = ambient_g
        layer.matrix[:, :, 2] = ambient_b
        layer.matrix[:, :, 3] = 1.0

        # Update and render each ember
        for ember in self._embers:
            # Drift upward
            ember.y -= ember.velocity / self.fps
            # Slight horizontal drift
            ember.x += math.sin(t * 0.5 + ember.phase) * 0.02

            # Wrap at top
            if ember.y < -1:
                ember.y = height + 0.5
                ember.x = random.random() * width

            # Pulsing brightness
            brightness = base_bright + math.sin(t * pulse_spd + ember.phase) * 0.2

            # Random flare
            if random.random() < flare:
                brightness = 1.0

            brightness = max(0.0, min(1.0, brightness))

            # Render with Gaussian falloff
            radius_sq = ember.radius * ember.radius
            sigma_sq = radius_sq / 2.0

            for row in range(
                max(0, int(ember.y - ember.radius - 1)),
                min(height, int(ember.y + ember.radius + 2)),
            ):
                for col in range(
                    max(0, int(ember.x - ember.radius - 1)),
                    min(width, int(ember.x + ember.radius + 2)),
                ):
                    dx = col - ember.x
                    dy = row - ember.y
                    dist_sq = dx * dx + dy * dy

                    if dist_sq < radius_sq * 2:
                        glow = brightness * math.exp(-dist_sq / sigma_sq)
                        # Additive blend
                        existing = layer.matrix[row][col]
                        layer.matrix[row][col] = (
                            min(1.0, existing[0] + r * glow),
                            min(1.0, existing[1] + g * glow),
                            min(1.0, existing[2] + b * glow),
                            1.0,
                        )

        return True
