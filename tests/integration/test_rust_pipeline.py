#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Integration tests for full Rust graphics pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from uchroma.blending import blend
from uchroma.color import ColorUtils
from uchroma.layer import Layer


class TestRustPipelineIntegration:
    """End-to-end tests exercising the full Rust pipeline."""

    def test_layer_draw_blend_compose(self):
        """Full pipeline: draw on layers, blend, compose to RGB."""
        # Create two layers
        layer1 = Layer(width=10, height=10)
        layer2 = Layer(width=10, height=10)

        # Draw on layers
        layer1.circle(5, 5, 3, "red", fill=True)
        layer2.circle(5, 5, 3, "blue", fill=True)
        layer2.blend_mode = "screen"
        layer2.opacity = 0.5

        # Compose (uses Rust blending)
        composed = blend(layer1.matrix, layer2.matrix, "screen", 0.5)

        assert composed.shape == (10, 10, 4)
        assert composed.dtype == np.float64

        # Convert to RGB (uses Rust compositor)
        rgb = ColorUtils.rgba2rgb(composed)

        assert rgb.shape == (10, 10, 3)
        assert rgb.dtype == np.uint8

    def test_drawing_primitives_in_layer(self):
        """Drawing primitives use Rust backend."""
        layer = Layer(width=20, height=20)

        # These use Rust circle_perimeter_aa and line_aa
        layer.circle(10, 10, 5, "green", fill=False)
        layer.line(0, 0, 19, 19, "yellow")

        # Verify some pixels are set
        assert not np.all(layer.matrix == 0)

    @pytest.mark.parametrize("size", [32, 64, 128])
    def test_performance_scaling(self, size):
        """Pipeline handles various sizes without error."""
        layer = Layer(width=size, height=size)
        layer.circle(size // 2, size // 2, size // 4, "red", fill=True)

        rgb = ColorUtils.rgba2rgb(layer.matrix)
        assert rgb.shape == (size, size, 3)
