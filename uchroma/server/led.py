from collections import OrderedDict
from enum import Enum

from traitlets import Bool, Float, HasTraits, observe

from uchroma.color import to_color
from uchroma.traits import ColorTrait, UseEnumCaseless, WriteOnceUseEnumCaseless
from uchroma.util import scale_brightness, Signal

from .types import BaseCommand, LEDType

from grapefruit import Color


NOSTORE = 0
VARSTORE = 1


class LEDMode(Enum):
    """
    Enumeration of LED effect modes
    """
    STATIC = 0x00
    BLINK = 0x01
    PULSE = 0x02
    SPECTRUM = 0x04


class LED(HasTraits, object):
    led_type = WriteOnceUseEnumCaseless(enum_class=LEDType)
    state = Bool(default_value=False, allow_none=False)

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
        self._restoring = True
        self._refreshing = False

        # dynamic traits, since they are normally class-level
        brightness = Float(min=0.0, max=100.0, default_value=80.0,
                           allow_none=False).tag(config=True)
        color = ColorTrait(default_value=led_type.default_color,
                           allow_none=False).tag(config=led_type.rgb)
        mode = UseEnumCaseless(enum_class=LEDMode, default_value=LEDMode.STATIC,
                               allow_none=False).tag(config=led_type.has_modes)

        self.add_traits(color=color, mode=mode, brightness=brightness)

        self._refresh()
        self._restoring = False


    def _get(self, cmd):
        return self._driver.run_with_result(cmd, VARSTORE, self._led_type.hardware_id)


    def _set(self, cmd, *args):
        return self._driver.run_command(cmd, *(VARSTORE, self._led_type.hardware_id) + args)


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
                self.color = Color.NewFromRgb(value[2] / 255.0,
                                              value[3] / 255.0,
                                              value[4] / 255.0)

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

        if not self._restoring:
            self._refresh()

            if self.led_type != LEDType.BACKLIGHT:
                self._update_prefs()


    def __str__(self):
        values = ', '.join('%s=%s' % (k, getattr(self, k)) \
                for k in ('led_type', 'state', 'brightness', 'color', 'mode'))
        return 'LED(%s)' % values


    def _update_prefs(self):
        prefs = OrderedDict()
        if self._driver.preferences.leds is not None:
            prefs.update(self._driver.preferences.leds)

        prefs[self.led_type.name.lower()] = self.get_values()
        self._driver.preferences.leds = prefs


    def get_values(self) -> dict:
        tdict = OrderedDict()
        for attr in sorted([k for k, v in self.traits().items() \
                            if v.metadata.get('config', False)]):
            tdict[attr] = getattr(self, attr)
        return tdict


    def set_values(self, values: dict):
        self._restoring = True
        for key, value in values.items():
            setattr(self, key, value)
        self._restoring = False


    __repr__ = __str__


class LEDManager(object):
    def __init__(self, driver):
        self._driver = driver
        self._leds = {}

        self.led_changed = Signal()

        driver.restore_prefs.connect(self._restore_prefs)


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


    def _restore_prefs(self, prefs):
        led_prefs = prefs.leds

        for led_type in self.supported_leds:
            if led_type == LEDType.BACKLIGHT:
                # handled elsewhere
                continue

            key = led_type.name.lower()
            led = self.get(led_type)

            if led_prefs is not None and key in led_prefs:
                led.set_values(led_prefs[key])
