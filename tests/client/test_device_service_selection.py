#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for DeviceService device selection."""

from uchroma.client.device_service import DeviceInfo, DeviceService


class _FakeClient:
    def __init__(self):
        self.last_identifier = None

    def get_device(self, identifier):
        self.last_identifier = identifier
        return f"proxy:{identifier}"


class _TestDeviceService(DeviceService):
    def __init__(self, devices, client):
        super().__init__()
        self._connected = True
        self._client = client
        self._devices = devices

    def _try_connect(self) -> bool:
        return self._connected

    def list_devices(self):
        return self._devices


def test_get_device_by_path_bypasses_matcher():
    client = _FakeClient()
    devices = [
        DeviceInfo(name="A", device_type="keyboard", key="1532:0001.00", index=0),
    ]
    service = _TestDeviceService(devices, client)

    path = "/io/uchroma/device/0"
    proxy = service.get_device(path)
    assert proxy == f"proxy:{path}"
    assert client.last_identifier == path


def test_get_device_by_index_matches_device_index_not_list_position():
    client = _FakeClient()
    devices = [
        DeviceInfo(name="A", device_type="keyboard", key="1532:0001.00", index=10),
        DeviceInfo(name="B", device_type="mouse", key="1532:0002.00", index=0),
    ]
    service = _TestDeviceService(devices, client)

    proxy = service.get_device("0")
    assert proxy == "proxy:1532:0002.00"
    assert client.last_identifier == "1532:0002.00"
