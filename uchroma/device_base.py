from enum import Enum

import hidapi
from uchroma.report import RazerReport


class Model(Enum):
    KEYBOARD = {
        0x010D: 'BlackWidow Ultimate 2012',
        0x011A: 'BlackWidow Ultimate 2013',
        0x011B: 'BlackWidow Classic',
        0x0203: 'BlackWidow Chroma',
        0x0208: 'Tartarus Chroma',
        0x0209: 'BlackWidow Chroma Tournament Edition',
        0x0214: 'BlackWidow Ultimate 2016',
        0x0216: 'BlackWidow X Chroma',
        0x021A: 'BlackWidow X Chroma Tournament Edition',
    }
    LAPTOP = {
        0x0205: 'Blade Stealth',
        0x0210: 'Blade Pro (Late 2016)',
        0x0220: 'Blade Stealth (Late 2016)'
    }
    MOUSE = {
        0x002F: 'Imperator 2012',
        0x0042: 'Abyssus 2014',
        0x0043: 'DeathAdder Chroma',
        0x0044: 'Mamba (Wired)',
        0x0045: 'Mamba (Wireless)',
        0x0046: 'Mamba Tournament Edition',
        0x0048: 'Orochi (Wired)'
    }
    MOUSEPAD = {
        0x0C00: 'Firefly'
    }


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


    def _get_report(self, command_class, command_id, data_size, *args):
        report = RazerReport(self._dev, command_class, command_id, data_size)
        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put_byte(arg)

        return report


    def run_with_result(self, command, *args, defer_close=False):
        self._ensure_open()
        report = self._get_report(*command.value, *args)
        result = None

        if report.run():
            result = report.result

        if not defer_close:
            self.close()

        return result


    def run_command(self, command, *args, defer_close=False):
        self._ensure_open()
        status = self._get_report(*command.value, *args).run()

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
