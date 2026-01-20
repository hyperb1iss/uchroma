//! Compositor operations for final frame output.
//!
//! Converts RGBA float layers to RGB uint8 for hardware output.
//! The `rgba2rgb` function is the last step before sending frames to hardware.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray3};
use pyo3::prelude::*;

/// Convert RGBA f64 layer to RGB u8 for hardware output.
///
/// Alpha-composites the input against a background color and converts
/// to uint8 [0-255] ready for hardware transmission.
///
/// # Arguments
/// * `arr` - Input RGBA f64 array shape (height, width, 4)
/// * `output` - Output RGB u8 array shape (height, width, 3), written in-place
/// * `bg_r` - Background red component (0.0..1.0)
/// * `bg_g` - Background green component (0.0..1.0)
/// * `bg_b` - Background blue component (0.0..1.0)
///
/// # Formula
/// ```text
/// out_r = (1.0 - alpha) * bg_r + alpha * r
/// out_g = (1.0 - alpha) * bg_g + alpha * g
/// out_b = (1.0 - alpha) * bg_b + alpha * b
/// // Then clamped to [0.0, 1.0] and scaled to u8 [0, 255]
/// ```
#[pyfunction]
pub fn rgba2rgb<'py>(
    _py: Python<'py>,
    arr: PyReadonlyArray3<'py, f64>,
    output: &Bound<'py, PyArray3<u8>>,
    bg_r: f64,
    bg_g: f64,
    bg_b: f64,
) -> PyResult<()> {
    let input = arr.as_array();
    let shape = input.shape();

    debug_assert_eq!(shape[2], 4, "Input must have 4 channels (RGBA)");

    let (h, w) = (shape[0], shape[1]);
    let bg = [bg_r, bg_g, bg_b];

    // SAFETY: We have exclusive write access to output through PyO3's borrow rules
    unsafe {
        let mut out = output.as_array_mut();

        for row in 0..h {
            for col in 0..w {
                let alpha = input[[row, col, 3]];
                let inv_alpha = 1.0 - alpha;

                for c in 0..3 {
                    let src = input[[row, col, c]];
                    let composited = inv_alpha * bg[c] + alpha * src;
                    let clamped = composited.clamp(0.0, 1.0);
                    out[[row, col, c]] = (clamped * 255.0) as u8;
                }
            }
        }
    }

    Ok(())
}
