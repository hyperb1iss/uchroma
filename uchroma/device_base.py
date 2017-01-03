from enum import Enum

import hidapi
from uchroma.models import Model
from uchroma.report import RazerReport


class BaseUChromaDevice(object):

    # commands
    class Command(Enum):
        # info queries, class 0
        SET_DEVICE_MODE = (0x00, 0x04, 0x02)

        GET_FIRMWARE_VERSION = (0x00, 0x81, 0x02)
        GET_SERIAL = (0x00, 0x82, 0x16)
        GET_DEVICE_MODE = (0x00, 0x84, 0x02)


    def __init__(self, devinfo, devtype, devname):
        self._devinfo = devinfo
        self._devtype = devtype
        self._devname = devname
        self._dev = None

        self._serial_number = None
        self._firmware_version = None


    def close(self):
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass

            self._dev = None


    def __del__(self):
        self.close()


    def _ensure_open(self):
        if self._dev is None:
            self._dev = hidapi.Device(self._devinfo)


    def _get_report(self, command_class, command_id, data_size, *args, transaction_id=0xFF):
        report = RazerReport(self._dev, command_class, command_id, data_size, transaction_id=transaction_id)
        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put(arg)

        return report


    def run_with_result(self, command, *args, transaction_id=0xFF, defer_close=False):
        self._ensure_open()
        report = self._get_report(*command.value, *args, transaction_id=transaction_id)
        result = None

        if report.run():
            result = report.result

        if not defer_close:
            self.close()

        return result


    def run_command(self, command, *args, transaction_id=0xFF, defer_close=False):
        self._ensure_open()
        status = self._get_report(*command.value, *args, transaction_id=transaction_id).run()

        if not defer_close:
            self.close()

        return status


    def get_device_mode(self):
        return self.run_with_result(BaseUChromaDevice.Command.GET_DEVICE_MODE)


    def set_device_mode(self, mode, param=0):
        return self.run_command(BaseUChromaDevice.Command.SET_DEVICE_MODE, mode, param)


    @property
    def serial_number(self):
        if self._devtype == Model.LAPTOP:
            return 'BUILTIN'

        if self._serial_number is None:
            self._serial_number = self.run_with_result(BaseUChromaDevice.Command.GET_SERIAL)

        return self._serial_number


    @property
    def firmware_version(self):
        if self._firmware_version is None:
            version = self.run_with_result(BaseUChromaDevice.Command.GET_FIRMWARE_VERSION)
            if version is None:
                self._firmware_version = '(unknown)'
            else:
                self._firmware_version = 'v%d.%d' % (version[0], version[1])

        return self._firmware_version


    @property
    def name(self):
        return self._devname


    @property
    def product_id(self):
        return self._devinfo.product_id


    @property
    def vendor_id(self):
        return self._devinfo.vendor_id


    @property
    def device_type(self):
        return self._devtype
