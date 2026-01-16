#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
from uchroma.server import hidadapter as hidapi

from .device_base import BaseUChromaDevice
from .frame import Frame
from .fx import FXManager
from .hardware import Hardware, Quirks
from .led import LED, LEDManager
from .standard_fx import StandardFX
from .types import LEDType


class UChromaDevice(BaseUChromaDevice):
    """
    Class encapsulating all functionality available on standard Chroma devices
    """

    def __init__(
        self,
        hardware: Hardware,
        devinfo: hidapi.DeviceInfo,
        devindex: int,
        sys_path: str,
        input_devices=None,
        *args,
        **kwargs,
    ):
        super().__init__(hardware, devinfo, devindex, sys_path, input_devices, *args, **kwargs)

        self._fx_manager = FXManager(self, StandardFX(self))
        self._led_manager = LEDManager(self)

        self._frame_control = None

    def get_led(self, led_type: LEDType) -> LED | None:
        """
        Fetches the requested LED interface on this device

        :param led_type: The LED type to fetch

        :return: The LED interface, if available
        """
        if self.led_manager is None:
            return None
        return self.led_manager.get(led_type)

    @property
    def frame_control(self) -> Frame | None:
        """
        Gets the Frame object for creating custom effects on this device

        :param base_color: Background color for the Frame (defaults to black)

        :return: The Frame interface
        """
        if self.width == 0 or self.height == 0:
            return None

        if self._frame_control is None:
            self._frame_control = Frame(self, self.width, self.height)

        return self._frame_control

    def _set_brightness(self, level: float) -> bool:
        led: LED | None = None
        if self.has_quirk(Quirks.SCROLL_WHEEL_BRIGHTNESS):
            led = self.get_led(LEDType.SCROLL_WHEEL)
        elif self.has_quirk(Quirks.LOGO_LED_BRIGHTNESS):
            led = self.get_led(LEDType.LOGO)
        else:
            led = self.get_led(LEDType.BACKLIGHT)

        if led is not None:
            led.brightness = level
        return True

    def _get_brightness(self) -> float:
        led: LED | None = None
        if self.has_quirk(Quirks.SCROLL_WHEEL_BRIGHTNESS):
            led = self.get_led(LEDType.SCROLL_WHEEL)
        elif self.has_quirk(Quirks.LOGO_LED_BRIGHTNESS):
            led = self.get_led(LEDType.LOGO)
        else:
            led = self.get_led(LEDType.BACKLIGHT)

        if led is not None:
            return led.brightness
        return 0.0

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
        if self._frame_control is not None:
            frame = self.frame_control
            if frame is not None:
                frame.background_color = None
                frame.reset()

        if hasattr(self, "fx_manager"):
            self.fx_manager.disable()

        return True
