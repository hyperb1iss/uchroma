import re

import hidapi

from wrapt import synchronized

from uchroma.input import InputManager
from uchroma.models import Hardware, HardwareInfo, Quirks
from uchroma.report import RazerReport
from uchroma.types import BaseCommand, FX
from uchroma.util import enumarg, EnumType, RepeatingTimer
from uchroma.version import __version__


class BaseUChromaDevice(object):
    """
    Base class for device objects
    """

    class Command(BaseCommand):
        """
        Standard commands used by all Chroma devices
        """
        # info queries, class 0
        GET_FIRMWARE_VERSION = (0x00, 0x81, 0x02)
        GET_SERIAL = (0x00, 0x82, 0x16)


    def __init__(self, hardware: HardwareInfo, devinfo: hidapi.DeviceInfo,
                 input_devices=None, *args, **kwargs):

        # needed for mixins
        super(BaseUChromaDevice, self).__init__(*args, **kwargs)

        self._hardware = hardware
        self._devinfo = devinfo

        self._dev = None
        self._serial_number = None
        self._firmware_version = None

        self._defer_close = hardware.has_matrix
        self._close_timer = RepeatingTimer(5.0, self.close, True)

        self._supported_fx = []

        self._offline = False

        self._input_manager = None
        if input_devices is not None:
            self._input_manager = InputManager(self, input_devices)


    def _close(self, force: bool=False):
        if self._defer_close:
            if not force:
                self._close_timer.start()
                return
            self._close_timer.cancel()

        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass

            self._dev = None


    @synchronized
    def close(self, force: bool=False):
        """
        Close this device

        Not strictly necessary to call this unless the device was opened with
        the defer_close flag.
        """
        self._close(force)


    @property
    def input_devices(self):
        return self._input_manager.input_devices


    def __del__(self):
        self._defer_close = False
        self._close(True)


    def _ensure_open(self):
        if self._dev is None:
            self._dev = hidapi.Device(self._devinfo)


    def _get_report(self, command_class: int, command_id: int, data_size: int,
                    *args, transaction_id: None, remaining_packets: int=0x00) -> RazerReport:

        if transaction_id is None:
            if self.has_quirk(Quirks.TRANSACTION_CODE_3F):
                transaction_id = 0x3F
            else:
                transaction_id = 0xFF

        report = RazerReport(self._dev, command_class, command_id, data_size,
                             transaction_id=transaction_id,
                             remaining_packets=remaining_packets)

        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put(arg)

        return report


    @synchronized
    @property
    def defer_close(self) -> bool:
        """
        True if we want to keep the device open
        """
        return self._defer_close


    @synchronized
    @defer_close.setter
    def defer_close(self, defer: bool):
        """
        True if we want to keep the device open
        """
        self._defer_close = defer
        if not defer:
            self._close(True)


    def _get_timeout_cb(self):
        """
        Getter for report timeout handler
        """
        return None


    @synchronized
    def run_with_result(self, command: BaseCommand, *args,
                        transaction_id: int=0xFF, delay: float=None,
                        remaining_packets: int=0x00) -> bytes:
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

        :return: The result report from the hardware
        """
        try:
            self._ensure_open()
            report = self._get_report(*command.value, *args, transaction_id=transaction_id,
                                      remaining_packets=remaining_packets)
            result = None

            if report.run(delay=delay, timeout_cb=self._get_timeout_cb()):
                result = report.result

            return result

        finally:
            self._close()


    @synchronized
    def run_command(self, command: BaseCommand, *args, transaction_id: int=0xFF,
                    delay: float=None, remaining_packets: int=0x00) -> bool:
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
        :param timeout_cb: Callback to invoke on a timeout

        :return: True if the command was successful
        """
        try:
            self._ensure_open()
            report = self._get_report(*command.value, *args, transaction_id=transaction_id,
                                      remaining_packets=remaining_packets)

            return report.run(delay=delay, timeout_cb=self._get_timeout_cb())

        finally:
            self._close()


    def add_input_callback(self, callback):
        if self._input_manager is not None:
            self._input_manager.add_callback(callback)


    def remove_input_callback(self, callback):
        if self._input_manager is not None:
            self._input_manager.remove_callback(callback)


    def _decode_serial(self, value: bytes) -> str:
        if value is not None:
            try:
                return value.decode()
            except UnicodeDecodeError:
                return self.device_id

        return None


    def _get_serial_number(self) -> str:
        """
        Get the serial number from the hardware directly

        Laptops don't return a serial number for their devices,
        so we return the model name.
        """
        value = self.run_with_result(BaseUChromaDevice.Command.GET_SERIAL)
        return self._decode_serial(value)


    @property
    def serial_number(self) -> str:
        """
        The hardware serial number of this device

        On laptops, this is not available.
        """
        if self._serial_number is not None:
            return self._serial_number

        serial = self._get_serial_number()

        if serial is not None:
            self._serial_number = re.sub(r'\W+', r'', serial)

        return self._serial_number


    def _get_firmware_version(self) -> str:
        """
        Get the firmware version from the hardware directly
        """
        return self.run_with_result(BaseUChromaDevice.Command.GET_FIRMWARE_VERSION)


    @property
    def firmware_version(self) -> str:
        """
        The firmware version present on this device
        """
        if self._firmware_version is None:
            version = self._get_firmware_version()

            if version is None:
                self._firmware_version = '(unknown)'
            else:
                self._firmware_version = 'v%d.%d' % (version[0], version[1])

        return self._firmware_version


    @property
    def is_offline(self) -> bool:
        """
        Some devices (such as wireless models) might be "offline" in that
        the dock or other USB receiver might be plugged in, but the actual
        device is switched off. In this case, we can't interact with it
        but it will still enumerate.
        """
        return self._offline


    @property
    def name(self) -> str:
        """
        The name of this device
        """
        return self.hardware.product_name


    @property
    def hardware(self) -> HardwareInfo:
        """
        The sub-enumeration of HardwareInfo
        """
        return self._hardware


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
    def device_type(self) -> Hardware.Type:
        """
        The type of this device, from the Hardware.Type enumeration
        """
        return self.hardware.type


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


    @property
    def width(self) -> int:
        """
        Gets the width of the key matrix (if applicable)
        """
        if not self.has_matrix:
            return 0

        return self.hardware.matrix_dims[1]


    @property
    def height(self) -> int:
        """
        Gets the height of the key matrix (if applicable)
        """
        if not self.has_matrix:
            return 0

        return self.hardware.matrix_dims[0]


    @property
    def has_matrix(self) -> bool:
        """
        True if the device supports matrix control
        """
        return self.hardware.has_matrix


    @property
    def supported_fx(self) -> tuple:
        """
        The color effects supported by this device
        """
        return self.hardware.supported_fx


    @enumarg(FX)
    def has_fx(self, fx: EnumType) -> bool:
        """
        True if the effect type is supported
        """
        return fx in self.supported_fx


    def has_quirk(self, quirk) -> bool:
        """
        True if the quirk is required for this device
        """
        return self.hardware.has_quirk(quirk)


    def reset(self) -> bool:
        """
        Reset effects and other configuration to defaults
        """
        return True
