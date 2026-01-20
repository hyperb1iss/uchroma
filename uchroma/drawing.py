"""
Drawing primitives implemented in Rust.

All drawing functions are implemented in Rust for performance and consistency.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from uchroma._native import (
    circle as _rust_circle,
    circle_perimeter_aa as _rust_circle_perimeter_aa,
    ellipse as _rust_ellipse,
    ellipse_perimeter as _rust_ellipse_perimeter,
    line_aa as _rust_line_aa,
)


def _normalize_shape(shape: tuple | None) -> tuple[int, int] | None:
    """Normalize shape tuple to 2-tuple (height, width) for Rust backend."""
    if shape is None:
        return None
    return (shape[0], shape[1])


def circle(
    r: int, c: int, radius: int, shape: tuple[int, int] | None = None
) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """
    Generate coordinates for a filled circle.

    :param r: Row (y) coordinate of center
    :param c: Column (x) coordinate of center
    :param radius: Radius of circle
    :param shape: Optional (rows, cols) to clip coordinates
    :returns: Tuple of (row_coords, col_coords)
    """
    rr, cc = _rust_circle(r, c, radius, _normalize_shape(shape))
    return rr.astype(np.intp), cc.astype(np.intp)


def circle_perimeter_aa(
    r: int, c: int, radius: int, shape: tuple[int, int] | None = None
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float64]]:
    """
    Generate coordinates for an anti-aliased circle perimeter.

    Uses bilinear interpolation for sub-pixel positioning.

    :param r: Row (y) coordinate of center
    :param c: Column (x) coordinate of center
    :param radius: Radius of circle
    :param shape: Optional (rows, cols) to clip coordinates
    :returns: Tuple of (row_coords, col_coords, alpha_values)
    """
    rr, cc, aa = _rust_circle_perimeter_aa(r, c, radius, _normalize_shape(shape))
    return rr.astype(np.intp), cc.astype(np.intp), aa


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
    rr, cc = _rust_ellipse(r, c, r_radius, c_radius, _normalize_shape(shape))
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
    rr, cc = _rust_ellipse_perimeter(r, c, r_radius, c_radius, _normalize_shape(shape))
    return rr.astype(np.intp), cc.astype(np.intp)


def line_aa(
    r0: int, c0: int, r1: int, c1: int
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float64]]:
    """
    Generate coordinates for an anti-aliased line using Xiaolin Wu's algorithm.

    :param r0: Starting row
    :param c0: Starting column
    :param r1: Ending row
    :param c1: Ending column
    :returns: Tuple of (row_coords, col_coords, alpha_values)
    """
    rr, cc, aa = _rust_line_aa(r0, c0, r1, c1)
    return rr.astype(np.intp), cc.astype(np.intp), aa


def img_as_ubyte(image: NDArray) -> NDArray[np.uint8]:
    """
    Convert image to 8-bit unsigned integer format.

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
