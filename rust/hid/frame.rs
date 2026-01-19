//! Custom frame upload helpers.
//!
//! Sends frame data as a sequence of feature reports with minimal allocations.

use crate::crc::fast_crc_impl;
use crate::hid::{HidDevice, HidError, DATA_SIZE, REPORT_SIZE};
use numpy::{PyReadonlyArray3, PyUntypedArrayMethods};
use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::future_into_py;
use std::time::Duration;
use tokio::time::sleep;

const FRAME_MAX_WIDTH: usize = 24;
const REPORT_DATA_OFFSET: usize = 8;
const REPORT_CRC_OFFSET: usize = 88;
const COMMAND_CLASS_LEGACY: u8 = 0x03;
const COMMAND_ID_FRAME_MATRIX: u8 = 0x0B;
const COMMAND_CLASS_EXTENDED: u8 = 0x0F;
const COMMAND_ID_FRAME_EXTENDED: u8 = 0x03;

#[pyfunction]
#[pyo3(
    signature = (
        device,
        frame,
        frame_id=0xFF,
        transaction_id=0xFF,
        is_extended=false,
        row_offsets=None,
        pre_delay_ms=7,
        post_delay_ms=1
    )
)]
#[allow(clippy::too_many_arguments)]
pub fn send_frame_async<'py>(
    py: Python<'py>,
    device: &HidDevice,
    frame: PyReadonlyArray3<u8>,
    frame_id: u8,
    transaction_id: u8,
    is_extended: bool,
    row_offsets: Option<Vec<u8>>,
    pre_delay_ms: u64,
    post_delay_ms: u64,
) -> PyResult<Bound<'py, PyAny>> {
    let shape = frame.shape();
    if shape.len() != 3 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "frame must be a 3D ndarray (height, width, channels)",
        ));
    }

    let height = shape[0];
    let width = shape[1];
    let channels = shape[2];

    if channels != 3 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "frame must have 3 channels (RGB)",
        ));
    }

    let frame_slice = frame
        .as_slice()
        .map_err(|_| pyo3::exceptions::PyValueError::new_err("frame must be C-contiguous uint8"))?;
    let frame_data = frame_slice.to_vec();

    let interface = device.interface_clone();

    let offsets = row_offsets.map(|vals| vals.into_iter().map(|v| v as usize).collect::<Vec<_>>());

    future_into_py(py, async move {
        if height == 0 || width == 0 {
            return Ok(());
        }

        if let Some(ref vals) = offsets {
            if vals.len() < height {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "row_offsets length must match frame height",
                ));
            }
        }

        let multi = width > FRAME_MAX_WIDTH;
        let split_width = if multi { width / 2 } else { width };
        let packets_per_row = if multi { 2 } else { 1 };
        let total_packets = height
            .checked_mul(packets_per_row)
            .ok_or_else(|| HidError::ProtocolError("packet count overflow".into()))?;

        if total_packets > u16::MAX as usize {
            return Err(HidError::ProtocolError("packet count too large".into()).into());
        }

        let command_class = if is_extended {
            COMMAND_CLASS_EXTENDED
        } else {
            COMMAND_CLASS_LEGACY
        };
        let command_id = if is_extended {
            COMMAND_ID_FRAME_EXTENDED
        } else {
            COMMAND_ID_FRAME_MATRIX
        };

        let pre_delay = Duration::from_millis(pre_delay_ms);
        let post_delay = Duration::from_millis(post_delay_ms);

        let mut report = [0u8; REPORT_SIZE];
        report[1] = transaction_id;
        report[6] = command_class;
        report[7] = command_id;

        let mut packet_index: usize = 0;

        for row in 0..height {
            let row_offset = offsets
                .as_ref()
                .and_then(|vals| vals.get(row).copied())
                .unwrap_or(0);

            let first_len = split_width;
            packet_index = send_segment(
                interface.clone(),
                &frame_data,
                &mut report,
                row,
                width,
                channels,
                0,
                row_offset,
                first_len,
                frame_id,
                is_extended,
                total_packets,
                packet_index,
                pre_delay,
                post_delay,
            )
            .await?;

            if multi {
                let second_len = width - split_width;
                packet_index = send_segment(
                    interface.clone(),
                    &frame_data,
                    &mut report,
                    row,
                    width,
                    channels,
                    split_width,
                    split_width,
                    second_len,
                    frame_id,
                    is_extended,
                    total_packets,
                    packet_index,
                    pre_delay,
                    post_delay,
                )
                .await?;
            }
        }

        Ok(())
    })
}

