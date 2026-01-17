#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Layer pixel operations - pure Python with numpy.

These functions were originally Cython but gain no benefit from it
since they're just numpy wrappers. The actual heavy lifting is in
numpy's C code.
"""

import numpy as np


def color_to_np(*colors):
    """
    Convert Color objects to numpy RGBA array.

    Args:
        *colors: Color objects to convert

    Returns:
        numpy array of shape (N, 4) with RGBA floats
    """
    result = []
    for c in colors:
        rgb = tuple(c)
        # Handle alpha as property (ColorAide style)
        if hasattr(c, "alpha"):
            alpha = c.alpha
            if callable(alpha):
                alpha = alpha()
        else:
            alpha = 1.0
        result.append((rgb[0], rgb[1], rgb[2], alpha))
    return np.array(result, dtype=np.float64)


def coords_inside_image(rr, cc, shape, val=None):
    """
    Filter coordinates to only those inside the image bounds.

    Args:
        rr: Row coordinates
        cc: Column coordinates
        shape: Image shape (height, width, ...)
        val: Optional values to filter alongside coords

    Returns:
        Filtered (rr, cc) or (rr, cc, val)
    """
    mask = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
    if val is None:
        return rr[mask], cc[mask]
    else:
        return rr[mask], cc[mask], val[mask]


def set_color(img, coords, color, alpha=1):
    """
    Set pixel colors with alpha blending.

    Args:
        img: Target image array (height, width, 4)
        coords: Tuple of (row_coords, col_coords)
        color: Color array of shape (N, 4) or (4,)
        alpha: Alpha multiplier (scalar or array)
    """
    rr, cc = coords

    if img.ndim == 2:
        img = img[..., np.newaxis]

    color = np.array(color, ndmin=1, copy=False)

    if img.shape[-1] != color.shape[-1]:
        raise ValueError(
            f"Color shape ({color.shape[0]}) must match last "
            f"image dimension ({img.shape[-1]}). color=({color})"
        )

    if np.isscalar(alpha):
        alpha = np.ones_like(rr) * alpha

    rr, cc, alpha = coords_inside_image(rr, cc, img.shape, val=alpha)

    color = color * alpha[..., np.newaxis]

    if np.all(img[rr, cc] == 0):
        img[rr, cc] = color
    else:
        src_alpha = color[..., -1][..., np.newaxis]
        src_rgb = color[..., :-1]

        dst_alpha = img[rr, cc][..., -1][..., np.newaxis] * 0.75
        dst_rgb = img[rr, cc][..., :-1]

        out_alpha = src_alpha + dst_alpha * (1 - src_alpha)
        out_rgb = (src_rgb * src_alpha + dst_rgb * dst_alpha * (1 - src_alpha)) / out_alpha

        img[rr, cc] = np.clip(np.hstack([out_rgb, out_alpha]), a_min=0, a_max=1)
