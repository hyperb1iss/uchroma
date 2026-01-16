#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Matrix Preview Widget

Animated LED matrix visualization using Cairo.
"""

import math

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

import numpy as np  # noqa: E402
from gi.repository import Gtk  # noqa: E402


class MatrixPreview(Gtk.DrawingArea):
    """Animated LED matrix preview with glow effects."""

    __gtype_name__ = "UChromaMatrixPreview"

    # SilkCircuit colors
    BACKGROUND = (0.05, 0.05, 0.05)
    CELL_OFF = (0.1, 0.1, 0.1)
    GLOW_PURPLE = (0.88, 0.21, 1.0, 0.15)

    def __init__(self, rows: int = 6, cols: int = 22):
        super().__init__()

        self.rows = rows
        self.cols = cols
        self.frame_data = None
        self.active_cells = None
        self.cell_radius = 3
        self.cell_gap = 2
        self.glow_enabled = True

        # Set size request based on matrix
        self.set_content_width(cols * 28 + 40)
        self.set_content_height(rows * 28 + 40)
        self.set_hexpand(True)
        self.set_vexpand(False)

        # Drawing
        self.set_draw_func(self._draw)

        # Styling
        self.add_css_class("matrix-preview")

    def set_matrix_size(self, rows: int, cols: int):
        """Update matrix dimensions."""
        self.rows = rows
        self.cols = cols
        self.set_content_width(cols * 28 + 40)
        self.set_content_height(rows * 28 + 40)
        self.queue_draw()

    def set_active_cells(self, cells: set[tuple[int, int]] | None):
        """Set active cell positions to render (None = all)."""
        self.active_cells = cells
        self.queue_draw()

    def update_frame(self, frame: np.ndarray):
        """Update with new frame data. Shape: (rows, cols, 3) or (rows, cols, 4)."""
        self.frame_data = frame
        self.queue_draw()

    def clear(self):
        """Clear the display."""
        self.frame_data = None
        self.queue_draw()

    def _draw(self, area, cr, width, height):
        """Cairo draw function."""
        # Background with subtle gradient
        self._draw_background(cr, width, height)

        # Calculate cell dimensions
        padding = 20
        available_w = width - padding * 2
        available_h = height - padding * 2

        cell_w = available_w / self.cols
        cell_h = available_h / self.rows

        # Draw glow layer first (if enabled)
        if self.glow_enabled and self.frame_data is not None:
            self._draw_glow_layer(cr, padding, cell_w, cell_h)

        # Draw cells
        for row in range(self.rows):
            for col in range(self.cols):
                if self.active_cells is not None and (row, col) not in self.active_cells:
                    continue

                x = padding + col * cell_w
                y = padding + row * cell_h

                # Get color
                if (
                    self.frame_data is not None
                    and row < self.frame_data.shape[0]
                    and col < self.frame_data.shape[1]
                ):
                    pixel = self.frame_data[row, col]
                    if self.frame_data.dtype == np.uint8:
                        r, g, b = pixel[0] / 255, pixel[1] / 255, pixel[2] / 255
                    else:
                        r, g, b = pixel[0], pixel[1], pixel[2]
                else:
                    r, g, b = self.CELL_OFF

                self._draw_cell(cr, x, y, cell_w, cell_h, r, g, b)

        # Border frame
        self._draw_border(cr, width, height, padding)

    def _draw_background(self, cr, width, height):
        """Draw gradient background."""
        # Radial gradient from center
        cx, cy = width / 2, height / 2
        pattern = cairo.RadialGradient(cx, cy, 0, cx, cy, max(width, height) / 2)
        pattern.add_color_stop_rgb(0, 0.08, 0.06, 0.10)  # Subtle purple tint
        pattern.add_color_stop_rgb(1, 0.04, 0.04, 0.04)

        cr.set_source(pattern)
        self._rounded_rect(cr, 0, 0, width, height, 12)
        cr.fill()

    def _draw_glow_layer(self, cr, padding, cell_w, cell_h):
        """Draw subtle glow behind bright cells."""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.frame_data is None:
                    continue

                pixel = self.frame_data[row, col]
                if self.frame_data.dtype == np.uint8:
                    r, g, b = pixel[0] / 255, pixel[1] / 255, pixel[2] / 255
                else:
                    r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])

                # Only glow for bright cells
                brightness = (r + g + b) / 3
                if brightness < 0.3:
                    continue

                x = padding + col * cell_w + cell_w / 2
                y = padding + row * cell_h + cell_h / 2
                glow_radius = max(cell_w, cell_h) * 1.2

                # Radial gradient glow
                pattern = cairo.RadialGradient(x, y, 0, x, y, glow_radius)
                pattern.add_color_stop_rgba(0, r, g, b, brightness * 0.4)
                pattern.add_color_stop_rgba(1, r, g, b, 0)

                cr.set_source(pattern)
                cr.arc(x, y, glow_radius, 0, 2 * math.pi)
                cr.fill()

    def _draw_cell(self, cr, x, y, cell_w, cell_h, r, g, b):
        """Draw a single LED cell."""
        gap = self.cell_gap
        radius = self.cell_radius

        # Cell background (slightly darker than color for depth)
        cr.set_source_rgb(r * 0.3, g * 0.3, b * 0.3)
        self._rounded_rect(cr, x + gap, y + gap, cell_w - gap * 2, cell_h - gap * 2, radius)
        cr.fill()

        # Main cell color
        cr.set_source_rgb(r, g, b)
        inset = gap + 1
        self._rounded_rect(
            cr, x + inset, y + inset, cell_w - inset * 2, cell_h - inset * 2, radius - 1
        )
        cr.fill()

        # Highlight (top-left shine)
        if r + g + b > 0.2:
            cr.set_source_rgba(1, 1, 1, 0.15)
            self._rounded_rect(
                cr,
                x + inset,
                y + inset,
                (cell_w - inset * 2) * 0.6,
                (cell_h - inset * 2) * 0.4,
                radius - 1,
            )
            cr.fill()

    def _draw_border(self, cr, width, height, padding):
        """Draw subtle border frame."""
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.set_line_width(1)
        self._rounded_rect(
            cr, padding - 2, padding - 2, width - padding * 2 + 4, height - padding * 2 + 4, 8
        )
        cr.stroke()

    def _rounded_rect(self, cr, x, y, w, h, r):
        """Draw a rounded rectangle path."""
        cr.new_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
