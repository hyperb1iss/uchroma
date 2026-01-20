#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
HID device access — Rust nusb backend.

Thin re-exports from the native Rust module.
"""

from uchroma._native import (
    DATA_SIZE,
    REPORT_SIZE,
    DeviceInfo,
    HeadsetDevice,
    HidDevice,
    RazerReport,
    Status,
    enumerate_devices,
    enumerate_devices_async,
    headset_constants,
    open_device_async,
    send_frame_async,
)

# Headset protocol constants
READ_RAM, READ_EEPROM, WRITE_RAM, HEADSET_REPORT_OUT_LEN, HEADSET_REPORT_IN_LEN = headset_constants()

__all__ = [
    "DATA_SIZE",
    "REPORT_SIZE",
    "DeviceInfo",
    "HeadsetDevice",
    "HidDevice",
    "RazerReport",
    "Status",
    "enumerate_devices",
    "enumerate_devices_async",
    "open_device_async",
    "send_frame_async",
    "READ_RAM",
    "READ_EEPROM",
    "WRITE_RAM",
    "HEADSET_REPORT_OUT_LEN",
    "HEADSET_REPORT_IN_LEN",
]
