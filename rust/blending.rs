//! Blend mode implementations for layer compositing.
//!
//! All blend modes operate on RGBA f64 arrays with shape (height, width, 4).
//! Input arrays are read-only views, output is written in-place.

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray3};
use pyo3::prelude::*;

/// Macro for simple blend modes that operate element-wise on RGB channels.
/// Generates a #[pyfunction] with the standard signature.
macro_rules! simple_blend {
    ($name:ident, |$b:ident, $l:ident| $formula:expr) => {
        #[pyfunction]
        pub fn $name<'py>(
            _py: Python<'py>,
            img_in: PyReadonlyArray3<'py, f64>,
            img_layer: PyReadonlyArray3<'py, f64>,
            output: &Bound<'py, PyArray3<f64>>,
        ) -> PyResult<()> {
            let base = img_in.as_array();
            let layer = img_layer.as_array();

            debug_assert_eq!(base.shape(), layer.shape(), "Input shapes must match");
            debug_assert!(base.shape()[2] >= 3, "Arrays must have at least 3 channels");

            unsafe {
                let mut out = output.as_array_mut();
                let shape = base.shape();
                let (h, w) = (shape[0], shape[1]);

                for row in 0..h {
                    for col in 0..w {
                        for c in 0..3 {
                            let $b = base[[row, col, c]];
                            let $l = layer[[row, col, c]];
                            out[[row, col, c]] = $formula;
                        }
                    }
                }
            }
            Ok(())
        }
    };
}

// Screen: 1 - (1-b)(1-l)
simple_blend!(blend_screen, |b, l| 1.0 - (1.0 - b) * (1.0 - l));

// Multiply: (b * l).clamp(0.0, 1.0)
simple_blend!(blend_multiply, |b, l| (b * l).clamp(0.0, 1.0));

// Addition: b + l (unclamped for HDR workflows)
simple_blend!(blend_addition, |b, l| b + l);

// Lighten only: max(b, l)
simple_blend!(blend_lighten_only, |b, l| b.max(l));

// Darken only: min(b, l)
simple_blend!(blend_darken_only, |b, l| b.min(l));

// Dodge: (b / (1 - l)).min(1.0)
simple_blend!(blend_dodge, |b, l| (b / (1.0 - l)).min(1.0));

// Subtract: b - l (unclamped)
simple_blend!(blend_subtract, |b, l| b - l);

// Grain extract: (b - l + 0.5).clamp(0.0, 1.0)
simple_blend!(blend_grain_extract, |b, l| (b - l + 0.5).clamp(0.0, 1.0));

// Grain merge: (b + l - 0.5).clamp(0.0, 1.0)
simple_blend!(blend_grain_merge, |b, l| (b + l - 0.5).clamp(0.0, 1.0));

// Divide: ((256/255 * b) / (1/255 + l)).min(1.0)
simple_blend!(blend_divide, |b, l| ((256.0 / 255.0 * b)
    / (1.0 / 255.0 + l))
    .min(1.0));

// Soft light: (1-b)*b*l + b*(1-(1-b)*(1-l))
simple_blend!(blend_soft_light, |b, l| {
    (1.0 - b) * b * l + b * (1.0 - (1.0 - b) * (1.0 - l))
});

// Difference: |b - l|
simple_blend!(blend_difference, |b, l| (b - l).abs());

/// Hard light blend mode.
///
/// Conditional blend at 0.5 threshold:
/// - l > 0.5: min(1 - (1-b)*(1-(l-0.5)*2), 1.0)  (screen-like)
/// - l <= 0.5: min(b*(l*2), 1.0)  (multiply-like)
#[pyfunction]
pub fn blend_hard_light<'py>(
    _py: Python<'py>,
    img_in: PyReadonlyArray3<'py, f64>,
    img_layer: PyReadonlyArray3<'py, f64>,
    output: &Bound<'py, PyArray3<f64>>,
) -> PyResult<()> {
    let base = img_in.as_array();
    let layer = img_layer.as_array();

    debug_assert_eq!(base.shape(), layer.shape(), "Input shapes must match");
    debug_assert!(base.shape()[2] >= 3, "Arrays must have at least 3 channels");

    unsafe {
        let mut out = output.as_array_mut();
        let shape = base.shape();
        let (h, w) = (shape[0], shape[1]);

        for row in 0..h {
            for col in 0..w {
                for c in 0..3 {
                    let b = base[[row, col, c]];
                    let l = layer[[row, col, c]];
                    out[[row, col, c]] = if l > 0.5 {
                        // Screen-like: 1 - (1-b)*(1-(l-0.5)*2)
                        (1.0 - (1.0 - b) * (1.0 - (l - 0.5) * 2.0)).min(1.0)
                    } else {
                        // Multiply-like: b * (l * 2)
                        (b * (l * 2.0)).min(1.0)
                    };
                }
            }
        }
    }
    Ok(())
}

