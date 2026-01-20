#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=protected-access

import asyncio
import struct

from traitlets import Unicode

from uchroma.color import to_color, to_rgb
from uchroma.colorlib import Color
from uchroma.server import hid
from uchroma.traits import ColorSchemeTrait, ColorTrait
from uchroma.util import scale_brightness, set_bits, test_bit

from .device_base import BaseUChromaDevice
from .fx import BaseFX, FXManager, FXModule
from .hardware import Hardware
from .types import BaseCommand

# Use constants from Rust HeadsetDevice
READ_RAM = hid.READ_RAM
READ_EEPROM = hid.READ_EEPROM
WRITE_RAM = hid.WRITE_RAM
REPORT_LENGTH_OUT = hid.HEADSET_REPORT_OUT_LEN
REPORT_LENGTH_IN = hid.HEADSET_REPORT_IN_LEN

# EEPROM
ADDR_FIRMWARE_VERSION = 0x0030
ADDR_SERIAL_NUMBER = 0x7F00

# RAM
ADDR_KYLIE_LED_MODE = 0x172D
ADDR_KYLIE_BREATHING1_START = 0x1741
ADDR_KYLIE_BREATHING2_START = 0x1745
ADDR_KYLIE_BREATHING3_START = 0x174D

ADDR_RAINIE_LED_MODE = 0x1008
ADDR_RAINIE_BREATHING1_START = 0x15DE


class EffectBits:
    """
    The effect mode on this hardware is represented by a single
    integer. This class assists with managing the bits of
    this value.
    """

    def __init__(self, value: int = 0):
        self.on = test_bit(value, 0)
        self.breathe_single = test_bit(value, 1)
        self.spectrum = test_bit(value, 2)
        self.sync = test_bit(value, 3)
        self.breathe_double = test_bit(value, 4)
        self.breathe_triple = test_bit(value, 5)

    @property
    def value(self) -> int:
        """
        Return the state as an integer
        """
        return set_bits(
            0,
            self.on,
            self.breathe_single,
            self.spectrum,
            self.sync,
            self.breathe_double,
            self.breathe_triple,
        )

    @property
    def color_count(self) -> int:
        """
        Returns the number of colors currently in use
        """
        if self.breathe_triple:
            return 3
        if self.breathe_double:
            return 2
        if self.breathe_single:
            return 1
        if self.on == 1:
            return 1
        return 0


