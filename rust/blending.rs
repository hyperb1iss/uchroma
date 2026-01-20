//! Blend mode implementations for layer compositing.
//!
//! All blend modes operate on RGBA f64 arrays with shape (height, width, 4).
//! Input arrays are read-only views, output is written in-place.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray3};
use pyo3::prelude::*;

/// Screen blend mode: 1 - (1-a)(1-b)
/// Lightens the image, commonly used as default blend.
#[pyfunction]
pub fn blend_screen<'py>(
    _py: Python<'py>,
    img_in: PyReadonlyArray3<'py, f64>,
    img_layer: PyReadonlyArray3<'py, f64>,
    output: &Bound<'py, PyArray3<f64>>,
) -> PyResult<()> {
    let base = img_in.as_array();
    let layer = img_layer.as_array();

    unsafe {
        let mut out = output.as_array_mut();
        let shape = base.shape();
        let (h, w, _) = (shape[0], shape[1], shape[2]);

        for row in 0..h {
            for col in 0..w {
                for c in 0..3 {
                    let b = base[[row, col, c]];
                    let l = layer[[row, col, c]];
                    out[[row, col, c]] = 1.0 - (1.0 - b) * (1.0 - l);
                }
            }
        }
    }
    Ok(())
}
