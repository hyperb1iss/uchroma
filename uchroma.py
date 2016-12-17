import logging
from enum import Enum

import hidapi
from color import RGB
from led import LED
from report import RazerReport

RAZER_VENDOR_ID = 0x1532


# commands
class Command(Enum):
    # info queries, command class 0
    SET_DEVICE_MODE = (0x00, 0x04, 0x02)

    GET_FIRMWARE_VERSION = (0x00, 0x81, 0x02)
    GET_SERIAL = (0x00, 0x82, 0x16)
    GET_DEVICE_MODE = (0x00, 0x84, 0x02)

    SET_EFFECT = (0x03, 0x0A, None)


# Effects
class ChromaEffect(Enum):
    NONE = 0x00
    WAVE = 0x01
    REACTIVE = 0x02
    BREATHE = 0x03
    SPECTRUM = 0x04
    CUSTOM = 0x05
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


class RazerChromaDriver(object):

    def __init__(self, path):

        self._path = path
        self._logger = logging.getLogger('uchroma.driver')
        self._devinfo = None

        devinfos = hidapi.enumerate()
        for devinfo in devinfos:
            if devinfo.path == str.encode(path) and devinfo.vendor_id == RAZER_VENDOR_ID:
                self._devinfo = devinfo
                break

        if self._devinfo is None:
            self._logger.error('No compatible Razer devices found')
            return

        try:
            self._dev = hidapi.Device(self._devinfo)
        except Exception as ex:
            self._logger.error('Error opening %s: %s', path, ex)
            raise

    def _get_report(self, command, *args):
        report = RazerReport(self._dev, command)
        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put_byte(arg)

        return report


    def run_with_result(self, command, *args):
        report = self._get_report(command, *args)
        if not report.run():
            return None

        return report.result


    def run_command(self, command, *args):
        return self._get_report(command, *args).run()


    def _set_effect(self, effect, *args):
        return self.run_command(Command.SET_EFFECT, effect, *args)


    def get_serial(self):
        return self.run_with_result(Command.GET_SERIAL)


    def get_firmware_version(self):
        version = self.run_with_result(Command.GET_FIRMWARE_VERSION)
        if version is None:
            return None

        return 'v%d.%d' % (version[0], version[1])


    def get_device_mode(self):
        return self.run_with_result(Command.GET_DEVICE_MODE)


    def set_device_mode(self, mode, param=0):
        return self.run_command(Command.SET_DEVICE_MODE, mode, param)


    def get_led(self, led_type):
        return LED(self, led_type)


    def disable_effects(self):
        return self._set_effect(ChromaEffect.NONE)


    def set_color(self, rgb=None):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        return self._set_effect(ChromaEffect.STATIC, rgb)


    def wave_effect(self, direction=WaveDirection.RIGHT):
        return self._set_effect(ChromaEffect.WAVE, direction)


    def spectrum_effect(self):
        return self._set_effect(ChromaEffect.SPECTRUM)


    def reactive_effect(self, rgb=None, speed=1):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_effect(ChromaEffect.REACTIVE, speed, rgb.red, rgb.green, rgb.blue)


    def _set_multi_mode_effect(self, effect, rgb1, rgb2, speed):
        if speed < 1 or speed > 4:
            raise ValueError('Speed for effect must be between 1 and 4 (got: %d)', speed)

        if rgb1 is None and rgb2 is None:
            return self._set_effect(effect, EffectMode.RANDOM, speed)

        elif rgb1 is not None and rgb2 is not None:
            return self._set_effect(effect, EffectMode.DUAL, speed, rgb1, rgb2)

        elif rgb1 is not None:
            return self._set_effect(effect, EffectMode.SINGLE, speed, rgb1)

        raise ValueError('Invalid arguments for effect')


    def starlight_effect(self, rgb1=None, rgb2=None, speed=1):
        return self._set_multi_mode_effect(ChromaEffect.STARLIGHT, rgb1, rgb2, speed)


    def breathe_effect(self, rgb1=None, rgb2=None, speed=1):
        return self._set_multi_mode_effect(ChromaEffect.BREATHE, rgb1, rgb2, speed)

