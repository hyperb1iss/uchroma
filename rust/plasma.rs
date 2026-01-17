//! Plasma effect renderer
//!
//! Classic demoscene plasma using layered sine waves.
//! Optimizations:
//! - Pre-computed trig values for duration-dependent terms
//! - Direct numpy buffer writes (no intermediate allocation)

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray2};
use pyo3::prelude::*;
use std::f64::consts::PI;

/// Draw a plasma effect into the given matrix.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `duration` - Animation time parameter (elapsed seconds)
/// * `gradient` - Color gradient as numpy array of shape (N, 3) with RGB floats
#[pyfunction]
pub fn draw_plasma<'py>(
    _py: Python<'py>,
    width: f64,
    height: f64,
    matrix: &Bound<'py, PyArray3<f64>>,
    duration: f64,
    gradient: PyReadonlyArray2<'py, f64>,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();

    if glen == 0 {
        return Ok(());
    }

    let w = width as usize;
    let h = height as usize;
    let glen_f = glen as f64;

    // Pre-compute duration-dependent values (loop invariants)
    let sin_d2 = (duration / 2.0).sin();
    let cos_d3 = (duration / 3.0).cos();
    let sin_d5 = (duration / 5.0).sin();
    let aspect = width / height;
    let inv_height_aspect = 1.0 / (height * aspect);
    let inv_width = 1.0 / width;

    // Write directly to numpy array - no intermediate buffer
    unsafe {
        let mut array = matrix.as_array_mut();

        for row in 0..h {
            let y = (row as f64) * inv_height_aspect;
            let cy = y * cos_d3;
            let y_term = y * cos_d3;

            for col in 0..w {
                let x = (col as f64) * inv_width;

                // First plasma component
                let val1 = (2.0 * (x * sin_d2 + y_term) + duration).sin();

                // Second plasma component (radial)
                let cx = x * sin_d5;
                let val2 = ((20.0 * (cx * cx + cy * cy) + 1.0).sqrt() + duration).sin();

                let val = val1 + val2;

                // Map to gradient position
                let pos = glen_f * ((1.0 + (PI * val).sin()) / 2.0);
                let idx = (pos as usize).saturating_sub(1).min(glen - 1);

                // Write RGBA directly
                array[[row, col, 0]] = grad[[idx, 0]];
                array[[row, col, 1]] = grad[[idx, 1]];
                array[[row, col, 2]] = grad[[idx, 2]];
                array[[row, col, 3]] = 1.0;
            }
        }
    }

    Ok(())
}
