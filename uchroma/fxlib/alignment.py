#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""
Alignment effect for keyboard bringup and key mapping.

Shows a repeating color pattern across the matrix with a highlighted
cursor position. Used by the key configuration tool to verify that
the LED matrix coordinates match physical key positions.
"""

from traitlets import Int, observe

from uchroma.colorlib import Color
from uchroma.renderer import Renderer, RendererMeta

# Column colors cycle through this palette
COLUMN_COLORS = [
    Color.NewFromHsv(0, 1.0, 1.0),  # Red
    Color.NewFromHsv(120, 1.0, 1.0),  # Green
    Color.NewFromHsv(240, 1.0, 1.0),  # Blue
    Color.NewFromHsv(60, 1.0, 1.0),  # Yellow
    Color.NewFromHsv(180, 1.0, 1.0),  # Cyan
    Color.NewFromHsv(300, 1.0, 1.0),  # Magenta
]

CURSOR_COLOR = Color.NewFromHsv(0, 0, 1.0)  # White


class Alignment(Renderer):
    """
    Alignment effect for key mapping tool.

    Displays a repeating column color pattern with a white cursor
    at the current position. The cursor can be moved by updating
    the cur_row and cur_col traits.
    """

    meta = RendererMeta(
        "Alignment",
        "Key mapping alignment pattern",
        "UChroma Developers",
        "1.0",
    )

    # Cursor position (row, col)
    cur_row = Int(default_value=0, min=0).tag(config=True)
    cur_col = Int(default_value=0, min=0).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fps = 30  # Responsive cursor movement

    def init(self, frame):
        return True

    @observe("cur_row", "cur_col")
    def _cursor_moved(self, change=None):
        # Clamp cursor to valid range
        if hasattr(self, "height") and self.height > 0:
            self.cur_row = max(0, min(self.cur_row, self.height - 1))
        if hasattr(self, "width") and self.width > 0:
            self.cur_col = max(0, min(self.cur_col, self.width - 1))

    async def draw(self, layer, timestamp):
        num_colors = len(COLUMN_COLORS)
        cur_r, cur_c = self.cur_row, self.cur_col

        for row in range(layer.height):
            for col in range(layer.width):
                if row == cur_r and col == cur_c:
                    # Cursor position - bright white
                    layer.put(row, col, CURSOR_COLOR)
                else:
                    # Column color pattern
                    color_idx = col % num_colors
                    layer.put(row, col, COLUMN_COLORS[color_idx])

        return True
