//! Embers - Glowing particle field effect
//!
//! Renders particles with Gaussian glow falloff.
//! Particle state management stays in Python; Rust handles rendering.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray1};
use pyo3::prelude::*;

/// Render embers particles with Gaussian glow.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `particles` - Flat array [x0, y0, brightness0, radius0, x1, y1, brightness1, radius1, ...]
/// * `color_r` - Red component of ember color (0.0-1.0)
/// * `color_g` - Green component of ember color (0.0-1.0)
/// * `color_b` - Blue component of ember color (0.0-1.0)
/// * `ambient_factor` - Background warmth factor (0.0-1.0)
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_embers<'py>(
    _py: Python<'py>,
    width: usize,
    height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    particles: PyReadonlyArray1<'py, f64>,
    color_r: f64,
    color_g: f64,
    color_b: f64,
    ambient_factor: f64,
) -> PyResult<()> {
    let parts = particles.as_array();
    let num_particles = parts.len() / 4;

    unsafe {
        let mut array = matrix.as_array_mut();

        // Fill with ambient warmth (cooler on G/B channels for warm glow)
        let ambient_r = color_r * ambient_factor;
        let ambient_g = color_g * ambient_factor * 0.6;
        let ambient_b = color_b * ambient_factor * 0.4;

        for row in 0..height {
            for col in 0..width {
                array[[row, col, 0]] = ambient_r;
                array[[row, col, 1]] = ambient_g;
                array[[row, col, 2]] = ambient_b;
                array[[row, col, 3]] = 1.0;
            }
        }

        // Render each particle with Gaussian glow
        for i in 0..num_particles {
            let px = parts[i * 4];
            let py = parts[i * 4 + 1];
            let brightness = parts[i * 4 + 2];
            let radius = parts[i * 4 + 3];

            let radius_sq = radius * radius;
            let sigma_sq = radius_sq / 2.0;

            // Compute bounding box for this particle
            let min_row = ((py - radius - 1.0).max(0.0)) as usize;
            let max_row = ((py + radius + 2.0).min(height as f64)) as usize;
            let min_col = ((px - radius - 1.0).max(0.0)) as usize;
            let max_col = ((px + radius + 2.0).min(width as f64)) as usize;

            for row in min_row..max_row {
                for col in min_col..max_col {
                    let dx = col as f64 - px;
                    let dy = row as f64 - py;
                    let dist_sq = dx * dx + dy * dy;

                    if dist_sq < radius_sq * 2.0 {
                        let glow = brightness * (-dist_sq / sigma_sq).exp();

                        // Additive blend
                        array[[row, col, 0]] = (array[[row, col, 0]] + color_r * glow).min(1.0);
                        array[[row, col, 1]] = (array[[row, col, 1]] + color_g * glow).min(1.0);
                        array[[row, col, 2]] = (array[[row, col, 2]] + color_b * glow).min(1.0);
                    }
                }
            }
        }
    }

    Ok(())
}
