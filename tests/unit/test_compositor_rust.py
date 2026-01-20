#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust compositor backend."""

from __future__ import annotations

import numpy as np

from uchroma.color import ColorUtils


class TestRustCompositor:
    """Tests that Rust compositor produces correct results."""

    def test_rgba2rgb_black_background(self):
        """rgba2rgb with black background."""
        arr = np.full((4, 4, 4), 0.5, dtype=np.float64)
        arr[:, :, 3] = 1.0  # Full alpha
        result = ColorUtils.rgba2rgb(arr)
        assert result.dtype == np.uint8
        assert result.shape == (4, 4, 3)
        # 0.5 * 255 = 127
        np.testing.assert_array_almost_equal(result, 127, decimal=0)

    def test_rgba2rgb_with_alpha_blend(self):
        """rgba2rgb blends with background based on alpha."""
        arr = np.full((4, 4, 4), 1.0, dtype=np.float64)
        arr[:, :, 3] = 0.5  # Half alpha
        result = ColorUtils.rgba2rgb(arr)  # Black background default
        # (1-0.5)*0 + 0.5*1 = 0.5 -> 127
        np.testing.assert_array_almost_equal(result, 127, decimal=0)
