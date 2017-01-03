import logging

import hidapi
from uchroma.device import UChromaDevice
from uchroma.models import Model, RAZER_VENDOR_ID


class UChromaDeviceManager(object):

    def __init__(self):
        self._logger = logging.getLogger('uchroma.devicemanager')

        self._devices = {}

        self.discover()


    def discover(self):
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
                        self._devices[devinfo.path.decode()] = UChromaDevice(devinfo, devtype.name, devtype.value[devinfo.product_id])


    @property
    def devices(self):
        return self._devices

