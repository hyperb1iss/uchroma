#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust-backed Kaleidoscope effect."""

import numpy as np

from uchroma._native import compute_polar_map, draw_kaleidoscope


class TestComputePolarMap:
    """Tests for the compute_polar_map Rust function."""

    def test_compute_polar_map_returns_correct_length(self):
        """Polar map has 2 values per pixel (angle, radius)."""
        width, height = 22, 6
        polar_map = compute_polar_map(width, height)
        assert len(polar_map) == width * height * 2

    def test_compute_polar_map_angles_in_range(self):
        """Angles should be in [-pi, pi] range."""
        import math

        width, height = 10, 8
        polar_map = compute_polar_map(width, height)

        # Extract angles (every other element starting at 0)
        angles = polar_map[::2]
        assert np.all(angles >= -math.pi)
        assert np.all(angles <= math.pi)

    def test_compute_polar_map_center_has_small_radius(self):
        """Center pixel should have relatively small radius."""
        # Use square dimensions to simplify aspect ratio
        width, height = 10, 10
        polar_map = compute_polar_map(width, height)

        # Center pixel index (between pixels for even dimensions)
        center_row = height // 2
        center_col = width // 2
        center_idx = center_row * width + center_col

        # Radius is at index center_idx * 2 + 1
        radius = polar_map[center_idx * 2 + 1]
        # Center should have smaller radius than corners
        corner_idx = 0  # Top-left corner
        corner_radius = polar_map[corner_idx * 2 + 1]
        assert radius < corner_radius


class TestDrawKaleidoscope:
    """Tests for the draw_kaleidoscope Rust function."""

    def test_draw_kaleidoscope_fills_matrix(self):
        """Kaleidoscope fills output matrix with non-zero values."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 0.0, 0.5], [0.0, 1.0, 0.5], [0.5, 0.0, 1.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        draw_kaleidoscope(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=1.0,
            symmetry=6,
            rotation_speed=0.5,
            pattern_mode=0,  # spiral
            ring_frequency=0.5,
            spiral_twist=2.0,
            hue_rotation=30.0,
        )

        # Should have some non-zero pixels
        assert np.any(matrix[:, :, :3] > 0)
        # Alpha should be set to 1.0
        assert np.all(matrix[:, :, 3] == 1.0)

    def test_draw_kaleidoscope_respects_dimensions(self):
        """Kaleidoscope writes correct array shape."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        draw_kaleidoscope(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=0.0,
            symmetry=6,
            rotation_speed=0.5,
            pattern_mode=0,
            ring_frequency=0.5,
            spiral_twist=2.0,
            hue_rotation=30.0,
        )

        assert matrix.shape == (height, width, 4)

    def test_draw_kaleidoscope_empty_gradient_no_crash(self):
        """Empty gradient doesn't crash."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.zeros((0, 3), dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        # Should not raise
        draw_kaleidoscope(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=0.0,
            symmetry=6,
            rotation_speed=0.5,
            pattern_mode=0,
            ring_frequency=0.5,
            spiral_twist=2.0,
            hue_rotation=30.0,
        )

    def test_draw_kaleidoscope_pattern_modes(self):
        """All pattern modes produce output."""
        width, height = 22, 6
        gradient = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        for mode in (0, 1, 2):  # spiral, rings, waves
            matrix = np.zeros((height, width, 4), dtype=np.float64)
            draw_kaleidoscope(
                width=width,
                height=height,
                matrix=matrix,
                gradient=gradient,
                polar_map=polar_map,
                time=1.0,
                symmetry=6,
                rotation_speed=0.5,
                pattern_mode=mode,
                ring_frequency=0.5,
                spiral_twist=2.0,
                hue_rotation=30.0,
            )
            assert np.any(matrix[:, :, :3] > 0), f"Pattern mode {mode} produced no output"

    def test_draw_kaleidoscope_brightness_range(self):
        """Brightness should be in 0.3-1.0 range (never fully dark)."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        # Single white color so brightness = pixel value
        gradient = np.array([[1.0, 1.0, 1.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        draw_kaleidoscope(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=0.5,
            symmetry=6,
            rotation_speed=0.5,
            pattern_mode=0,
            ring_frequency=0.5,
            spiral_twist=2.0,
            hue_rotation=30.0,
        )

        # RGB values should be between 0.3 and 1.0 (brightness range)
        rgb = matrix[:, :, :3]
        assert np.all(rgb >= 0.29)  # Allow small float tolerance
        assert np.all(rgb <= 1.01)
