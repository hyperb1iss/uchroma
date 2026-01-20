//! Drawing primitives with anti-aliasing.
//!
//! Rust implementations of the drawing primitives from uchroma/drawing.py.
//! Moves the hot Python loops into Rust for significant speedup.
//!
//! - `circle` - Filled circle
//! - `circle_perimeter_aa` - Xiaolin Wu-style anti-aliased circle perimeter
//! - `ellipse` - Filled ellipse
//! - `ellipse_perimeter` - Ellipse outline
//! - `line_aa` - Xiaolin Wu's anti-aliased line algorithm

use numpy::PyArray1;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::collections::HashSet;
use std::f64::consts::PI;

/// Return type for non-AA drawing functions: (rows, cols) as numpy arrays
type DrawResult = (Py<PyArray1<i64>>, Py<PyArray1<i64>>);

/// Return type for anti-aliased drawing functions: (rows, cols, alphas) as numpy arrays
type AaDrawResult = (Py<PyArray1<i64>>, Py<PyArray1<i64>>, Py<PyArray1<f64>>);

/// Generate coordinates for a filled circle.
///
/// Uses the equation x² + y² <= r² to determine which points are inside.
///
/// # Arguments
/// * `r` - Row (y) coordinate of center
/// * `c` - Column (x) coordinate of center
/// * `radius` - Radius of circle
/// * `shape` - Optional (rows, cols) tuple for clipping coordinates
///
/// # Returns
/// Tuple of (row_coords, col_coords) as numpy arrays
#[pyfunction]
#[pyo3(signature = (r, c, radius, shape=None))]
pub fn circle(
    py: Python<'_>,
    r: i64,
    c: i64,
    radius: i64,
    shape: Option<(i64, i64)>,
) -> PyResult<DrawResult> {
    if radius <= 0 {
        let empty = PyArray1::<i64>::zeros(py, [0], false);
        return Ok((empty.clone().unbind(), empty.unbind()));
    }

    let mut rows: Vec<i64> = Vec::new();
    let mut cols: Vec<i64> = Vec::new();
    let r_sq = radius * radius;

    // Iterate over bounding box and check circle equation
    for dy in -radius..=radius {
        for dx in -radius..=radius {
            if dx * dx + dy * dy <= r_sq {
                let row = r + dy;
                let col = c + dx;

                // Apply shape clipping if provided
                if let Some((h, w)) = shape {
                    if row < 0 || row >= h || col < 0 || col >= w {
                        continue;
                    }
                }

                rows.push(row);
                cols.push(col);
            }
        }
    }

    let rows_arr = PyArray1::from_vec(py, rows);
    let cols_arr = PyArray1::from_vec(py, cols);

    Ok((rows_arr.unbind(), cols_arr.unbind()))
}

/// Generate coordinates for a filled ellipse.
///
/// Uses the equation (x/a)² + (y/b)² <= 1 to determine which points are inside.
///
/// # Arguments
/// * `r` - Row (y) coordinate of center
/// * `c` - Column (x) coordinate of center
/// * `r_radius` - Radius in row (y) direction
/// * `c_radius` - Radius in column (x) direction
/// * `shape` - Optional (rows, cols) tuple for clipping coordinates
///
/// # Returns
/// Tuple of (row_coords, col_coords) as numpy arrays
#[pyfunction]
#[pyo3(signature = (r, c, r_radius, c_radius, shape=None))]
pub fn ellipse(
    py: Python<'_>,
    r: i64,
    c: i64,
    r_radius: i64,
    c_radius: i64,
    shape: Option<(i64, i64)>,
) -> PyResult<DrawResult> {
    if r_radius <= 0 || c_radius <= 0 {
        let empty = PyArray1::<i64>::zeros(py, [0], false);
        return Ok((empty.clone().unbind(), empty.unbind()));
    }

    let mut rows: Vec<i64> = Vec::new();
    let mut cols: Vec<i64> = Vec::new();

    let r_rad_sq = (r_radius * r_radius) as f64;
    let c_rad_sq = (c_radius * c_radius) as f64;

    // Iterate over bounding box and check ellipse equation
    for dy in -r_radius..=r_radius {
        for dx in -c_radius..=c_radius {
            let dy_f = dy as f64;
            let dx_f = dx as f64;

            // Check if point is inside ellipse: (dx/c_radius)² + (dy/r_radius)² <= 1
            if (dx_f * dx_f) / c_rad_sq + (dy_f * dy_f) / r_rad_sq <= 1.0 {
                let row = r + dy;
                let col = c + dx;

                // Apply shape clipping if provided
                if let Some((h, w)) = shape {
                    if row < 0 || row >= h || col < 0 || col >= w {
                        continue;
                    }
                }

                rows.push(row);
                cols.push(col);
            }
        }
    }

    let rows_arr = PyArray1::from_vec(py, rows);
    let cols_arr = PyArray1::from_vec(py, cols);

    Ok((rows_arr.unbind(), cols_arr.unbind()))
}

