//! Razer HID report protocol implementation
//!
//! The report structure is 90 bytes:
//!   0      - Status (0x00 for requests)
//!   1      - Transaction ID
//!   2-3    - Remaining packets (u16 LE)
//!   4      - Protocol type
//!   5      - Data size
//!   6      - Command class
//!   7      - Command ID
//!   8-87   - Argument data (80 bytes)
//!   88     - CRC (XOR of bytes 1-87)
//!   89     - Reserved (0x00)

use crate::crc::fast_crc_impl;
use crate::hid::{HidDevice, HidError};
use pyo3::prelude::*;
use std::thread;
use std::time::Duration;

pub const REPORT_SIZE: usize = 90;
pub const DATA_SIZE: usize = 80;

// Default inter-command delay
const CMD_DELAY_MS: u64 = 7;

/// Status codes returned by Razer devices.
#[pyclass(eq, eq_int)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Status {
    Unknown = 0x00,
    Busy = 0x01,
    Ok = 0x02,
    Fail = 0x03,
    Timeout = 0x04,
    Unsupported = 0x05,
    BadCrc = 0xFE,
    OsError = 0xFF,
}

impl From<u8> for Status {
    fn from(v: u8) -> Self {
        match v {
            0x01 => Status::Busy,
            0x02 => Status::Ok,
            0x03 => Status::Fail,
            0x04 => Status::Timeout,
            0x05 => Status::Unsupported,
            0xFE => Status::BadCrc,
            0xFF => Status::OsError,
            _ => Status::Unknown,
        }
    }
}

/// Razer HID report for device communication.
#[pyclass]
pub struct RazerReport {
    buf: [u8; REPORT_SIZE],
    data_ptr: usize,
    transaction_id: u8,
    command_class: u8,
    command_id: u8,
    data_size: Option<u8>,
}

#[pymethods]
impl RazerReport {
    /// Create a new report.
    ///
    /// Args:
    ///     command_class: Command class byte
    ///     command_id: Command ID byte
    ///     data_size: Expected data size (None for variable, will use actual args size)
    ///     transaction_id: Transaction ID (default 0xFF)
    #[new]
    #[pyo3(signature = (command_class, command_id, data_size=None, transaction_id=0xFF))]
    fn new(
        command_class: u8,
        command_id: u8,
        data_size: Option<u8>,
        transaction_id: u8,
    ) -> Self {
        let mut report = Self {
            buf: [0u8; REPORT_SIZE],
            data_ptr: 0,
            transaction_id,
            command_class,
            command_id,
            data_size,
        };
        report.buf[1] = transaction_id;
        report.buf[6] = command_class;
        report.buf[7] = command_id;
        report
    }

    /// Clear the report data for reuse.
    fn clear(&mut self) {
        self.buf[8..88].fill(0);
        self.data_ptr = 0;
    }

    /// Put a single byte argument.
    fn put_byte(&mut self, value: u8) -> PyResult<()> {
        if self.data_ptr >= DATA_SIZE {
            return Err(pyo3::exceptions::PyValueError::new_err("Buffer full"));
        }
        self.buf[8 + self.data_ptr] = value;
        self.data_ptr += 1;
        Ok(())
    }

    /// Put multiple bytes from a buffer.
    fn put_bytes(&mut self, data: &[u8]) -> PyResult<()> {
        if self.data_ptr + data.len() > DATA_SIZE {
            return Err(pyo3::exceptions::PyValueError::new_err("Buffer overflow"));
        }
        self.buf[8 + self.data_ptr..8 + self.data_ptr + data.len()].copy_from_slice(data);
        self.data_ptr += data.len();
        Ok(())
    }

    /// Put a u16 (little-endian).
    fn put_u16(&mut self, value: u16) -> PyResult<()> {
        self.put_bytes(&value.to_le_bytes())
    }

    /// Put a u16 (big-endian).
    fn put_u16_be(&mut self, value: u16) -> PyResult<()> {
        self.put_bytes(&value.to_be_bytes())
    }

    /// Put RGB color (3 bytes).
    fn put_rgb(&mut self, r: u8, g: u8, b: u8) -> PyResult<()> {
        self.put_byte(r)?;
        self.put_byte(g)?;
        self.put_byte(b)
    }

    /// Set remaining packets count (for multi-packet transfers).
    fn set_remaining_packets(&mut self, count: u16) {
        self.buf[2..4].copy_from_slice(&count.to_le_bytes());
    }

    /// Get remaining packets count.
    fn get_remaining_packets(&self) -> u16 {
        u16::from_le_bytes([self.buf[2], self.buf[3]])
    }

    /// Pack the report for sending.
    ///
    /// Returns the 90-byte report with CRC calculated.
    fn pack(&mut self) -> Vec<u8> {
        // Set data size
        let size = self.data_size.unwrap_or(self.data_ptr as u8);
        self.buf[5] = size;

        // Calculate CRC (XOR of bytes 1-87)
        self.buf[88] = fast_crc_impl(&self.buf);

        self.buf.to_vec()
    }

