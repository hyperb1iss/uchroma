//! Headset-specific HID protocol via interrupt transfers.
//!
//! Kraken headsets use a different protocol than keyboards/mice:
//! - Output Report ID 0x04 (37 bytes) for commands
//! - Input Report ID 0x05 (33 bytes) for responses
//! - Memory-mapped command format instead of standard Razer protocol

#![allow(dead_code)] // Constants and struct fields will be used in later tasks

use crate::hid::{DeviceInfo, HidError, Result};
use nusb::descriptors::TransferType;
use nusb::transfer::{Buffer, Direction, In, Interrupt, Out};
use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::future_into_py;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;

// Report IDs
const REPORT_ID_OUT: u8 = 0x04;
const REPORT_ID_IN: u8 = 0x05;

// Report sizes (excluding report ID byte)
const REPORT_LENGTH_OUT: usize = 37;
const REPORT_LENGTH_IN: usize = 33;

// Inter-command delay
const DELAY_MS: u64 = 25;

// Memory destinations
const READ_RAM: u8 = 0x00;
const READ_EEPROM: u8 = 0x20;
const WRITE_RAM: u8 = 0x40;

/// Headset device handle using interrupt transfers.
#[pyclass]
pub struct HeadsetDevice {
    interface: Arc<Mutex<Option<nusb::Interface>>>,
    info: DeviceInfo,
    ep_out: u8,
    ep_in: u8,
}

impl HeadsetDevice {
    /// Find interrupt endpoints from interface descriptor.
    ///
    /// Scans endpoint descriptors to locate the interrupt IN and OUT endpoints
    /// used for headset communication.
    fn find_endpoints(interface: &nusb::Interface) -> Result<(u8, u8)> {
        let mut ep_out: Option<u8> = None;
        let mut ep_in: Option<u8> = None;

        // interface.descriptors() yields InterfaceDescriptor items
        // Each has endpoints() to get the EndpointDescriptor items
        for iface_desc in interface.descriptors() {
            for ep in iface_desc.endpoints() {
                if ep.transfer_type() == TransferType::Interrupt {
                    let addr = ep.address();
                    match ep.direction() {
                        Direction::In if ep_in.is_none() => ep_in = Some(addr),
                        Direction::Out if ep_out.is_none() => ep_out = Some(addr),
                        _ => {}
                    }
                }
            }
        }

        match (ep_out, ep_in) {
            (Some(out), Some(inp)) => Ok((out, inp)),
            _ => Err(HidError::ProtocolError(
                "Could not find interrupt endpoints".into(),
            )),
        }
    }

    /// Internal async write to interrupt OUT endpoint.
    pub(crate) async fn write_interrupt(
        interface: Arc<Mutex<Option<nusb::Interface>>>,
        ep_addr: u8,
        data: &[u8],
    ) -> Result<()> {
        let guard = interface.lock().await;
        let iface = guard.as_ref().ok_or(HidError::Disconnected)?;

        let mut ep = iface
            .endpoint::<Interrupt, Out>(ep_addr)
            .map_err(HidError::UsbError)?;

        let buffer = Buffer::from(data.to_vec());
        ep.submit(buffer);

        let completion = ep.next_complete().await;
        completion.status.map_err(HidError::TransferError)?;

        Ok(())
    }

