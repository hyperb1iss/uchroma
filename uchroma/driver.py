import logging
from enum import Enum

import hidapi
from uchroma.report import RazerReport


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


class Driver(object):

    # commands
    class Command(Enum):
        # info queries, class 0
        SET_DEVICE_MODE = (0x00, 0x04, 0x02)

        GET_FIRMWARE_VERSION = (0x00, 0x81, 0x02)
        GET_SERIAL = (0x00, 0x82, 0x16)
        GET_DEVICE_MODE = (0x00, 0x84, 0x02)

        # device commands, class 3
        SET_EFFECT = (0x03, 0x0A, None)
        SET_CUSTOM_FRAME_DATA = (0x03, 0x0B, None)

        # blade commands
        SET_BRIGHTNESS = (0x0e, 0x04, 0x02)
        GET_BRIGHTNESS = (0x0e, 0x84, 0x02)


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


    def _get_report(self, command_class, command_id, data_size, *args):
        report = RazerReport(self._dev, command_class, command_id, data_size)
        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put_byte(arg)

        return report


    def run_with_result(self, command, *args):
        report = self._get_report(*command.value, *args)
        if not report.run():
            return None

        return report.result


    def run_command(self, command, *args):
        return self._get_report(*command.value, *args).run()


    def _set_effect(self, effect, *args):
        return self.run_command(Driver.Command.SET_EFFECT, effect, *args)


    def get_serial(self):
        return self.run_with_result(Driver.Command.GET_SERIAL)


    def get_firmware_version(self):
        version = self.run_with_result(Driver.Command.GET_FIRMWARE_VERSION)
        if version is None:
            return None

        return 'v%d.%d' % (version[0], version[1])


    def get_device_mode(self):
        return self.run_with_result(Driver.Command.GET_DEVICE_MODE)


    def set_device_mode(self, mode, param=0):
        return self.run_command(Driver.Command.SET_DEVICE_MODE, mode, param)


    def get_led(self, led_type):
        return LED(self, led_type)


    def set_blade_brightness(self, brightness):
        return self.run_command(Driver.Command.SET_BRIGHTNESS, 0x01, brightness)


    def get_blade_brightness(self):
        value = self.run_with_result(Driver.Command.GET_BRIGHTNESS)

        if value is None:
            return 0

        return value[1]


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


    def _set_multi_mode_effect(self, effect, rgb1=None, rgb2=None, speed=1, splotch=None):
        if speed < 1 or speed > 4:
            raise ValueError('Speed for effect must be between 1 and 4 (got: %d)', speed)

        if splotch is not None:
            rgb1 = splotch.value[0]
            rgb2 = splotch.value[1]

        if rgb1 is None and rgb2 is None:
            return self._set_effect(effect, EffectMode.RANDOM, speed)

        elif rgb1 is not None and rgb2 is not None:
            return self._set_effect(effect, EffectMode.DUAL, speed, rgb1, rgb2)

        elif rgb1 is not None:
            return self._set_effect(effect, EffectMode.SINGLE, speed, rgb1)

        raise ValueError('Invalid arguments for effect')


    def starlight_effect(self, rgb1=None, rgb2=None, speed=1, splotch=None):
        return self._set_multi_mode_effect(Effect.STARLIGHT, rgb1, rgb2, speed, splotch)


    def breathe_effect(self, rgb1=None, rgb2=None, speed=1, splotch=None):
        return self._set_multi_mode_effect(Effect.BREATHE, rgb1, rgb2, speed, splotch)


    def show_custom_frame(self):
        return self._set_effect(Effect.CUSTOM_FRAME, 0x01)


    def get_frame_control(self, width, height, base_rgb=None):
        return Frame(self, width, height, base_rgb)