    /// Parse a response buffer and extract status and data.
    ///
    /// Returns (status, data_bytes) tuple.
    fn parse_response(&self, response: &[u8]) -> PyResult<(Status, Vec<u8>)> {
        if response.len() != REPORT_SIZE {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Invalid response size: expected {}, got {}",
                REPORT_SIZE,
                response.len()
            )));
        }

        let status = Status::from(response[0]);
        let data_size = response[5] as usize;
        let data = response[8..8 + data_size.min(DATA_SIZE)].to_vec();

        Ok((status, data))
    }

    /// Run the report on a device (blocking).
    ///
    /// Sends the report and reads the response, with retry logic for BUSY status.
    ///
    /// Args:
    ///     device: HidDevice to communicate with
    ///     delay_ms: Inter-command delay in milliseconds (default 7)
    ///     retries: Number of retries on BUSY (default 3)
    ///
    /// Returns:
    ///     (status, response_data) tuple
    #[pyo3(signature = (device, delay_ms=None, retries=3))]
    fn run(
        &mut self,
        device: &HidDevice,
        delay_ms: Option<u64>,
        retries: u32,
    ) -> PyResult<(Status, Vec<u8>)> {
        let delay = Duration::from_millis(delay_ms.unwrap_or(CMD_DELAY_MS));
        let data = self.pack();
        let mut attempts = retries;

        loop {
            // Delay before sending
            thread::sleep(delay);

            // Send report
            device.send_report(data.clone(), 0)?;

            // If this is a multi-packet send (remaining > 0), don't read response
            if self.get_remaining_packets() > 0 {
                return Ok((Status::Ok, vec![]));
            }

            // Delay before reading response
            thread::sleep(delay);

            // Get response
            let response = device.get_report(0, REPORT_SIZE)?;
            let (status, resp_data) = self.parse_response(&response)?;

            match status {
                Status::Ok => return Ok((status, resp_data)),
                Status::Unsupported => return Ok((status, resp_data)),
                Status::Fail => {
                    return Err(HidError::ProtocolError("Command failed".into()).into())
                }
                Status::Busy | Status::Timeout => {
                    if attempts == 0 {
                        return Err(
                            HidError::ProtocolError(format!("Max retries: {:?}", status)).into(),
                        );
                    }
                    attempts -= 1;
                    thread::sleep(Duration::from_millis(100));
                }
                _ => {
                    return Err(
                        HidError::ProtocolError(format!("Unknown status: {:?}", status)).into(),
                    )
                }
            }
        }
    }

    /// Get the current argument data pointer position.
    #[getter]
    fn args_size(&self) -> usize {
        self.data_ptr
    }

    /// Get the transaction ID.
    #[getter]
    fn transaction_id(&self) -> u8 {
        self.transaction_id
    }

    /// Get the command class.
    #[getter]
    fn command_class(&self) -> u8 {
        self.command_class
    }

    /// Get the command ID.
    #[getter]
    fn command_id(&self) -> u8 {
        self.command_id
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_report_creation() {
        let report = RazerReport::new(0x00, 0x81, Some(2), 0xFF);
        assert_eq!(report.transaction_id, 0xFF);
        assert_eq!(report.command_class, 0x00);
        assert_eq!(report.command_id, 0x81);
    }

    #[test]
    fn test_report_pack() {
        let mut report = RazerReport::new(0x00, 0x81, Some(2), 0xFF);
        let data = report.pack();
        assert_eq!(data.len(), 90);
        assert_eq!(data[1], 0xFF); // transaction_id
        assert_eq!(data[5], 2); // data_size
        assert_eq!(data[6], 0x00); // command_class
        assert_eq!(data[7], 0x81); // command_id
    }

    #[test]
    fn test_report_put_bytes() {
        let mut report = RazerReport::new(0x03, 0x0B, None, 0xFF);
        report.put_byte(0x00).unwrap();
        report.put_byte(0x01).unwrap();
        report.put_rgb(255, 0, 0).unwrap();

        assert_eq!(report.args_size(), 5);

        let data = report.pack();
        assert_eq!(data[8], 0x00);
        assert_eq!(data[9], 0x01);
        assert_eq!(data[10], 255);
        assert_eq!(data[11], 0);
        assert_eq!(data[12], 0);
    }

    #[test]
    fn test_report_crc() {
        let mut report = RazerReport::new(0x00, 0x81, Some(2), 0xFF);
        let data = report.pack();
        // CRC should be non-zero for non-trivial reports
        // Verify it matches our CRC implementation
        assert_eq!(data[88], fast_crc_impl(&data));
    }

    #[test]
    fn test_status_from_u8() {
        assert_eq!(Status::from(0x00), Status::Unknown);
        assert_eq!(Status::from(0x01), Status::Busy);
        assert_eq!(Status::from(0x02), Status::Ok);
        assert_eq!(Status::from(0x03), Status::Fail);
        assert_eq!(Status::from(0x04), Status::Timeout);
        assert_eq!(Status::from(0x05), Status::Unsupported);
    }

    #[test]
    fn test_remaining_packets() {
        let mut report = RazerReport::new(0x03, 0x0B, None, 0xFF);
        report.set_remaining_packets(5);
        assert_eq!(report.get_remaining_packets(), 5);
    }

    #[test]
    fn test_report_clear() {
        let mut report = RazerReport::new(0x00, 0x81, None, 0xFF);
        report.put_byte(0xAA).unwrap();
        report.put_byte(0xBB).unwrap();
        assert_eq!(report.args_size(), 2);

        report.clear();
        assert_eq!(report.args_size(), 0);
    }
}