#[allow(clippy::too_many_arguments)]
async fn send_segment(
    interface: std::sync::Arc<tokio::sync::Mutex<Option<nusb::Interface>>>,
    frame_data: &[u8],
    report: &mut [u8; REPORT_SIZE],
    row: usize,
    width: usize,
    channels: usize,
    data_start_col: usize,
    header_start_col: usize,
    segment_width: usize,
    frame_id: u8,
    is_extended: bool,
    total_packets: usize,
    packet_index: usize,
    pre_delay: Duration,
    post_delay: Duration,
) -> Result<usize, HidError> {
    if segment_width == 0 {
        return Ok(packet_index);
    }

    let data_len = segment_width
        .checked_mul(channels)
        .ok_or_else(|| HidError::ProtocolError("segment size overflow".into()))?;
    let prefix_len = if is_extended { 5 } else { 4 };
    if prefix_len + data_len > DATA_SIZE {
        return Err(HidError::ProtocolError("segment payload too large".into()));
    }

    let row_base = row
        .checked_mul(width)
        .and_then(|v| v.checked_mul(channels))
        .ok_or_else(|| HidError::ProtocolError("frame index overflow".into()))?;
    let data_start = row_base
        .checked_add(data_start_col * channels)
        .ok_or_else(|| HidError::ProtocolError("frame index overflow".into()))?;
    let data_end = data_start
        .checked_add(data_len)
        .ok_or_else(|| HidError::ProtocolError("frame index overflow".into()))?;

    if data_end > frame_data.len() {
        return Err(HidError::ProtocolError("frame data out of bounds".into()));
    }

    let remaining = total_packets
        .checked_sub(packet_index + 1)
        .ok_or_else(|| HidError::ProtocolError("packet index overflow".into()))?;
    let remaining_u16 = u16::try_from(remaining)
        .map_err(|_| HidError::ProtocolError("remaining packet overflow".into()))?;

    let stop_col = header_start_col + segment_width - 1;
    if stop_col > u8::MAX as usize || header_start_col > u8::MAX as usize {
        return Err(HidError::ProtocolError("column index overflow".into()));
    }

    report[REPORT_DATA_OFFSET..REPORT_CRC_OFFSET].fill(0);
    report[2..4].copy_from_slice(&remaining_u16.to_le_bytes());
    report[5] = (prefix_len + data_len) as u8;

    if is_extended {
        report[REPORT_DATA_OFFSET] = 0x00;
        report[REPORT_DATA_OFFSET + 1] = 0x00;
        report[REPORT_DATA_OFFSET + 2] = row as u8;
        report[REPORT_DATA_OFFSET + 3] = header_start_col as u8;
        report[REPORT_DATA_OFFSET + 4] = stop_col as u8;
    } else {
        report[REPORT_DATA_OFFSET] = frame_id;
        report[REPORT_DATA_OFFSET + 1] = row as u8;
        report[REPORT_DATA_OFFSET + 2] = header_start_col as u8;
        report[REPORT_DATA_OFFSET + 3] = stop_col as u8;
    }

    let data_dst_start = REPORT_DATA_OFFSET + prefix_len;
    let data_dst_end = data_dst_start + data_len;
    report[data_dst_start..data_dst_end].copy_from_slice(&frame_data[data_start..data_end]);

    report[REPORT_CRC_OFFSET] = fast_crc_impl(report);

    if pre_delay.as_millis() > 0 {
        sleep(pre_delay).await;
    }

    HidDevice::send_feature_report_inner(interface, report, 0).await?;

    if post_delay.as_millis() > 0 {
        sleep(post_delay).await;
    }

    Ok(packet_index + 1)
}