/// Generate coordinates for an ellipse perimeter (outline).
///
/// Uses parametric representation to generate points around the ellipse.
///
/// # Arguments
/// * `r` - Row (y) coordinate of center
/// * `c` - Column (x) coordinate of center
/// * `r_radius` - Radius in row (y) direction
/// * `c_radius` - Radius in column (x) direction
/// * `shape` - Optional (rows, cols) tuple for clipping coordinates
///
/// # Returns
/// Tuple of (row_coords, col_coords) as numpy arrays
#[pyfunction]
#[pyo3(signature = (r, c, r_radius, c_radius, shape=None))]
pub fn ellipse_perimeter(
    py: Python<'_>,
    r: i64,
    c: i64,
    r_radius: i64,
    c_radius: i64,
    shape: Option<(i64, i64)>,
) -> PyResult<DrawResult> {
    if r_radius <= 0 || c_radius <= 0 {
        let empty = PyArray1::<i64>::zeros(py, [0], false);
        return Ok((empty.clone().unbind(), empty.unbind()));
    }

    // Use enough points for smooth curve
    let max_radius = r_radius.max(c_radius) as f64;
    let n_points = 64.max((2.0 * PI * max_radius) as usize);

    // Use HashSet to deduplicate coordinates
    let mut seen: HashSet<(i64, i64)> = HashSet::with_capacity(n_points);
    let mut rows: Vec<i64> = Vec::new();
    let mut cols: Vec<i64> = Vec::new();

    for i in 0..n_points {
        let theta = 2.0 * PI * (i as f64) / (n_points as f64);

        let row = (r as f64 + (r_radius as f64) * theta.sin()).round() as i64;
        let col = (c as f64 + (c_radius as f64) * theta.cos()).round() as i64;

        // Skip duplicates
        if !seen.insert((row, col)) {
            continue;
        }

        // Apply shape clipping if provided
        if let Some((h, w)) = shape {
            if row < 0 || row >= h || col < 0 || col >= w {
                continue;
            }
        }

        rows.push(row);
        cols.push(col);
    }

    let rows_arr = PyArray1::from_vec(py, rows);
    let cols_arr = PyArray1::from_vec(py, cols);

    Ok((rows_arr.unbind(), cols_arr.unbind()))
}

/// Generate coordinates for an anti-aliased circle perimeter.
///
/// Uses bilinear interpolation for sub-pixel positioning, similar to
/// Xiaolin Wu's algorithm.
///
/// # Arguments
/// * `r` - Row (y) coordinate of center
/// * `c` - Column (x) coordinate of center
/// * `radius` - Radius of circle
/// * `shape` - Optional (rows, cols) tuple for clipping coordinates
///
/// # Returns
/// Tuple of (row_coords, col_coords, alpha_values) as numpy arrays
#[pyfunction]
#[pyo3(signature = (r, c, radius, shape=None))]
pub fn circle_perimeter_aa(
    py: Python<'_>,
    r: i64,
    c: i64,
    radius: i64,
    shape: Option<(i64, i64)>,
) -> PyResult<AaDrawResult> {
    // Handle radius <= 0 case
    if radius <= 0 {
        let empty_i64 = PyArray1::<i64>::zeros(py, [0], false);
        let empty_f64 = PyArray1::<f64>::zeros(py, [0], false);
        return Ok((
            empty_i64.clone().unbind(),
            empty_i64.unbind(),
            empty_f64.unbind(),
        ));
    }

    let radius_f = radius as f64;
    let r_f = r as f64;
    let c_f = c as f64;

    // Generate n_points around the circle with sub-pixel precision
    let n_points = 64.max((2.0 * PI * radius_f * 2.0) as usize);

    // Use HashMap to combine duplicate coordinates by summing alpha
    // Key: (row, col) as i64 pair
    let mut alpha_map: HashMap<(i64, i64), f64> = HashMap::with_capacity(n_points * 4);

    for i in 0..n_points {
        let theta = 2.0 * PI * (i as f64) / (n_points as f64);

        // Exact floating-point positions
        let fr = r_f + radius_f * theta.sin();
        let fc = c_f + radius_f * theta.cos();

        // Integer coordinates surrounding this point
        let r0 = fr.floor() as i64;
        let r1 = fr.ceil() as i64;
        let c0 = fc.floor() as i64;
        let c1 = fc.ceil() as i64;

        // Fractional parts for anti-aliasing
        let fr_frac = fr - (r0 as f64);
        let fc_frac = fc - (c0 as f64);

        // Add all 4 neighboring pixels with bilinear weights
        for (ri, rw) in [(r0, 1.0 - fr_frac), (r1, fr_frac)] {
            for (ci, cw) in [(c0, 1.0 - fc_frac), (c1, fc_frac)] {
                let alpha = rw * cw;
                *alpha_map.entry((ri, ci)).or_insert(0.0) += alpha;
            }
        }
    }

    // Apply shape clipping if provided and collect results
    let (rows, cols, alphas): (Vec<i64>, Vec<i64>, Vec<f64>) = if let Some((h, w)) = shape {
        alpha_map
            .into_iter()
            .filter(|((row, col), _)| *row >= 0 && *row < h && *col >= 0 && *col < w)
            .map(|((row, col), alpha)| (row, col, alpha.clamp(0.0, 1.0)))
            .fold(
                (Vec::new(), Vec::new(), Vec::new()),
                |(mut rs, mut cs, mut as_), (r, c, a)| {
                    rs.push(r);
                    cs.push(c);
                    as_.push(a);
                    (rs, cs, as_)
                },
            )
    } else {
        alpha_map.into_iter().fold(
            (Vec::new(), Vec::new(), Vec::new()),
            |(mut rs, mut cs, mut as_), ((row, col), alpha)| {
                rs.push(row);
                cs.push(col);
                as_.push(alpha.clamp(0.0, 1.0));
                (rs, cs, as_)
            },
        )
    };

    // Convert to numpy arrays
    let rows_arr = PyArray1::from_vec(py, rows);
    let cols_arr = PyArray1::from_vec(py, cols);
    let alphas_arr = PyArray1::from_vec(py, alphas);

    Ok((rows_arr.unbind(), cols_arr.unbind(), alphas_arr.unbind()))
}

