#
# uchroma - Copyright (C) 2017 Steve Kondik
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
import hidapi

from uchroma.util import scale_brightness

from .keyboard import UChromaKeyboard
from .hardware import Hardware
from .types import BaseCommand


class UChromaLaptop(UChromaKeyboard):
    """
    Commands required for Blade laptops
    """

    # commands
    class Command(BaseCommand):
        """
        Enumeration of standard commands not handled elsewhere
        """
        SET_BRIGHTNESS = (0x0e, 0x04, 0x02)
        GET_BRIGHTNESS = (0x0e, 0x84, 0x02)


    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):
        super(UChromaLaptop, self).__init__(hardware, devinfo, devindex,
                                            sys_path, input_devices,
                                            *args, **kwargs)


    def _get_serial_number(self):
        return self.name


    def _set_brightness(self, level: float):
        return self.run_command(UChromaLaptop.Command.SET_BRIGHTNESS, 0x01, scale_brightness(level))


    def _get_brightness(self) -> float:
        value = self.run_with_result(UChromaLaptop.Command.GET_BRIGHTNESS)
        if value is None:
            return 0.0
        return scale_brightness(int(value[1]), True)

