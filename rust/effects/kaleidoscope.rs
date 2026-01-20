//! Kaleidoscope - Rotating symmetric patterns
//!
//! Symmetric patterns that rotate and morph using polar coordinate
//! transforms and n-fold symmetry.

use numpy::{PyArray1, PyArray3, PyArrayMethods, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use std::f64::consts::PI;

const MODE_SPIRAL: u8 = 0;
const MODE_RINGS: u8 = 1;
const MODE_WAVES: u8 = 2;

/// Draw kaleidoscope effect into the given matrix.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels (for API consistency, matrix shape used internally)
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `gradient` - Color gradient as numpy array of shape (N, 3) with RGB floats
/// * `polar_map` - Pre-computed polar coordinates as flat array [angle, radius, ...]
/// * `time` - Animation time in seconds
/// * `symmetry` - Number of symmetry folds (3-12)
/// * `rotation_speed` - Rotation speed multiplier
/// * `pattern_mode` - Pattern type: 0=spiral, 1=rings, 2=waves
/// * `ring_frequency` - Ring/spiral frequency
/// * `spiral_twist` - Spiral twist factor
/// * `hue_rotation` - Color rotation speed
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_kaleidoscope<'py>(
    _py: Python<'py>,
    width: usize,
    #[allow(unused_variables)] height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    gradient: PyReadonlyArray2<'py, f64>,
    polar_map: PyReadonlyArray1<'py, f64>,
    time: f64,
    symmetry: usize,
    rotation_speed: f64,
    pattern_mode: u8,
    ring_frequency: f64,
    spiral_twist: f64,
    hue_rotation: f64,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();
    let polar = polar_map.as_array();

    if glen == 0 {
        return Ok(());
    }

    let glen_f = glen as f64;
    let wedge = 2.0 * PI / symmetry as f64;

    unsafe {
        let mut array = matrix.as_array_mut();
        let num_pixels = polar.len() / 2;

        for idx in 0..num_pixels {
            let angle = polar[idx * 2];
            let radius = polar[idx * 2 + 1];

            let row = idx / width;
            let col = idx % width;

            // Apply rotation
            let rotated_angle = angle - time * rotation_speed;

            // Apply n-fold symmetry (fold into first wedge)
            let mut sym_angle = rotated_angle.rem_euclid(wedge);

            // Mirror for kaleidoscope effect
            if ((rotated_angle / wedge) as i64) % 2 == 1 {
                sym_angle = wedge - sym_angle;
            }

            // Pattern value based on mode
            let value = match pattern_mode {
                MODE_RINGS => (radius * ring_frequency * 3.0 + time * 2.0).sin(),
                MODE_SPIRAL => (radius * ring_frequency + sym_angle * spiral_twist + time).sin(),
                MODE_WAVES => {
                    (sym_angle * 4.0 + time * 2.0).sin() * (radius * ring_frequency).cos()
                }
                _ => (radius * ring_frequency + sym_angle * spiral_twist + time).sin(),
            };

            // Color from symmetric angle + time rotation
            let hue_idx =
                ((sym_angle / wedge) * glen_f * 0.5 + time * hue_rotation) as usize % glen;
            let r = grad[[hue_idx, 0]];
            let g = grad[[hue_idx, 1]];
            let b = grad[[hue_idx, 2]];

            // Brightness: never fully dark (0.3 to 1.0)
            let brightness = (value + 1.0) / 2.0 * 0.7 + 0.3;

            array[[row, col, 0]] = r * brightness;
            array[[row, col, 1]] = g * brightness;
            array[[row, col, 2]] = b * brightness;
            array[[row, col, 3]] = 1.0;
        }
    }

    Ok(())
}

/// Pre-compute polar coordinates for a given dimension.
///
/// Returns a flat array of [angle0, radius0, angle1, radius1, ...] for each pixel
/// in row-major order.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels
#[pyfunction]
pub fn compute_polar_map<'py>(
    py: Python<'py>,
    width: usize,
    height: usize,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let cx = width as f64 / 2.0;
    let cy = height as f64 / 2.0;
    let aspect = width as f64 / height as f64;

    let mut result = Vec::with_capacity(width * height * 2);

    for row in 0..height {
        for col in 0..width {
            let dx = col as f64 - cx;
            let dy = (row as f64 - cy) / aspect;
            let angle = dy.atan2(dx);
            let radius = (dx * dx + dy * dy).sqrt();
            result.push(angle);
            result.push(radius);
        }
    }

    Ok(PyArray1::from_vec(py, result))
}
