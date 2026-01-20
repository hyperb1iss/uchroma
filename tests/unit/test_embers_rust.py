#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust-backed Embers effect."""

import numpy as np

from uchroma._native import draw_embers


class TestDrawEmbers:
    """Tests for the draw_embers Rust function."""

    def test_draw_embers_fills_matrix(self):
        """Embers fills output matrix with non-zero values."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        # Single particle at center
        particles = np.array([11.0, 3.0, 0.8, 2.0], dtype=np.float64)

        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=0.42,
            color_b=0.21,
            ambient_factor=0.05,
        )

        # Should have some non-zero pixels
        assert np.any(matrix[:, :, :3] > 0)
        # Alpha should be set
        assert np.all(matrix[:, :, 3] == 1.0)

    def test_draw_embers_respects_dimensions(self):
        """Embers writes correct array shape."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        particles = np.array([5.0, 2.0, 1.0, 1.5], dtype=np.float64)

        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=0.5,
            color_b=0.2,
            ambient_factor=0.0,
        )

        assert matrix.shape == (height, width, 4)

    def test_draw_embers_empty_particles_no_crash(self):
        """Empty particles array doesn't crash."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        particles = np.array([], dtype=np.float64)

        # Should not raise
        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=0.5,
            color_b=0.2,
            ambient_factor=0.05,
        )

        # Should just have ambient fill
        assert np.all(matrix[:, :, 3] == 1.0)

    def test_draw_embers_multiple_particles(self):
        """Multiple particles render without issues."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        # 3 particles: [x, y, brightness, radius] each
        particles = np.array(
            [
                5.0,
                2.0,
                0.8,
                2.0,  # particle 1
                15.0,
                4.0,
                1.0,
                1.5,  # particle 2
                10.0,
                1.0,
                0.6,
                2.5,  # particle 3
            ],
            dtype=np.float64,
        )

        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=0.42,
            color_b=0.21,
            ambient_factor=0.05,
        )

        # Should have brighter spots where particles are
        center_brightness = matrix[2, 5, 0]  # Near particle 1
        edge_brightness = matrix[0, 0, 0]  # Far from particles
        assert center_brightness > edge_brightness

    def test_draw_embers_gaussian_falloff(self):
        """Particle brightness falls off with distance."""
        width, height = 11, 11
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        # Single particle at center
        particles = np.array([5.0, 5.0, 1.0, 3.0], dtype=np.float64)

        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=1.0,
            color_b=1.0,
            ambient_factor=0.0,
        )

        # Center should be brightest
        center = matrix[5, 5, 0]
        # Adjacent pixel should be dimmer
        adjacent = matrix[5, 6, 0]
        # Edge should be dimmest
        edge = matrix[5, 10, 0]

        assert center > adjacent
        assert adjacent >= edge

    def test_draw_embers_ambient_warmth(self):
        """Ambient factor creates warm background."""
        width, height = 10, 10
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        particles = np.array([], dtype=np.float64)  # No particles

        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=0.5,
            color_b=0.25,
            ambient_factor=0.1,
        )

        # Check ambient scaling (G and B reduced for warm glow)
        assert np.allclose(matrix[:, :, 0], 0.1)  # R * 0.1
        assert np.allclose(matrix[:, :, 1], 0.03)  # G * 0.1 * 0.6
        assert np.allclose(matrix[:, :, 2], 0.01)  # B * 0.1 * 0.4

    def test_draw_embers_values_clamped(self):
        """Output values are clamped to 1.0 max."""
        width, height = 5, 5
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        # Very bright particle at center
        particles = np.array([2.0, 2.0, 10.0, 2.0], dtype=np.float64)

        draw_embers(
            width=width,
            height=height,
            matrix=matrix,
            particles=particles,
            color_r=1.0,
            color_g=1.0,
            color_b=1.0,
            ambient_factor=0.5,
        )

        # All values should be <= 1.0
        assert np.all(matrix[:, :, :3] <= 1.0)
