#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""
Directional wipe effect for testing key layouts.

Sweeps a color band across the matrix in a configurable direction.
Useful for verifying that LED coordinates are correctly mapped to
physical key positions.
"""

from traitlets import Float, Int, observe

from uchroma.colorlib import Color
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait


class Wipe(Renderer):
    """
    Directional color wipe for layout testing.

    Sweeps a colored band across the matrix, revealing whether
    keys are properly aligned. The wipe direction, speed, and
    colors are all configurable.

    Directions:
        0 = left to right
        1 = right to left
        2 = top to bottom
        3 = bottom to top
    """

    meta = RendererMeta(
        "Wipe",
        "Directional color wipe for layout testing",
        "UChroma Developers",
        "1.0",
    )

    # Wipe direction: 0=L→R, 1=R→L, 2=T→B, 3=B→T
    direction = Int(default_value=0, min=0, max=3).tag(config=True)

    # Band width in cells
    band_width = Int(default_value=3, min=1, max=10).tag(config=True)

    # Wipe speed (cells per second)
    speed = Float(default_value=5.0, min=0.5, max=30.0).tag(config=True)

    # Primary wipe color
    color = ColorTrait(default_value="cyan").tag(config=True)

    # Background color (revealed after wipe passes)
    trail_color = ColorTrait(default_value="black").tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._position = 0.0
        self._start_time = None
        self.fps = 30

    def init(self, frame):
        self._position = 0.0
        self._start_time = None
        return True

    @observe("direction", "speed")
    def _reset_position(self, change=None):
        self._position = 0.0
        self._start_time = None

    def _get_axis_length(self) -> int:
        """Get length of the axis we're wiping along."""
        if self.direction in (0, 1):  # Horizontal
            return self.width
        return self.height  # Vertical

    async def draw(self, layer, timestamp):
        if self._start_time is None:
            self._start_time = timestamp

        # Calculate current wipe position
        elapsed = timestamp - self._start_time
        axis_length = self._get_axis_length()
        total_travel = axis_length + self.band_width

        # Position wraps around
        self._position = (elapsed * self.speed) % total_travel

        # Convert color traits
        wipe_color = Color(self.color) if self.color else Color("cyan")
        bg_color = Color(self.trail_color) if self.trail_color else Color("black")

        for row in range(layer.height):
            for col in range(layer.width):
                # Determine coordinate along wipe axis
                if self.direction == 0:  # Left to right
                    coord = col
                elif self.direction == 1:  # Right to left
                    coord = self.width - 1 - col
                elif self.direction == 2:  # Top to bottom
                    coord = row
                else:  # Bottom to top
                    coord = self.height - 1 - row

                # Check if this cell is in the wipe band
                band_start = self._position - self.band_width
                band_end = self._position

                if band_start <= coord < band_end:
                    # In the wipe band - use gradient based on position in band
                    band_pos = (coord - band_start) / self.band_width
                    # Fade from trail color to wipe color
                    blended = bg_color.mix(wipe_color, band_pos, space="oklch")
                    layer.put(row, col, blended)
                elif coord < band_start:
                    # Behind the wipe - show trail/background
                    layer.put(row, col, bg_color)
                else:
                    # Ahead of the wipe - show wipe color (waiting to be revealed)
                    layer.put(row, col, wipe_color)

        return True
