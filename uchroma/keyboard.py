import hidapi

from uchroma.device import UChromaDevice
from uchroma.device_base import BaseCommand
from uchroma.models import Keyboard, Model


class UChromaKeyboard(UChromaDevice):
    """
    Additional functionality for Chroma Keyboards
    """

    class Command(BaseCommand):
        """
        Commands used for keyboard features
        """
        SET_DEVICE_MODE = (0x00, 0x04, 0x02)

        GET_DEVICE_MODE = (0x00, 0x84, 0x02)


    def __init__(self, model: Keyboard, devinfo: hidapi.DeviceInfo, input_devices=None):
        super(UChromaKeyboard, self).__init__(model, devinfo, input_devices)


    def get_device_mode(self) -> tuple:
        """
        Gets the current device mode
        """
        if self.device_type == Model.Type.LAPTOP:
            return None

        value = self.run_with_result(UChromaKeyboard.Command.GET_DEVICE_MODE)
        if value is None:
            return None

        return (value[0], value[1])


    def set_device_mode(self, mode, param=0) -> bool:
        """
        Sets the requested device mode
        """
        if self.device_type == Model.Type.LAPTOP:
            return None

        return self.run_command(UChromaKeyboard.Command.SET_DEVICE_MODE, mode, param)
