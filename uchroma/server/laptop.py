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
from uchroma.util import scale_brightness

from .hardware import Hardware
from .keyboard import UChromaKeyboard
from .system_control import SystemControlMixin
from .types import BaseCommand

# LED constants from Razer protocol
VARSTORE = 0x01
BACKLIGHT_LED = 0x05


class UChromaLaptop(SystemControlMixin, UChromaKeyboard):
    """
    Commands required for Blade laptops
    """

    # Standard LED brightness commands (class 0x03)
    # These work on Blade 2021+ models
    class Command(BaseCommand):
        """
        Enumeration of standard commands not handled elsewhere
        """

        SET_BRIGHTNESS = (0x03, 0x03, 0x03)
        GET_BRIGHTNESS = (0x03, 0x83, 0x03)

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

    def _get_serial_number(self):
        return self.name

    def _set_brightness(self, level: float):
        # Standard LED brightness: args = [VARSTORE, BACKLIGHT_LED, brightness]
        return self.run_command(
            UChromaLaptop.Command.SET_BRIGHTNESS, VARSTORE, BACKLIGHT_LED, scale_brightness(level)
        )

    def _get_brightness(self) -> float:
        # Standard LED brightness: args = [VARSTORE, BACKLIGHT_LED, 0x00]
        value = self.run_with_result(
            UChromaLaptop.Command.GET_BRIGHTNESS, VARSTORE, BACKLIGHT_LED, 0x00
        )
        if value is None:
            return 0.0
        # Response: brightness is in args[2]
        return scale_brightness(int(value[2]), True)
