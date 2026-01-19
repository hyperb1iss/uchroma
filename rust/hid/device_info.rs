//! HID device information from enumeration

use pyo3::prelude::*;

/// HID device information from enumeration.
#[pyclass]
#[derive(Clone, Debug)]
pub struct DeviceInfo {
    #[pyo3(get)]
    pub vendor_id: u16,

    #[pyo3(get)]
    pub product_id: u16,

    #[pyo3(get)]
    pub interface_number: i32,

    #[pyo3(get)]
    pub manufacturer_string: String,

    #[pyo3(get)]
    pub product_string: String,

    #[pyo3(get)]
    pub serial_number: String,

    // Internal: device identifiers for opening
    #[pyo3(get)]
    pub bus_number: u8,

    #[pyo3(get)]
    pub device_address: u8,
}

#[pymethods]
impl DeviceInfo {
    fn __repr__(&self) -> String {
        format!(
            "DeviceInfo(vendor_id=0x{:04x}, product_id=0x{:04x}, interface={})",
            self.vendor_id, self.product_id, self.interface_number
        )
    }

    /// Unique path identifier for this device (bus:addr:interface)
    #[getter]
    fn path(&self) -> Vec<u8> {
        // Return as bytes to match hidapi path format
        format!(
            "{:03}:{:03}:{:02}",
            self.bus_number, self.device_address, self.interface_number
        )
        .into_bytes()
    }
}

impl DeviceInfo {
    #[cfg(target_os = "linux")]
    pub fn from_nusb(dev: &nusb::DeviceInfo, interface: u8) -> Self {
        Self {
            vendor_id: dev.vendor_id(),
            product_id: dev.product_id(),
            interface_number: interface as i32,
            manufacturer_string: dev.manufacturer_string().unwrap_or_default().to_string(),
            product_string: dev.product_string().unwrap_or_default().to_string(),
            serial_number: dev.serial_number().unwrap_or_default().to_string(),
            bus_number: dev.busnum(),
            device_address: dev.device_address(),
        }
    }

    #[cfg(not(target_os = "linux"))]
    pub fn from_nusb(dev: &nusb::DeviceInfo, interface: u8) -> Self {
        Self {
            vendor_id: dev.vendor_id(),
            product_id: dev.product_id(),
            interface_number: interface as i32,
            manufacturer_string: dev.manufacturer_string().unwrap_or_default().to_string(),
            product_string: dev.product_string().unwrap_or_default().to_string(),
            serial_number: dev.serial_number().unwrap_or_default().to_string(),
            bus_number: 0, // Not available on non-Linux
            device_address: dev.device_address(),
        }
    }
}
