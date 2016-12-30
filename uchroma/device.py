import logging
from enum import Enum

from uchroma.device_base import BaseUChromaDevice
from uchroma.device_base import Model
from uchroma.frame import Frame
from uchroma.fx import FX
from uchroma.led import LED

RAZER_VENDOR_ID = 0x1532


class UChromaDevice(BaseUChromaDevice):

    # commands
    class Command(Enum):
        # blade commands
        SET_BRIGHTNESS = (0x0e, 0x04, 0x02)
        GET_BRIGHTNESS = (0x0e, 0x84, 0x02)


    def __init__(self, devinfo, devtype, devname):
        super(UChromaDevice, self).__init__(devinfo, devtype, devname)

        self._logger = logging.getLogger('uchroma.driver')
        self._leds = {}
        self._fx = FX(self)

        # TODO: check device capabilities
        for fxtype in FX.Type:
            method = fxtype.name.lower()
            setattr(self, method, getattr(self._fx, method))


    def get_led(self, led_type):
        if led_type not in self._leds:
            self._leds[led_type] = LED(self, led_type)

        return self._leds[led_type]


    def get_frame_control(self, width, height, base_rgb=None):
        return Frame(self, width, height, base_rgb)


    def _set_blade_brightness(self, level):
        return self.run_command(UChromaDevice.Command.SET_BRIGHTNESS, 0x01, level)


    def _get_blade_brightness(self):
        value = self.run_with_result(UChromaDevice.Command.GET_BRIGHTNESS)

        if value is None:
            return 0

        return value[1]


    @property
    def brightness(self):
        if self._devtype == Model.LAPTOP:
            return self._get_blade_brightness()
        else:
            return self.get_led(LED.Type.BACKLIGHT).brightness


    @brightness.setter
    def brightness(self, level):
        if level < 0 or level > 255:
            raise ValueError('Brightness must be between 0 and 255')

        if self._devtype == Model.LAPTOP:
            self._set_blade_brightness(level)
        else:
            self.get_led(LED.Type.BACKLIGHT).brightness = level
