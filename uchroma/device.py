import hidapi

from uchroma.device_base import BaseUChromaDevice
from uchroma.frame import Frame
from uchroma.fx import FXManager
from uchroma.hardware import Hardware, Quirks
from uchroma.led import LED, LEDManager, LEDType
from uchroma.standard_fx import StandardFX
from uchroma.util import ValueAnimator


class UChromaDevice(BaseUChromaDevice):
    """
    Class encapsulating all functionality available on standard Chroma devices
    """

    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):

        super(UChromaDevice, self).__init__(hardware, devinfo, devindex,
                                            sys_path, input_devices,
                                            *args, **kwargs)

        self._fx_manager = FXManager(self, StandardFX(self))
        self._led_manager = LEDManager(self)

        self._frame_control = None

        self._brightness_animator = ValueAnimator(self._brightness_callback)
        self._suspended = False


    def get_led(self, led_type: LEDType) -> LED:
        """
        Fetches the requested LED interface on this device

        :param led_type: The LED type to fetch

        :return: The LED interface, if available
        """
        if self.led_manager is None:
            return None
        return self.led_manager.get(led_type)


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
            self.get_led(LEDType.SCROLL_WHEEL).brightness = level

        elif self.has_quirk(Quirks.LOGO_LED_BRIGHTNESS):
            self.get_led(LEDType.LOGO).brightness = level

        else:
            self.get_led(LEDType.BACKLIGHT).brightness = level


    def _get_brightness(self) -> float:
        if self.has_quirk(Quirks.SCROLL_WHEEL_BRIGHTNESS):
            return self.get_led(LEDType.SCROLL_WHEEL).brightness

        if self.has_quirk(Quirks.LOGO_LED_BRIGHTNESS):
            return self.get_led(LEDType.LOGO).brightness

        return self.get_led(LEDType.BACKLIGHT).brightness


    @property
    def suspended(self):
        """
        The power state of the device, true if suspended
        """
        return self._suspended


    def suspend(self):
        """
        Suspend the device

        Performs any actions necessary to suspend the device. By default,
        the current brightness level is saved and set to zero.
        """
        if self._suspended:
            return

        self.preferences.brightness = self.brightness
        self._brightness_animator.animate(self.brightness, 0)
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
        self.brightness = self.preferences.brightness


    @property
    def brightness(self):
        """
        The current brightness level of the device lighting
        """
        if self._suspended:
            return self.preferences.brightness

        return self._get_brightness()


    def _brightness_callback(self, level):
        self._set_brightness(level)

        suspended = self.suspended and level == 0
        self.power_state_changed.fire(level, suspended)


    @brightness.setter
    def brightness(self, level: float):
        """
        Set the brightness level of the main device lighting

        :param level: Brightness level, 0-100
        """
        if not self._suspended:
            self._brightness_animator.animate(self.brightness, level)

        self.preferences.brightness = level


    @property
    def supported_leds(self) -> tuple:
        return self.hardware.supported_leds


    @property
    def led_manager(self) -> LEDManager:
        return self._led_manager


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
