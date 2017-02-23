from enum import Enum

from traitlets import Bool, Float, HasTraits, observe

from uchroma.traits import ColorTrait, UseEnumCaseless, WriteOnceUseEnumCaseless
from uchroma.types import BaseCommand
from uchroma.util import scale_brightness, Signal, to_color

from grapefruit import Color


NOSTORE = 0
VARSTORE = 1


class LEDType(Enum):
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


class LEDMode(Enum):
    """
    Enumeration of LED effect modes
    """
    STATIC = 0x00
    BLINK = 0x01
    PULSE = 0x02
    SPECTRUM = 0x04


class LED(HasTraits):
    led_type = WriteOnceUseEnumCaseless(enum_class=LEDType)
    state = Bool(default_value=False, allow_none=False)

    color = ColorTrait(default_value='green', allow_none=False).tag(config=True)
    mode = UseEnumCaseless(enum_class=LEDMode, default_value=LEDMode.STATIC,
                           allow_none=False).tag(config=True)
    brightness = Float(min=0.0, max=100.0, default_value=0.0,
                       allow_none=False).tag(config=True)

    """
    Control individual LEDs which may be present on a device

    This class should not need to be instantiated directly, the
    correct singleton instance is obtained by calling the
    get_led() method of UChromaDevice.

    The API does not yet support listing the LED types actually
    available on a device.
    """

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


    def __init__(self, driver, led_type: LEDType, *args, **kwargs):
        super(LED, self).__init__(*args, **kwargs)
        self._driver = driver
        self._led_type = led_type
        self._logger = driver.logger
        self.led_type = led_type
        self._refreshing = False
        self._refresh()


    def _get(self, cmd):
        return self._driver.run_with_result(cmd, VARSTORE, self._led_type)


    def _set(self, cmd, *args):
        return self._driver.run_command(cmd, *(VARSTORE, self._led_type) + args)


    def _refresh(self):
        try:
            self._refreshing = True

            # state
            value = self._get(LED.Command.GET_LED_STATE)
            if value is not None:
                self.state = bool(value[2])

            # color
            value = self._get(LED.Command.GET_LED_COLOR)
            if value is not None:
                self.color = Color.NewFromRgb(value[2], value[3], value[4])

            # mode
            value = self._get(LED.Command.GET_LED_MODE)
            if value is not None:
                self.mode = LEDMode(value[2])

            # brightness
            value = self._get(LED.Command.GET_LED_BRIGHTNESS)
            if value is not None:
                self.brightness = scale_brightness(int(value[2]), True)

        finally:
            self._refreshing = False


    @observe('color', 'mode', 'state', 'brightness')
    def _observer(self, change):
        if self._refreshing or change.old == change.new:
            return

        self._logger.debug("LED settings changed: %s", change)

        if change.name == 'color':
            self._set(LED.Command.SET_LED_COLOR, to_color(change.new))
        elif change.name == 'mode':
            self._set(LED.Command.SET_LED_MODE, change.new)
        elif change.name == 'brightness':
            self._set(LED.Command.SET_LED_BRIGHTNESS, scale_brightness(change.new))
            if change.old == 0 and change.new > 0:
                self._set(LED.Command.SET_LED_STATE, 1)
            elif change.old > 0 and change.new == 0:
                self._set(LED.Command.SET_LED_STATE, 0)
        else:
            raise ValueError("Unknown LED property: %s" % change.new)

        self._refresh()


    def __str__(self):
        values = ', '.join('%s=%s' % (k, getattr(self, k)) \
                for k in ('led_type', 'state', 'brightness', 'color', 'mode'))
        return 'LED(%s)' % values


    __repr__ = __str__


class LEDManager(object):
    def __init__(self, driver):
        self._driver = driver
        self._leds = {}

        self.led_changed = Signal()


    @property
    def supported_leds(self):
        return self._driver.hardware.supported_leds


    def get(self, led_type: LEDType) -> LED:
        """
        Fetches the requested LED interface on this device

        :param led_type: The LED type to fetch

        :return: The LED interface, if available
        """
        if led_type not in self._driver.supported_leds:
            return None

        if led_type not in self._leds:
            self._leds[led_type] = LED(self._driver, led_type)
            self._leds[led_type].observe(self._led_changed)

        return self._leds[led_type]


    def _led_changed(self, change):
        self.led_changed.fire(change.owner)
