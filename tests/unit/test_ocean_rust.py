#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust-backed Ocean effect."""

import numpy as np

from uchroma._native import draw_ocean


class TestDrawOcean:
    """Tests for the draw_ocean Rust function."""

    def test_draw_ocean_fills_matrix(self):
        """Ocean fills output matrix."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array(
            [
                [0.0, 0.1, 0.2],
                [0.0, 0.5, 0.8],
                [0.5, 0.9, 1.0],
                [1.0, 1.0, 1.0],
            ],
            dtype=np.float64,
        )

        draw_ocean(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            time=1.0,
            wave_speed=1.0,
            wave_height=0.5,
            foam_threshold=0.5,
            caustic_intensity=0.3,
        )

        assert np.any(matrix[:, :, :3] > 0)
        # Ocean always sets alpha to 1.0
        assert np.all(matrix[:, :, 3] == 1.0)

    def test_draw_ocean_respects_dimensions(self):
        """Ocean writes correct array shape."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[0.0, 0.3, 0.6], [0.0, 0.6, 1.0]], dtype=np.float64)

        draw_ocean(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            time=0.0,
            wave_speed=1.0,
            wave_height=0.5,
            foam_threshold=0.5,
            caustic_intensity=0.3,
        )

        assert matrix.shape == (height, width, 4)

    def test_draw_ocean_empty_gradient_no_crash(self):
        """Empty gradient doesn't crash."""
        matrix = np.zeros((4, 10, 4), dtype=np.float64)
        gradient = np.zeros((0, 3), dtype=np.float64)

        draw_ocean(
            width=10,
            height=4,
            matrix=matrix,
            gradient=gradient,
            time=0.0,
            wave_speed=1.0,
            wave_height=0.5,
            foam_threshold=0.5,
            caustic_intensity=0.3,
        )
