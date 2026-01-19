//! Error types for HID operations

use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum HidError {
    #[error("Device not found: {0}")]
    DeviceNotFound(String),

    #[error("USB error: {0}")]
    UsbError(#[from] nusb::Error),

    #[error("Transfer error: {0}")]
    TransferError(#[from] nusb::transfer::TransferError),

    #[error("Device disconnected")]
    Disconnected,

    #[error("Invalid report size: expected {expected}, got {actual}")]
    InvalidReportSize { expected: usize, actual: usize },

    #[error("Protocol error: {0}")]
    ProtocolError(String),
}

impl From<HidError> for PyErr {
    fn from(err: HidError) -> PyErr {
        PyOSError::new_err(err.to_string())
    }
}

#[allow(dead_code)]
pub type Result<T> = std::result::Result<T, HidError>;
