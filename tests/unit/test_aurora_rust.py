#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust-backed Aurora effect."""

import numpy as np

from uchroma._native import draw_aurora


class TestDrawAurora:
    """Tests for the draw_aurora Rust function."""

    def test_draw_aurora_fills_matrix(self):
        """Aurora fills output matrix with non-zero values."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[0.0, 1.0, 0.5], [0.0, 0.8, 1.0], [0.7, 0.0, 1.0]], dtype=np.float64)

        draw_aurora(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            time=1.0,
            speed=1.0,
            drift=0.3,
            curtain_height=0.7,
            shimmer=0.3,
            color_drift=0.5,
            floor_glow=0.15,
        )

        # Should have some non-zero pixels
        assert np.any(matrix[:, :, :3] > 0)
        # Alpha should be set
        assert np.any(matrix[:, :, 3] > 0)

    def test_draw_aurora_respects_dimensions(self):
        """Aurora writes correct array shape."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)

        draw_aurora(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            time=0.0,
            speed=1.0,
            drift=0.3,
            curtain_height=0.7,
            shimmer=0.0,
            color_drift=0.5,
            floor_glow=0.0,
        )

        assert matrix.shape == (height, width, 4)

    def test_draw_aurora_empty_gradient_no_crash(self):
        """Empty gradient doesn't crash."""
        matrix = np.zeros((4, 10, 4), dtype=np.float64)
        gradient = np.zeros((0, 3), dtype=np.float64)

        # Should not raise
        draw_aurora(
            width=10,
            height=4,
            matrix=matrix,
            gradient=gradient,
            time=0.0,
            speed=1.0,
            drift=0.3,
            curtain_height=0.7,
            shimmer=0.0,
            color_drift=0.5,
            floor_glow=0.0,
        )
