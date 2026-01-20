#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust-backed Nebula effect."""

import numpy as np

from uchroma._native import draw_nebula


class TestDrawNebula:
    """Tests for the draw_nebula Rust function."""

    def test_draw_nebula_fills_matrix(self):
        """Nebula fills output matrix with non-zero values."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array(
            [[0.29, 0.0, 0.5], [1.0, 0.0, 0.43], [0.0, 0.83, 1.0], [0.0, 1.0, 0.53]],
            dtype=np.float64,
        )
        noise_table = np.random.rand(64, 64).astype(np.float64)

        draw_nebula(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            noise_table=noise_table,
            time=1.0,
            drift_speed=0.3,
            scale=0.15,
            octaves=2,
            contrast=0.6,
            base_brightness=0.5,
            color_shift=0.3,
        )

        # Should have filled pixels
        assert np.any(matrix[:, :, :3] > 0)
        # Alpha should be 1.0 for all pixels
        assert np.all(matrix[:, :, 3] == 1.0)

    def test_draw_nebula_respects_dimensions(self):
        """Nebula writes correct array shape."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)
        noise_table = np.random.rand(64, 64).astype(np.float64)

        draw_nebula(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            noise_table=noise_table,
            time=0.0,
            drift_speed=0.3,
            scale=0.15,
            octaves=2,
            contrast=0.6,
            base_brightness=0.5,
            color_shift=0.0,
        )

        assert matrix.shape == (height, width, 4)

    def test_draw_nebula_empty_gradient_no_crash(self):
        """Empty gradient doesn't crash."""
        matrix = np.zeros((4, 10, 4), dtype=np.float64)
        gradient = np.zeros((0, 3), dtype=np.float64)
        noise_table = np.random.rand(64, 64).astype(np.float64)

        # Should not raise
        draw_nebula(
            width=10,
            height=4,
            matrix=matrix,
            gradient=gradient,
            noise_table=noise_table,
            time=0.0,
            drift_speed=0.3,
            scale=0.15,
            octaves=2,
            contrast=0.6,
            base_brightness=0.5,
            color_shift=0.0,
        )

    def test_draw_nebula_time_animation(self):
        """Nebula output changes with time parameter."""
        width, height = 8, 4
        gradient = np.array([[0.5, 0.0, 0.5], [0.0, 0.5, 0.5]], dtype=np.float64)
        noise_table = np.random.rand(64, 64).astype(np.float64)

        matrix1 = np.zeros((height, width, 4), dtype=np.float64)
        matrix2 = np.zeros((height, width, 4), dtype=np.float64)

        draw_nebula(
            width=width,
            height=height,
            matrix=matrix1,
            gradient=gradient,
            noise_table=noise_table,
            time=0.0,
            drift_speed=0.3,
            scale=0.15,
            octaves=2,
            contrast=0.6,
            base_brightness=0.5,
            color_shift=0.3,
        )

        draw_nebula(
            width=width,
            height=height,
            matrix=matrix2,
            gradient=gradient,
            noise_table=noise_table,
            time=5.0,
            drift_speed=0.3,
            scale=0.15,
            octaves=2,
            contrast=0.6,
            base_brightness=0.5,
            color_shift=0.3,
        )

        # Frames should differ at different times
        assert not np.allclose(matrix1, matrix2)

    def test_draw_nebula_brightness_clamped(self):
        """Brightness values stay within valid range."""
        width, height = 10, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 1.0, 1.0]], dtype=np.float64)
        noise_table = np.random.rand(64, 64).astype(np.float64)

        draw_nebula(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            noise_table=noise_table,
            time=2.5,
            drift_speed=1.0,
            scale=0.3,
            octaves=3,
            contrast=1.0,
            base_brightness=0.7,
            color_shift=1.0,
        )

        # All RGB values should be in [0, 1] range
        assert np.all(matrix[:, :, :3] >= 0.0)
        assert np.all(matrix[:, :, :3] <= 1.0)
