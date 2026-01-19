#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
from uchroma.server import hid

from .hardware import Hardware
from .keyboard import UChromaKeyboard
from .macro import MacroDevice


class UChromaKeypad(UChromaKeyboard):
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

        self._macrodev = None
        if hardware.macro_keys is not None:
            self._macrodev = MacroDevice(self)

    @property
    def macro_manager(self):
        return self._macrodev
