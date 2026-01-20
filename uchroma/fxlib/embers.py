#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Embers - Glowing particle field effect.

A field of warm glowing particles that drift slowly upward,
pulse in brightness, and occasionally flare brighter.
Like embers in a dying fire — warm and well-lit.

Particle state management stays in Python; Rust handles the hot rendering loop.
"""

import math
import random
from dataclasses import dataclass

import numpy as np
from traitlets import Float, Int, observe

from uchroma._native import draw_embers as _rust_draw_embers
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

    def _calc_brightness(self, ember: Ember) -> float:
        """Calculate brightness for an ember (pulse + flare)."""
        brightness = (
            self.base_brightness + math.sin(self._time * self.pulse_speed + ember.phase) * 0.2
        )

        # Random flare
        if random.random() < self.flare_chance:
            brightness = 1.0

        return max(0.0, min(1.0, brightness))

    async def draw(self, layer, timestamp):
        self._time += 1.0 / self.fps

        width = layer.width
        height = layer.height
        t = self._time

        # Update particle positions (stays in Python)
        for ember in self._embers:
            # Drift upward
            ember.y -= ember.velocity / self.fps
            # Slight horizontal drift
            ember.x += math.sin(t * 0.5 + ember.phase) * 0.02

            # Wrap at top
            if ember.y < -1:
                ember.y = height + 0.5
                ember.x = random.random() * width

        # Pack particle data for Rust: [x, y, brightness, radius, ...]
        particles = np.array(
            [
                val
                for ember in self._embers
                for val in (ember.x, ember.y, self._calc_brightness(ember), ember.radius)
            ],
            dtype=np.float64,
        )

        r, g, b = self._color_rgb
        _rust_draw_embers(
            width=width,
            height=height,
            matrix=layer.matrix,
            particles=particles,
            color_r=r,
            color_g=g,
            color_b=b,
            ambient_factor=0.05,
        )

        return True
