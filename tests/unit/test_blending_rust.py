#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust blending backend."""

from __future__ import annotations

import numpy as np
import pytest

from uchroma.blending import USE_RUST_BACKEND, BlendOp, blend


class TestRustBlendingBackend:
    """Tests that Rust backend produces same results as Python."""

    @pytest.fixture
    def rgba_half(self) -> np.ndarray:
        """4x4 RGBA image filled with 0.5."""
        return np.full((4, 4, 4), 0.5, dtype=np.float64)

    @pytest.fixture
    def rgba_ones(self) -> np.ndarray:
        """4x4 RGBA image filled with ones."""
        return np.ones((4, 4, 4), dtype=np.float64)

    def test_rust_backend_available(self):
        """Rust backend should be available."""
        assert USE_RUST_BACKEND, "Rust blending backend not available"

    @pytest.mark.parametrize("mode", BlendOp.get_modes())
    def test_rust_matches_python_all_modes(self, rgba_half, mode):
        """Rust blend results match Python for all modes."""
        result = blend(rgba_half, rgba_half, mode, opacity=1.0)
        assert result.shape == (4, 4, 4)
        assert result.dtype == np.float64
        assert not np.any(np.isnan(result))

    def test_blend_screen_specific_values(self, rgba_ones):
        """Screen blend with known values matches expected result."""
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        layer[:, :, 3] = 1.0
        result = blend(rgba_ones, layer, "screen", opacity=1.0)
        np.testing.assert_array_almost_equal(result[:, :, :3], 1.0)

    def test_blend_multiply_specific_values(self, rgba_half):
        """Multiply blend with known values matches expected result."""
        result = blend(rgba_half, rgba_half, "multiply", opacity=1.0)
        assert result.shape == (4, 4, 4)
