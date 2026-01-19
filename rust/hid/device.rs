//! HID device handle for communication

use crate::hid::{DeviceInfo, HidError, Result};
use nusb::transfer::{ControlIn, ControlOut, ControlType, Recipient};
use nusb::MaybeFuture;
use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::future_into_py;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;

/// HID device handle for feature report communication.
#[pyclass]
pub struct HidDevice {
    interface: Arc<Mutex<Option<nusb::Interface>>>,
    info: DeviceInfo,
}

fn matches_info(dev_info: &nusb::DeviceInfo, info: &DeviceInfo) -> bool {
    #[cfg(target_os = "linux")]
    {
        dev_info.busnum() == info.bus_number && dev_info.device_address() == info.device_address
    }
    #[cfg(not(target_os = "linux"))]
    {
        dev_info.device_address() == info.device_address
            && dev_info.vendor_id() == info.vendor_id
            && dev_info.product_id() == info.product_id
    }
}

// HID class requests
const HID_GET_REPORT: u8 = 0x01;
const HID_SET_REPORT: u8 = 0x09;

// Report types (in high byte of wValue)
const HID_REPORT_TYPE_FEATURE: u16 = 0x03;

// Default timeout for USB transfers
const DEFAULT_TIMEOUT: Duration = Duration::from_millis(1000);

#[pymethods]
impl HidDevice {
    /// Open a HID device from DeviceInfo.
    #[new]
    fn new(info: DeviceInfo) -> Result<Self> {
        // Find the device by bus/address
        let dev_info = nusb::list_devices()
            .wait()?
            .find(|d| matches_info(d, &info))
            .ok_or_else(|| HidError::DeviceNotFound(format!("{:?}", info)))?;

        let device = dev_info.open().wait()?;
        // On Linux, detach kernel driver before claiming (e.g., hid-generic)
        #[cfg(target_os = "linux")]
        let interface = device
            .detach_and_claim_interface(info.interface_number as u8)
            .wait()?;
        #[cfg(not(target_os = "linux"))]
        let interface = device.claim_interface(info.interface_number as u8).wait()?;

        Ok(Self {
            interface: Arc::new(Mutex::new(Some(interface))),
            info,
        })
    }

    /// Close the device.
    fn close(&self) {
        if let Ok(mut guard) = self.interface.try_lock() {
            *guard = None;
        }
    }

    /// Check if device is open.
    #[getter]
    fn is_open(&self) -> bool {
        if let Ok(guard) = self.interface.try_lock() {
            guard.is_some()
        } else {
            true
        }
    }

    /// Device info.
    #[getter]
    fn info(&self) -> DeviceInfo {
        self.info.clone()
    }

    /// Send a feature report (blocking).
    ///
    /// Args:
    ///     data: Report data (e.g., 90 bytes for Razer devices)
    ///     report_id: HID report ID (typically 0)
    ///
    /// Returns:
    ///     Number of bytes sent
    fn send_feature_report(&self, data: Vec<u8>, report_id: u8) -> Result<usize> {
        let interface = self.interface.clone();
        let len = data.len();

        // Get or create runtime
        let result = if let Ok(rt) = tokio::runtime::Handle::try_current() {
            rt.block_on(Self::send_feature_report_inner(interface, &data, report_id))
        } else {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap();
            rt.block_on(Self::send_feature_report_inner(interface, &data, report_id))
        };

        result.map(|_| len)
    }

    /// Get a feature report (blocking).
    ///
    /// Args:
    ///     report_id: HID report ID (typically 0)
    ///     size: Number of bytes to read
    ///
    /// Returns:
    ///     Report data as bytes
    fn get_feature_report(&self, report_id: u8, size: usize) -> Result<Vec<u8>> {
        let interface = self.interface.clone();

        if let Ok(rt) = tokio::runtime::Handle::try_current() {
            rt.block_on(Self::get_feature_report_inner(interface, report_id, size))
        } else {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap();
            rt.block_on(Self::get_feature_report_inner(interface, report_id, size))
        }
    }

    /// Send a feature report (async).
    fn send_feature_report_async<'py>(
        &self,
        py: Python<'py>,
        data: Vec<u8>,
        report_id: u8,
    ) -> PyResult<Bound<'py, PyAny>> {
        let interface = self.interface.clone();
        let len = data.len();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            Self::send_feature_report_inner(interface, &data, report_id).await?;
            Ok(len)
        })
    }

    /// Get a feature report (async).
    fn get_feature_report_async<'py>(
        &self,
        py: Python<'py>,
        report_id: u8,
        size: usize,
    ) -> PyResult<Bound<'py, PyAny>> {
        let interface = self.interface.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let result = Self::get_feature_report_inner(interface, report_id, size).await?;
            Ok(result)
        })
    }
}

