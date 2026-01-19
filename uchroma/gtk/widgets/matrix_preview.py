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

        # Ambient halo (color wash based on frame content)
        if self.glow_enabled:
            self._draw_ambient_halo(cr, width, height)

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
        """Draw gradient background with vignette and subtle texture."""
        # Vignette-style radial gradient
        cx, cy = width / 2, height / 2
        max_dim = max(width, height)

        pattern = cairo.RadialGradient(cx, cy, 0, cx, cy, max_dim * 0.7)
        # Center: subtle purple tint (SilkCircuit aesthetic)
        pattern.add_color_stop_rgb(0, 0.06, 0.04, 0.08)
        # Edge: near black
        pattern.add_color_stop_rgb(1, 0.02, 0.02, 0.02)

        cr.set_source(pattern)
        self._rounded_rect(cr, 0, 0, width, height, 12)
        cr.fill()

        # Subtle grid pattern for texture (adds visual interest)
        cr.set_source_rgba(1, 1, 1, 0.012)
        cr.set_line_width(0.5)
        grid_size = 8
        for gx in range(0, int(width), grid_size):
            cr.move_to(gx, 0)
            cr.line_to(gx, height)
        for gy in range(0, int(height), grid_size):
            cr.move_to(0, gy)
            cr.line_to(width, gy)
        cr.stroke()

    def _draw_glow_layer(self, cr, padding, cell_w, cell_h):
        """Draw bloom/glow layer with two passes for depth."""
        if self.frame_data is None:
            return

        # Pass 1: Wide diffuse bloom for overall ambiance
        for row in range(self.rows):
            for col in range(self.cols):
                pixel = self.frame_data[row, col]
                if self.frame_data.dtype == np.uint8:
                    r, g, b = pixel[0] / 255, pixel[1] / 255, pixel[2] / 255
                else:
                    r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])

                # Calculate perceptual brightness (rec. 709 luma)
                brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b
                if brightness < 0.25:
                    continue

                x = padding + col * cell_w + cell_w / 2
                y = padding + row * cell_h + cell_h / 2

                # Wide diffuse bloom
                wide_radius = max(cell_w, cell_h) * 2.0
                pattern = cairo.RadialGradient(x, y, 0, x, y, wide_radius)
                pattern.add_color_stop_rgba(0, r, g, b, brightness * 0.25)
                pattern.add_color_stop_rgba(0.3, r, g, b, brightness * 0.12)
                pattern.add_color_stop_rgba(1, r, g, b, 0)

                cr.set_source(pattern)
                cr.arc(x, y, wide_radius, 0, 2 * math.pi)
                cr.fill()

        # Pass 2: Tight core glow for very bright cells only
        for row in range(self.rows):
            for col in range(self.cols):
                pixel = self.frame_data[row, col]
                if self.frame_data.dtype == np.uint8:
                    r, g, b = pixel[0] / 255, pixel[1] / 255, pixel[2] / 255
                else:
                    r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])

                brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b
                if brightness < 0.5:  # Only very bright cells get core glow
                    continue

                x = padding + col * cell_w + cell_w / 2
                y = padding + row * cell_h + cell_h / 2

                # Tight bright core
                core_radius = max(cell_w, cell_h) * 0.8
                pattern = cairo.RadialGradient(x, y, 0, x, y, core_radius)
                # Boost the color slightly for the core
                boost = 1.2
                pattern.add_color_stop_rgba(
                    0, min(r * boost, 1), min(g * boost, 1), min(b * boost, 1), brightness * 0.5
                )
                pattern.add_color_stop_rgba(0.5, r, g, b, brightness * 0.2)
                pattern.add_color_stop_rgba(1, r, g, b, 0)

                cr.set_source(pattern)
                cr.arc(x, y, core_radius, 0, 2 * math.pi)
                cr.fill()

    def _draw_cell(self, cr, x, y, cell_w, cell_h, r, g, b):
        """Draw a single LED cell with dome lighting effect."""
        gap = self.cell_gap
        radius = self.cell_radius
        brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Drop shadow for depth (only for lit cells)
        if brightness > 0.1:
            cr.set_source_rgba(0, 0, 0, 0.3)
            self._rounded_rect(
                cr, x + gap + 1, y + gap + 2, cell_w - gap * 2, cell_h - gap * 2, radius
            )
            cr.fill()

        # Outer bezel (dark ring around the LED)
        bezel_darkness = 0.15
        cr.set_source_rgb(r * bezel_darkness, g * bezel_darkness, b * bezel_darkness)
        self._rounded_rect(cr, x + gap, y + gap, cell_w - gap * 2, cell_h - gap * 2, radius)
        cr.fill()

        # LED cavity (slightly recessed)
        cr.set_source_rgb(r * 0.25, g * 0.25, b * 0.25)
        inset = gap + 1
        self._rounded_rect(
            cr, x + inset, y + inset, cell_w - inset * 2, cell_h - inset * 2, radius - 1
        )
        cr.fill()

        # Main LED surface with radial gradient for dome effect
        inner_inset = inset + 1
        inner_w = cell_w - inner_inset * 2
        inner_h = cell_h - inner_inset * 2
        cx = x + inner_inset + inner_w / 2
        cy = y + inner_inset + inner_h / 2
        inner_r = min(inner_w, inner_h) / 2

        # Offset gradient center for 3D dome effect (light from top-left)
        offset_x = cx - inner_r * 0.3
        offset_y = cy - inner_r * 0.3

        pattern = cairo.RadialGradient(offset_x, offset_y, 0, cx, cy, inner_r * 1.2)
        # Brighter center (light source)
        pattern.add_color_stop_rgb(0, min(1, r * 1.4), min(1, g * 1.4), min(1, b * 1.4))
        pattern.add_color_stop_rgb(0.6, r, g, b)
        pattern.add_color_stop_rgb(1, r * 0.6, g * 0.6, b * 0.6)

        cr.set_source(pattern)
        self._rounded_rect(
            cr, x + inner_inset, y + inner_inset, inner_w, inner_h, radius - 2
        )
        cr.fill()

        # Specular highlight (top-left reflection) — only on lit cells
        if brightness > 0.15:
            spec_x = x + inner_inset + inner_w * 0.15
            spec_y = y + inner_inset + inner_h * 0.15
            spec_r = min(inner_w, inner_h) * 0.2

            # Gradient for natural specular falloff
            spec_pattern = cairo.RadialGradient(spec_x, spec_y, 0, spec_x, spec_y, spec_r)
            spec_pattern.add_color_stop_rgba(0, 1, 1, 1, 0.35 * brightness)
            spec_pattern.add_color_stop_rgba(1, 1, 1, 1, 0)

            cr.set_source(spec_pattern)
            cr.arc(spec_x, spec_y, spec_r, 0, 2 * math.pi)
            cr.fill()

        # Inner glow for very bright cells — makes them feel like they're emitting light
        if brightness > 0.6:
            glow_strength = (brightness - 0.6) / 0.4  # 0 to 1 for brightness 0.6 to 1.0

            glow_pattern = cairo.RadialGradient(cx, cy, 0, cx, cy, inner_r * 0.8)
            # Boosted white core
            glow_pattern.add_color_stop_rgba(0, 1, 1, 1, glow_strength * 0.25)
            glow_pattern.add_color_stop_rgba(0.4, r, g, b, glow_strength * 0.1)
            glow_pattern.add_color_stop_rgba(1, r, g, b, 0)

            cr.set_source(glow_pattern)
            cr.arc(cx, cy, inner_r * 0.8, 0, 2 * math.pi)
            cr.fill()

    def _draw_border(self, cr, width, height, padding):
        """Draw border frame with subtle glow."""
        # Inner shadow line
        cr.set_source_rgba(0, 0, 0, 0.3)
        cr.set_line_width(2)
        self._rounded_rect(
            cr, padding - 1, padding - 1, width - padding * 2 + 2, height - padding * 2 + 2, 8
        )
        cr.stroke()

        # Outer highlight
        cr.set_source_rgba(1, 1, 1, 0.04)
        cr.set_line_width(1)
        self._rounded_rect(
            cr, padding - 3, padding - 3, width - padding * 2 + 6, height - padding * 2 + 6, 10
        )
        cr.stroke()

    def _draw_ambient_halo(self, cr, width, height):
        """Draw ambient color wash based on average frame content."""
        if self.frame_data is None:
            return

        # Sample average color from frame
        avg_r = float(np.mean(self.frame_data[:, :, 0]))
        avg_g = float(np.mean(self.frame_data[:, :, 1]))
        avg_b = float(np.mean(self.frame_data[:, :, 2]))

        # Normalize if uint8
        if self.frame_data.dtype == np.uint8:
            avg_r, avg_g, avg_b = avg_r / 255, avg_g / 255, avg_b / 255

        # Only glow if there's meaningful color
        brightness = 0.2126 * avg_r + 0.7152 * avg_g + 0.0722 * avg_b
        if brightness < 0.1:
            return

        # Large outer halo
        cx, cy = width / 2, height / 2
        max_dim = max(width, height)

        pattern = cairo.RadialGradient(cx, cy, 0, cx, cy, max_dim * 0.6)
        pattern.add_color_stop_rgba(0, avg_r, avg_g, avg_b, brightness * 0.12)
        pattern.add_color_stop_rgba(0.5, avg_r, avg_g, avg_b, brightness * 0.04)
        pattern.add_color_stop_rgba(1, avg_r, avg_g, avg_b, 0)

        cr.set_source(pattern)
        cr.paint()

    def _rounded_rect(self, cr, x, y, w, h, r):
        """Draw a rounded rectangle path."""
        cr.new_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
