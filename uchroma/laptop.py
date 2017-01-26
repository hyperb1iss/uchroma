import hidapi

from uchroma.keyboard import UChromaKeyboard
from uchroma.hardware import Hardware
from uchroma.types import BaseCommand
from uchroma.util import scale_brightness


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


    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo,
                 input_devices=None, *args, **kwargs):
        super(UChromaLaptop, self).__init__(hardware, devinfo, input_devices,
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

