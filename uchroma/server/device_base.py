#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
import asyncio
import functools
import re
from concurrent import futures
from contextlib import contextmanager, suppress

from wrapt import synchronized

from uchroma.log import Log
from uchroma.server import hidadapter as hidapi
from uchroma.util import Signal, ValueAnimator, ensure_future
from uchroma.version import __version__

from .anim import AnimationManager
from .hardware import Hardware
from .input import InputManager
from .prefs import PreferenceManager
from .protocol import get_transaction_id
from .report import RazerReport
from .types import BaseCommand


class BaseUChromaDevice:
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

    def __init__(
        self,
        hardware: Hardware,
        devinfo: hidapi.DeviceInfo,
        index: int,
        sys_path: str,
        input_devices=None,
        *args,
        **kwargs,
    ):
        self._hardware = hardware
        self._devinfo = devinfo
        self._devindex = index
        self._sys_path = sys_path

        self.logger = Log.get(f"uchroma.driver-{index}")

        # needed for mixins
        super().__init__(*args, **kwargs)

        self._dev = None
        self._serial_number = None
        self._firmware_version = None
        self._last_cmd_time = None
        self._prefs = None

        self._offline = False
        self._suspended = False

        self.power_state_changed = Signal()
        self.restore_prefs = Signal()

        self._input_manager = None
        if input_devices is not None:
            self._input_manager = InputManager(self, input_devices)

        self._animation_manager = None
        if self.width > 0 and self.height > 0:
            self._animation_manager = AnimationManager(self)

        self._brightness_animator = ValueAnimator(self._update_brightness)

        self._fx_manager = None

        self._ref_count = 0
        self._executor = futures.ThreadPoolExecutor(max_workers=1)

    async def shutdown(self):
        """
        Shuts down all services associated with the device and closes the HID instance.
        """
        if asyncio.get_event_loop().is_running():
            if hasattr(self, "_animation_manager") and self.animation_manager is not None:
                await self.animation_manager.shutdown()

            if hasattr(self, "_input_manager") and self._input_manager is not None:
                await self._input_manager.shutdown()

        self.close(True)

    def close(self, force: bool = False):
        if not force:
            if self.animation_manager is not None and self.is_animating:
                return

            if self._ref_count > 0:
                return

        if hasattr(self, "_dev") and self._dev is not None:
            with suppress(Exception):
                self._dev.close()

            self._dev = None

    def has_fx(self, fx_type: str) -> bool:
        """
        Test if the device supports a particular built-in effect

        :param fx_type: the effect to test
        :return: true if the effect is supported
        """
        if self.fx_manager is None:
            return False
        return fx_type in self.fx_manager.available_fx

    @property
    def animation_manager(self):
        """
        Animation manager for this device
        """
        if hasattr(self, "_animation_manager"):
            return self._animation_manager
        return None

    @property
    def is_animating(self):
        """
        True if an animation is currently running
        """
        if self.animation_manager is not None:
            return self.animation_manager.running
        return False

    @property
    def fx_manager(self):
        """
        Built-in effects manager for this device
        """
        return self._fx_manager

    @property
    def input_manager(self):
        """
        Input manager service for this device
        """
        return self._input_manager

    @property
    def input_devices(self):
        """
        Input devices associated with this instance
        """
        if self._input_manager is None:
            return None
        return self._input_manager.input_devices

    @property
    def hid(self):
        """
        The lower-layer hidapi device
        """
        return self._dev

    @property
    def last_cmd_time(self):
        """
        Timestamp of the last command sent to the hardware, used for delay enforcement
        """
        return self._last_cmd_time

    @last_cmd_time.setter
    def last_cmd_time(self, last_cmd_time):
        self._last_cmd_time = last_cmd_time

    def _set_brightness(self, level: float) -> bool:
        return False

    def _get_brightness(self) -> float:
        return 0.0

    async def _update_brightness(self, level):
        await ensure_future(
            asyncio.get_event_loop().run_in_executor(
                self._executor, functools.partial(self._set_brightness, level)
            )
        )

        suspended = self.suspended and level == 0
        self.power_state_changed.fire(level, suspended)

    @property
    def suspended(self):
        """
        The power state of the device, true if suspended
        """
        return self._suspended

    def suspend(self, fast=False):
        """
        Suspend the device

        Performs any actions necessary to suspend the device. By default,
        the current brightness level is saved and set to zero.
        """
        if self._suspended:
            return

        self.preferences.brightness = self.brightness
        if fast:
            self._set_brightness(0)
        else:
            if self._device_open():
                self._brightness_animator.animate(self.brightness, 0, done_cb=self._done_cb)

        self._suspended = True

    def resume(self):
        """
        Resume the device

        Performs any actions necessary to resume the device. By default,
        the saved brightness level is restored.
        """
        if not self._suspended:
            return

        self._suspended = False
        self.brightness = self.preferences.brightness

    @property
    def brightness(self):
        """
        The current brightness level of the device lighting
        """
        if self._suspended:
            return self.preferences.brightness

        return self._get_brightness()

    @brightness.setter
    def brightness(self, level: float):
        """
        Set the brightness level of the main device lighting

        :param level: Brightness level, 0-100
        """
        if not self._suspended and self._device_open():
            self._brightness_animator.animate(self.brightness, level, done_cb=self._done_cb)

        self.preferences.brightness = level

    def _ensure_open(self) -> bool:
        try:
            if self._dev is None:
                self._dev = hidapi.Device(self._devinfo, blocking=False)
        except Exception as err:
            self.logger.exception("Failed to open connection", exc_info=err)
            return False

        return True

    def get_report(
        self,
        command_class: int,
        command_id: int,
        data_size: int,
        *args,
        transaction_id: int | None = None,
        remaining_packets: int = 0x00,
    ) -> RazerReport:
        """
        Create and initialize a new RazerReport on this device
        """
        if transaction_id is None:
            transaction_id = get_transaction_id(self.hardware)

        report = RazerReport(
            self,
            command_class,
            command_id,
            data_size,
            transaction_id=transaction_id,
            remaining_packets=remaining_packets,
        )

        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put(arg)

        return report

    def _get_timeout_cb(self):
        """
        Getter for report timeout handler
        """
        return None

    def run_with_result(
        self,
        command: BaseCommand,
        *args,
        transaction_id: int | None = None,
        delay: float | None = None,
        remaining_packets: int = 0x00,
    ) -> bytes | None:
        """
        Run a command and return the result

        Executes the given command with the provided list of arguments, returning
        the result report.

        Transaction id is only necessary for specialized commands or hardware.

        The connection to the device will be automatically closed by default.

        :param command: The command to run

        :param args: The list of arguments to call the command with
        :type args: varies
        :param transaction_id: Transaction identified, defaults to 0xFF

        :return: The result report from the hardware
        """
        report = self.get_report(
            *command.value,
            *args,
            transaction_id=transaction_id,
            remaining_packets=remaining_packets,
        )
        result = None

        if self.run_report(report, delay=delay):
            result = report.result

        return result

    @synchronized
    def run_report(self, report: RazerReport, delay: float | None = None) -> bool:
        """
        Runs a previously initialized RazerReport on the device

        :param report: the report to run
        :param delay: custom delay to enforce between commands
        :return: True if successful
        """
        with self.device_open():
            return report.run(delay=delay, timeout_cb=self._get_timeout_cb())

    def run_command(
        self,
        command: BaseCommand,
        *args,
        transaction_id: int | None = None,
        delay: float | None = None,
        remaining_packets: int = 0x00,
    ) -> bool:
        """
        Run a command

        Executes the given command with the provided list of arguments.
        Transaction id is only necessary for specialized commands or hardware.

        The connection to the device will be automatically closed by default.

        :param command: The command to run
        :param args: The list of arguments to call the command with
        :type args: varies
        :param transaction_id: Transaction identified, defaults to 0xFF
        :param timeout_cb: Callback to invoke on a timeout

        :return: True if the command was successful
        """
        report = self.get_report(
            *command.value,
            *args,
            transaction_id=transaction_id,
            remaining_packets=remaining_packets,
        )

        return self.run_report(report, delay=delay)

    def _decode_serial(self, value: bytes | None) -> str | None:
        if value is not None:
            try:
                return value.decode()
            except UnicodeDecodeError:
                return self.key

        return None

    def _get_serial_number(self) -> str | None:
        """
        Get the serial number from the hardware directly

        Laptops don't return a serial number for their devices,
        so we return the model name.
        """
        value = self.run_with_result(BaseUChromaDevice.Command.GET_SERIAL)
        return self._decode_serial(value)

    @property
    def serial_number(self) -> str | None:
        """
        The hardware serial number of this device

        On laptops, this is not available.
        """
        if self._serial_number is not None:
            return self._serial_number

        serial = self._get_serial_number()

        if serial is not None:
            self._serial_number = re.sub(r"\W+", r"", serial)

        return self._serial_number

    def _get_firmware_version(self) -> bytes | None:
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
                self._firmware_version = "(unknown)"
            else:
                self._firmware_version = f"v{int(version[0])}.{int(version[1])}"

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
        return self.hardware.name

    @property
    def device_index(self) -> int:
        """
        The internal index of this device in the device manager
        """
        return self._devindex

    @property
    def sys_path(self) -> str:
        """
        The sysfs path of this device
        """
        return self._sys_path

    @property
    def key(self) -> str:
        """
        Unique key which identifies this device to the device manager
        """
        return f"{self.vendor_id:04x}:{self.product_id:04x}.{self.device_index:02d}"

    @property
    def hardware(self) -> Hardware:
        """
        The sub-enumeration of Hardware
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
    def manufacturer(self) -> str:
        """
        The manufacturer of this device
        """
        return self._hardware.manufacturer

    @property
    def device_type(self) -> Hardware.Type:
        """
        The type of this device, from the Hardware.Type enumeration
        """
        return self.hardware.type

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
        if self.hardware.dimensions is None:
            return 0

        return self.hardware.dimensions.x

    @property
    def height(self) -> int:
        """
        Gets the height of the key matrix (if applicable)
        """
        if self.hardware.dimensions is None:
            return 0

        return self.hardware.dimensions.y

    @property
    def has_matrix(self) -> bool:
        """
        True if the device supports matrix control
        """
        return self.hardware.has_matrix

    def has_quirk(self, quirk) -> bool:
        """
        True if the quirk is required for this device
        """
        return self.hardware.has_quirk(quirk)

    @property
    def key_mapping(self):
        """
        The mapping between keycodes and lighting matrix coordinates
        """
        return self.hardware.key_mapping

    @property
    def preferences(self):
        """
        Saved preferences for this device
        """
        if self._prefs is None:
            self._prefs = PreferenceManager().get(self.serial_number)
        return self._prefs

    def reset(self) -> bool:
        """
        Reset effects and other configuration to defaults
        """
        return True

    def fire_restore_prefs(self):
        """
        Restore saved preferences
        """
        with self.preferences.observers_paused():
            if hasattr(self, "brightness") and self.preferences.brightness is not None:
                self.brightness = self.preferences.brightness

            self.restore_prefs.fire(self.preferences)

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, type={self.device_type.value}, product_id=0x{self.product_id:04x}, index={self.device_index}, quirks={self.hardware.quirks})"

    def _device_open(self):
        self._ref_count += 1
        return self._ensure_open()

    def _device_close(self):
        self._ref_count -= 1
        self.close()

    def _done_cb(self, future):
        self._device_close()

    @contextmanager
    def device_open(self):
        try:
            if self._device_open():
                yield
        finally:
            self._device_close()

    def __del__(self):
        self.close(force=True)
