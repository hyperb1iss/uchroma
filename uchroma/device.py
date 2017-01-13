import logging

import hidapi

from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.frame import Frame
from uchroma.fx import FX
from uchroma.led import LED
from uchroma.models import Model
from uchroma.util import scale_brightness


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


    def __init__(self, model: Model, devinfo: hidapi.DeviceInfo, input_devices=None):
        super(UChromaDevice, self).__init__(model, devinfo)

        self._logger = logging.getLogger('uchroma.driver')
        self._leds = {}
        self._fx = FX(self)
        self._input_devices = []

        self._frame_control = None

        self._width = 25
        self._height = 6

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


    @property
    def width(self) -> int:
        """
        Gets the width of the key matrix (if applicable)
        """
        return self._width


    @property
    def height(self) -> int:
        """
        Gets the height of the key matrix (if applicable)
        """
        return self._height


    @property
    def has_matrix(self):
        """
        True if the device supports matrix control
        """
        return True


    @property
    def frame_control(self, base_color=None) -> Frame:
        """
        Gets the Frame object for creating custom effects on this device

        NOTE: This API is a work-in-progress and subject to change

        :param base_color: Background color for the Frame (defaults to black)

        :return: The Frame interface
        """
        if self._frame_control is None:
            self._frame_control = Frame(self, self.width, self.height, base_color)

        return self._frame_control


    def _set_blade_brightness(self, level: float):
        return self.run_command(UChromaDevice.Command.SET_BRIGHTNESS, 0x01, scale_brightness(level))


    def _get_blade_brightness(self) -> float:
        value = self.run_with_result(UChromaDevice.Command.GET_BRIGHTNESS)

        return scale_brightness(int(value[1]), True)


    def _set_mouse_brightness(self, level: float):
        self.get_led(LED.Type.BACKLIGHT).brightness = level
        self.get_led(LED.Type.LOGO).brightness = level
        self.get_led(LED.Type.SCROLL_WHEEL).brightness = level


    def _get_mouse_brightness(self) -> float:
        return self.get_led(LED.Type.BACKLIGHT).brightness


    def suspend(self):
        """
        Suspend the device

        Performs any actions necessary to suspend the device. By default,
        the current brightness level is saved and set to zero.
        """
        if self._suspended:
            return

        self._last_brightness = self.brightness
        self.brightness = 0.0

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
        if self._model.type == Model.Type.LAPTOP:
            return self._get_blade_brightness()
        elif self._model.type == Model.Type.MOUSE:
            return self._get_mouse_brightness()
        else:
            return self.get_led(LED.Type.BACKLIGHT).brightness


    @brightness.setter
    def brightness(self, level: float):
        """
        Set the brightness level of the main device lighting

        :param level: Brightness level, 0-100
        """
        if self._suspended:
            self._last_brightness = level
        elif self._model.type == Model.Type.LAPTOP:
            self._set_blade_brightness(level)
        elif self._model.type == Model.Type.MOUSE:
            self._set_mouse_brightness(level)
        else:
            self.get_led(LED.Type.BACKLIGHT).brightness = level
