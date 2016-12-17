from enum import Enum

from color import RGB

# LED states
class LEDState(Enum):
    OFF = 0x00
    ON = 0x01


# LED types
class LEDType(Enum):
    SCROLL_WHEEL = 0x01
    BATTERY = 0x03
    LOGO = 0x04
    BACKLIGHT = 0x05
    MACRO = 0x07
    GAME = 0x08
    PROFILE_RED = 0x0E
    PROFILE_GREEN = 0x0C
    PROFILE_BLUE = 0x0D


# LED modes
class LEDMode(Enum):
    STATIC = 0x00
    BLINK = 0x01
    PULSE = 0x02
    SPECTRUM = 0x04


class Command(Enum):
    SET_LED_STATE = (0x03, 0x00, 0x03)
    SET_LED_COLOR = (0x03, 0x01, 0x05)
    SET_LED_MODE = (0x03, 0x02, 0x03)
    SET_LED_BRIGHTNESS = (0x03, 0x03, 0x03)

    GET_LED_STATE = (0x03, 0x80, 0x03)
    GET_LED_COLOR = (0x03, 0x81, 0x05)
    GET_LED_MODE = (0x03, 0x82, 0x03)
    GET_LED_BRIGHTNESS = (0x03, 0x83, 0x03)


NOSTORE = 0
VARSTORE = 1


class LED(object):

    def __init__(self, driver, led_type):
        self._driver = driver
        self._led_type = led_type

    def _get(self, cmd):
        return self._driver.run_with_result(cmd, VARSTORE, self._led_type)

    def _set(self, cmd, *args):
        return self._driver.run_command(cmd, *(VARSTORE, self._led_type) + args)


    @property
    def state(self):
        value = self._get(Command.GET_LED_STATE)
        if value is None:
            return None

        return LEDState(value[2])


    @state.setter
    def state(self, led_state):
        return self._set(Command.SET_LED_STATE, led_state)


    @property
    def color(self):
        value = self._get(Command.GET_LED_COLOR)
        if value is None:
            return None

        return RGB(value[2], value[3], value[4])


    @color.setter
    def color(self, rgb):
        return self._set(Command.SET_LED_COLOR, rgb)


    @property
    def mode(self):
        value = self._get(Command.GET_LED_MODE)
        if value is None:
            return None

        return LEDMode(value[2])


    @mode.setter
    def mode(self, led_mode):
        return self._set(Command.SET_LED_MODE, led_mode)


    @property
    def brightness(self):
        value = self._get(Command.GET_LED_BRIGHTNESS)
        if value is None:
            return 0

        return int(value[2])


    @brightness.setter
    def brightness(self, led_brightness):
        return self._set(Command.SET_LED_BRIGHTNESS, led_brightness)