    /// Internal async read from interrupt IN endpoint.
    pub(crate) async fn read_interrupt(
        interface: Arc<Mutex<Option<nusb::Interface>>>,
        ep_addr: u8,
        size: usize,
        timeout: Duration,
    ) -> Result<Vec<u8>> {
        let guard = interface.lock().await;
        let iface = guard.as_ref().ok_or(HidError::Disconnected)?;

        let mut ep = iface
            .endpoint::<Interrupt, In>(ep_addr)
            .map_err(HidError::UsbError)?;

        let mut buffer = ep.allocate(size);
        buffer.set_requested_len(size);
        ep.submit(buffer);

        let completion = tokio::time::timeout(timeout, ep.next_complete())
            .await
            .map_err(|_| HidError::ProtocolError("Interrupt read timeout".into()))?;

        completion.status.map_err(HidError::TransferError)?;
        Ok(completion.buffer.into_vec())
    }
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

#[pymethods]
impl HeadsetDevice {
    /// Open a headset device from DeviceInfo.
    #[new]
    fn new(info: DeviceInfo) -> Result<Self> {
        use nusb::MaybeFuture;

        let dev_info = nusb::list_devices()
            .wait()?
            .find(|d| matches_info(d, &info))
            .ok_or_else(|| HidError::DeviceNotFound(format!("{:?}", info)))?;

        let device = dev_info.open().wait()?;

        #[cfg(target_os = "linux")]
        let interface = device
            .detach_and_claim_interface(info.interface_number as u8)
            .wait()?;
        #[cfg(not(target_os = "linux"))]
        let interface = device
            .claim_interface(info.interface_number as u8)
            .wait()?;

        // Find interrupt endpoints
        let (ep_out, ep_in) = Self::find_endpoints(&interface)?;

        Ok(Self {
            interface: Arc::new(Mutex::new(Some(interface))),
            info,
            ep_out,
            ep_in,
        })
    }

    /// Close the device.
    fn close(&self) {
        use crate::hid::device::get_or_create_runtime;

        if let Ok(rt) = tokio::runtime::Handle::try_current() {
            rt.block_on(async {
                let mut guard = self.interface.lock().await;
                *guard = None;
            });
        } else if let Ok(rt) = get_or_create_runtime() {
            rt.block_on(async {
                let mut guard = self.interface.lock().await;
                *guard = None;
            });
        }
    }

    /// Check if device is open.
    #[getter]
    fn is_open(&self) -> bool {
        self.interface
            .try_lock()
            .map(|guard| guard.is_some())
            .unwrap_or(false)
    }

    /// Device info.
    #[getter]
    fn info(&self) -> DeviceInfo {
        self.info.clone()
    }

    /// Write data to interrupt OUT endpoint (async).
    ///
    /// Prepends the OUT report ID (0x04) and pads to 38 bytes (37 + 1).
    ///
    /// Args:
    ///     data: Payload bytes (up to 37 bytes)
    fn write<'py>(&self, py: Python<'py>, data: Vec<u8>) -> PyResult<Bound<'py, PyAny>> {
        let interface = self.interface.clone();
        let ep_addr = self.ep_out;

        future_into_py(py, async move {
            // Prepend report ID
            let mut buf = vec![REPORT_ID_OUT];
            buf.extend_from_slice(&data);
            buf.resize(REPORT_LENGTH_OUT + 1, 0);

            Self::write_interrupt(interface, ep_addr, &buf).await?;
            Ok(())
        })
    }

    /// Read data from interrupt IN endpoint (async).
    ///
    /// Verifies the IN report ID (0x05) and strips it from the result.
    ///
    /// Args:
    ///     timeout_ms: Timeout in milliseconds
    ///
    /// Returns:
    ///     Payload bytes (33 bytes, excluding report ID)
    fn read<'py>(&self, py: Python<'py>, timeout_ms: u64) -> PyResult<Bound<'py, PyAny>> {
        let interface = self.interface.clone();
        let ep_addr = self.ep_in;
        let timeout = Duration::from_millis(timeout_ms);

        future_into_py(py, async move {
            let data = Self::read_interrupt(
                interface,
                ep_addr,
                REPORT_LENGTH_IN + 1, // +1 for report ID
                timeout,
            )
            .await?;

            // Verify report ID
            if data.is_empty() || data[0] != REPORT_ID_IN {
                return Err(HidError::ProtocolError(format!(
                    "Expected report ID 0x{:02X}, got 0x{:02X}",
                    REPORT_ID_IN,
                    data.first().unwrap_or(&0)
                ))
                .into());
            }

            // Return without report ID
            Ok(data[1..].to_vec())
        })
    }
}
