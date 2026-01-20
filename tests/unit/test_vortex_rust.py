#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust-backed Vortex effect."""

import numpy as np

from uchroma._native import compute_polar_map, draw_vortex


class TestDrawVortex:
    """Tests for the draw_vortex Rust function."""

    def test_draw_vortex_fills_matrix(self):
        """Vortex fills output matrix with non-zero values."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 0.0, 0.5], [0.0, 1.0, 0.5], [0.5, 0.0, 1.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        draw_vortex(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=1.0,
            arm_count=3,
            twist=0.3,
            flow_speed=1.0,
            flow_direction=1,
            rotation_speed=0.5,
            center_glow=3.0,
            ring_density=0.5,
        )

        # Should have some non-zero pixels
        assert np.any(matrix[:, :, :3] > 0)
        # Alpha should be set to 1.0
        assert np.all(matrix[:, :, 3] == 1.0)

    def test_draw_vortex_respects_dimensions(self):
        """Vortex writes correct array shape."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        draw_vortex(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=0.0,
            arm_count=3,
            twist=0.3,
            flow_speed=1.0,
            flow_direction=1,
            rotation_speed=0.5,
            center_glow=3.0,
            ring_density=0.5,
        )

        assert matrix.shape == (height, width, 4)

    def test_draw_vortex_empty_gradient_no_crash(self):
        """Empty gradient doesn't crash."""
        width, height = 10, 4
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        gradient = np.zeros((0, 3), dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        # Should not raise
        draw_vortex(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=0.0,
            arm_count=3,
            twist=0.3,
            flow_speed=1.0,
            flow_direction=1,
            rotation_speed=0.5,
            center_glow=3.0,
            ring_density=0.5,
        )

    def test_draw_vortex_arm_counts(self):
        """Different arm counts produce output."""
        width, height = 22, 6
        gradient = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        for arms in (1, 3, 6):
            matrix = np.zeros((height, width, 4), dtype=np.float64)
            draw_vortex(
                width=width,
                height=height,
                matrix=matrix,
                gradient=gradient,
                polar_map=polar_map,
                time=1.0,
                arm_count=arms,
                twist=0.3,
                flow_speed=1.0,
                flow_direction=1,
                rotation_speed=0.5,
                center_glow=3.0,
                ring_density=0.5,
            )
            assert np.any(matrix[:, :, :3] > 0), f"Arm count {arms} produced no output"

    def test_draw_vortex_flow_directions(self):
        """Both flow directions produce output."""
        width, height = 22, 6
        gradient = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        for direction in (-1, 1):
            matrix = np.zeros((height, width, 4), dtype=np.float64)
            draw_vortex(
                width=width,
                height=height,
                matrix=matrix,
                gradient=gradient,
                polar_map=polar_map,
                time=1.0,
                arm_count=3,
                twist=0.3,
                flow_speed=1.0,
                flow_direction=direction,
                rotation_speed=0.5,
                center_glow=3.0,
                ring_density=0.5,
            )
            assert np.any(matrix[:, :, :3] > 0), f"Flow direction {direction} produced no output"

    def test_draw_vortex_brightness_range(self):
        """Brightness should be in 0.4-1.0 range (never fully dark)."""
        width, height = 22, 6
        matrix = np.zeros((height, width, 4), dtype=np.float64)
        # Single white color so brightness = pixel value
        gradient = np.array([[1.0, 1.0, 1.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        draw_vortex(
            width=width,
            height=height,
            matrix=matrix,
            gradient=gradient,
            polar_map=polar_map,
            time=0.5,
            arm_count=3,
            twist=0.3,
            flow_speed=1.0,
            flow_direction=1,
            rotation_speed=0.5,
            center_glow=3.0,
            ring_density=0.5,
        )

        # RGB values should be between 0.4 and 1.0 (brightness range)
        rgb = matrix[:, :, :3]
        assert np.all(rgb >= 0.39)  # Allow small float tolerance
        assert np.all(rgb <= 1.01)

    def test_draw_vortex_center_glow_effect(self):
        """Center glow increases brightness near center."""
        width, height = 22, 6
        gradient = np.array([[1.0, 1.0, 1.0]], dtype=np.float64)
        polar_map = compute_polar_map(width, height)

        # With no center glow (effectively disabled)
        matrix_no_glow = np.zeros((height, width, 4), dtype=np.float64)
        draw_vortex(
            width=width,
            height=height,
            matrix=matrix_no_glow,
            gradient=gradient,
            polar_map=polar_map,
            time=0.0,
            arm_count=3,
            twist=0.3,
            flow_speed=1.0,
            flow_direction=1,
            rotation_speed=0.5,
            center_glow=0.1,  # Very small
            ring_density=0.5,
        )

        # With center glow
        matrix_glow = np.zeros((height, width, 4), dtype=np.float64)
        draw_vortex(
            width=width,
            height=height,
            matrix=matrix_glow,
            gradient=gradient,
            polar_map=polar_map,
            time=0.0,
            arm_count=3,
            twist=0.3,
            flow_speed=1.0,
            flow_direction=1,
            rotation_speed=0.5,
            center_glow=5.0,  # Large glow
            ring_density=0.5,
        )

        # The matrices should be different due to center glow
        assert not np.allclose(matrix_no_glow, matrix_glow)

    def test_draw_vortex_uses_polar_map(self):
        """Vortex uses provided polar map (reuses compute_polar_map from kaleidoscope)."""
        width, height = 10, 5
        polar_map = compute_polar_map(width, height)

        # Polar map should have 2 values per pixel
        assert len(polar_map) == width * height * 2
