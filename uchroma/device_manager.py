import logging

import hidapi
from uchroma.device import UChromaDevice
from uchroma.models import Model, RAZER_VENDOR_ID


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

    def __init__(self):
        self._logger = logging.getLogger('uchroma.devicemanager')

        self._devices = {}

        self.discover()


    def discover(self):
        """
        Perform HID device discovery

        Iterates over all connected HID devices with RAZER_VENDOR_ID
        and checks the product ID against the Model enumeration.

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
        for devinfo in devinfos:
            for devtype in Model:
                if devinfo.product_id in devtype.value:
                    add = True
                    if devtype == Model.KEYBOARD or devtype == Model.LAPTOP:
                        if devinfo.interface_number != 2:
                            add = False
                    elif devtype == Model.MOUSEPAD:
                        if devinfo.interface_number != 1:
                            add = False

                    if add:
                        self._devices[devinfo.path.decode()] = UChromaDevice(
                            devinfo, devtype.name, devtype.value[devinfo.product_id])


    @property
    def devices(self):
        """
        Dict of available devices, empty if no devices are detected.

        The keys of this dict depend on the backend used by HIDAPI.
        If the HIDRAW backend is used, the keys will be an absolute
        path to the device (/dev/hidraw2). If the libusb backend
        is used, the keys will contain the USB identifier string
        in the format "bus_id:dev_id:interface_id" (0001:0004:02).
        On Linux this corresponds to the path /dev/bus/usb/001/004.
        """
        return self._devices

