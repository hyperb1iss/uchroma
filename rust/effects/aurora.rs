//! Aurora - Northern lights curtain effect
//!
//! Shimmering vertical curtains with layered sine waves.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray2};
use pyo3::prelude::*;

/// Draw aurora effect into the given matrix.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `gradient` - Color gradient as numpy array of shape (N, 3) with RGB floats
/// * `time` - Animation time in seconds
/// * `speed` - Animation speed multiplier
/// * `drift` - Horizontal drift amount
/// * `curtain_height` - Base curtain height (0.0-1.0)
/// * `shimmer` - High-frequency shimmer intensity
/// * `color_drift` - Color shifting speed
/// * `floor_glow` - Minimum brightness at bottom
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_aurora<'py>(
    _py: Python<'py>,
    width: usize,
    height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    gradient: PyReadonlyArray2<'py, f64>,
    time: f64,
    speed: f64,
    drift: f64,
    curtain_height: f64,
    shimmer: f64,
    color_drift: f64,
    floor_glow: f64,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();

    if glen == 0 {
        return Ok(());
    }

    let _glen_f = glen as f64;
    let h_f = height as f64;

    unsafe {
        let mut array = matrix.as_array_mut();

        for col in 0..width {
            let col_f = col as f64;

            // Curtain height oscillates via layered sines
            let wave1 = (col_f * 0.4 + time * speed).sin();
            let wave2 = (time * drift * 0.7).sin() * 0.5;
            let curtain_h = curtain_height + wave1 * wave2 * 0.3;

            // Convert to row threshold (0 = top, height-1 = bottom)
            let curtain_row = (1.0 - curtain_h) * h_f;

            // Color shifts across columns and time
            let hue_offset = col_f * 3.0 + time * color_drift * 20.0;
            let base_color_idx = (hue_offset as usize) % glen;

            for row in 0..height {
                let row_f = row as f64;

                // Intensity falls off below curtain edge
                let fade_range = h_f * 0.8;
                let intensity_raw = smoothstep(
                    curtain_row + fade_range,
                    curtain_row - 1.0,
                    row_f,
                );

                // Minimum brightness at bottom (aurora glow floor)
                let row_norm = if height > 1 {
                    row_f / (h_f - 1.0)
                } else {
                    0.0
                };
                let min_intensity = floor_glow * row_norm;
                let mut intensity = intensity_raw.max(min_intensity);

                // High-frequency shimmer
                if shimmer > 0.0 {
                    let shimmer_val = (col_f * 2.1 + row_f * 1.3 + time * 8.0).sin()
                        * shimmer
                        * 0.15;
                    intensity = (intensity + shimmer_val).clamp(0.0, 1.0);
                }

                if intensity > 0.01 {
                    // Gradient shifts slightly per row for depth
                    let color_idx = (base_color_idx + row * 2) % glen;
                    array[[row, col, 0]] = grad[[color_idx, 0]];
                    array[[row, col, 1]] = grad[[color_idx, 1]];
                    array[[row, col, 2]] = grad[[color_idx, 2]];
                    array[[row, col, 3]] = intensity;
                } else {
                    array[[row, col, 0]] = 0.0;
                    array[[row, col, 1]] = 0.0;
                    array[[row, col, 2]] = 0.0;
                    array[[row, col, 3]] = 0.0;
                }
            }
        }
    }

    Ok(())
}

/// Smooth interpolation between edges (Hermite polynomial)
#[inline]
fn smoothstep(edge0: f64, edge1: f64, x: f64) -> f64 {
    let t = ((x - edge0) / (edge1 - edge0)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}
