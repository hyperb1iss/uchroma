//! Ocean - Rolling wave caustics effect
//!
//! Horizontal waves with caustic highlights on crests.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray2};
use pyo3::prelude::*;

/// Wave component: (frequency, amplitude, speed, phase)
const WAVES: [(f64, f64, f64, f64); 3] = [
    (0.3, 0.4, 1.0, 0.0),
    (0.5, 0.25, 1.3, 2.1),
    (0.8, 0.15, 0.7, 4.2),
];

/// Draw ocean effect into the given matrix.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_ocean<'py>(
    _py: Python<'py>,
    width: usize,
    height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    gradient: PyReadonlyArray2<'py, f64>,
    time: f64,
    wave_speed: f64,
    wave_height: f64,
    foam_threshold: f64,
    caustic_intensity: f64,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();

    if glen == 0 {
        return Ok(());
    }

    let h_f = height as f64;
    let t = time * wave_speed;
    let surface_rows = 3.min(height);
    let surface_scale = if surface_rows > 0 {
        1.0 / surface_rows as f64
    } else {
        0.0
    };

    unsafe {
        let mut array = matrix.as_array_mut();

        for col in 0..width {
            let col_f = col as f64;

            // Sum wave heights at this column
            let mut height_val = 0.0;
            let mut slope = 0.0;
            for (freq, amp, spd, phase) in WAVES {
                height_val += amp * (col_f * freq - t * spd + phase).sin();
                slope += amp * freq * (col_f * freq - t * spd + phase).cos();
            }
            height_val *= wave_height;
            slope *= wave_height;

            for row in 0..height {
                // Depth: 0 = surface (top), 1 = deep (bottom)
                let depth = if height > 1 {
                    row as f64 / (h_f - 1.0)
                } else {
                    0.0
                };

                // Base color from gradient (deep to surface)
                let grad_idx = ((1.0 - depth) * (glen as f64 - 1.0)) as usize;
                let mut r = grad[[grad_idx, 0]];
                let mut g = grad[[grad_idx, 1]];
                let mut b = grad[[grad_idx, 2]];

                // Brightness: surface is brighter
                let mut brightness = 0.5 + (1.0 - depth) * 0.4;

                // Wave height affects surface brightness (caustics)
                if row < surface_rows {
                    let wave_effect = (height_val + 1.0) / 2.0;
                    let surface_factor = (surface_rows - row) as f64 * surface_scale;
                    brightness += wave_effect * caustic_intensity * surface_factor;
                }

                // Foam on steep slopes at surface
                if slope.abs() > foam_threshold && row < surface_rows {
                    let surface_factor = (surface_rows - row) as f64 * surface_scale;
                    r += (1.0 - r) * surface_factor;
                    g += (1.0 - g) * surface_factor;
                    b += (1.0 - b) * surface_factor;
                    brightness = (brightness + surface_factor * 0.3).min(1.0);
                }

                brightness = brightness.min(1.0);

                array[[row, col, 0]] = r * brightness;
                array[[row, col, 1]] = g * brightness;
                array[[row, col, 2]] = b * brightness;
                array[[row, col, 3]] = 1.0;
            }
        }
    }

    Ok(())
}
