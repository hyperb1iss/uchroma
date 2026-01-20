#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""
Layer blending operations implemented in Rust.

All blending is performed by the native Rust module for performance and consistency.
"""

import numpy as np

from uchroma._native import blend_full as _rust_blend_full

# Available blend modes (must match Rust implementation)
BLEND_MODES = [
    "addition",
    "darken_only",
    "difference",
    "divide",
    "dodge",
    "grain_extract",
    "grain_merge",
    "hard_light",
    "lighten_only",
    "multiply",
    "screen",
    "soft_light",
    "subtract",
]


def blend(
    img_in: np.ndarray,
    img_layer: np.ndarray,
    blend_mode: str | None = None,
    opacity: float = 1.0,
) -> np.ndarray:
    """
    Blend two RGBA images using the specified blend mode.

    :param img_in: Base image (float64, shape [h, w, 4])
    :param img_layer: Layer image (float64, shape [h, w, 4])
    :param blend_mode: Blend mode name (default: "screen")
    :param opacity: Layer opacity (0.0 to 1.0)
    :returns: Blended image (float64, shape [h, w, 4])
    """
    assert img_in.dtype == np.float64, "img_in must be float64"
    assert img_layer.dtype == np.float64, "img_layer must be float64"
    assert img_in.shape[2] == 4, "img_in must have 4 channels (RGBA)"
    assert img_layer.shape[2] == 4, "img_layer must have 4 channels (RGBA)"
    assert 0.0 <= opacity <= 1.0, "opacity must be between 0.0 and 1.0"

    if blend_mode is None:
        blend_mode = "screen"

    if blend_mode not in BLEND_MODES:
        raise ValueError(f"Invalid blend mode: {blend_mode}. Valid modes: {BLEND_MODES}")

    output = np.empty_like(img_in)
    _rust_blend_full(img_in, img_layer, output, blend_mode, opacity)
    return output


# Legacy compatibility - BlendOp class for code that references it
class BlendOp:
    """Legacy compatibility class. Use BLEND_MODES list and blend() function instead."""

    @classmethod
    def get_modes(cls) -> list[str]:
        """Return list of available blend mode names."""
        return BLEND_MODES.copy()
