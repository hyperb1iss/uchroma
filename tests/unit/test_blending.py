#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.blending module."""

from __future__ import annotations

import numpy as np
import pytest

from uchroma.blending import BLEND_MODES, BlendOp, blend


# ─────────────────────────────────────────────────────────────────────────────
# BLEND_MODES tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendModes:
    """Tests for BLEND_MODES constant."""

    def test_blend_modes_is_list(self):
        """BLEND_MODES is a list of strings."""
        assert isinstance(BLEND_MODES, list)
        assert len(BLEND_MODES) > 0
        assert all(isinstance(m, str) for m in BLEND_MODES)

    def test_blend_modes_contains_expected(self):
        """BLEND_MODES contains all expected blend modes."""
        expected_modes = [
            "screen",
            "multiply",
            "addition",
            "dodge",
            "lighten_only",
            "darken_only",
            "hard_light",
            "soft_light",
            "difference",
            "subtract",
            "grain_extract",
            "grain_merge",
            "divide",
        ]
        for mode in expected_modes:
            assert mode in BLEND_MODES, f"Mode {mode} not found in BLEND_MODES"

    def test_blend_modes_is_sorted(self):
        """BLEND_MODES is sorted alphabetically."""
        assert BLEND_MODES == sorted(BLEND_MODES)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp compatibility tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpCompat:
    """Tests for BlendOp legacy compatibility class."""

    def test_get_modes_returns_blend_modes(self):
        """BlendOp.get_modes() returns BLEND_MODES."""
        modes = BlendOp.get_modes()
        assert modes == BLEND_MODES


# ─────────────────────────────────────────────────────────────────────────────
# blend function tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendFunction:
    """Tests for the main blend function."""

    def test_blend_with_string_op(self, rgba_ones):
        """Blend accepts a string mode name."""
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        layer[:, :, 3] = 1.0
        result = blend(rgba_ones, layer, "multiply", opacity=1.0)
        assert result.shape == (4, 4, 4)
        np.testing.assert_array_almost_equal(result[:, :, :3], layer[:, :, :3])

    def test_blend_with_none_uses_screen(self, rgba_half):
        """Blend with None defaults to screen mode."""
        result_none = blend(rgba_half, rgba_half, None, opacity=1.0)
        result_screen = blend(rgba_half, rgba_half, "screen", opacity=1.0)
        np.testing.assert_array_almost_equal(result_none, result_screen)

    def test_blend_invalid_string_raises(self, rgba_half):
        """Blend with invalid string mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid blend mode"):
            blend(rgba_half, rgba_half, "nonexistent_mode", opacity=1.0)

    def test_blend_preserves_alpha(self, rgba_half):
        """Blend preserves input alpha channel."""
        img_in = rgba_half.copy()
        img_in[:, :, 3] = 0.7
        result = blend(img_in, rgba_half, "screen", opacity=1.0)
        np.testing.assert_array_almost_equal(result[:, :, 3], img_in[:, :, 3])

    def test_blend_opacity_zero(self, rgba_ones, rgba_half):
        """Blend with opacity=0 returns base image."""
        result = blend(rgba_ones, rgba_half, "multiply", opacity=0.0)
        np.testing.assert_array_almost_equal(result[:, :, :3], rgba_ones[:, :, :3])

    def test_blend_opacity_half(self, rgba_ones):
        """Blend with opacity=0.5 interpolates."""
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        layer[:, :, 3] = 1.0
        result = blend(rgba_ones, layer, "multiply", opacity=0.5)
        expected = np.full((4, 4, 3), 0.75, dtype=np.float64)
        np.testing.assert_array_almost_equal(result[:, :, :3], expected)

    def test_blend_requires_float64(self, rgba_half):
        """Blend raises assertion for non-float64 arrays."""
        img_int = rgba_half.astype(np.float32)
        with pytest.raises(AssertionError, match="float64"):
            blend(img_int, rgba_half, "screen", opacity=1.0)

    def test_blend_requires_4_channels_input(self):
        """Blend raises assertion for 3-channel input."""
        img_3ch = np.ones((4, 4, 3), dtype=np.float64)
        img_4ch = np.ones((4, 4, 4), dtype=np.float64)
        with pytest.raises(AssertionError, match="4 channels"):
            blend(img_3ch, img_4ch, "screen", opacity=1.0)

    def test_blend_requires_4_channels_layer(self):
        """Blend raises assertion for 3-channel layer."""
        img_3ch = np.ones((4, 4, 3), dtype=np.float64)
        img_4ch = np.ones((4, 4, 4), dtype=np.float64)
        with pytest.raises(AssertionError, match="4 channels"):
            blend(img_4ch, img_3ch, "screen", opacity=1.0)

    def test_blend_opacity_bounds(self, rgba_half):
        """Blend raises assertion for out-of-bounds opacity."""
        with pytest.raises(AssertionError, match="opacity"):
            blend(rgba_half, rgba_half, "screen", opacity=1.5)
        with pytest.raises(AssertionError, match="opacity"):
            blend(rgba_half, rgba_half, "screen", opacity=-0.1)

    def test_blend_handles_nan(self, rgba_zeros):
        """Blend handles NaN values gracefully."""
        result = blend(rgba_zeros, rgba_zeros, "screen", opacity=1.0)
        assert not np.any(np.isnan(result))

    def test_blend_red_green(self, rgb_red, rgb_green):
        """Blend red and green images with screen."""
        result = blend(rgb_red, rgb_green, "screen", opacity=1.0)
        assert result.shape == (4, 4, 4)
        np.testing.assert_array_almost_equal(result[:, :, 0], 1.0)
        np.testing.assert_array_almost_equal(result[:, :, 1], 1.0)


class TestBlendWithAllModes:
    """Integration tests running blend with all available modes."""

    @pytest.mark.parametrize("mode", BLEND_MODES)
    def test_blend_all_modes_run(self, rgba_half, mode):
        """All blend modes can be called via string."""
        result = blend(rgba_half, rgba_half, mode, opacity=1.0)
        assert result.shape == (4, 4, 4)
        assert result.dtype == np.float64

    @pytest.mark.parametrize("mode", BLEND_MODES)
    def test_blend_all_modes_no_nan(self, rgba_half, mode):
        """All blend modes produce no NaN values with valid input."""
        result = blend(rgba_half, rgba_half, mode, opacity=1.0)
        assert not np.any(np.isnan(result))
