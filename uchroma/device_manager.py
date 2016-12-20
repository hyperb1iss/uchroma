import logging

import hidapi
from uchroma.device import RazerChromaDevice
from uchroma.device_base import RazerDeviceType


RAZER_VENDOR_ID = 0x1532


class DeviceManager(object):

    def __init__(self):
        self._logger = logging.getLogger('uchroma.devicemanager')

        self._devices = {}

        self.discover()


    def discover(self):
        devinfos = hidapi.enumerate(vendor_id=RAZER_VENDOR_ID)
        for devinfo in devinfos:
            for devtype in RazerDeviceType:
                if devinfo.product_id in devtype.value:
                    add = True
                    if devtype == RazerDeviceType.KEYBOARD or devtype == RazerDeviceType.LAPTOP:
                        if devinfo.interface_number != 2:
                            add = False
                    elif devtype == RazerDeviceType.MOUSEPAD:
                        if devinfo.interface_number != 1:
                            add = False

                    if add:
                        self._devices[devinfo.path.decode()] = RazerChromaDevice(devinfo, devtype.name, devtype.value[devinfo.product_id])


    @property
    def devices(self):
        return self._devices

