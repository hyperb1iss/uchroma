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

from .device import UChromaDevice
from .fixups import KeyboardFixup
from .hardware import Hardware
from .types import BaseCommand


class UChromaKeyboard(UChromaDevice, KeyboardFixup):
    """
    Additional functionality for Chroma Keyboards
    """

    class Command(BaseCommand):
        """
        Commands used for keyboard features
        """
        SET_DEVICE_MODE = (0x00, 0x04, 0x02)

        GET_DEVICE_MODE = (0x00, 0x84, 0x02)


    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):
        super(UChromaKeyboard, self).__init__(hardware, devinfo, devindex,
                                              sys_path, input_devices,
                                              *args, **kwargs)


    def get_device_mode(self) -> tuple:
        """
        Gets the current device mode
        """
        if self.device_type == Hardware.Type.LAPTOP:
            return None

        value = self.run_with_result(UChromaKeyboard.Command.GET_DEVICE_MODE)
        if value is None:
            return None

        return (value[0], value[1])


    def set_device_mode(self, mode, param=0) -> bool:
        """
        Sets the requested device mode
        """
        if self.device_type == Hardware.Type.LAPTOP:
            return None

        return self.run_command(UChromaKeyboard.Command.SET_DEVICE_MODE, mode, param)
