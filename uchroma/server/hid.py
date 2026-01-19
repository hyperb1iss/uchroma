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
    HidDevice,
    RazerReport,
    Status,
    enumerate_devices,
    enumerate_devices_async,
    open_device_async,
    send_frame_async,
)

__all__ = [
    "DATA_SIZE",
    "REPORT_SIZE",
    "DeviceInfo",
    "HidDevice",
    "RazerReport",
    "Status",
    "enumerate_devices",
    "enumerate_devices_async",
    "open_device_async",
    "send_frame_async",
]
