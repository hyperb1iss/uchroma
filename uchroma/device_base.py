import re
from enum import Enum

import hidapi

from uchroma.models import Model
from uchroma.report import RazerReport

from uchroma import __version__

class BaseCommand(Enum):
    """
    Base class for Command enumerations

    Tuples, in the form of:
        (command_class, command_id, data_length)
    """

class BaseUChromaDevice(object):
    """
    Base class for device objects
    """

    class Command(BaseCommand):
        """
        Standard commands used by all Chroma devices
        """
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
        """
        Close this device

        Not strictly necessary to call this unless the device was opened with
        the defer_close flag.
        """
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


    def _get_report(self, command_class: int, command_id: int, data_size: int,
                    *args, transaction_id: int=0xFF, remaining_packets: int=0x00) -> RazerReport:
        report = RazerReport(self._dev, command_class, command_id, data_size,
                             transaction_id=transaction_id,
                             remaining_packets=remaining_packets)

        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put(arg)

        return report


    def run_with_result(self, command: BaseCommand, *args,
                        transaction_id: int=0xFF, defer_close: bool=False,
                        delay: float=None, remaining_packets: int=0x00) -> RazerReport:
        """
        Run a command and return the result

        Executes the given command with the provided list of arguments, returning
        the result report.

        Transaction id is only necessary for specialized commands or hardware.

        The connection to the device will be automatically closed by default. If
        many commands will be sent rapidly (like when using a Frame to do animations),
        set the defer_close flag to True and close it manually when finished.

        :param command: The command to run

        :param args: The list of arguments to call the command with
        :type args: varies
        :param transaction_id: Transaction identified, defaults to 0xFF
        :param defer_close: Whether the device should be closed after execution, defaults to False

        :return: The result report from the hardware
        """
        self._ensure_open()
        report = self._get_report(*command.value, *args, transaction_id=transaction_id,
                                  remaining_packets=remaining_packets)
        result = None

        if report.run(delay=delay):
            result = report.result

        if not defer_close:
            self.close()

        return result


    def run_command(self, command: BaseCommand, *args, transaction_id: int=0xFF,
                    defer_close: bool=False, delay: float=None,
                    remaining_packets: int=0x00) -> bool:
        """
        Run a command

        Executes the given command with the provided list of arguments.
        Transaction id is only necessary for specialized commands or hardware.

        The connection to the device will be automatically closed by default. If
        many commands will be sent rapidly (like when using a Frame to do animations),
        set the defer_close flag to True and close it manually when finished.

        :param command: The command to run

        :param args: The list of arguments to call the command with
        :type args: varies

        :param transaction_id: Transaction identified, defaults to 0xFF
        :param defer_close: Whether the device should be closed after execution, defaults to False

        :return: True if the command was successful
        """
        self._ensure_open()
        status = self._get_report(*command.value, *args, transaction_id=transaction_id,
                                  remaining_packets=remaining_packets).run(delay=delay)

        if not defer_close:
            self.close()

        return status


    def get_device_mode(self):
        """
        Gets the current device mode

        FIXME: implement this correctly
        """
        return self.run_with_result(BaseUChromaDevice.Command.GET_DEVICE_MODE)


    def set_device_mode(self, mode, param=0) -> bool:
        """
        Sets the requested device mode

        FIXME: implement this correctly
        """
        return self.run_command(BaseUChromaDevice.Command.SET_DEVICE_MODE, mode, param)


    @property
    def serial_number(self) -> str:
        """
        The hardware serial number of this device

        On laptops, this is not available.
        """
        if self._serial_number is not None:
            return self._serial_number

        serial = None

        if self._devtype == Model.LAPTOP.name:
            serial = self.name
        else:
            value = self.run_with_result(BaseUChromaDevice.Command.GET_SERIAL)
            if value is not None:
                try:
                    serial = value.decode()
                except UnicodeDecodeError:
                    serial = self.device_id

        self._serial_number = re.sub(r'\W+', r'', serial)

        return self._serial_number

    @property
    def firmware_version(self) -> str:
        """
        The firmware version present on this device
        """
        if self._firmware_version is None:
            version = self.run_with_result(BaseUChromaDevice.Command.GET_FIRMWARE_VERSION)
            if version is None:
                self._firmware_version = '(unknown)'
            else:
                self._firmware_version = 'v%d.%d' % (version[0], version[1])

        return self._firmware_version


    @property
    def name(self) -> str:
        """
        The name of this device
        """
        return self._devname


    @property
    def product_id(self) -> int:
        """
        The USB product identifier of this device
        """
        return self._devinfo.product_id


    @property
    def vendor_id(self) -> int:
        """
        The USB vendor identifier of this device
        """
        return self._devinfo.vendor_id


    @property
    def device_type(self) -> str:
        """
        The type of this device, from the Model enumeration
        """
        return self._devtype


    @property
    def device_id(self) -> str:
        """
        A unique identifier for this device
        """
        return '%04x:%04x' % (self.vendor_id, self.product_id)

    @property
    def driver_version(self):
        """
        Get the uChroma version
        """
        return __version__