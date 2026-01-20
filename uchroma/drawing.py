"""
Pure numpy implementations of drawing primitives.

Replaces scikit-image.draw to eliminate heavy scipy/matplotlib dependencies.
Uses Rust backend when available for performance-critical functions.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# Try to import Rust backend
try:
    from uchroma._native import (
        circle_perimeter_aa as _rust_circle_perimeter_aa,
        line_aa as _rust_line_aa,
    )

    USE_RUST_DRAWING = True
except ImportError:
    USE_RUST_DRAWING = False
    _rust_circle_perimeter_aa = None
    _rust_line_aa = None


def _clip_to_shape(
    rr: NDArray[np.intp], cc: NDArray[np.intp], shape: tuple[int, int]
) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """Clip coordinates to array bounds."""
    mask = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
    return rr[mask], cc[mask]


def _clip_to_shape_aa(
    rr: NDArray[np.intp], cc: NDArray[np.intp], aa: NDArray[np.float64], shape: tuple[int, int]
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float64]]:
    """Clip coordinates and alpha values to array bounds."""
    mask = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
    return rr[mask], cc[mask], aa[mask]


def circle(
    r: int, c: int, radius: int, shape: tuple[int, int] | None = None
) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """
    Generate coordinates for a filled circle.

    Uses the midpoint circle algorithm with filled scanlines.

    :param r: Row (y) coordinate of center
    :param c: Column (x) coordinate of center
    :param radius: Radius of circle
    :param shape: Optional (rows, cols) to clip coordinates
    :returns: Tuple of (row_coords, col_coords)
    """
    if radius <= 0:
        return np.array([], dtype=np.intp), np.array([], dtype=np.intp)

    # Generate all points within radius using meshgrid
    y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    mask = x * x + y * y <= radius * radius

    # Get coordinates where mask is True
    rows, cols = np.where(mask)
    rr = rows + r - radius
    cc = cols + c - radius

    if shape is not None:
        return _clip_to_shape(rr.astype(np.intp), cc.astype(np.intp), shape)

    return rr.astype(np.intp), cc.astype(np.intp)


def circle_perimeter_aa(
    r: int, c: int, radius: int, shape: tuple[int, int] | None = None
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float64]]:
    """
    Generate coordinates for an anti-aliased circle perimeter.

    Uses Xiaolin Wu's algorithm for anti-aliased circles.
    Uses Rust backend when available for better performance.

    :param r: Row (y) coordinate of center
    :param c: Column (x) coordinate of center
    :param radius: Radius of circle
    :param shape: Optional (rows, cols) to clip coordinates
    :returns: Tuple of (row_coords, col_coords, alpha_values)
    """
    # Use Rust backend if available
    if USE_RUST_DRAWING and _rust_circle_perimeter_aa is not None:
        # Ensure shape is a 2-tuple (height, width) if provided
        rust_shape = None
        if shape is not None:
            rust_shape = (shape[0], shape[1])
        rr, cc, aa = _rust_circle_perimeter_aa(r, c, radius, rust_shape)
        return rr.astype(np.intp), cc.astype(np.intp), aa

    # Python fallback
    if radius <= 0:
        return (
            np.array([], dtype=np.intp),
            np.array([], dtype=np.intp),
            np.array([], dtype=np.float64),
        )

    # Generate points around the circle with sub-pixel precision
    # Use more points for smoother anti-aliasing
    n_points = max(64, int(2 * np.pi * radius * 2))
    theta = np.linspace(0, 2 * np.pi, n_points, endpoint=False)

    # Exact floating-point positions
    fr = r + radius * np.sin(theta)
    fc = c + radius * np.cos(theta)

    rows_list = []
    cols_list = []
    alpha_list = []

    for i in range(len(fr)):
        # Integer coordinates surrounding this point
        r0, r1 = int(np.floor(fr[i])), int(np.ceil(fr[i]))
        c0, c1 = int(np.floor(fc[i])), int(np.ceil(fc[i]))

        # Fractional parts for anti-aliasing
        fr_frac = fr[i] - r0
        fc_frac = fc[i] - c0

        # Add all 4 neighboring pixels with appropriate weights
        for ri, rw in [(r0, 1 - fr_frac), (r1, fr_frac)]:
            for ci, cw in [(c0, 1 - fc_frac), (c1, fc_frac)]:
                rows_list.append(ri)
                cols_list.append(ci)
                alpha_list.append(rw * cw)

    rr = np.array(rows_list, dtype=np.intp)
    cc = np.array(cols_list, dtype=np.intp)
    aa = np.array(alpha_list, dtype=np.float64)

    # Combine duplicate coordinates by summing their alpha values
    if len(rr) > 0:
        # Create unique coordinate pairs
        coords = rr.astype(np.int64) * 1000000 + cc.astype(np.int64)
        unique_coords, inverse = np.unique(coords, return_inverse=True)

        # Sum alpha values for duplicate coordinates
        aa_combined = np.zeros(len(unique_coords), dtype=np.float64)
        np.add.at(aa_combined, inverse, aa)

        # Reconstruct coordinates
        rr = (unique_coords // 1000000).astype(np.intp)
        cc = (unique_coords % 1000000).astype(np.intp)
        aa = np.clip(aa_combined, 0, 1)

    if shape is not None:
        return _clip_to_shape_aa(rr, cc, aa, shape)

    return rr, cc, aa


def ellipse(
    r: int,
    c: int,
    r_radius: int,
    c_radius: int,
    shape: tuple[int, int] | None = None,
) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """
    Generate coordinates for a filled ellipse.

    :param r: Row (y) coordinate of center
    :param c: Column (x) coordinate of center
    :param r_radius: Radius in row (y) direction
    :param c_radius: Radius in column (x) direction
    :param shape: Optional (rows, cols) to clip coordinates
    :returns: Tuple of (row_coords, col_coords)
    """
    if r_radius <= 0 or c_radius <= 0:
        return np.array([], dtype=np.intp), np.array([], dtype=np.intp)

    # Generate grid and check ellipse equation
    y, x = np.ogrid[-r_radius : r_radius + 1, -c_radius : c_radius + 1]
    mask = (x * x) / (c_radius * c_radius) + (y * y) / (r_radius * r_radius) <= 1

    rows, cols = np.where(mask)
    rr = rows + r - r_radius
    cc = cols + c - c_radius

    if shape is not None:
        return _clip_to_shape(rr.astype(np.intp), cc.astype(np.intp), shape)

    return rr.astype(np.intp), cc.astype(np.intp)


def ellipse_perimeter(
    r: int,
    c: int,
    r_radius: int,
    c_radius: int,
    shape: tuple[int, int] | None = None,
) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """
    Generate coordinates for an ellipse perimeter (outline).

    :param r: Row (y) coordinate of center
    :param c: Column (x) coordinate of center
    :param r_radius: Radius in row (y) direction
    :param c_radius: Radius in column (x) direction
    :param shape: Optional (rows, cols) to clip coordinates
    :returns: Tuple of (row_coords, col_coords)
    """
    if r_radius <= 0 or c_radius <= 0:
        return np.array([], dtype=np.intp), np.array([], dtype=np.intp)

    # Parametric ellipse with enough points for smooth curve
    n_points = max(64, int(2 * np.pi * max(r_radius, c_radius)))
    theta = np.linspace(0, 2 * np.pi, n_points, endpoint=False)

    rr = np.round(r + r_radius * np.sin(theta)).astype(np.intp)
    cc = np.round(c + c_radius * np.cos(theta)).astype(np.intp)

    # Remove duplicates while preserving order
    coords = np.column_stack([rr, cc])
    _, idx = np.unique(coords, axis=0, return_index=True)
    idx.sort()
    rr, cc = coords[idx, 0], coords[idx, 1]

    if shape is not None:
        return _clip_to_shape(rr, cc, shape)

    return rr, cc


def line_aa(
    r0: int, c0: int, r1: int, c1: int
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float64]]:
    """
    Generate coordinates for an anti-aliased line using Xiaolin Wu's algorithm.

    Uses Rust backend when available for better performance.

    :param r0: Starting row
    :param c0: Starting column
    :param r1: Ending row
    :param c1: Ending column
    :returns: Tuple of (row_coords, col_coords, alpha_values)
    """
    # Use Rust backend if available
    if USE_RUST_DRAWING and _rust_line_aa is not None:
        rr, cc, aa = _rust_line_aa(r0, c0, r1, c1)
        return rr.astype(np.intp), cc.astype(np.intp), aa

    # Python fallback
    rows = []
    cols = []
    alphas = []

    steep = abs(r1 - r0) > abs(c1 - c0)

    if steep:
        r0, c0 = c0, r0
        r1, c1 = c1, r1

    if c0 > c1:
        c0, c1 = c1, c0
        r0, r1 = r1, r0

    dc = c1 - c0
    dr = r1 - r0

    if dc == 0:
        gradient = 1.0
    else:
        gradient = dr / dc

    # Handle first endpoint
    cend = round(c0)
    rend = r0 + gradient * (cend - c0)
    cgap = 1 - ((c0 + 0.5) % 1)
    cpxl1 = int(cend)
    rpxl1 = int(rend)

    if steep:
        rows.extend([cpxl1, cpxl1])
        cols.extend([rpxl1, rpxl1 + 1])
        alphas.extend([(1 - (rend % 1)) * cgap, (rend % 1) * cgap])
    else:
        rows.extend([rpxl1, rpxl1 + 1])
        cols.extend([cpxl1, cpxl1])
        alphas.extend([(1 - (rend % 1)) * cgap, (rend % 1) * cgap])

    intery = rend + gradient

    # Handle second endpoint
    cend = round(c1)
    rend = r1 + gradient * (cend - c1)
    cgap = (c1 + 0.5) % 1
    cpxl2 = int(cend)
    rpxl2 = int(rend)

    if steep:
        rows.extend([cpxl2, cpxl2])
        cols.extend([rpxl2, rpxl2 + 1])
        alphas.extend([(1 - (rend % 1)) * cgap, (rend % 1) * cgap])
    else:
        rows.extend([rpxl2, rpxl2 + 1])
        cols.extend([cpxl2, cpxl2])
        alphas.extend([(1 - (rend % 1)) * cgap, (rend % 1) * cgap])

    # Main loop
    for c in range(cpxl1 + 1, cpxl2):
        if steep:
            rows.extend([c, c])
            cols.extend([int(intery), int(intery) + 1])
            alphas.extend([1 - (intery % 1), intery % 1])
        else:
            rows.extend([int(intery), int(intery) + 1])
            cols.extend([c, c])
            alphas.extend([1 - (intery % 1), intery % 1])
        intery += gradient

    return (
        np.array(rows, dtype=np.intp),
        np.array(cols, dtype=np.intp),
        np.array(alphas, dtype=np.float64),
    )


def img_as_ubyte(image: NDArray) -> NDArray[np.uint8]:
    """
    Convert image to 8-bit unsigned integer format.

    Replaces skimage.util.dtype.img_as_ubyte.

    :param image: Input array (float [0,1] or other numeric type)
    :returns: Array scaled to uint8 [0, 255]
    """
    image = np.asarray(image)

    if image.dtype == np.uint8:
        return image

    if np.issubdtype(image.dtype, np.floating):
        # Clip to [0, 1] and scale to [0, 255]
        return np.clip(image * 255, 0, 255).astype(np.uint8)

    if np.issubdtype(image.dtype, np.integer):
        # Get the range of the input dtype
        info = np.iinfo(image.dtype)
        # Scale to [0, 255]
        return ((image.astype(np.float64) - info.min) / (info.max - info.min) * 255).astype(
            np.uint8
        )

    raise ValueError(f"Unsupported dtype: {image.dtype}")
