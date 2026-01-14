#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
"""
HID adapter layer.

Provides a compatibility layer between the old hidapi-cffi API
and the modern cython-hidapi (hid) package.
"""

import hid


class DeviceInfo:
    """
    Device info wrapper matching the old hidapi-cffi API.
    """
    def __init__(self, info_dict: dict):
        self._info = info_dict

    @property
    def path(self) -> bytes:
        return self._info['path']

    @property
    def vendor_id(self) -> int:
        return self._info['vendor_id']

    @property
    def product_id(self) -> int:
        return self._info['product_id']

    @property
    def serial_number(self) -> str:
        return self._info.get('serial_number', '')

    @property
    def release_number(self) -> int:
        return self._info.get('release_number', 0)

    @property
    def manufacturer_string(self) -> str:
        return self._info.get('manufacturer_string', '')

    @property
    def product_string(self) -> str:
        return self._info.get('product_string', '')

    @property
    def usage_page(self) -> int:
        return self._info.get('usage_page', 0)

    @property
    def usage(self) -> int:
        return self._info.get('usage', 0)

    @property
    def interface_number(self) -> int:
        return self._info.get('interface_number', -1)

    def __repr__(self):
        return (f"DeviceInfo(vendor_id=0x{self.vendor_id:04x}, "
                f"product_id=0x{self.product_id:04x}, "
                f"interface={self.interface_number})")


class Device:
    """
    HID device wrapper matching the old hidapi-cffi API.
    """
    def __init__(self, devinfo: DeviceInfo, blocking: bool = True):
        self._devinfo = devinfo
        self._blocking = blocking
        self._device = hid.device()
        self._device.open_path(devinfo.path)
        self._device.set_nonblocking(not blocking)

    def close(self):
        """Close the device."""
        if self._device:
            self._device.close()
            self._device = None

    def write(self, data: bytes) -> int:
        """Write data to the device."""
        return self._device.write(data)

    def read(self, size: int, timeout_ms: int = 0) -> bytes:
        """Read data from the device."""
        if timeout_ms > 0:
            return bytes(self._device.read(size, timeout_ms))
        return bytes(self._device.read(size))

    def send_feature_report(self, data: bytes) -> int:
        """Send a feature report."""
        return self._device.send_feature_report(data)

    def get_feature_report(self, report_id: int, size: int) -> bytes:
        """Get a feature report."""
        return bytes(self._device.get_feature_report(report_id, size))

    def set_nonblocking(self, nonblocking: bool):
        """Set non-blocking mode."""
        self._blocking = not nonblocking
        self._device.set_nonblocking(nonblocking)

    @property
    def blocking(self) -> bool:
        return self._blocking


def enumerate(vendor_id: int = 0, product_id: int = 0) -> list:
    """
    Enumerate HID devices.

    Returns a list of DeviceInfo objects (matching old API).
    """
    devices = hid.enumerate(vendor_id, product_id)
    return [DeviceInfo(d) for d in devices]
