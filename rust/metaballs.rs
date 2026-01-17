//! Metaballs effect renderer
//!
//! Organic blob fusion effect - classic demoscene algorithm.
//! Blobs drift, merge when close, and split apart like a lava lamp.
//!
//! Optimizations:
//! - Pre-squared radii to avoid sqrt in hot loop
//! - Direct numpy buffer writes (no intermediate allocation)
//! - Branchless field accumulation

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray2};
use pyo3::prelude::*;

/// Blob data packed for efficient iteration.
#[derive(Clone, Copy)]
struct Blob {
    x: f64,
    y: f64,
    radius_sq: f64,
    hue_idx: usize,
}

/// Draw metaballs effect into the given matrix.
///
/// # Arguments
/// * `width` - Frame width in pixels
/// * `height` - Frame height in pixels
/// * `matrix` - Target numpy array of shape (height, width, 4) for RGBA output
/// * `blobs` - Blob data as numpy array of shape (N, 4): [x, y, radius, hue_idx]
/// * `gradient` - Color gradient as numpy array of shape (N, 3) with RGB floats
/// * `threshold` - Field threshold for blob boundary (typically 1.0)
/// * `glow_falloff` - Brightness falloff rate (typically 2.0)
/// * `base_brightness` - Background brightness (typically 0.2)
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn draw_metaballs<'py>(
    _py: Python<'py>,
    width: usize,
    height: usize,
    matrix: &Bound<'py, PyArray3<f64>>,
    blobs: PyReadonlyArray2<'py, f64>,
    gradient: PyReadonlyArray2<'py, f64>,
    threshold: f64,
    glow_falloff: f64,
    base_brightness: f64,
) -> PyResult<()> {
    let blob_data = blobs.as_array();
    let grad = gradient.as_array();
    let grad_len = grad.nrows();

    if grad_len == 0 {
        return Ok(());
    }

    // Convert blob data to struct for cache efficiency
    let blobs: Vec<Blob> = (0..blob_data.nrows())
        .map(|i| {
            let radius = blob_data[[i, 2]];
            Blob {
                x: blob_data[[i, 0]],
                y: blob_data[[i, 1]],
                radius_sq: radius * radius,
                hue_idx: blob_data[[i, 3]] as usize,
            }
        })
        .collect();

    let half_thresh = threshold * 0.5;
    let bg_r = base_brightness * 0.3;
    let bg_g = base_brightness * 0.2;
    let bg_b = base_brightness * 0.4;

    // Write directly to numpy array
    unsafe {
        let mut array = matrix.as_array_mut();

        for row in 0..height {
            let row_f = row as f64;

            for col in 0..width {
                let col_f = col as f64;
                let mut field = 0.0;
                let mut total_weight = 0.0;
                let mut weighted_hue = 0.0;

                // Accumulate field contribution from each blob
                for blob in &blobs {
                    let dx = col_f - blob.x;
                    let dy = row_f - blob.y;
                    let dist_sq = dx * dx + dy * dy + 0.1;

                    let contribution = blob.radius_sq / dist_sq;
                    field += contribution;

                    let blob_hue = (blob.hue_idx * 60) % grad_len;
                    weighted_hue += blob_hue as f64 * contribution;
                    total_weight += contribution;
                }

                // Determine pixel color based on field value
                let (r, g, b) = if field > threshold {
                    // Inside blob - full brightness with falloff
                    let brightness = ((field - threshold) * glow_falloff * 0.5 + 0.5).min(1.0);
                    let hue_idx = ((weighted_hue / total_weight) as usize) % grad_len;
                    (
                        grad[[hue_idx, 0]] * brightness,
                        grad[[hue_idx, 1]] * brightness,
                        grad[[hue_idx, 2]] * brightness,
                    )
                } else if field > half_thresh {
                    // Glow region - partial brightness
                    let glow = (field - half_thresh) / half_thresh;
                    let brightness = base_brightness + glow * 0.3;
                    let hue_idx = ((weighted_hue / total_weight) as usize) % grad_len;
                    (
                        grad[[hue_idx, 0]] * brightness,
                        grad[[hue_idx, 1]] * brightness,
                        grad[[hue_idx, 2]] * brightness,
                    )
                } else {
                    // Background
                    (bg_r, bg_g, bg_b)
                };

                array[[row, col, 0]] = r;
                array[[row, col, 1]] = g;
                array[[row, col, 2]] = b;
                array[[row, col, 3]] = 1.0;
            }
        }
    }

    Ok(())
}
