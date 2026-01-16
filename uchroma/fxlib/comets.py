"""
Comets - Streaking trails of light.

Bright points zoom horizontally across the keyboard leaving
glowing trails. Multiple comets at different speeds create
depth and motion.
"""

import math
import random
from dataclasses import dataclass, field

from traitlets import Float, Int, observe

from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorSchemeTrait

COMET_COLORS = ["#00ffff", "#ff00ff", "#ffff00", "#00ff88"]


@dataclass
class Comet:
    """A single comet with position, velocity, and trail."""

    x: float
    y: int
    speed: float
    color: tuple
    trail: list = field(default_factory=list)


class Comets(Renderer):
    """Streaking comets with glowing trails."""

    meta = RendererMeta(
        "Comets",
        "Bright streaks with glowing trails",
        "uchroma",
        "1.0",
    )

    # Configurable traits
    comet_count = Int(default_value=3, min=1, max=6).tag(config=True)
    speed = Float(default_value=1.5, min=0.5, max=4.0).tag(config=True)
    trail_length = Int(default_value=8, min=3, max=15).tag(config=True)
    trail_decay = Float(default_value=0.3, min=0.1, max=0.6).tag(config=True)
    head_brightness = Float(default_value=1.0, min=0.7, max=1.0).tag(config=True)

    color_scheme = ColorSchemeTrait(minlen=2, default_value=COMET_COLORS).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._comets: list[Comet] = []
        self._colors = []
        self.fps = 30

    def _spawn_comet(self, idx: int, off_screen: bool = True) -> Comet:
        """Create a new comet with randomized properties."""
        speed_var = 0.7 + random.random() * 0.6  # 0.7 to 1.3
        x = -self.trail_length - random.random() * 5 if off_screen else random.random() * self.width
        y = random.randint(0, self.height - 1)
        color = self._colors[idx % len(self._colors)]
        return Comet(x=x, y=y, speed=self.speed * speed_var, color=color.rgb)

    def _gen_colors(self):
        self._colors = list(ColorUtils.gradient(len(self.color_scheme) * 2, *self.color_scheme))

    @observe("color_scheme")
    def _scheme_changed(self, changed):
        self._gen_colors()

    @observe("comet_count")
    def _count_changed(self, changed):
        # Adjust comet list to match new count
        while len(self._comets) < self.comet_count:
            self._comets.append(self._spawn_comet(len(self._comets), off_screen=False))
        while len(self._comets) > self.comet_count:
            self._comets.pop()

    def init(self, frame):
        self._gen_colors()
        self._comets = [self._spawn_comet(i, off_screen=False) for i in range(self.comet_count)]
        return True

    async def draw(self, layer, timestamp):
        width = layer.width
        height = layer.height
        decay = self.trail_decay
        trail_len = self.trail_length
        head_bright = self.head_brightness

        # Clear layer
        layer.matrix.fill(0)

        for idx, comet in enumerate(self._comets):
            # Store current position in trail
            if 0 <= comet.x < width + trail_len:
                comet.trail.append((comet.x, comet.y))

            # Trim trail to max length
            while len(comet.trail) > trail_len:
                comet.trail.pop(0)

            # Move comet
            comet.x += comet.speed

            # Respawn if off screen
            if comet.x > width + trail_len:
                self._comets[idx] = self._spawn_comet(idx, off_screen=True)
                continue

            # Render trail with exponential decay
            for i, (tx, ty) in enumerate(comet.trail):
                col = int(tx)
                if 0 <= col < width and 0 <= ty < height:
                    age = len(comet.trail) - i
                    brightness = math.exp(-age * decay)
                    r, g, b = comet.color
                    # Additive blend
                    existing = layer.matrix[ty][col]
                    layer.matrix[ty][col] = (
                        min(1.0, existing[0] + r * brightness),
                        min(1.0, existing[1] + g * brightness),
                        min(1.0, existing[2] + b * brightness),
                        1.0,
                    )

            # Render bright head
            head_col = int(comet.x)
            if 0 <= head_col < width:
                layer.matrix[comet.y][head_col] = (
                    head_bright,
                    head_bright,
                    head_bright,
                    1.0,
                )

        return True
