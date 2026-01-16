#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.blending module."""

from __future__ import annotations

import numpy as np
import pytest

from uchroma.blending import BlendOp, _compose_alpha, blend

# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.screen tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpScreen:
    """Tests for BlendOp.screen blending mode."""

    def test_screen_with_zeros(self, rgba_zeros, rgba_ones):
        """Screen with zeros layer returns base image unchanged."""
        result = BlendOp.screen(rgba_ones, rgba_zeros)
        expected = rgba_ones[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_screen_with_ones(self, rgba_ones, rgba_zeros):
        """Screen with ones layer returns all ones."""
        result = BlendOp.screen(rgba_zeros, rgba_ones)
        expected = np.ones((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_screen_with_half(self, rgba_half):
        """Screen 0.5 with 0.5 gives 0.75."""
        result = BlendOp.screen(rgba_half, rgba_half)
        expected = np.full((4, 4, 3), 0.75, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_screen_identity_black(self, rgba_zeros):
        """Screen with black is identity (returns layer)."""
        layer = np.full((4, 4, 4), 0.3, dtype=np.float64)
        result = BlendOp.screen(rgba_zeros, layer)
        expected = layer[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.multiply tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpMultiply:
    """Tests for BlendOp.multiply blending mode."""

    def test_multiply_with_zeros(self, rgba_zeros, rgba_ones):
        """Multiply with zeros returns zeros."""
        result = BlendOp.multiply(rgba_ones, rgba_zeros)
        expected = np.zeros((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_multiply_with_ones(self, rgba_ones):
        """Multiply with ones returns base image unchanged."""
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        result = BlendOp.multiply(layer, rgba_ones)
        expected = layer[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_multiply_with_half(self, rgba_half):
        """Multiply 0.5 with 0.5 gives 0.25."""
        result = BlendOp.multiply(rgba_half, rgba_half)
        expected = np.full((4, 4, 3), 0.25, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_multiply_clamps_to_one(self):
        """Multiply result is clipped to [0, 1]."""
        # Values over 1.0 should be clipped
        img = np.full((4, 4, 4), 2.0, dtype=np.float64)
        result = BlendOp.multiply(img, img)
        assert np.all(result <= 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.addition tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpAddition:
    """Tests for BlendOp.addition blending mode."""

    def test_addition_with_zeros(self, rgba_zeros, rgba_half):
        """Addition with zeros returns base image."""
        result = BlendOp.addition(rgba_half, rgba_zeros)
        expected = rgba_half[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_addition_half_plus_half(self, rgba_half):
        """Addition 0.5 + 0.5 = 1.0."""
        result = BlendOp.addition(rgba_half, rgba_half)
        expected = np.full((4, 4, 3), 1.0, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_addition_can_exceed_one(self, rgba_ones):
        """Addition can produce values > 1.0 (not clamped)."""
        result = BlendOp.addition(rgba_ones, rgba_ones)
        expected = np.full((4, 4, 3), 2.0, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.dodge tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpDodge:
    """Tests for BlendOp.dodge blending mode."""

    def test_dodge_with_zeros(self, rgba_zeros, rgba_half):
        """Dodge with zeros layer returns base image."""
        result = BlendOp.dodge(rgba_half, rgba_zeros)
        expected = rgba_half[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_dodge_clamps_to_one(self, rgba_half):
        """Dodge is clamped to 1.0 maximum."""
        layer = np.full((4, 4, 4), 0.9, dtype=np.float64)
        result = BlendOp.dodge(rgba_half, layer)
        # Should be clamped to 1.0
        assert np.all(result <= 1.0)

    def test_dodge_brightens(self, rgba_half):
        """Dodge brightens the image."""
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        result = BlendOp.dodge(rgba_half, layer)
        # 0.5 / (1.0 - 0.5) = 1.0 (clamped)
        expected = np.full((4, 4, 3), 1.0, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.lighten_only tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpLightenOnly:
    """Tests for BlendOp.lighten_only blending mode."""

    def test_lighten_only_with_zeros(self, rgba_zeros, rgba_half):
        """Lighten only with zeros returns base image (lighter)."""
        result = BlendOp.lighten_only(rgba_half, rgba_zeros)
        expected = rgba_half[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_lighten_only_with_ones(self, rgba_half, rgba_ones):
        """Lighten only with ones returns ones (lighter)."""
        result = BlendOp.lighten_only(rgba_half, rgba_ones)
        expected = rgba_ones[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_lighten_only_picks_max(self):
        """Lighten only picks maximum value per pixel."""
        img_in = np.zeros((2, 2, 4), dtype=np.float64)
        img_in[:, :, 0] = 0.8  # R high
        img_in[:, :, 1] = 0.2  # G low
        img_layer = np.zeros((2, 2, 4), dtype=np.float64)
        img_layer[:, :, 0] = 0.3  # R low
        img_layer[:, :, 1] = 0.9  # G high
        result = BlendOp.lighten_only(img_in, img_layer)
        assert np.all(result[:, :, 0] == 0.8)  # Max R
        assert np.all(result[:, :, 1] == 0.9)  # Max G


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.darken_only tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpDarkenOnly:
    """Tests for BlendOp.darken_only blending mode."""

    def test_darken_only_with_zeros(self, rgba_zeros, rgba_half):
        """Darken only with zeros returns zeros (darker)."""
        result = BlendOp.darken_only(rgba_half, rgba_zeros)
        expected = rgba_zeros[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_darken_only_with_ones(self, rgba_half, rgba_ones):
        """Darken only with ones returns base image (darker)."""
        result = BlendOp.darken_only(rgba_half, rgba_ones)
        expected = rgba_half[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_darken_only_picks_min(self):
        """Darken only picks minimum value per pixel."""
        img_in = np.zeros((2, 2, 4), dtype=np.float64)
        img_in[:, :, 0] = 0.8  # R high
        img_in[:, :, 1] = 0.2  # G low
        img_layer = np.zeros((2, 2, 4), dtype=np.float64)
        img_layer[:, :, 0] = 0.3  # R low
        img_layer[:, :, 1] = 0.9  # G high
        result = BlendOp.darken_only(img_in, img_layer)
        assert np.all(result[:, :, 0] == 0.3)  # Min R
        assert np.all(result[:, :, 1] == 0.2)  # Min G


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.hard_light tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpHardLight:
    """Tests for BlendOp.hard_light blending mode."""

    def test_hard_light_with_half(self, rgba_half):
        """Hard light at 0.5 behaves as threshold."""
        result = BlendOp.hard_light(rgba_half, rgba_half)
        # At exactly 0.5, uses multiply path: 0.5 * (0.5 * 2) = 0.5
        expected = np.full((4, 4, 3), 0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_hard_light_with_zeros(self, rgba_zeros, rgba_half):
        """Hard light with zero layer uses multiply path (darkens)."""
        result = BlendOp.hard_light(rgba_half, rgba_zeros)
        expected = np.zeros((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_hard_light_with_ones(self, rgba_ones, rgba_half):
        """Hard light with ones layer uses screen path (lightens)."""
        result = BlendOp.hard_light(rgba_half, rgba_ones)
        expected = np.ones((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_hard_light_above_threshold(self):
        """Hard light with layer > 0.5 uses screen formula."""
        img_in = np.full((2, 2, 4), 0.4, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.7, dtype=np.float64)
        result = BlendOp.hard_light(img_in, img_layer)
        # Screen formula: 1 - (1 - base) * (1 - (layer - 0.5) * 2)
        # = 1 - 0.6 * (1 - 0.4) = 1 - 0.36 = 0.64
        expected = np.full((2, 2, 3), 0.64, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.soft_light tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpSoftLight:
    """Tests for BlendOp.soft_light blending mode."""

    def test_soft_light_with_half(self, rgba_half):
        """Soft light at 0.5 is neutral-ish."""
        result = BlendOp.soft_light(rgba_half, rgba_half)
        # Formula: (1-a)*a*b + a*(1-(1-a)*(1-b))
        # = 0.5*0.5*0.5 + 0.5*(1-0.5*0.5) = 0.125 + 0.375 = 0.5
        expected = np.full((4, 4, 3), 0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_soft_light_with_zeros(self, rgba_zeros, rgba_half):
        """Soft light with zero layer."""
        result = BlendOp.soft_light(rgba_half, rgba_zeros)
        # = (1-0.5)*0.5*0 + 0.5*(1-(1-0.5)*(1-0)) = 0 + 0.5*(1-0.5) = 0.25
        expected = np.full((4, 4, 3), 0.25, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_soft_light_with_ones(self, rgba_ones, rgba_half):
        """Soft light with ones layer lightens."""
        result = BlendOp.soft_light(rgba_half, rgba_ones)
        # = (1-0.5)*0.5*1 + 0.5*(1-(1-0.5)*(1-1)) = 0.25 + 0.5 = 0.75
        expected = np.full((4, 4, 3), 0.75, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.difference tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpDifference:
    """Tests for BlendOp.difference blending mode."""

    def test_difference_with_zeros(self, rgba_zeros, rgba_half):
        """Difference with zeros returns absolute base value."""
        result = BlendOp.difference(rgba_half, rgba_zeros)
        expected = rgba_half[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_difference_same_images(self, rgba_half):
        """Difference of identical images is zero."""
        result = BlendOp.difference(rgba_half, rgba_half)
        expected = np.zeros((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_difference_is_absolute(self):
        """Difference returns absolute value."""
        img_in = np.full((2, 2, 4), 0.3, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.8, dtype=np.float64)
        result = BlendOp.difference(img_in, img_layer)
        expected = np.full((2, 2, 3), 0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.subtract tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpSubtract:
    """Tests for BlendOp.subtract blending mode."""

    def test_subtract_with_zeros(self, rgba_zeros, rgba_half):
        """Subtract zeros returns base image."""
        result = BlendOp.subtract(rgba_half, rgba_zeros)
        expected = rgba_half[:, :, :3]
        np.testing.assert_array_almost_equal(result, expected)

    def test_subtract_same_images(self, rgba_half):
        """Subtract identical images gives zero."""
        result = BlendOp.subtract(rgba_half, rgba_half)
        expected = np.zeros((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_subtract_can_go_negative(self):
        """Subtract can produce negative values (not clamped)."""
        img_in = np.full((2, 2, 4), 0.3, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.8, dtype=np.float64)
        result = BlendOp.subtract(img_in, img_layer)
        expected = np.full((2, 2, 3), -0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.grain_extract tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpGrainExtract:
    """Tests for BlendOp.grain_extract blending mode."""

    def test_grain_extract_with_half(self, rgba_half):
        """Grain extract at 0.5 is identity-like."""
        result = BlendOp.grain_extract(rgba_half, rgba_half)
        # 0.5 - 0.5 + 0.5 = 0.5
        expected = np.full((4, 4, 3), 0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_grain_extract_clamps_high(self):
        """Grain extract clamps to 1.0."""
        img_in = np.full((2, 2, 4), 0.9, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.1, dtype=np.float64)
        result = BlendOp.grain_extract(img_in, img_layer)
        # 0.9 - 0.1 + 0.5 = 1.3 -> clamped to 1.0
        expected = np.full((2, 2, 3), 1.0, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_grain_extract_clamps_low(self):
        """Grain extract clamps to 0.0."""
        img_in = np.full((2, 2, 4), 0.1, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.9, dtype=np.float64)
        result = BlendOp.grain_extract(img_in, img_layer)
        # 0.1 - 0.9 + 0.5 = -0.3 -> clamped to 0.0
        expected = np.zeros((2, 2, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.grain_merge tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpGrainMerge:
    """Tests for BlendOp.grain_merge blending mode."""

    def test_grain_merge_with_half(self, rgba_half):
        """Grain merge at 0.5 is identity-like."""
        result = BlendOp.grain_merge(rgba_half, rgba_half)
        # 0.5 + 0.5 - 0.5 = 0.5
        expected = np.full((4, 4, 3), 0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_grain_merge_clamps_high(self):
        """Grain merge clamps to 1.0."""
        img_in = np.full((2, 2, 4), 0.8, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.9, dtype=np.float64)
        result = BlendOp.grain_merge(img_in, img_layer)
        # 0.8 + 0.9 - 0.5 = 1.2 -> clamped to 1.0
        expected = np.full((2, 2, 3), 1.0, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_grain_merge_clamps_low(self):
        """Grain merge clamps to 0.0."""
        img_in = np.full((2, 2, 4), 0.1, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.2, dtype=np.float64)
        result = BlendOp.grain_merge(img_in, img_layer)
        # 0.1 + 0.2 - 0.5 = -0.2 -> clamped to 0.0
        expected = np.zeros((2, 2, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.divide tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpDivide:
    """Tests for BlendOp.divide blending mode."""

    def test_divide_with_ones(self, rgba_ones, rgba_half):
        """Divide by ones returns scaled base image."""
        result = BlendOp.divide(rgba_half, rgba_ones)
        # (256/255 * 0.5) / (1/255 + 1.0) ~ 0.5
        np.testing.assert_array_almost_equal(result, rgba_half[:, :, :3], decimal=2)

    def test_divide_clamps_to_one(self):
        """Divide clamps result to 1.0."""
        img_in = np.full((2, 2, 4), 0.9, dtype=np.float64)
        img_layer = np.full((2, 2, 4), 0.1, dtype=np.float64)
        result = BlendOp.divide(img_in, img_layer)
        assert np.all(result <= 1.0)

    def test_divide_with_zeros_safe(self, rgba_zeros, rgba_half):
        """Divide by near-zero doesn't explode (has epsilon)."""
        # The formula adds 1/255 to prevent true division by zero
        result = BlendOp.divide(rgba_half, rgba_zeros)
        # Should be clamped to 1.0
        expected = np.ones((4, 4, 3), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# BlendOp.get_modes tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendOpGetModes:
    """Tests for BlendOp.get_modes class method."""

    def test_get_modes_returns_list(self):
        """get_modes returns a sorted list of mode names."""
        modes = BlendOp.get_modes()
        assert isinstance(modes, list)
        assert len(modes) > 0

    def test_get_modes_contains_expected(self):
        """get_modes contains all expected blend modes."""
        modes = BlendOp.get_modes()
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
            assert mode in modes, f"Mode {mode} not found in get_modes()"

    def test_get_modes_is_sorted(self):
        """get_modes returns a sorted list."""
        modes = BlendOp.get_modes()
        assert modes == sorted(modes)

    def test_get_modes_excludes_private(self):
        """get_modes excludes private methods."""
        modes = BlendOp.get_modes()
        for mode in modes:
            assert not mode.startswith("_")


# ─────────────────────────────────────────────────────────────────────────────
# _compose_alpha tests
# ─────────────────────────────────────────────────────────────────────────────


class TestComposeAlpha:
    """Tests for _compose_alpha function."""

    def test_compose_alpha_full_opacity(self, rgba_ones):
        """Full opacity with full alpha returns ones."""
        result = _compose_alpha(rgba_ones, rgba_ones, opacity=1.0)
        # Both have alpha=1.0, so comp_alpha=1.0, new_alpha=1.0, ratio=1.0
        expected = np.ones((4, 4), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_compose_alpha_zero_opacity(self, rgba_ones):
        """Zero opacity returns zero ratio."""
        result = _compose_alpha(rgba_ones, rgba_ones, opacity=0.0)
        expected = np.zeros((4, 4), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_compose_alpha_half_opacity(self, rgba_ones):
        """Half opacity affects composition ratio."""
        result = _compose_alpha(rgba_ones, rgba_ones, opacity=0.5)
        # comp_alpha = min(1,1)*0.5 = 0.5
        # new_alpha = 1 + (1-1)*0.5 = 1
        # ratio = 0.5/1 = 0.5
        expected = np.full((4, 4), 0.5, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_compose_alpha_zero_alpha_input(self, rgba_zeros, rgba_ones):
        """Zero alpha in input produces zero ratio (handles NaN)."""
        result = _compose_alpha(rgba_zeros, rgba_ones, opacity=1.0)
        # img_in alpha is 0, so comp_alpha=0, new_alpha=0, ratio=0/0=NaN->0
        expected = np.zeros((4, 4), dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_compose_alpha_respects_minimum(self):
        """Compose alpha uses minimum of input alphas."""
        img_in = np.ones((2, 2, 4), dtype=np.float64)
        img_in[:, :, 3] = 0.3  # Low alpha
        img_layer = np.ones((2, 2, 4), dtype=np.float64)
        img_layer[:, :, 3] = 0.9  # High alpha
        result = _compose_alpha(img_in, img_layer, opacity=1.0)
        # comp_alpha = min(0.3, 0.9) * 1.0 = 0.3
        # new_alpha = 0.3 + (1-0.3)*0.3 = 0.3 + 0.21 = 0.51
        # ratio = 0.3/0.51 ~ 0.588
        expected = np.full((2, 2), 0.3 / 0.51, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected, decimal=5)


# ─────────────────────────────────────────────────────────────────────────────
# blend function tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBlendFunction:
    """Tests for the main blend function."""

    def test_blend_with_function_op(self, rgba_ones):
        """Blend accepts a callable as blend_op."""
        # Use full alpha on layer to get pure blend result
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        layer[:, :, 3] = 1.0  # Full alpha
        result = blend(rgba_ones, layer, BlendOp.multiply, opacity=1.0)
        assert result.shape == (4, 4, 4)
        # Multiply 1.0 * 0.5 = 0.5
        np.testing.assert_array_almost_equal(result[:, :, :3], layer[:, :, :3])

    def test_blend_with_string_op(self, rgba_ones):
        """Blend accepts a string mode name."""
        # Use full alpha on layer to get pure blend result
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        layer[:, :, 3] = 1.0  # Full alpha
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
        img_in[:, :, 3] = 0.7  # Custom alpha
        result = blend(img_in, rgba_half, "screen", opacity=1.0)
        np.testing.assert_array_almost_equal(result[:, :, 3], img_in[:, :, 3])

    def test_blend_opacity_zero(self, rgba_ones, rgba_half):
        """Blend with opacity=0 returns base image."""
        result = blend(rgba_ones, rgba_half, "multiply", opacity=0.0)
        np.testing.assert_array_almost_equal(result[:, :, :3], rgba_ones[:, :, :3])

    def test_blend_opacity_half(self, rgba_ones):
        """Blend with opacity=0.5 interpolates."""
        # Use full alpha layer for predictable results
        layer = np.full((4, 4, 4), 0.5, dtype=np.float64)
        layer[:, :, 3] = 1.0  # Full alpha
        result = blend(rgba_ones, layer, "multiply", opacity=0.5)
        # With full alphas: ratio = 0.5, blend = multiply(1, 0.5) = 0.5
        # result = 0.5 * 0.5 + (1-0.5) * 1 = 0.25 + 0.5 = 0.75
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
        with pytest.raises(AssertionError, match="shape"):
            blend(img_3ch, img_4ch, "screen", opacity=1.0)

    def test_blend_requires_4_channels_layer(self):
        """Blend raises assertion for 3-channel layer."""
        img_3ch = np.ones((4, 4, 3), dtype=np.float64)
        img_4ch = np.ones((4, 4, 4), dtype=np.float64)
        with pytest.raises(AssertionError, match="shape"):
            blend(img_4ch, img_3ch, "screen", opacity=1.0)

    def test_blend_opacity_bounds(self, rgba_half):
        """Blend raises assertion for out-of-bounds opacity."""
        with pytest.raises(AssertionError, match="Opacity"):
            blend(rgba_half, rgba_half, "screen", opacity=1.5)
        with pytest.raises(AssertionError, match="Opacity"):
            blend(rgba_half, rgba_half, "screen", opacity=-0.1)

    def test_blend_handles_nan(self, rgba_zeros):
        """Blend handles NaN values gracefully (replaces with 0)."""
        result = blend(rgba_zeros, rgba_zeros, "screen", opacity=1.0)
        assert not np.any(np.isnan(result))

    def test_blend_red_green(self, rgb_red, rgb_green):
        """Blend red and green images."""
        result = blend(rgb_red, rgb_green, "screen", opacity=1.0)
        # Screen: 1 - (1-r)*(1-g)
        # Red channel: 1 - (1-1)*(1-0) = 1
        # Green channel: 1 - (1-0)*(1-1) = 1
        assert result.shape == (4, 4, 4)
        np.testing.assert_array_almost_equal(result[:, :, 0], 1.0)  # Red stays
        np.testing.assert_array_almost_equal(result[:, :, 1], 1.0)  # Green added


class TestBlendWithAllModes:
    """Integration tests running blend with all available modes."""

    @pytest.mark.parametrize("mode", BlendOp.get_modes())
    def test_blend_all_modes_run(self, rgba_half, mode):
        """All blend modes can be called via string."""
        result = blend(rgba_half, rgba_half, mode, opacity=1.0)
        assert result.shape == (4, 4, 4)
        assert result.dtype == np.float64

    @pytest.mark.parametrize("mode", BlendOp.get_modes())
    def test_blend_all_modes_no_nan(self, rgba_half, mode):
        """All blend modes produce no NaN values with valid input."""
        result = blend(rgba_half, rgba_half, mode, opacity=1.0)
        assert not np.any(np.isnan(result))
