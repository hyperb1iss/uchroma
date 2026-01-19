//! HID device enumeration

use crate::hid::{DeviceInfo, Result};
use nusb::descriptors::ConfigurationDescriptor;
use nusb::MaybeFuture;
use pyo3::prelude::*;

/// Enumerate HID devices, optionally filtered by vendor/product ID.
///
/// Returns a list of DeviceInfo for all matching HID devices.
/// Pass 0 for vendor_id or product_id to match all.
#[pyfunction]
#[pyo3(signature = (vendor_id=0, product_id=0))]
pub fn enumerate_devices(vendor_id: u16, product_id: u16) -> Result<Vec<DeviceInfo>> {
    let mut results = Vec::new();

    // nusb 0.2 uses MaybeFuture - call .wait() for blocking
    for dev_info in nusb::list_devices().wait()? {
        // Filter by vendor/product if specified
        if vendor_id != 0 && dev_info.vendor_id() != vendor_id {
            continue;
        }
        if product_id != 0 && dev_info.product_id() != product_id {
            continue;
        }

        // Open device to get interface info (.wait() for blocking)
        let device: nusb::Device = match dev_info.open().wait() {
            Ok(d) => d,
            Err(_) => continue, // Skip devices we can't open
        };

        // Get active configuration to enumerate interfaces
        let config: ConfigurationDescriptor = match device.active_configuration() {
            Ok(c) => c,
            Err(_) => continue,
        };

        // Find HID interfaces (class 0x03)
        for iface in config.interfaces() {
            let iface_num = iface.interface_number();

            for alt in iface.alt_settings() {
                // Check if this is an HID interface (class 0x03)
                if alt.class() == 0x03 {
                    results.push(DeviceInfo::from_nusb(&dev_info, iface_num));
                    break; // Only add once per interface
                }
            }
        }
    }

    // Sort by bus:addr:interface for consistent ordering
    results.sort_by(|a, b| {
        (a.bus_number, a.device_address, a.interface_number).cmp(&(
            b.bus_number,
            b.device_address,
            b.interface_number,
        ))
    });

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_enumerate_returns_vec() {
        // Should return a vec (possibly empty if no devices)
        let result = enumerate_devices(0, 0);
        assert!(result.is_ok());
    }

    #[test]
    fn test_enumerate_with_invalid_filter() {
        // Should return empty vec for non-existent vendor
        let result = enumerate_devices(0xFFFF, 0xFFFF).unwrap();
        assert!(result.is_empty());
    }
}