/// Open a HID device asynchronously from DeviceInfo.
#[pyfunction]
pub fn open_device_async<'py>(py: Python<'py>, info: DeviceInfo) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        let dev_info = nusb::list_devices()
            .await
            .map_err(HidError::UsbError)?
            .find(|d| matches_info(d, &info))
            .ok_or_else(|| HidError::DeviceNotFound(format!("{:?}", info)))?;

        let device = dev_info.open().await.map_err(HidError::UsbError)?;
        #[cfg(target_os = "linux")]
        let interface = device
            .detach_and_claim_interface(info.interface_number as u8)
            .await
            .map_err(HidError::UsbError)?;
        #[cfg(not(target_os = "linux"))]
        let interface = device
            .claim_interface(info.interface_number as u8)
            .await
            .map_err(HidError::UsbError)?;

        Ok(HidDevice {
            interface: Arc::new(Mutex::new(Some(interface))),
            info,
        })
    })
}

impl HidDevice {
    pub(crate) fn interface_clone(&self) -> Arc<Mutex<Option<nusb::Interface>>> {
        self.interface.clone()
    }

    /// Send a feature report (blocking, callable from Rust).
    pub fn send_report(&self, data: Vec<u8>, report_id: u8) -> Result<usize> {
        let interface = self.interface.clone();
        let len = data.len();

        let result = if let Ok(rt) = tokio::runtime::Handle::try_current() {
            rt.block_on(Self::send_feature_report_inner(interface, &data, report_id))
        } else {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap();
            rt.block_on(Self::send_feature_report_inner(interface, &data, report_id))
        };

        result.map(|_| len)
    }

    /// Get a feature report (blocking, callable from Rust).
    pub fn get_report(&self, report_id: u8, size: usize) -> Result<Vec<u8>> {
        let interface = self.interface.clone();

        if let Ok(rt) = tokio::runtime::Handle::try_current() {
            rt.block_on(Self::get_feature_report_inner(interface, report_id, size))
        } else {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap();
            rt.block_on(Self::get_feature_report_inner(interface, report_id, size))
        }
    }

    pub(crate) async fn send_feature_report_inner(
        interface: Arc<Mutex<Option<nusb::Interface>>>,
        data: &[u8],
        report_id: u8,
    ) -> Result<()> {
        let guard = interface.lock().await;
        let iface = guard.as_ref().ok_or(HidError::Disconnected)?;

        // SET_REPORT: bmRequestType=0x21, bRequest=0x09
        // wValue = (report_type << 8) | report_id
        // wIndex = interface number
        let w_value = (HID_REPORT_TYPE_FEATURE << 8) | (report_id as u16);

        iface
            .control_out(
                ControlOut {
                    control_type: ControlType::Class,
                    recipient: Recipient::Interface,
                    request: HID_SET_REPORT,
                    value: w_value,
                    index: iface.interface_number() as u16,
                    data,
                },
                DEFAULT_TIMEOUT,
            )
            .await?;

        Ok(())
    }

    pub(crate) async fn get_feature_report_inner(
        interface: Arc<Mutex<Option<nusb::Interface>>>,
        report_id: u8,
        size: usize,
    ) -> Result<Vec<u8>> {
        let guard = interface.lock().await;
        let iface = guard.as_ref().ok_or(HidError::Disconnected)?;

        // GET_REPORT: bmRequestType=0xA1, bRequest=0x01
        let w_value = (HID_REPORT_TYPE_FEATURE << 8) | (report_id as u16);

        let result = iface
            .control_in(
                ControlIn {
                    control_type: ControlType::Class,
                    recipient: Recipient::Interface,
                    request: HID_GET_REPORT,
                    value: w_value,
                    index: iface.interface_number() as u16,
                    length: size as u16,
                },
                DEFAULT_TIMEOUT,
            )
            .await?;

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hid_constants() {
        assert_eq!(HID_GET_REPORT, 0x01);
        assert_eq!(HID_SET_REPORT, 0x09);
        assert_eq!(HID_REPORT_TYPE_FEATURE, 0x03);
    }
}
