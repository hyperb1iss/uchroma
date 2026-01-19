#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
import asyncio

from uchroma.server import hid
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
        devinfo: hid.DeviceInfo,
        devindex: int,
        sys_path: str,
        input_devices=None,
        *args,
        **kwargs,
    ):
        super().__init__(hardware, devinfo, devindex, sys_path, input_devices, *args, **kwargs)
        self._cached_brightness = 0.0
        self._brightness_lock = asyncio.Lock()

    async def _get_serial_number_async(self) -> str | None:
        return self.name

    def _set_brightness(self, level: float):
        # Standard LED brightness: args = [VARSTORE, BACKLIGHT_LED, brightness]
        return self.run_command(
            UChromaLaptop.Command.SET_BRIGHTNESS, VARSTORE, BACKLIGHT_LED, scale_brightness(level)
        )

    def _get_brightness(self) -> float:
        return self._cached_brightness

    async def _set_brightness_async(self, level: float) -> bool:
        success = await self.run_command_async(
            UChromaLaptop.Command.SET_BRIGHTNESS,
            VARSTORE,
            BACKLIGHT_LED,
            scale_brightness(level),
        )
        if success:
            self._cached_brightness = level
        return success

    async def refresh_brightness_async(self) -> float | None:
        async with self._brightness_lock:
            value = await self.run_with_result_async(
                UChromaLaptop.Command.GET_BRIGHTNESS, VARSTORE, BACKLIGHT_LED, 0x00
            )
            if value is not None and len(value) > 2:
                self._cached_brightness = scale_brightness(int(value[2]), True)
        return self._cached_brightness
