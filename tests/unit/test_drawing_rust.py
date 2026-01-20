#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Tests for Rust drawing backend."""

from __future__ import annotations

import numpy as np

from uchroma.drawing import USE_RUST_DRAWING, circle_perimeter_aa, line_aa


class TestRustDrawingBackend:
    """Tests that Rust drawing produces valid results."""

    def test_rust_backend_available(self):
        """Rust drawing backend should be available."""
        assert USE_RUST_DRAWING, "Rust drawing backend not available"

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