/// Generate coordinates for an anti-aliased line using Xiaolin Wu's algorithm.
///
/// # Arguments
/// * `r0` - Starting row
/// * `c0` - Starting column
/// * `r1` - Ending row
/// * `c1` - Ending column
///
/// # Returns
/// Tuple of (row_coords, col_coords, alpha_values) as numpy arrays
#[pyfunction]
pub fn line_aa(py: Python<'_>, r0: i64, c0: i64, r1: i64, c1: i64) -> PyResult<AaDrawResult> {
    let mut rows: Vec<i64> = Vec::new();
    let mut cols: Vec<i64> = Vec::new();
    let mut alphas: Vec<f64> = Vec::new();

    // Work with floats internally
    let mut x0 = c0 as f64;
    let mut y0 = r0 as f64;
    let mut x1 = c1 as f64;
    let mut y1 = r1 as f64;

    let steep = (y1 - y0).abs() > (x1 - x0).abs();

    if steep {
        // Swap x and y
        std::mem::swap(&mut x0, &mut y0);
        std::mem::swap(&mut x1, &mut y1);
    }

    if x0 > x1 {
        // Swap endpoints
        std::mem::swap(&mut x0, &mut x1);
        std::mem::swap(&mut y0, &mut y1);
    }

    let dx = x1 - x0;
    let dy = y1 - y0;

    let gradient = if dx == 0.0 { 1.0 } else { dy / dx };

    // Helper to add a pixel
    let mut add_pixel = |steep: bool, x: i64, y: i64, alpha: f64| {
        if steep {
            rows.push(x);
            cols.push(y);
        } else {
            rows.push(y);
            cols.push(x);
        }
        alphas.push(alpha);
    };

    // Handle first endpoint
    let xend = x0.round();
    let yend = y0 + gradient * (xend - x0);
    let xgap = 1.0 - ((x0 + 0.5) % 1.0);
    let xpxl1 = xend as i64;
    let ypxl1 = yend.floor() as i64;
    let yfrac1 = yend % 1.0;

    add_pixel(steep, xpxl1, ypxl1, (1.0 - yfrac1) * xgap);
    add_pixel(steep, xpxl1, ypxl1 + 1, yfrac1 * xgap);

    let mut intery = yend + gradient;

    // Handle second endpoint
    let xend = x1.round();
    let yend = y1 + gradient * (xend - x1);
    let xgap = (x1 + 0.5) % 1.0;
    let xpxl2 = xend as i64;
    let ypxl2 = yend.floor() as i64;
    let yfrac2 = yend % 1.0;

    add_pixel(steep, xpxl2, ypxl2, (1.0 - yfrac2) * xgap);
    add_pixel(steep, xpxl2, ypxl2 + 1, yfrac2 * xgap);

    // Main loop
    for x in (xpxl1 + 1)..xpxl2 {
        let y = intery.floor() as i64;
        let frac = intery % 1.0;

        add_pixel(steep, x, y, 1.0 - frac);
        add_pixel(steep, x, y + 1, frac);

        intery += gradient;
    }

    // Convert to numpy arrays
    let rows_arr = PyArray1::from_vec(py, rows);
    let cols_arr = PyArray1::from_vec(py, cols);
    let alphas_arr = PyArray1::from_vec(py, alphas);

    Ok((rows_arr.unbind(), cols_arr.unbind(), alphas_arr.unbind()))
}
