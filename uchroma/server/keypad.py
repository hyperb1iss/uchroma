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

