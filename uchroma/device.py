import logging
from enum import Enum

from uchroma.device_base import RazerDevice
from uchroma.device_base import RazerDeviceType
from uchroma.color import RGB
from uchroma.frame import Frame
from uchroma.led import LED

RAZER_VENDOR_ID = 0x1532


# Effects
class Effect(Enum):
    NONE = 0x00
    WAVE = 0x01
    REACTIVE = 0x02
    BREATHE = 0x03
    SPECTRUM = 0x04
    CUSTOM_FRAME = 0x05
    STATIC = 0x06
    STARLIGHT = 0x19


# Modes for the Wave effect
# The "chase" modes add a circular spin around the trackpad (if supported)
class WaveDirection(Enum):
    RIGHT = 0
    LEFT = 2
    LEFT_CHASE = 3
    RIGHT_CHASE = 4


# Modes for starlight and breathe effects
class EffectMode(Enum):
    RANDOM = 0
    SINGLE = 1
    DUAL = 2


class RazerChromaDevice(RazerDevice):

    # commands
    class Command(Enum):
        # device commands, class 3
        SET_EFFECT = (0x03, 0x0A, None)
        SET_CUSTOM_FRAME_DATA = (0x03, 0x0B, None)

        # blade commands
        SET_BRIGHTNESS = (0x0e, 0x04, 0x02)
        GET_BRIGHTNESS = (0x0e, 0x84, 0x02)


    def __init__(self, devinfo, devtype, devname):
        super(RazerChromaDevice, self).__init__(devinfo, devtype, devname)

        self._logger = logging.getLogger('uchroma.driver')
        self._leds = {}


    def _set_effect(self, effect, *args):
        return self.run_command(RazerChromaDevice.Command.SET_EFFECT, effect, *args)


    def get_led(self, led_type):
        if led_type not in self._leds:
            self._leds[led_type] = LED(self, led_type)

        return self._leds[led_type]


    def _set_blade_brightness(self, level):
        return self.run_command(RazerChromaDevice.Command.SET_BRIGHTNESS, 0x01, level)


    def _get_blade_brightness(self):
        value = self.run_with_result(RazerChromaDevice.Command.GET_BRIGHTNESS)

        if value is None:
            return 0

        return value[1]


    @property
    def brightness(self):
        if self._devtype == RazerDeviceType.LAPTOP:
            return self._get_blade_brightness()
        else:
            return self.get_led(LED.Type.BACKLIGHT).brightness


    @brightness.setter
    def brightness(self, level):
        if level < 0 or level > 255:
            raise ValueError('Brightness must be between 0 and 255')

        if self._devtype == RazerDeviceType.LAPTOP:
            self._set_blade_brightness(level)
        else:
            self.get_led(LED.Type.BACKLIGHT).brightness = level


    def disable_effects(self):
        return self._set_effect(Effect.NONE)


    def set_color(self, rgb=None):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        return self._set_effect(Effect.STATIC, rgb)


    def wave_effect(self, direction=WaveDirection.RIGHT):
        return self._set_effect(Effect.WAVE, direction)


    def spectrum_effect(self):
        return self._set_effect(Effect.SPECTRUM)


    def reactive_effect(self, rgb=None, speed=1):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_effect(Effect.REACTIVE, speed, rgb.red, rgb.green, rgb.blue)


    def _set_multi_mode_effect(self, effect, rgb1=None, rgb2=None, speed=None, splotch=None):
        if speed is not None and (speed < 1 or speed > 4):
            raise ValueError('Speed for effect must be between 1 and 4 (got: %d)', speed)

        if splotch is not None:
            rgb1 = splotch.value[0]
            rgb2 = splotch.value[1]

        mode = None

        if rgb1 is not None and rgb2 is not None:
            mode = EffectMode.DUAL.value
        elif rgb1 is not None:
            mode = EffectMode.SINGLE.value
        else:
            mode = EffectMode.RANDOM.value

        args = [mode]

        if speed is not None:
            args.append(speed)

        if rgb1 is not None:
            args.append(rgb1)

        if rgb2 is not None:
            args.append(rgb2)

        self._set_effect(effect, *args)


    def starlight_effect(self, rgb1=None, rgb2=None, speed=1, splotch=None):
        return self._set_multi_mode_effect(Effect.STARLIGHT, rgb1, rgb2, speed=speed, splotch=splotch)


    def breathe_effect(self, rgb1=None, rgb2=None, splotch=None):
        return self._set_multi_mode_effect(Effect.BREATHE, rgb1, rgb2, splotch=splotch)


    def show_custom_frame(self):
        return self._set_effect(Effect.CUSTOM_FRAME, 0x01)


    def get_frame_control(self, width, height, base_rgb=None):
        return Frame(self, width, height, base_rgb)

