//! Vortex - Hypnotic spiral tunnel effect
//!
//! A swirling vortex with spiral arms flowing inward or outward,
//! creating a mesmerizing tunnel effect using polar coordinate transforms.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use std::f64::consts::PI;

/// Draw vortex effect into the given matrix.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels (for API consistency)
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `gradient` - Color gradient as numpy array of shape (N, 3) with RGB floats
/// * `polar_map` - Pre-computed polar coordinates as flat array [angle, radius, ...]
/// * `time` - Animation time in seconds
/// * `arm_count` - Number of spiral arms (1-6)
/// * `twist` - Spiral twist factor
/// * `flow_speed` - Speed of radial flow
/// * `flow_direction` - Direction of flow (-1 outward, 1 inward)
/// * `rotation_speed` - Rotation speed multiplier
/// * `center_glow` - Center glow radius
/// * `ring_density` - Density of depth rings
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_vortex<'py>(
    _py: Python<'py>,
    width: usize,
    #[allow(unused_variables)] height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    gradient: PyReadonlyArray2<'py, f64>,
    polar_map: PyReadonlyArray1<'py, f64>,
    time: f64,
    arm_count: usize,
    twist: f64,
    flow_speed: f64,
    flow_direction: i32,
    rotation_speed: f64,
    center_glow: f64,
    ring_density: f64,
) -> PyResult<()> {
    let grad = gradient.as_array();
    let glen = grad.nrows();
    let polar = polar_map.as_array();

    if glen == 0 {
        return Ok(());
    }

    let glen_f = glen as f64;
    let flow_dir = flow_direction as f64;

    unsafe {
        let mut array = matrix.as_array_mut();
        let num_pixels = polar.len() / 2;

        for idx in 0..num_pixels {
            let angle = polar[idx * 2];
            let radius = polar[idx * 2 + 1];

            let row = idx / width;
            let col = idx % width;

            // Spiral: angle offset by radius creates twist
            let spiral_angle = angle - radius * twist - time * rotation_speed;

            // Multiple spiral arms
            let arm_value = (spiral_angle * arm_count as f64).sin();

            // Radial "depth" rings
            let depth_value = (radius * ring_density * 2.0 - time * flow_speed * flow_dir).sin();

            // Combine spiral and depth
            let value = arm_value * 0.5 + depth_value * 0.5;

            // Color: hue from angle
            let hue_idx = ((angle / PI + 1.0) * (glen_f / 2.0) + time * 30.0) as usize % glen;
            let r = grad[[hue_idx, 0]];
            let g = grad[[hue_idx, 1]];
            let b = grad[[hue_idx, 2]];

            // Brightness from combined value (0.4 to 1.0)
            let mut brightness = (value + 1.0) / 2.0 * 0.6 + 0.4;

            // Center glow boost
            if radius < center_glow {
                let sigma = center_glow / 2.0;
                let center_boost = (-radius * radius / (2.0 * sigma * sigma)).exp();
                brightness = (brightness + center_boost * 0.4).min(1.0);
            }

            array[[row, col, 0]] = r * brightness;
            array[[row, col, 1]] = g * brightness;
            array[[row, col, 2]] = b * brightness;
            array[[row, col, 3]] = 1.0;
        }
    }

    Ok(())
}
