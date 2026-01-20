//! Compositor operations for final frame output.
//!
//! Converts RGBA float layers to RGB uint8 for hardware output.
//! Provides both single-layer `rgba2rgb` and multi-layer `compose_layers`.
//!
//! Uses thread-local buffer pooling to eliminate per-frame allocations.

use std::cell::RefCell;

use numpy::{PyArray3, PyArrayMethods, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::blending::BlendMode;

// Thread-local buffer pool for intermediate RGBA composition.
// Reused across frames to avoid allocation overhead (typically ~4KB for keyboards,
// ~130KB for 64x64 previews). Buffer grows as needed but never shrinks.
thread_local! {
    static COMPOSE_BUFFER: RefCell<Vec<f64>> = const { RefCell::new(Vec::new()) };
}

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

/// Compose multiple RGBA layers into a single RGB output.
///
/// Fuses the entire composition pipeline into a single Rust function:
/// 1. Starts with first layer as base
/// 2. Blends each subsequent layer using its blend mode and opacity
/// 3. Converts final RGBA to RGB uint8 with background color compositing
///
/// This eliminates N Python→Rust boundary crossings for N layers.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn compose_layers<'py>(
    _py: Python<'py>,
    layers: Vec<PyReadonlyArray3<'py, f64>>,
    blend_modes: Vec<String>,
    opacities: Vec<f64>,
    bg_r: f64,
    bg_g: f64,
    bg_b: f64,
    output: &Bound<'py, PyArray3<u8>>,
) -> PyResult<()> {
    if layers.is_empty() {
        return Ok(());
    }

    let first = layers[0].as_array();
    let (h, w) = (first.shape()[0], first.shape()[1]);
    let pixels = h * w;

    // Validate all layers have same shape
    for (i, layer) in layers.iter().enumerate() {
        let arr = layer.as_array();
        let (lh, lw) = (arr.shape()[0], arr.shape()[1]);
        if lh != h || lw != w {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Layer {} has shape {}x{}, expected {}x{}",
                i, lh, lw, h, w
            )));
        }
    }

    // Parse blend modes upfront
    let modes: Vec<BlendMode> = blend_modes
        .iter()
        .map(|s| s.parse().unwrap_or(BlendMode::Screen))
        .collect();

    let required_size = pixels * 4;
    let bg = [bg_r, bg_g, bg_b];

    // Use thread-local buffer pool to avoid per-frame allocation
    COMPOSE_BUFFER.with(|cell| {
        let mut buffer = cell.borrow_mut();

        // Grow buffer if needed (never shrinks - amortized O(1))
        if buffer.len() < required_size {
            buffer.resize(required_size, 0.0);
        }

        // Copy base layer into buffer
        {
            let base = first;
            for row in 0..h {
                for col in 0..w {
                    let buf_idx = (row * w + col) * 4;
                    buffer[buf_idx] = base[[row, col, 0]];
                    buffer[buf_idx + 1] = base[[row, col, 1]];
                    buffer[buf_idx + 2] = base[[row, col, 2]];
                    buffer[buf_idx + 3] = base[[row, col, 3]];
                }
            }
        }

        // Blend each subsequent layer in-place
        for (layer_idx, layer_arr) in layers.iter().enumerate().skip(1) {
            let layer = layer_arr.as_array();
            let mode = modes.get(layer_idx).copied().unwrap_or(BlendMode::Screen);
            let opacity = opacities.get(layer_idx).copied().unwrap_or(1.0);

            for row in 0..h {
                for col in 0..w {
                    let buf_idx = (row * w + col) * 4;

                    let base_alpha = buffer[buf_idx + 3];
                    let layer_alpha = layer[[row, col, 3]];

                    let comp_alpha = base_alpha.min(layer_alpha) * opacity;
                    let new_alpha = base_alpha + (1.0 - base_alpha) * comp_alpha;

                    let ratio = if new_alpha > 0.0 {
                        comp_alpha / new_alpha
                    } else {
                        0.0
                    };

                    for c in 0..3 {
                        let b = buffer[buf_idx + c];
                        let l = layer[[row, col, c]];
                        let blended = mode.apply(b, l);
                        let blended = if blended.is_nan() { 0.0 } else { blended };
                        buffer[buf_idx + c] = blended * ratio + b * (1.0 - ratio);
                    }

                    buffer[buf_idx + 3] = base_alpha;
                }
            }
        }

        // Fused RGBA→RGB conversion
        // SAFETY: We have exclusive write access to output through PyO3's borrow rules
        unsafe {
            let mut out = output.as_array_mut();

            for row in 0..h {
                for col in 0..w {
                    let buf_idx = (row * w + col) * 4;
                    let alpha = buffer[buf_idx + 3];
                    let inv_alpha = 1.0 - alpha;

                    for c in 0..3 {
                        let src = buffer[buf_idx + c];
                        let composited = inv_alpha * bg[c] + alpha * src;
                        let clamped = composited.clamp(0.0, 1.0);
                        out[[row, col, c]] = (clamped * 255.0) as u8;
                    }
                }
            }
        }
    });

    Ok(())
}

// ============================================================================
// Pure Rust implementation for benchmarking
// ============================================================================

/// Compose layers entirely in Rust (for benchmarking without PyO3 overhead).
pub fn compose_layers_impl(
    layers: &[&[f64]],
    blend_modes: &[BlendMode],
    opacities: &[f64],
    h: usize,
    w: usize,
    bg: [f64; 3],
    output: &mut [u8],
) {
    if layers.is_empty() {
        return;
    }

    let pixels = h * w;
    let mut buffer = vec![0.0f64; pixels * 4];

    buffer.copy_from_slice(&layers[0][..pixels * 4]);

    for (layer_idx, &layer) in layers.iter().enumerate().skip(1) {
        let mode = blend_modes
            .get(layer_idx)
            .copied()
            .unwrap_or(BlendMode::Screen);
        let opacity = opacities.get(layer_idx).copied().unwrap_or(1.0);

        for p in 0..pixels {
            let idx = p * 4;

            let base_alpha = buffer[idx + 3];
            let layer_alpha = layer[idx + 3];

            let comp_alpha = base_alpha.min(layer_alpha) * opacity;
            let new_alpha = base_alpha + (1.0 - base_alpha) * comp_alpha;

            let ratio = if new_alpha > 0.0 {
                comp_alpha / new_alpha
            } else {
                0.0
            };

            for c in 0..3 {
                let b = buffer[idx + c];
                let l = layer[idx + c];
                let blended = mode.apply(b, l);
                let blended = if blended.is_nan() { 0.0 } else { blended };
                buffer[idx + c] = blended * ratio + b * (1.0 - ratio);
            }

            buffer[idx + 3] = base_alpha;
        }
    }

    for p in 0..pixels {
        let src_idx = p * 4;
        let dst_idx = p * 3;
        let alpha = buffer[src_idx + 3];
        let inv_alpha = 1.0 - alpha;

        for c in 0..3 {
            let src = buffer[src_idx + c];
            let composited = inv_alpha * bg[c] + alpha * src;
            let clamped = composited.clamp(0.0, 1.0);
            output[dst_idx + c] = (clamped * 255.0) as u8;
        }
    }
}
