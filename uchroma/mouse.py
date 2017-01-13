import struct
from enum import Enum

import hidapi

from grapefruit import Color

from uchroma.device import UChromaDevice
from uchroma.device_base import BaseCommand
from uchroma.led import LED
from uchroma.models import Model
from uchroma.util import clamp, scale, scale_brightness


class UChromaMouse(UChromaDevice):
    """
    Additional functionality for Chroma Mice
    """

    class Command(BaseCommand):
        """
        Commands used for mouse features
        """
        SET_DOCK_CHARGE_EFFECT = (0x03, 0x10, 0x01)
        SET_POLLING_RATE = (0x00, 0x05, 0x01)
        SET_DOCK_BRIGHTNESS = (0x07, 0x02, 0x01)
        SET_DPI_XY = (0x04, 0x05, 0x07)
        SET_IDLE_TIME = (0x07, 0x03, 0x02)
        SET_LOW_BATTERY_THRESHOLD = (0x07, 0x01, 0x01)

        GET_BATTERY_LEVEL = (0x07, 0x80, 0x02)
        GET_DOCK_BRIGHTNESS = (0x07, 0x02, 0x01)
        GET_CHARGING_STATUS = (0x07, 0x84, 0x02)
        GET_POLLING_RATE = (0x00, 0x85, 0x01)
        GET_DPI_XY = (0x04, 0x85, 0x07)


    class PollingRate(Enum):
        """
        Enumeration of polling rates
        """
        MHZ_1000 = 0x01
        MHZ_500 = 0x02
        MHZ_128 = 0x08


    def __init__(self, model: Model, devinfo: hidapi.DeviceInfo, input_devices=None):
        super(UChromaMouse, self).__init__(model, devinfo, input_devices)


    def _set_dock_brightness(self, brightness: float) -> bool:
        return self.run_command(UChromaMouse.Command.SET_DOCK_BRIGHTNESS,
                                scale_brightness(brightness))


    def _get_dock_brightness(self) -> float:
        value = self.run_with_result(UChromaMouse.Command.GET_DOCK_BRIGHTNESS)
        if value is None:
            return 0.0
        return scale_brightness(int(value[0]), True)


    @property
    def battery_level(self) -> float:
        """
        The current battery level
        """
        value = self.run_with_result(UChromaMouse.Command.GET_BATTERY_LEVEL)
        if value is None:
            return -1.0
        return (value[1] / 255) * 100


    @property
    def is_charging(self) -> bool:
        """
        Is the device currently charging?
        """
        value = self.run_with_result(UChromaMouse.Command.GET_CHARGING_STATUS)
        if value is None:
            return False
        return value[1] == 1


    @property
    def polling_rate(self) -> 'PollingRate':
        return None


    @polling_rate.setter
    def polling_rate(self, rate: PollingRate):
        pass


    @property
    def dock_brightness(self) -> float:
        """
        The brightness level of dock illumination
        """
        if self.model == Model.Mouse.MAMBA_WIRELESS:
            return self._get_dock_brightness()
        if self.model == Model.Mouse.OROCHI_CHROMA:
            return self.get_led(LED.Type.SCROLL_WHEEL).brightness

        return self.get_led(LED.Type.BACKLIGHT).brightness


    @dock_brightness.setter
    def dock_brightness(self, brightness: float):
        """
        Set brightness level of dock illumination
        """
        if self.model == Model.Mouse.MAMBA_WIRELESS:
            self._set_dock_brightness(brightness)
        elif self.model == Model.Mouse.OROCHI_CHROMA:
            self.get_led(LED.Type.SCROLL_WHEEL).brightness = brightness
        else:
            self.get_led(LED.Type.BACKLIGHT).brightness = brightness


    @property
    def dpi_xy(self) -> tuple:
        return None


    @dpi_xy.setter
    def dpi_xy(self, x, y):
        pass


    def set_dock_charge_effect(self, enable: bool) -> bool:
        """
        If enabled, a special charge effect will be shown on the device lighting.

        :param enable: True to enable the charge effect

        :return: True if successful
        """
        return self.run_command(UChromaMouse.Command.SET_DOCK_CHARGE_EFFECT, int(enable))


    def set_dock_charge_color(self, color: Color) -> bool:
        """
        Sets the color of the chargie effect

        :param color: Color or RGB tuple

        :return: True if successful
        """
        self.set_dock_charge_effect(True)
        self.get_led(LED.Type.BATTERY).color = color


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


    def set_low_battery_threshold(self, threshold: float) -> bool:
        """
        Sets the low battery warning threshold as a percentage

        :param threshold: Threshold percentage, must be between 5 and 25

        :return: True if successful
        """
        arg = scale(threshold, 5.0, 25.0, 0x0C, 0x3F, True)
        return self.run_command(UChromaMouse.Command.SET_LOW_BATTERY_THRESHOLD, arg)

