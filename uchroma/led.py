from enum import Enum

from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.util import scale_brightness, to_color

from grapefruit import Color


NOSTORE = 0
VARSTORE = 1


class LED(object):
    """
    Control individual LEDs which may be present on a device

    This class should not need to be instantiated directly, the
    correct singleton instance is obtained by calling the
    get_led() method of UChromaDevice.

    The API does not yet support listing the LED types actually
    available on a device.
    """


    class Type(Enum):
        """
        Enumeration of LED types

        All types not available on all devices.
        """
        SCROLL_WHEEL = 0x01
        BATTERY = 0x03
        LOGO = 0x04
        BACKLIGHT = 0x05
        MACRO = 0x07
        GAME = 0x08
        PROFILE_RED = 0x0E
        PROFILE_GREEN = 0x0C
        PROFILE_BLUE = 0x0D


    class Mode(Enum):
        """
        Enumeration of LED effect modes
        """
        STATIC = 0x00
        BLINK = 0x01
        PULSE = 0x02
        SPECTRUM = 0x04


    class Command(BaseCommand):
        """
        Commands used by this class
        """
        SET_LED_STATE = (0x03, 0x00, 0x03)
        SET_LED_COLOR = (0x03, 0x01, 0x05)
        SET_LED_MODE = (0x03, 0x02, 0x03)
        SET_LED_BRIGHTNESS = (0x03, 0x03, 0x03)

        GET_LED_STATE = (0x03, 0x80, 0x03)
        GET_LED_COLOR = (0x03, 0x81, 0x05)
        GET_LED_MODE = (0x03, 0x82, 0x03)
        GET_LED_BRIGHTNESS = (0x03, 0x83, 0x03)


    def __init__(self, driver: BaseUChromaDevice, led_type: Type):
        self._driver = driver
        self._led_type = led_type


    def _get(self, cmd):
        return self._driver.run_with_result(cmd, VARSTORE, self._led_type)


    def _set(self, cmd, *args):
        return self._driver.run_command(cmd, *(VARSTORE, self._led_type) + args)


    @property
    def led_type(self) -> 'Type':
        """
        The LED.Type controlled by this instance
        """
        return self._led_type


    @property
    def state(self) -> bool:
        """
        The on/off state of this LED
        """
        value = self._get(LED.Command.GET_LED_STATE)
        if value is None:
            return False

        return bool(value[2])


    @state.setter
    def state(self, led_state: bool):
        """
        Set the on/off state of this LED
        """
        self._set(LED.Command.SET_LED_STATE, int(led_state))


    @property
    def color(self) -> Color:
        """
        The current color of this LED

        May return None if unsupported
        """
        value = self._get(LED.Command.GET_LED_COLOR)
        if value is None:
            return None

        return Color.NewFromRgb(value[2], value[3], value[4])


    @color.setter
    def color(self, color):
        """
        Set the color of this LED

        :param color: The color to set
        """
        self._set(LED.Command.SET_LED_COLOR, to_color(color))


    @property
    def mode(self) -> 'Mode':
        """
        The current mode of this LED

        May return None if unsupported
        """
        value = self._get(LED.Command.GET_LED_MODE)
        if value is None:
            return None

        return LED.Mode(value[2])


    @mode.setter
    def mode(self, led_mode: Mode):
        """
        Set the mode of this LED

        :param led_mode: The mode to set
        """
        self._set(LED.Command.SET_LED_MODE, led_mode)


    @property
    def brightness(self) -> float:
        """
        The current brightness of this LED
        """
        value = self._get(LED.Command.GET_LED_BRIGHTNESS)

        return scale_brightness(int(value[2]), True)


    @brightness.setter
    def brightness(self, level: float):
        """
        Set the brightness of this LED

        :param level: The brightness level to set, 0-100
        """
        return self._set(LED.Command.SET_LED_BRIGHTNESS, scale_brightness(level))
