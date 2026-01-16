#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
import asyncio
import contextlib
from collections import OrderedDict
from concurrent import futures

from pyudev import Context, Monitor, MonitorObserver
from pyudev._os import pipe

from uchroma.log import Log
from uchroma.server import hidadapter as hidapi
from uchroma.util import Signal, Singleton, ensure_future

from .device import UChromaDevice
from .device_base import BaseUChromaDevice
from .hardware import RAZER_VENDOR_ID, Hardware, Quirks
from .headset import UChromaHeadset
from .keyboard import UChromaKeyboard
from .keypad import UChromaKeypad
from .laptop import UChromaLaptop
from .mouse import UChromaMouse, UChromaWirelessMouse


class AsyncMonitorObserver:
    def __init__(self, monitor, callback=None, name=None, *args, **kwargs):
        if callback is None:
            raise ValueError("callback missing")

        self.monitor = monitor
        self._stop_event = None
        self._callback = callback

        self._executor = futures.ThreadPoolExecutor(max_workers=2)
        self._run_future = None

    def _run(self):
        self._stop_event = pipe.Pipe.open()
        MonitorObserver.run(self)  # type: ignore[arg-type]  # duck-typing MonitorObserver

    def _stop(self):
        MonitorObserver.send_stop(self)  # type: ignore[arg-type]  # duck-typing MonitorObserver

    async def start(self):
        loop = asyncio.get_running_loop()
        if self._run_future is None or self._run_future.done():
            self._run_future = loop.run_in_executor(self._executor, self._run)

    async def stop(self):
        if self._run_future is None:
            return

        # Request stop and wait for the observer thread to exit.
        with contextlib.suppress(Exception):
            self._stop()
        with contextlib.suppress(Exception):
            await self._run_future

        self._run_future = None
        self._executor.shutdown(wait=False, cancel_futures=True)


