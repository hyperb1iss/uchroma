import logging
import sys
import time

from collections import OrderedDict

import hidapi

from pyudev import Context, Monitor, MonitorObserver

from uchroma.device import UChromaDevice
from uchroma.hardware import Hardware, Quirks, RAZER_VENDOR_ID
from uchroma.headset import UChromaHeadset
from uchroma.keyboard import UChromaKeyboard
from uchroma.laptop import UChromaLaptop
from uchroma.mouse import UChromaMouse, UChromaWirelessMouse

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class UChromaDeviceManager(object):
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
        self._logger = logging.getLogger('uchroma.devicemanager')

        self._devices = OrderedDict()
        self._monitor = False
        self._udev_context = Context()
        self._udev_observer = None
        self._callbacks = []

        if callbacks is not None:
            self._callbacks.extend(callbacks)

        self.discover()


    def _fire_callbacks(self, action: str, device: UChromaDevice):
        # delay for udev setup
        time.sleep(0.2)

        for callback in self._callbacks:
            callback(action, device)


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
        devinfos = hidapi.enumerate(vendor_id=RAZER_VENDOR_ID)
        index = 0

        for devinfo in devinfos:
            self._logger.debug('Check device %04x interface %d (%s)',
                               devinfo.product_id, devinfo.interface_number, devinfo.product_string)
            hardware = Hardware.get_device(devinfo.product_id)
            if hardware is None:
                continue

            if hardware.type == Hardware.Type.HEADSET:
                if devinfo.interface_number != 3:
                    continue
            elif hardware.type == Hardware.Type.KEYBOARD or hardware.type == Hardware.Type.LAPTOP:
                if devinfo.interface_number != 2:
                    continue
            elif hardware.type == Hardware.Type.MOUSEPAD:
                if devinfo.interface_number != 1:
                    continue
            else:
                if devinfo.interface_number != 0:
                    continue

            key = '%04x:%04x.%02d' % (devinfo.vendor_id, devinfo.product_id, index)
            if key in self._devices:
                continue

            self._devices[key] = self._create_device(hardware, devinfo, index)
            self._fire_callbacks('add', self._devices[key])

            index += 1


    def _create_device(self, hardware, devinfo, index):
        parent = self._get_parent(devinfo.product_id)
        input_devs = self._get_input_devices(parent)

        if hardware.type == Hardware.Type.MOUSE:
            if hardware.has_quirk(Quirks.WIRELESS):
                return UChromaWirelessMouse(hardware, devinfo, index, input_devs)
            return UChromaMouse(hardware, devinfo, input_devs)

        if hardware.type == Hardware.Type.LAPTOP:
            return UChromaLaptop(hardware, devinfo, index, input_devs)

        if hardware.type == Hardware.Type.KEYBOARD:
            input_devs = self._get_input_devices(parent)
            return UChromaKeyboard(hardware, devinfo, index, input_devs)

        if hardware.type == Hardware.Type.HEADSET:
            return UChromaHeadset(hardware, devinfo, index)

        return UChromaDevice(hardware, devinfo, index)


    @property
    def devices(self):
        """
        Dict of available devices, empty if no devices are detected.
        """
        return self._devices


    @property
    def callbacks(self):
        """
        List of callbacks invoked when device changes are detected
        """
        return self._callbacks


    def _get_parent(self, product_id: int):
        pid = "%04x" % product_id

        devs = self._udev_context.list_devices(tag='uchroma', subsystem='usb',
                                               ID_MODEL_ID=pid)
        for dev in devs:
            if dev['DEVTYPE'] == 'usb_device':
                return dev

        return None


    def _get_input_devices(self, parent) -> list:
        inputs = []
        if parent is not None:
            for child in parent.children:
                if child.subsystem == 'input' and 'DEVNAME' in child:
                    for link in child.device_links:
                        if link.startswith('/dev/input/by-id/'):
                            inputs.append(link)
                            continue

        return inputs


    def _udev_event(self, device):
        self._logger.debug('Device event [%s]: %s', device.action, device.device_path)

        if device.action == 'remove':
            key = '%s:%s' % (device['ID_VENDOR_ID'], device['ID_MODEL_ID'])
            removed = self._devices.pop(key, None)
            if removed is not None:
                removed.close()
                self._fire_callbacks('remove', removed)

        else:
            self.discover()


    def monitor_start(self):
        """
        Start watching for device changes

        Listen for relevant add/remove events from udev and fire callbacks.
        """

        if self._monitor:
            return

        udev_monitor = Monitor.from_netlink(self._udev_context)
        udev_monitor.filter_by_tag('uchroma')
        udev_monitor.filter_by(subsystem='usb', device_type=u'usb_device')

        self._udev_observer = MonitorObserver(udev_monitor, callback=self._udev_event,
                                              name='uchroma-monitor')
        self._udev_observer.start()
        self._monitor = True

        self._logger.debug('Udev monitor started')


    def monitor_stop(self):
        """
        Stop watching for device changes
        """
        if not self._monitor:
            return

        self._udev_observer.send_stop()
        self._monitor = False

        self._logger.debug('Udev monitor stopped')
