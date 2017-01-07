import logging

from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.frame import Frame
from uchroma.fx import FX
from uchroma.led import LED
from uchroma.models import Model


class UChromaDevice(BaseUChromaDevice):
    """
    Class encapsulating all functionality available on standard Chroma devices
    """

    # commands
    class Command(BaseCommand):
        """
        Enumeration of standard commands not handled elsewhere
        """
        SET_BRIGHTNESS = (0x0e, 0x04, 0x02)
        GET_BRIGHTNESS = (0x0e, 0x84, 0x02)


    def __init__(self, devinfo, devtype, devname, input_devices=None):
        super(UChromaDevice, self).__init__(devinfo, devtype, devname)

        self._logger = logging.getLogger('uchroma.driver')
        self._leds = {}
        self._fx = FX(self)
        self._input_devices = []

        if input_devices is not None:
            self._input_devices.extend(input_devices)

        self._last_brightness = None
        self._suspended = False

        # TODO: check device capabilities
        for fxtype in FX.Type:
            method = fxtype.name.lower()
            if hasattr(self._fx, method):
                setattr(self, method, getattr(self._fx, method))


    def get_led(self, led_type: LED.Type) -> LED:
        """
        Fetches the requested LED interface on this device

        :param led_type: The LED type to fetch

        :return: The LED interface, if available
        """
        if led_type not in self._leds:
            self._leds[led_type] = LED(self, led_type)

        return self._leds[led_type]


    def get_frame_control(self, width: int, height: int, base_color=None) -> Frame:
        """
        Gets the Frame object for creating custom effects on this device

        NOTE: This API is a work-in-progress and subject to change

        :param width: The width of the matrix
        :param height: The height of the matrix
        :param base_color: Background color for the Frame (defaults to black)

        :return: The Frame interface
        """
        return Frame(self, width, height, base_color)


    def _set_blade_brightness(self, level):
        return self.run_command(UChromaDevice.Command.SET_BRIGHTNESS, 0x01, level)


    def _get_blade_brightness(self):
        value = self.run_with_result(UChromaDevice.Command.GET_BRIGHTNESS)

        if value is None:
            return 0

        return value[1]


    def suspend(self):
        """
        Suspend the device

        Performs any actions necessary to suspend the device. By default,
        the current brightness level is saved and set to zero.
        """
        if self._suspended:
            return

        self._last_brightness = self.brightness
        self.brightness = 0

        self._suspended = True


    def resume(self):
        """
        Resume the device

        Performs any actions necessary to resume the device. By default,
        the saved brightness level is restored.
        """
        if not self._suspended:
            return

        self.brightness = self._last_brightness

        self._suspended = False


    @property
    def input_devices(self):
        """
        List of associated input device path
        """
        return self._input_devices


    @property
    def brightness(self):
        """
        The current brightness level of the device lighting
        """
        if self._devtype == Model.LAPTOP:
            return self._get_blade_brightness()
        else:
            return self.get_led(LED.Type.BACKLIGHT).brightness


    @brightness.setter
    def brightness(self, level):
        """
        Set the brightness level of the device lighting
        """
        if level < 0 or level > 255:
            raise ValueError('Brightness must be between 0 and 255')

        if self._suspended:
            self._last_brightness = level
        elif self._devtype == Model.LAPTOP:
            self._set_blade_brightness(level)
        else:
            self.get_led(LED.Type.BACKLIGHT).brightness = level
