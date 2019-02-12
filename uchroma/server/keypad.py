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

from .keyboard import UChromaKeyboard
from .hardware import Hardware
from .macro import MacroDevice


class UChromaKeypad(UChromaKeyboard):

    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, devindex: int,
                 sys_path: str, input_devices=None, *args, **kwargs):
        super(UChromaKeypad, self).__init__(hardware, devinfo, devindex,
                                            sys_path, input_devices,
                                            *args, **kwargs)

        self._macrodev = None
        if hardware.macro_keys is not None:
            self._macrodev = MacroDevice(self)


    @property
    def macro_manager(self):
        return self._macrodev