/// Full blend operation with alpha composition.
///
/// Performs complete layer blending with:
/// - Alpha composition using min(base_alpha, layer_alpha) * opacity
/// - Blend mode application to RGB channels
/// - Interpolation of result based on alpha ratio
/// - Preservation of base alpha channel in output
///
/// # Arguments
/// * `img_in` - Base image, RGBA f64 array shape (h, w, 4)
/// * `img_layer` - Layer to blend, RGBA f64 array shape (h, w, 4)
/// * `output` - Output array, same shape (h, w, 4)
/// * `blend_mode` - Mode name: "screen", "multiply", "addition", etc.
/// * `opacity` - Layer opacity 0.0..1.0
#[pyfunction]
pub fn blend_full<'py>(
    _py: Python<'py>,
    img_in: PyReadonlyArray3<'py, f64>,
    img_layer: PyReadonlyArray3<'py, f64>,
    output: &Bound<'py, PyArray3<f64>>,
    blend_mode: &str,
    opacity: f64,
) -> PyResult<()> {
    let base = img_in.as_array();
    let layer = img_layer.as_array();

    debug_assert_eq!(base.shape(), layer.shape(), "Input shapes must match");
    debug_assert_eq!(base.shape()[2], 4, "Arrays must have 4 channels (RGBA)");
    debug_assert!(
        (0.0..=1.0).contains(&opacity),
        "Opacity must be between 0.0 and 1.0"
    );

    // Get the blend function based on mode name
    let blend_fn: fn(f64, f64) -> f64 = match blend_mode {
        "screen" => |b, l| 1.0 - (1.0 - b) * (1.0 - l),
        "multiply" => |b, l| (b * l).clamp(0.0, 1.0),
        "addition" => |b, l| b + l,
        "lighten_only" => |b: f64, l| b.max(l),
        "darken_only" => |b: f64, l| b.min(l),
        "dodge" => |b, l| (b / (1.0 - l)).min(1.0),
        "subtract" => |b, l| b - l,
        "grain_extract" => |b, l| (b - l + 0.5).clamp(0.0, 1.0),
        "grain_merge" => |b, l| (b + l - 0.5).clamp(0.0, 1.0),
        "divide" => |b, l| ((256.0 / 255.0 * b) / (1.0 / 255.0 + l)).min(1.0),
        "soft_light" => |b, l| (1.0 - b) * b * l + b * (1.0 - (1.0 - b) * (1.0 - l)),
        "difference" => |b, l| (b - l).abs(),
        "hard_light" => |b, l| {
            if l > 0.5 {
                (1.0 - (1.0 - b) * (1.0 - (l - 0.5) * 2.0)).min(1.0)
            } else {
                (b * (l * 2.0)).min(1.0)
            }
        },
        _ => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Unknown blend mode: {}",
                blend_mode
            )))
        }
    };

    unsafe {
        let mut out = output.as_array_mut();
        let shape = base.shape();
        let (h, w) = (shape[0], shape[1]);

        for row in 0..h {
            for col in 0..w {
                let base_alpha = base[[row, col, 3]];
                let layer_alpha = layer[[row, col, 3]];

                // Alpha composition: min(base, layer) * opacity
                let comp_alpha = base_alpha.min(layer_alpha) * opacity;

                // Compute new alpha for the output
                let new_alpha = base_alpha + (1.0 - base_alpha) * comp_alpha;

                // Calculate interpolation ratio (handle division by zero)
                let ratio = if new_alpha > 0.0 {
                    comp_alpha / new_alpha
                } else {
                    0.0
                };

                // Apply blend and interpolate for each RGB channel
                for c in 0..3 {
                    let b = base[[row, col, c]];
                    let l = layer[[row, col, c]];
                    let blended = blend_fn(b, l);

                    // Handle NaN from division operations
                    let blended = if blended.is_nan() { 0.0 } else { blended };

                    // Interpolate: blended * ratio + base * (1 - ratio)
                    out[[row, col, c]] = blended * ratio + b * (1.0 - ratio);
                }

                // Preserve base alpha channel
                out[[row, col, 3]] = base_alpha;
            }
        }
    }
    Ok(())
}