class KrakenFX(FXModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class DisableFX(BaseFX):
        description = Unicode("Disable all effects")

        def apply(self) -> bool:
            # Headset FX uses async - call via apply_async()
            return False

        async def apply_async(self) -> bool:
            """
            Disable all effects

            :return: True if successful
            """
            bits = EffectBits()
            bits.spectrum = True
            return await self._driver._set_led_mode(bits)

    class SpectrumFX(BaseFX):
        description = Unicode("Cycle thru all colors of the spectrum")

        def apply(self) -> bool:
            # Headset FX uses async - call via apply_async()
            return False

        async def apply_async(self) -> bool:
            """
            Cycle thru all colors of the spectrum

            :return: True if successful
            """
            bits = EffectBits()
            bits.on = bits.spectrum = True
            return await self._driver._set_led_mode(bits)

    class StaticFX(BaseFX):
        description = Unicode("Static color")
        color = ColorTrait(default_value="green").tag(config=True)

        def apply(self) -> bool:
            # Headset FX uses async - call via apply_async()
            return False

        async def apply_async(self) -> bool:
            """
            Sets lighting to a static color

            :param color: The color to apply

            :return: True if successful
            """
            bits = EffectBits()
            bits.on = True
            if await self._driver._set_rgb(self.color):
                return await self._driver._set_led_mode(bits)
            return False

    class BreatheFX(BaseFX):
        description = Unicode("Colors pulse in and out")
        colors = ColorSchemeTrait(minlen=1, maxlen=3, default_value=("red", "green", "blue")).tag(
            config=True
        )

        def apply(self) -> bool:
            # Headset FX uses async - call via apply_async()
            return False

        async def apply_async(self) -> bool:
            """
            Breathing color effect. Accepts up to three colors on v2 hardware

            :param color1: Primary color
            :param color2: Secondary color
            :param color3: Tertiary color
            :param preset: Predefinied color pair

            :return True if successful:
            """
            bits = EffectBits()
            bits.on = True
            bits.sync = True
            if len(self.colors) == 3:
                bits.breathe_triple = True
            elif len(self.colors) == 2:
                bits.breathe_double = True
            elif len(self.colors) == 1:
                bits.breathe_single = True

            if await self._driver._set_rgb(*self.colors):
                return await self._driver._set_led_mode(bits)
            return False


class UChromaHeadset(BaseUChromaDevice):
    """
    Additional functionality for Chroma Headsets
    The protocol on these devices is different than
    the rest of the Chroma line.
    """

    class Command(BaseCommand):
        """
        Commands used for headset features

        0: Destination
        1: Length
        2-3: Address
        """

        GET_SERIAL = (READ_EEPROM, 0x16, ADDR_SERIAL_NUMBER)
        GET_FIRMWARE_VERSION = (READ_EEPROM, 0x02, ADDR_FIRMWARE_VERSION)

        KYLIE_GET_LED_MODE = (READ_RAM, 0x01, ADDR_KYLIE_LED_MODE)
        KYLIE_SET_LED_MODE = (WRITE_RAM, 0x01, ADDR_KYLIE_LED_MODE)

        KYLIE_GET_RGB_1 = (READ_RAM, 0x04, ADDR_KYLIE_BREATHING1_START)
        KYLIE_GET_RGB_2 = (READ_RAM, 0x08, ADDR_KYLIE_BREATHING2_START)
        KYLIE_GET_RGB_3 = (READ_RAM, 0x0C, ADDR_KYLIE_BREATHING3_START)
        KYLIE_SET_RGB_1 = (WRITE_RAM, 0x04, ADDR_KYLIE_BREATHING1_START)
        KYLIE_SET_RGB_2 = (WRITE_RAM, 0x08, ADDR_KYLIE_BREATHING2_START)
        KYLIE_SET_RGB_3 = (WRITE_RAM, 0x0C, ADDR_KYLIE_BREATHING3_START)

        RAINIE_GET_LED_MODE = (READ_RAM, 0x01, ADDR_RAINIE_LED_MODE)
        RAINIE_SET_LED_MODE = (WRITE_RAM, 0x01, ADDR_RAINIE_LED_MODE)

        RAINIE_GET_RGB = (WRITE_RAM, 0x04, ADDR_RAINIE_BREATHING1_START)
        RAINIE_SET_RGB = (WRITE_RAM, 0x04, ADDR_RAINIE_BREATHING1_START)

        def __init__(self, destination, length, address):
            self._destination = destination
            self._length = length
            self._address = address

        @property
        def destination(self):
            return self._destination

        @property
        def length(self):
            return self._length

        @property
        def address(self):
            return self._address

    def __init__(
        self,
        hardware: Hardware,
        devinfo: hid.DeviceInfo,
        devindex: int,
        sys_path: str,
        *args,
        **kwargs,
    ):
        super().__init__(hardware, devinfo, devindex, sys_path, *args, **kwargs)

        self._last_cmd_time = None

        if self.hardware.revision == 1:
            self._cmd_get_led = UChromaHeadset.Command.RAINIE_GET_LED_MODE
            self._cmd_set_led = UChromaHeadset.Command.RAINIE_SET_LED_MODE
            self._cmd_get_rgb = [UChromaHeadset.Command.RAINIE_GET_RGB]
            self._cmd_set_rgb = [UChromaHeadset.Command.RAINIE_SET_RGB]

        elif self.hardware.revision == 2:
            self._cmd_get_led = UChromaHeadset.Command.KYLIE_GET_LED_MODE
            self._cmd_set_led = UChromaHeadset.Command.KYLIE_SET_LED_MODE
            self._cmd_get_rgb = [
                UChromaHeadset.Command.KYLIE_GET_RGB_1,
                UChromaHeadset.Command.KYLIE_GET_RGB_2,
                UChromaHeadset.Command.KYLIE_GET_RGB_3,
            ]
            self._cmd_set_rgb = [
                UChromaHeadset.Command.KYLIE_SET_RGB_1,
                UChromaHeadset.Command.KYLIE_SET_RGB_2,
                UChromaHeadset.Command.KYLIE_SET_RGB_3,
            ]
        else:
            raise ValueError(f"Incompatible model ({self.hardware!r})")

        self._fx_manager = FXManager(self, KrakenFX(self))
        self._rgb = None
        self._mode = None
        self._cached_brightness = 0.0
        self._brightness_lock = asyncio.Lock()

    def _ensure_open(self) -> bool:
        """Open the headset device using HeadsetDevice (interrupt transfers)."""
        try:
            if self._dev is None:
                self._dev = hid.HeadsetDevice(self._devinfo)
        except Exception as err:
            self.logger.exception("Failed to open headset connection", exc_info=err)
            return False
        return True

    def _pack_args(self, args) -> bytes | None:
        """Pack command arguments into bytes for the headset protocol."""
        if not args:
            return None

        result = bytearray()
        for arg in args:
            if arg is None:
                continue
            elif isinstance(arg, Color):
                rgb = arg.convert("srgb")
                result.extend(
                    struct.pack(
                        "=BBB",
                        int(rgb["red"] * 255),
                        int(rgb["green"] * 255),
                        int(rgb["blue"] * 255),
                    )
                )
            elif isinstance(arg, (bytes, bytearray)):
                result.extend(arg)
            elif isinstance(arg, int):
                result.append(arg & 0xFF)
            else:
                result.extend(bytes(arg))
        return bytes(result) if result else None

    async def _run_command_async(self, command: BaseCommand, *args) -> bool:
        """
        Run a command against the Kraken hardware (async).

        :param command: The command tuple
        :param args: Argument list (varargs)

        :return: True if successful
        """
        try:
            arg_bytes = self._pack_args(args) if args else None
            await self._dev.run_command(
                command.destination,
                command.length,
                command.address,
                list(arg_bytes) if arg_bytes else None,
            )
            return True
        except OSError as err:
            self.logger.exception("Caught exception running command", exc_info=err)
            return False

    async def _run_with_result_async(self, command: BaseCommand, *args) -> bytes | None:
        """
        Run a command against the Kraken hardware and fetch the result (async).

        :param command: The command tuple
        :param args: Argument list (varargs)

        :return: Raw response bytes
        """
        try:
            arg_bytes = self._pack_args(args) if args else None
            result = await self._dev.run_command(
                command.destination,
                command.length,
                command.address,
                list(arg_bytes) if arg_bytes else None,
            )
            return bytes(result) if result else None
        except OSError as err:
            self.logger.exception("Caught exception running command", exc_info=err)
            return None

    async def _get_serial_number_async(self) -> str | None:
        """Get the serial number from the hardware directly."""
        result = await self._run_with_result_async(UChromaHeadset.Command.GET_SERIAL)
        return self._decode_serial(result)

    async def _get_firmware_version_async(self) -> bytes | None:
        """Get the firmware version from the hardware directly."""
        return await self._run_with_result_async(UChromaHeadset.Command.GET_FIRMWARE_VERSION)

    async def _get_led_mode(self) -> "EffectBits":
        if self._mode is None:
            value = await self._run_with_result_async(self._cmd_get_led)
            bits = 0
            if value:
                bits = value[0]
            self._mode = EffectBits(bits)
        return self._mode

    async def _set_led_mode(self, bits: EffectBits) -> bool:
        status = await self._run_command_async(self._cmd_set_led, bits.value)
        if status:
            self._mode = bits
        return status

    async def _get_rgb(self) -> list | None:
        bits = await self._get_led_mode()
        if bits.color_count == 0:
            return None

        value = await self._run_with_result_async(self._cmd_get_rgb[bits.color_count - 1])
        if value is None:
            return None

        it = iter(value)
        values = list(iter(zip(it, it, it, it, strict=False)))

        return [to_color(x) for x in values]

    async def _set_rgb(self, *colors, brightness: float | None = None) -> bool:
        if not colors:
            self.logger.error("RGB group out of range")
            return False

        # only allow what the hardware permits
        colors = colors[0 : len(self._cmd_set_rgb)]

        if brightness is None:
            brightness = await self._get_brightness_impl()
            if brightness == 0.0:
                brightness = 80.0

        brightness = scale_brightness(brightness)

        args = []
        for color in colors:
            args.append(to_color(color))
            args.append(brightness)

        return await self._run_command_async(self._cmd_set_rgb[len(colors) - 1], *args)

    async def get_current_effect(self) -> EffectBits:
        """
        Gets the current effects configuration

        :return: EffectBits populated from the hardware
        """
        return await self._get_led_mode()

    async def get_current_colors(self) -> list | None:
        """
        Gets the colors currently in use

        :return: List of RGB tuples
        """
        colors = await self._get_rgb()
        if not colors:
            return None

        return [to_rgb(color) for color in colors]

    def _get_brightness(self) -> float:
        """Sync stub - returns cached value. Use _get_brightness_impl for async."""
        return self._cached_brightness

    async def _get_brightness_impl(self) -> float:
        """The current brightness level (async)."""
        bits = await self._get_led_mode()
        if bits.color_count == 0:
            if bits.on:
                return 100.0
            return 0.0

        value = await self._run_with_result_async(self._cmd_get_rgb[bits.color_count - 1])
        if value is None:
            return 0.0

        self._cached_brightness = scale_brightness(value[3], True)
        return self._cached_brightness

    async def _set_brightness_async(self, level: float) -> bool:
        success = await self._set_brightness_impl(level)
        if success:
            self._cached_brightness = level
        return success

    async def refresh_brightness_async(self) -> float | None:
        async with self._brightness_lock:
            self._cached_brightness = await self._get_brightness_impl()
        return self._cached_brightness

    @property
    def brightness(self):
        if self._suspended:
            return self.preferences.brightness
        return self._cached_brightness

    @brightness.setter
    def brightness(self, level: float):
        self.set_brightness(level)

    def _set_brightness(self, level: float) -> bool:
        """Sync stub - headset uses async. Use _set_brightness_async instead."""
        return False

    async def _set_brightness_impl(self, level: float) -> bool:
        """Set the brightness level (async)."""
        bits = await self._get_led_mode()
        if bits.color_count == 0:
            return False

        value = await self._run_with_result_async(self._cmd_get_rgb[bits.color_count - 1])
        if value is None:
            return False

        scaled_level = scale_brightness(level)

        data = bytearray(value)
        for num in range(bits.color_count):
            data[(num * 4) + 3] = scaled_level

        return await self._run_command_async(self._cmd_set_rgb[bits.color_count - 1], data)
