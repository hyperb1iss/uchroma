//! Nebula - Flowing space clouds effect
//!
//! Soft, colorful clouds using layered noise (FBM).

use numpy::ndarray::ArrayView2;
use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray2};
use pyo3::prelude::*;

const NOISE_SIZE: usize = 64;

/// Draw a nebula effect into the given matrix.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `gradient` - Color gradient as numpy array of shape (N, 3) with RGB floats
/// * `noise_table` - Pre-generated noise lookup table (64x64 random values)
/// * `time` - Animation time in seconds
/// * `drift_speed` - How fast clouds drift
/// * `scale` - Pattern scale (noise sampling density)
/// * `octaves` - Number of FBM layers (detail level)
/// * `contrast` - Color contrast (0.3-1.0)
/// * `base_brightness` - Minimum brightness
/// * `color_shift` - Secondary noise color shifting
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_nebula<'py>(
    _py: Python<'py>,
    width: usize,
    height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    gradient: PyReadonlyArray2<'py, f64>,
    noise_table: PyReadonlyArray2<'py, f64>,
    time: f64,
    drift_speed: f64,
    scale: f64,
    octaves: usize,
    contrast: f64,
    base_brightness: f64,
    color_shift: f64,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();
    let noise = noise_table.as_array();

    if glen == 0 {
        return Ok(());
    }

    let glen_f = glen as f64;
    let t = time * drift_speed;
    let scale_adj = scale * 10.0;

    unsafe {
        let mut array = matrix.as_array_mut();

        for row in 0..height {
            for col in 0..width {
                let nx = col as f64 * scale_adj + t * 3.0;
                let ny = row as f64 * scale_adj + t * 2.0;

                // Primary noise for cloud shape
                let n1 = fbm(&noise, nx, ny, octaves);

                // Secondary noise for color variation
                let n2 = fbm(&noise, nx * 0.7 + 100.0, ny * 0.7 + 100.0, octaves);

                // Map to gradient position
                let grad_pos = (n1 * contrast + (1.0 - contrast) * 0.5).clamp(0.0, 1.0);
                let mut color_idx = (grad_pos * (glen_f - 1.0)) as usize;

                // Color shift from secondary noise
                if color_shift > 0.0 {
                    let shift = ((n2 - 0.5) * color_shift * glen_f * 0.5) as i64;
                    color_idx = ((color_idx as i64 + shift).rem_euclid(glen as i64)) as usize;
                }

                let r = grad[[color_idx, 0]];
                let g = grad[[color_idx, 1]];
                let b = grad[[color_idx, 2]];

                // Brightness modulated by secondary noise
                let brightness = (base_brightness + n2 * 0.3).clamp(0.3, 1.0);

                array[[row, col, 0]] = r * brightness;
                array[[row, col, 1]] = g * brightness;
                array[[row, col, 2]] = b * brightness;
                array[[row, col, 3]] = 1.0;
            }
        }
    }

    Ok(())
}

/// Sample noise table with bilinear interpolation and smoothstep.
#[inline]
fn sample_noise(noise: &ArrayView2<f64>, x: f64, y: f64) -> f64 {
    let size = NOISE_SIZE as f64;
    let x = x.rem_euclid(size);
    let y = y.rem_euclid(size);

    let x0 = (x as usize) % NOISE_SIZE;
    let y0 = (y as usize) % NOISE_SIZE;
    let x1 = (x0 + 1) % NOISE_SIZE;
    let y1 = (y0 + 1) % NOISE_SIZE;

    let fx = x - x.floor();
    let fy = y - y.floor();

    // Smoothstep interpolation
    let fx = fx * fx * (3.0 - 2.0 * fx);
    let fy = fy * fy * (3.0 - 2.0 * fy);

    let v00 = noise[[y0, x0]];
    let v10 = noise[[y0, x1]];
    let v01 = noise[[y1, x0]];
    let v11 = noise[[y1, x1]];

    let v0 = v00 + (v10 - v00) * fx;
    let v1 = v01 + (v11 - v01) * fx;

    v0 + (v1 - v0) * fy
}

/// Fractal Brownian Motion - layered noise for organic shapes.
#[inline]
fn fbm(noise: &ArrayView2<f64>, x: f64, y: f64, octaves: usize) -> f64 {
    let mut value = 0.0;
    let mut amplitude = 1.0;
    let mut frequency = 1.0;
    let mut max_value = 0.0;

    for _ in 0..octaves {
        value += sample_noise(noise, x * frequency, y * frequency) * amplitude;
        max_value += amplitude;
        amplitude *= 0.5;
        frequency *= 2.0;
    }

    value / max_value
}
