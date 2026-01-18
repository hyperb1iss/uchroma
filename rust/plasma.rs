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
/// * `scale` - Pattern scale/zoom (1.0 = default, higher = zoomed in)
/// * `complexity` - Number of wave layers (1-4)
/// * `turbulence` - Chaos factor (0.0 = smooth, 1.0 = wild)
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_plasma<'py>(
    _py: Python<'py>,
    width: f64,
    height: f64,
    matrix: &Bound<'py, PyArray3<f64>>,
    duration: f64,
    gradient: PyReadonlyArray2<'py, f64>,
    scale: f64,
    complexity: i32,
    turbulence: f64,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();

    if glen == 0 {
        return Ok(());
    }

    let w = width as usize;
    let h = height as usize;
    let glen_f = glen as f64;

    // Scale factor (invert so higher = zoomed in / larger blobs)
    let inv_scale = 1.0 / scale;

    // Pre-compute duration-dependent values (loop invariants)
    let sin_d2 = (duration / 2.0).sin();
    let cos_d3 = (duration / 3.0).cos();
    let sin_d5 = (duration / 5.0).sin();
    let cos_d7 = (duration / 7.0).cos();
    let sin_d11 = (duration / 11.0).sin();
    let aspect = width / height;
    let inv_height_aspect = inv_scale / (height * aspect);
    let inv_width = inv_scale / width;

    // Turbulence phase offsets (time-varying chaos)
    let turb_x = turbulence * (duration * 3.7).sin();
    let turb_y = turbulence * (duration * 2.3).cos();

    // Write directly to numpy array - no intermediate buffer
    unsafe {
        let mut array = matrix.as_array_mut();

        for row in 0..h {
            let y_base = (row as f64) * inv_height_aspect;
            let y = y_base + turb_y * (row as f64 * 0.1).sin();
            let cy = y * cos_d3;
            let y_term = y * cos_d3;

            for col in 0..w {
                let x_base = (col as f64) * inv_width;
                let x = x_base + turb_x * (col as f64 * 0.1).cos();

                // Layer 1: diagonal waves
                let val1 = (2.0 * (x * sin_d2 + y_term) + duration).sin();

                // Layer 2: radial ripples
                let cx = x * sin_d5;
                let val2 = ((20.0 * (cx * cx + cy * cy) + 1.0).sqrt() + duration).sin();

                // Layer 3: swirling vortex
                let val3 = if complexity >= 3 {
                    let angle = y.atan2(x) + duration * 0.5;
                    let dist = (x * x + y * y).sqrt();
                    (angle * 3.0 + dist * 5.0 * cos_d7).sin()
                } else {
                    0.0
                };

                // Layer 4: interference pattern
                let val4 = if complexity >= 4 {
                    let wave_x = (x * 8.0 + duration).sin();
                    let wave_y = (y * 8.0 - duration * 0.7).sin();
                    wave_x * wave_y * sin_d11
                } else {
                    0.0
                };

                // Combine layers based on complexity
                let val = match complexity {
                    1 => val1 * 2.0,
                    2 => val1 + val2,
                    3 => val1 + val2 + val3 * 0.7,
                    _ => val1 + val2 + val3 * 0.5 + val4 * 0.5,
                };

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