class UChromaDeviceManager(metaclass=Singleton):
    """
    Enumerates HID devices which can be managed by uChroma

    This is the main API entry point when developing applications
    with uChroma. Simply instantiate this object and the
    available devices can be fetched from the "devices" dict.

    Uses HIDAPI for low-level hardware interactions. Suitable
    permissions are required on the device nodes or this will
    fail.
    """

    def __init__(self, *callbacks):
        self._logger = Log.get("uchroma.devicemanager")

        self._devices = OrderedDict()
        self._monitor = False
        self._udev_context = Context()
        self._udev_observer = None
        self._callbacks = []

        if callbacks is not None:
            self._callbacks.extend(callbacks)

        self._loop = None

        self.device_added = Signal()
        self.device_removed = Signal()

        self.discover()

    async def _fire_callbacks(self, action: str, device: BaseUChromaDevice):
        # delay for udev setup
        await asyncio.sleep(0.2)

        for callback in self._callbacks:
            await callback(action, device)

    def discover(self):
        """
        Perform HID device discovery

        Iterates over all connected HID devices with RAZER_VENDOR_ID
        and checks the product ID against the Hardware descriptor.

        Interface endpoint restrictions are currently hard-coded. In
        the future this should be done by checking the HID report
        descriptor of the endpoint, however this functionality in
        HIDAPI is broken (report_descriptor returns garbage) on
        Linux in the current release.

        Discovery is automatically performed when the object is
        constructed, so this should only need to be called if the
        list of devices changes (monitoring for changes is beyond
        the scope of this API).
        """
        devinfos = sorted(hidapi.enumerate(vendor_id=RAZER_VENDOR_ID), key=lambda x: x.path)

        for devinfo in devinfos:
            parent = self._get_parent(devinfo.product_id)
            if parent is None:
                continue

            if self._key_for_path(parent.sys_path) is not None:
                continue

            hardware = Hardware.get_device(devinfo.product_id)
            if hardware is None:
                continue

            if hardware.type == Hardware.Type.HEADSET:
                if devinfo.interface_number != 3:
                    continue
            elif hardware.type == Hardware.Type.LAPTOP:
                # Blade laptops use interface 0 for control
                if devinfo.interface_number != 0:
                    continue
            elif hardware.type in (Hardware.Type.KEYBOARD, Hardware.Type.KEYPAD):
                # Modern keyboards use interface 3, legacy use interface 0
                expected_iface = 3 if hardware.has_quirk(Quirks.CONTROL_IFACE_3) else 0
                if devinfo.interface_number != expected_iface:
                    continue
            elif hardware.type in (Hardware.Type.MOUSE, Hardware.Type.MOUSEPAD):
                if devinfo.interface_number != 1:
                    continue
            else:
                if devinfo.interface_number != 0:
                    continue

            device = self._create_device(parent, hardware, devinfo)
            if device is not None:
                self._devices[device.key] = device

                if hardware.type == Hardware.Type.KEYBOARD:
                    device.set_device_mode(0)

                if self._monitor and self._callbacks:
                    ensure_future(self._fire_callbacks("add", device), loop=self._loop)

    def _next_index(self):
        if not self._devices:
            return 0

        indexes = [device.device_index for device in self._devices.values()]
        indexes.sort()
        for idx, _ in enumerate(indexes):
            if idx + 1 == len(indexes):
                return _ + 1
            if _ + 1 == indexes[idx + 1]:
                continue
            return _ + 1
        raise ValueError("should not be here")

    def _create_device(self, parent, hardware, devinfo):
        input_devs = self._get_input_devices(parent)
        sys_path = parent.sys_path
        index = self._next_index()

        if hardware.type == Hardware.Type.MOUSE:
            if hardware.has_quirk(Quirks.WIRELESS):
                return UChromaWirelessMouse(hardware, devinfo, index, sys_path, input_devs)
            return UChromaMouse(hardware, devinfo, index, sys_path, input_devs)

        if hardware.type == Hardware.Type.LAPTOP:
            return UChromaLaptop(hardware, devinfo, index, sys_path, input_devs)

        if hardware.type == Hardware.Type.KEYBOARD:
            input_devs = self._get_input_devices(parent)
            return UChromaKeyboard(hardware, devinfo, index, sys_path, input_devs)

        if hardware.type == Hardware.Type.KEYPAD:
            input_devs = self._get_input_devices(parent)
            return UChromaKeypad(hardware, devinfo, index, sys_path, input_devs)

        if hardware.type == Hardware.Type.HEADSET:
            return UChromaHeadset(hardware, devinfo, index, sys_path)

        return UChromaDevice(hardware, devinfo, index, sys_path)

    def _key_for_path(self, path):
        for key, device in self._devices.items():
            if device.sys_path == path:
                return key
        return None

    @property
    def devices(self):
        """
        Dict of available devices, empty if no devices are detected.
        """
        self.discover()

        return self._devices

    @property
    def callbacks(self):
        """
        List of coroutines invoked when device changes are detected
        """
        return self._callbacks

    def _get_parent(self, product_id: int):
        pid = f"{product_id:04x}"
        vid = f"{RAZER_VENDOR_ID:04x}"

        # Try with uchroma tag first (requires udev rules installed)
        devs = self._udev_context.list_devices(tag="uchroma", subsystem="usb", ID_MODEL_ID=pid)
        for dev in devs:
            if dev["DEVTYPE"] == "usb_device":
                return dev

        # Fallback: search without tag (for testing without udev rules)
        devs = self._udev_context.list_devices(subsystem="usb", ID_VENDOR_ID=vid, ID_MODEL_ID=pid)
        for dev in devs:
            if dev.get("DEVTYPE") == "usb_device":
                return dev

        return None

    def _get_input_devices(self, parent) -> list:
        inputs = []
        if parent is not None:
            for child in parent.children:
                # Only include event devices (evdev), not raw mouse/joystick devices
                if child.subsystem == "input" and child.get("DEVNAME", "").startswith(
                    "/dev/input/event"
                ):
                    for link in child.device_links:
                        if link.startswith("/dev/input/by-id/"):
                            inputs.append(link)
                            break

        return inputs

    def _udev_event(self, device):
        self._logger.debug("Device event [%s]: %s", device.action, device)

        if device.action == "remove":
            key = self._key_for_path(device.sys_path)
            if key is not None:
                removed = self._devices.pop(key, None)
                if removed is not None:
                    removed.close()
                    if self._callbacks and self._loop is not None:
                        ensure_future(self._fire_callbacks("remove", removed), loop=self._loop)

        else:
            if self._key_for_path(device.sys_path) is None:
                self.discover()

    async def close_devices(self):
        """
        Close all open devices and perform cleanup
        """
        for device in self._devices.values():
            await device.shutdown()
        self._devices.clear()

    async def monitor_start(self):
        """
        Start watching for device changes

        Listen for relevant add/remove events from udev and fire callbacks.
        """

        if self._monitor:
            return

        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        udev_monitor = Monitor.from_netlink(self._udev_context)
        udev_monitor.filter_by_tag("uchroma")
        udev_monitor.filter_by(subsystem="usb", device_type="usb_device")

        self._udev_observer = AsyncMonitorObserver(
            udev_monitor, callback=self._udev_event, name="uchroma-monitor"
        )
        await self._udev_observer.start()
        self._monitor = True

        if self._callbacks and self._loop is not None:
            for device in self._devices.values():
                ensure_future(self._fire_callbacks("add", device), loop=self._loop)

        self._logger.debug("Udev monitor started")

    async def monitor_stop(self):
        """
        Stop watching for device changes
        """
        if not self._monitor:
            return

        await self._udev_observer.stop()
        self._monitor = False

        self._logger.debug("Udev monitor stopped")
