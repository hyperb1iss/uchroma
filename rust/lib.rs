//! Native Rust extensions for uchroma
//!
//! High-performance implementations of hot paths:
//! - CRC calculation for USB HID reports
//! - Plasma effect rendering
//! - Metaballs effect rendering
//! - Async HID device access (nusb)

#![allow(non_snake_case)]

use pyo3::prelude::*;

mod crc;
mod hid;
mod metaballs;
mod plasma;

// Re-export for benchmarks
pub use crc::fast_crc_impl;

/// Native Rust extensions for uchroma performance-critical code.
#[pymodule(name = "_native")]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Existing functions
    m.add_function(wrap_pyfunction!(crc::fast_crc, m)?)?;
    m.add_function(wrap_pyfunction!(plasma::draw_plasma, m)?)?;
    m.add_function(wrap_pyfunction!(metaballs::draw_metaballs, m)?)?;

    // HID types
    m.add_class::<hid::DeviceInfo>()?;

    Ok(())
}
