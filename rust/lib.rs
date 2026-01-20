//! Native Rust extensions for uchroma
//!
//! High-performance implementations of hot paths:
//! - CRC calculation for USB HID reports
//! - Plasma effect rendering
//! - Metaballs effect rendering
//! - Async HID device access (nusb)

#![allow(non_snake_case)]

use pyo3::prelude::*;

mod blending;
mod compositor;
mod crc;
mod drawing;
mod hid;
mod metaballs;
mod plasma;

// Re-export for benchmarks
pub use blending::{blend_full_impl, blend_screen_impl};
pub use crc::fast_crc_impl;

/// Native Rust extensions for uchroma performance-critical code.
#[pymodule(name = "_native")]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Existing functions
    m.add_function(wrap_pyfunction!(crc::fast_crc, m)?)?;
    m.add_function(wrap_pyfunction!(plasma::draw_plasma, m)?)?;
    m.add_function(wrap_pyfunction!(metaballs::draw_metaballs, m)?)?;

    // Blending functions - individual blend modes
    m.add_function(wrap_pyfunction!(blending::blend_screen, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_multiply, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_addition, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_lighten_only, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_darken_only, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_dodge, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_subtract, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_grain_extract, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_grain_merge, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_divide, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_soft_light, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_hard_light, m)?)?;
    m.add_function(wrap_pyfunction!(blending::blend_difference, m)?)?;
    // Full blend with alpha composition
    m.add_function(wrap_pyfunction!(blending::blend_full, m)?)?;

    // HID types and functions
    m.add_class::<hid::DeviceInfo>()?;
    m.add_class::<hid::HidDevice>()?;
    m.add_class::<hid::RazerReport>()?;
    m.add_class::<hid::Status>()?;
    m.add_function(wrap_pyfunction!(hid::enumerate_devices, m)?)?;
    m.add_function(wrap_pyfunction!(hid::enumerate_devices_async, m)?)?;
    m.add_function(wrap_pyfunction!(hid::open_device_async, m)?)?;
    m.add_function(wrap_pyfunction!(hid::send_frame_async, m)?)?;

    // HID constants
    m.add("REPORT_SIZE", hid::REPORT_SIZE)?;
    m.add("DATA_SIZE", hid::DATA_SIZE)?;

    // Drawing primitives
    m.add_function(wrap_pyfunction!(drawing::circle_perimeter_aa, m)?)?;
    m.add_function(wrap_pyfunction!(drawing::line_aa, m)?)?;

    // Compositor
    m.add_function(wrap_pyfunction!(compositor::rgba2rgb, m)?)?;

    Ok(())
}
