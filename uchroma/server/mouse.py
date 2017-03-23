#
# uchroma - Copyright (C) 2017 Steve Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
import struct
from enum import Enum

import hidapi

from grapefruit import Color

from uchroma.color import colorarg, ColorType, to_color
from uchroma.util import clamp, scale, scale_brightness

from .device import UChromaDevice
from .device_base import BaseCommand
from .hardware import Hardware
from .report import Status
from .types import LEDType


class PollingRate(Enum):
    """
    Enumeration of polling rates
    """
    INVALID = 0x00
    MHZ_1000 = 0x01
    MHZ_500 = 0x02
    MHZ_128 = 0x08


class UChromaMouse(UChromaDevice):
    """
    Additional functionality for Chroma Mice
    """

    class Command(BaseCommand):
        """
        Commands used for mouse features
        """
        SET_POLLING_RATE = (0x00, 0x05, 0x01)
        SET_DPI_XY = (0x04, 0x05, 0x07)
        SET_IDLE_TIME = (0x07, 0x03, 0x02)

        GET_POLLING_RATE = (0x00, 0x85, 0x01)
        GET_DPI_XY = (0x04, 0x85, 0x07)


    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):
        super(UChromaMouse, self).__init__(hardware, devinfo, devindex,
                                           sys_path, input_devices,
                                           *args, **kwargs)


    @property
    def polling_rate(self) -> PollingRate:
        """
        Get the current polling rate
        """
        value = self.run_with_result(UChromaMouse.Command.GET_POLLING_RATE)
        if value is None:
            return PollingRate.INVALID

        return PollingRate(value[0])


    @polling_rate.setter
    def polling_rate(self, rate: PollingRate):
        """
        Set the polling rate
        """
        if isinstance(rate, str):
            rate = PollingRate.__members__[rate.upper()]

        self.run_command(UChromaMouse.Command.SET_POLLING_RATE, rate.value)



    @property
    def dpi_xy(self) -> tuple:
        """
        Get an (x, y) tuple of the current device DPI
        """
        value = self.run_with_result(UChromaMouse.Command.GET_DPI_XY)
        if value is None:
            return (-1, -1)

        return struct.unpack('>HH', value[1:5])


    @dpi_xy.setter
    def dpi_xy(self, dpi: tuple):
        """
        Set the (x, y) device DPI
        """
        args = None
        if len(dpi) == 2:
            args = struct.pack('>HH', dpi[0], dpi[1])
        elif len(dpi == 1):
            args = struct.pack('>H', dpi[0])
        else:
            raise ValueError("Must specify one (x) or two (x, y) integers to set DPI")

        self.run_with_result(UChromaMouse.Command.SET_DPI_XY, 0x01, args)


    def set_idle_time(self, idle_time: int):
        """
        Sets the idle time in seconds. The device will enter powersave
        mode after the timeout expires.

        :param idle_time: Timeout in seconds. Must be between 60 and 900.

        :return: True if successful
        """
        idle_time = clamp(idle_time, 60, 900)
        arg = struct.pack('>H', idle_time)

        return self.run_command(UChromaMouse.Command.SET_IDLE_TIME, arg)


    @property
    def is_wireless(self):
        """
        True if this device has battery and dock settings
        """
        return False



class UChromaWirelessMouse(UChromaMouse):
    """
    A mouse with dock and battery functions
    """
    class Command(BaseCommand):
        """
        Commands used for mouse features
        """
        SET_DOCK_CHARGE_EFFECT = (0x03, 0x10, 0x01)
        SET_DOCK_BRIGHTNESS = (0x07, 0x02, 0x01)
        SET_LOW_BATTERY_THRESHOLD = (0x07, 0x01, 0x01)

        GET_BATTERY_LEVEL = (0x07, 0x80, 0x02)
        GET_DOCK_BRIGHTNESS = (0x07, 0x82, 0x01)
        GET_CHARGING_STATUS = (0x07, 0x84, 0x02)


    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):
        super(UChromaWirelessMouse, self).__init__(hardware, devinfo, devindex,
                                                   sys_path, input_devices,
                                                   *args, **kwargs)


    @property
    def is_wireless(self):
        """
        This mouse has wireless controls
        """
        return True


    def _timeout_cb(self, status, data):
        if self._offline and status == Status.OK:
            self._offline = False
            self.close(True)
        self._offline = True


    def _get_timeout_cb(self):
        return self._timeout_cb


    @property
    def dock_brightness(self) -> float:
        value = self.run_with_result(UChromaWirelessMouse.Command.GET_DOCK_BRIGHTNESS)
        if value is None:
            return 0.0
        return scale_brightness(int(value[0]), True)


    @dock_brightness.setter
    def dock_brightness(self, brightness: float) -> bool:
        return self.run_command(UChromaWirelessMouse.Command.SET_DOCK_BRIGHTNESS,
                                scale_brightness(brightness))


    @property
    def battery_level(self) -> float:
        """
        The current battery level
        """
        value = self.run_with_result(UChromaWirelessMouse.Command.GET_BATTERY_LEVEL)
        if value is None:
            return -1.0
        return (value[1] / 255) * 100


    @property
    def is_charging(self) -> bool:
        """
        Is the device currently charging?
        """
        value = self.run_with_result(UChromaWirelessMouse.Command.GET_CHARGING_STATUS)
        if value is None:
            return False
        return value[1] == 1


    def enable_dock_charge_effect(self, enable: bool) -> bool:
        """
        If enabled, a special charge effect will be shown on the device lighting.

        :param enable: True to enable the charge effect

        :return: True if successful
        """
        return self.run_command(UChromaWirelessMouse.Command.SET_DOCK_CHARGE_EFFECT, int(enable))


    @property
    def dock_charge_color(self) -> Color:
        """
        The color of the dock LEDs while charging
        """
        return self.get_led(LEDType.BATTERY).color


    @dock_charge_color.setter
    @colorarg
    def dock_charge_color(self, color: ColorType):
        """
        Set the color of the dock while charging. None to disable
        """
        if color is None or (color.rgb[0] == 0.0 and \
                             color.rgb[1] == 0.0 and \
                             color.rgb[2] == 0.0):
            self.enable_dock_charge_effect(False)
        else:
            self.enable_dock_charge_effect(True)
            self.get_led(LEDType.BATTERY).color = color


    def set_low_battery_threshold(self, threshold: float) -> bool:
        """
        Sets the low battery warning threshold as a percentage

        :param threshold: Threshold percentage, must be between 5 and 25

        :return: True if successful
        """
        arg = scale(threshold, 5.0, 25.0, 0x0C, 0x3F, True)
        return self.run_command(UChromaWirelessMouse.Command.SET_LOW_BATTERY_THRESHOLD, arg)
