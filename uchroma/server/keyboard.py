#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
from uchroma.server import hid

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

    def __init__(
        self,
        hardware: Hardware,
        devinfo: hid.DeviceInfo,
        devindex: int,
        sys_path: str,
        input_devices=None,
        *args,
        **kwargs,
    ):
        super().__init__(hardware, devinfo, devindex, sys_path, input_devices, *args, **kwargs)

    def get_device_mode(self) -> tuple | None:
        """
        Gets the current device mode
        """
        if self.device_type == Hardware.Type.LAPTOP:
            return None

        value = self.run_with_result(UChromaKeyboard.Command.GET_DEVICE_MODE)
        if value is None:
            return None

        return (value[0], value[1])

    def set_device_mode(self, mode, param=0) -> bool | None:
        """
        Sets the requested device mode
        """
        if self.device_type == Hardware.Type.LAPTOP:
            return None

        return self.run_command(UChromaKeyboard.Command.SET_DEVICE_MODE, mode, param)
