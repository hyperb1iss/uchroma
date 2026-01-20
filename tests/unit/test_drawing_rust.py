#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust drawing backend."""

from __future__ import annotations

import numpy as np

from uchroma.drawing import circle, circle_perimeter_aa, ellipse, ellipse_perimeter, line_aa


class TestRustDrawingBackend:
    """Tests that Rust drawing produces valid results."""

    # ─── circle (filled) ─────────────────────────────────────────────────

    def test_circle_returns_arrays(self):
        """circle returns two numpy arrays."""
        rr, cc = circle(5, 5, 3)
        assert isinstance(rr, np.ndarray)
        assert isinstance(cc, np.ndarray)
        assert len(rr) == len(cc)
        assert len(rr) > 0

    def test_circle_with_shape_clips(self):
        """circle with shape clips to bounds."""
        rr, cc = circle(2, 2, 5, shape=(10, 10))
        assert np.all(rr >= 0)
        assert np.all(rr < 10)
        assert np.all(cc >= 0)
        assert np.all(cc < 10)

    def test_circle_zero_radius(self):
        """circle with zero radius returns empty arrays."""
        rr, cc = circle(5, 5, 0)
        assert len(rr) == 0
        assert len(cc) == 0

    def test_circle_point_count(self):
        """circle returns expected number of points for radius."""
        rr, _cc = circle(10, 10, 3)
        # Filled circle of radius 3 should have ~πr² points
        assert 20 <= len(rr) <= 40

    # ─── circle_perimeter_aa ─────────────────────────────────────────────

    def test_circle_perimeter_aa_returns_arrays(self):
        """circle_perimeter_aa returns three numpy arrays."""
        rr, cc, aa = circle_perimeter_aa(5, 5, 3)
        assert isinstance(rr, np.ndarray)
        assert isinstance(cc, np.ndarray)
        assert isinstance(aa, np.ndarray)
        assert len(rr) == len(cc) == len(aa)

    def test_circle_perimeter_aa_with_shape_clips(self):
        """circle_perimeter_aa with shape clips to bounds."""
        rr, cc, _aa = circle_perimeter_aa(2, 2, 5, shape=(10, 10))
        assert np.all(rr >= 0)
        assert np.all(rr < 10)
        assert np.all(cc >= 0)
        assert np.all(cc < 10)

    def test_circle_perimeter_aa_zero_radius(self):
        """circle_perimeter_aa with zero radius returns empty arrays."""
        rr, _cc, _aa = circle_perimeter_aa(5, 5, 0)
        assert len(rr) == 0

    def test_circle_perimeter_aa_alphas_bounded(self):
        """circle_perimeter_aa alpha values are in [0, 1]."""
        _rr, _cc, aa = circle_perimeter_aa(10, 10, 5)
        assert np.all(aa >= 0.0)
        assert np.all(aa <= 1.0)

    # ─── ellipse (filled) ────────────────────────────────────────────────

    def test_ellipse_returns_arrays(self):
        """ellipse returns two numpy arrays."""
        rr, cc = ellipse(5, 5, 3, 5)
        assert isinstance(rr, np.ndarray)
        assert isinstance(cc, np.ndarray)
        assert len(rr) == len(cc)
        assert len(rr) > 0

    def test_ellipse_with_shape_clips(self):
        """ellipse with shape clips to bounds."""
        rr, cc = ellipse(2, 2, 5, 8, shape=(10, 10))
        assert np.all(rr >= 0)
        assert np.all(rr < 10)
        assert np.all(cc >= 0)
        assert np.all(cc < 10)

    def test_ellipse_zero_radius(self):
        """ellipse with zero radius returns empty arrays."""
        rr, cc = ellipse(5, 5, 0, 5)
        assert len(rr) == 0
        rr, cc = ellipse(5, 5, 5, 0)
        assert len(rr) == 0

    def test_ellipse_asymmetric(self):
        """ellipse with different radii produces asymmetric shape."""
        rr, cc = ellipse(10, 10, 2, 5)
        # Should span more in x than y
        assert cc.max() - cc.min() > rr.max() - rr.min()

    # ─── ellipse_perimeter ───────────────────────────────────────────────

    def test_ellipse_perimeter_returns_arrays(self):
        """ellipse_perimeter returns two numpy arrays."""
        rr, cc = ellipse_perimeter(5, 5, 3, 5)
        assert isinstance(rr, np.ndarray)
        assert isinstance(cc, np.ndarray)
        assert len(rr) == len(cc)
        assert len(rr) > 0

    def test_ellipse_perimeter_with_shape_clips(self):
        """ellipse_perimeter with shape clips to bounds."""
        rr, cc = ellipse_perimeter(2, 2, 5, 8, shape=(10, 10))
        assert np.all(rr >= 0)
        assert np.all(rr < 10)
        assert np.all(cc >= 0)
        assert np.all(cc < 10)

    def test_ellipse_perimeter_zero_radius(self):
        """ellipse_perimeter with zero radius returns empty arrays."""
        rr, cc = ellipse_perimeter(5, 5, 0, 5)
        assert len(rr) == 0
        rr, cc = ellipse_perimeter(5, 5, 5, 0)
        assert len(rr) == 0

    def test_ellipse_perimeter_is_outline(self):
        """ellipse_perimeter returns fewer points than filled ellipse."""
        filled_rr, _ = ellipse(10, 10, 5, 8)
        outline_rr, _ = ellipse_perimeter(10, 10, 5, 8)
        assert len(outline_rr) < len(filled_rr)

    # ─── line_aa ─────────────────────────────────────────────────────────

    def test_line_aa_returns_arrays(self):
        """line_aa returns three numpy arrays."""
        rr, cc, aa = line_aa(0, 0, 5, 5)
        assert isinstance(rr, np.ndarray)
        assert isinstance(cc, np.ndarray)
        assert isinstance(aa, np.ndarray)
        assert len(rr) == len(cc) == len(aa)

    def test_line_aa_alphas_bounded(self):
        """line_aa alpha values are in [0, 1]."""
        _rr, _cc, aa = line_aa(0, 0, 10, 10)
        assert np.all(aa >= 0.0)
        assert np.all(aa <= 1.0)

    def test_line_aa_horizontal(self):
        """line_aa works for horizontal lines."""
        rr, cc, aa = line_aa(5, 0, 5, 10)
        assert len(rr) > 0
        assert np.all(aa >= 0.0)

    def test_line_aa_vertical(self):
        """line_aa works for vertical lines."""
        rr, cc, aa = line_aa(0, 5, 10, 5)
        assert len(rr) > 0
        assert np.all(aa >= 0.0)
