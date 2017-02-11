import logging

import hidapi

from uchroma.device_base import BaseUChromaDevice
from uchroma.frame import Frame
from uchroma.fx import FXManager
from uchroma.hardware import Hardware, Quirks
from uchroma.led import LED
from uchroma.standard_fx import StandardFX


class UChromaDevice(BaseUChromaDevice):
    """
    Class encapsulating all functionality available on standard Chroma devices
    """

    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):
        super(UChromaDevice, self).__init__(hardware, devinfo, devindex,
                                            sys_path, input_devices,
                                            *args, **kwargs)

        self._logger = logging.getLogger('uchroma.driver')
        self._leds = {}
        self._fx_manager = FXManager(self, StandardFX(self))

        self._frame_control = None

        self._last_brightness = None
        self._suspended = False


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
    def frame_control(self) -> Frame:
        """
        Gets the Frame object for creating custom effects on this device

        NOTE: This API is a work-in-progress and subject to change

        :param base_color: Background color for the Frame (defaults to black)

        :return: The Frame interface
        """
        if not self.has_matrix:
            return None

        if self._frame_control is None:
            self._frame_control = Frame(self, self.width, self.height)

        return self._frame_control


    def _set_brightness(self, level: float):
        if self.has_quirk(Quirks.SCROLL_WHEEL_BRIGHTNESS):
            self.get_led(LED.Type.SCROLL_WHEEL).brightness = level

        elif self.has_quirk(Quirks.LOGO_LED_BRIGHTNESS):
            self.get_led(LED.Type.LOGO).brightness = level

        else:
            self.get_led(LED.Type.BACKLIGHT).brightness = level


    def _get_brightness(self) -> float:
        if self.has_quirk(Quirks.SCROLL_WHEEL_BRIGHTNESS):
            return self.get_led(LED.Type.SCROLL_WHEEL).brightness

        if self.has_quirk(Quirks.LOGO_LED_BRIGHTNESS):
            return self.get_led(LED.Type.LOGO).brightness

        return self.get_led(LED.Type.BACKLIGHT).brightness


    @property
    def suspended(self):
        return self._suspended


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

        self._suspended = False

        self.brightness = self._last_brightness


    @property
    def brightness(self):
        """
        The current brightness level of the device lighting
        """
        if self._suspended:
            return self._last_brightness

        return self._get_brightness()


    @brightness.setter
    def brightness(self, level: float):
        """
        Set the brightness level of the main device lighting

        :param level: Brightness level, 0-100
        """
        if self._suspended:
            self._last_brightness = level
        else:
            self._set_brightness(level)


    def reset(self) -> bool:
        """
        Clear all effects and custom frame

        :return: True if successful
        """
        if self.has_matrix:
            self.frame_control.background_color = None
            self.frame_control.reset()

        if hasattr(self, 'fx_manager'):
            self.fx_manager.disable()
