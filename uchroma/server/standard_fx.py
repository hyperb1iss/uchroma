#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=no-member, invalid-name

from enum import Enum

from traitlets import Bool, Int, Unicode

from uchroma.color import ColorUtils
from uchroma.traits import ColorSchemeTrait, ColorTrait, UseEnumCaseless

from .effects import Effects
from .fx import BaseFX, FXModule
from .hardware import Hardware, Quirks
from .report_utils import put_arg
from .types import BaseCommand, LEDType


class FX(Enum):
    """
    Legacy lighting effect IDs (Command Class 0x03).

    Not all effects are available on all devices. See Effects registry
    in effects.py for the authoritative source of effect ID mappings.

    Note: These IDs are for the legacy protocol only. Devices with
    EXTENDED_FX_CMDS quirk use different IDs (see ExtendedFX enum).
    """

    DISABLE = 0x00
    WAVE = 0x01
    REACTIVE = 0x02
    BREATHE = 0x03
    SPECTRUM = 0x04
    CUSTOM_FRAME = 0x05
    STATIC = 0x06
    GRADIENT = 0x0A
    SWEEP = 0x0C
    CIRCLE = 0x0D
    HIGHLIGHT = 0x10
    MORPH = 0x11
    FIRE = 0x12
    RIPPLE_SOLID = 0x13
    RIPPLE = 0x14
    SPECTRUM_BLADE = 0x1C
    STARLIGHT = 0x19

    ALIGNMENT = 0xFE
    RAINBOW = 0xFF


class ExtendedFX(Enum):
    """
    Extended lighting effect IDs (Command Class 0x0F).

    These effects use a different command structure than the standard
    effects and are used by devices with EXTENDED_FX_CMDS quirk.

    See Effects registry in effects.py for the authoritative source
    of effect ID mappings. Should not normally be used as part of the API.
    """

    DISABLE = 0x00
    STATIC = 0x01
    BREATHE = 0x02
    SPECTRUM = 0x03
    WAVE = 0x04
    REACTIVE = 0x05
    STARLIGHT = 0x07
    CUSTOM_FRAME = 0x08


# Modes for the Wave effect
# The "chase" modes add a circular spin around the trackpad (if supported)
class Direction(Enum):
    """
    Enumeration of directions and arguments for some animated effects
    which pan across the device. The "chase" variants are only available
    on devices with an illuminated trackpad such as the Blade Pro, and
    produce a rotating animation around the trackpad.
    """

    RIGHT = 1
    LEFT = 2


# Modes for starlight and breathe effects
class Mode(Enum):
    """
    Enumeration of modes and arguments for some animated effects which
    accept a variable number of colors.
    """

    RANDOM = 0
    SINGLE = 1
    DUAL = 2


class StandardFX(FXModule):
    """
    Manages device lighting effects
    """

    class Command(BaseCommand):
        """
        Commands used to apply effects

        """

        SET_EFFECT = (0x03, 0x0A, None)
        SET_EFFECT_EXTENDED = (0x0F, 0x02, None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._report = None

    async def _set_effect_basic(
        self, effect: FX, *args, transaction_id: int | None = None
    ) -> bool:
        if self._report is None:
            self._report = self._driver.get_report(
                *StandardFX.Command.SET_EFFECT.value, transaction_id=transaction_id
            )

        self._report.clear()
        put_arg(self._report, effect.value)
        for arg in args:
            put_arg(self._report, arg)

        success, _ = await self._driver.run_report(self._report)
        return success

    async def _set_effect_extended(self, effect: ExtendedFX, *args) -> bool:
        # Per OpenRazer: custom_frame uses NOSTORE (0x00) and ZERO_LED (0x00)
        # Other effects use VARSTORE (0x01) and BACKLIGHT_LED
        if effect == ExtendedFX.CUSTOM_FRAME:
            varstore = 0x00  # NOSTORE
            led_id = 0x00  # ZERO_LED
        else:
            varstore = 0x01  # VARSTORE
            led_id = LEDType.BACKLIGHT.hardware_id

        return await self._driver.run_command(
            StandardFX.Command.SET_EFFECT_EXTENDED,
            varstore,
            led_id,
            effect.value,
            *args,
        )

    async def set_effect(self, effect: FX | ExtendedFX, *args) -> bool:
        """Apply a lighting effect to the device.

        Uses the Effects registry to determine protocol support.
        """
        uses_extended = self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS)

        # Validate effect is supported on this protocol using Effects registry
        if not Effects.supports_protocol(effect.name, uses_extended):
            self._driver.logger.warning(
                f"Effect '{effect.name}' not supported on {'extended' if uses_extended else 'legacy'} protocol"
            )
            return False

        if uses_extended:
            return await self._set_effect_extended(ExtendedFX[effect.name], *args)
        return await self._set_effect_basic(FX[effect.name], *args)

    class DisableFX(BaseFX):
        description = Unicode("Disable all effects")

        async def apply(self) -> bool:
            """
            Disables all running effects

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.DISABLE)

    class StaticFX(BaseFX):
        description = Unicode("Static color")
        color = ColorTrait(default_value="green").tag(config=True)

        async def apply(self) -> bool:
            """
            Sets lighting to a static color

            :param color: The color to apply

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.STATIC, self.color)

    class WaveFX(BaseFX):
        description = Unicode("Waves of color")
        direction = UseEnumCaseless(enum_class=Direction, default_value=Direction.RIGHT).tag(
            config=True
        )
        trackpad_effect = Bool(default_value=False).tag(config=True)

        async def apply(self) -> bool:
            """
            Activates the "wave" effect

            :param direction: Optional direction for the effect, defaults to right

            :return: True if successful
            """
            direction = self.direction.value

            if self.trackpad_effect:
                if self.direction == Direction.LEFT:
                    direction = 0x03
                elif self.direction == Direction.RIGHT:
                    direction = 0x04

            return await self._fxmod.set_effect(FX.WAVE, direction)

    class SpectrumFX(BaseFX):
        description = Unicode("Cycle thru all colors of the spectrum")

        async def apply(self) -> bool:
            """
            Slowly cycles lighting thru all colors of the spectrum

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.SPECTRUM)

    class ReactiveFX(BaseFX):
        description = Unicode("Keys light up when pressed")
        color = ColorTrait(default_value="skyblue").tag(config=True)
        speed = Int(1, min=1, max=4).tag(config=True)

        async def apply(self) -> bool:
            """
            Lights up keys when they are pressed

            :param color: Color of lighting when keys are pressed
            :param speed: Speed (1-4) at which the keys should fade out

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.REACTIVE, self.speed, self.color)

    class SweepFX(BaseFX):
        description = Unicode("Colors sweep across the device")
        color = ColorTrait(default_value="green").tag(config=True)
        base_color = ColorTrait().tag(config=True)
        speed = Int(default_value=15, min=1, max=30).tag(config=True)
        direction = UseEnumCaseless(enum_class=Direction, default_value=Direction.RIGHT).tag(
            config=True
        )

        async def apply(self) -> bool:
            """
            Produces colors which sweep across the device

            :param color: The color to sweep with (defaults to light blue)
            :param base_color: The base color for the effect (defaults to black)
            :param direction: The direction for the sweep
            :param speed: Speed of the sweep
            :param preset: Predefined color pair to use. Invalid with color/base_color.

            :return: True if successful
            """
            return await self._fxmod.set_effect(
                FX.SWEEP, self.direction, self.speed, self.base_color, self.color
            )

    class MorphFX(BaseFX):
        description = Unicode("Morphing colors when keys are pressed")
        color = ColorTrait(default_value="magenta").tag(config=True)
        base_color = ColorTrait(default_value="darkblue").tag(config=True)
        speed = Int(default_value=2, min=1, max=4).tag(config=True)

        async def apply(self) -> bool:
            """
            A "morphing" color effect when keys are pressed

            :param color: The color when keys are pressed (defaults to magenta)
            :param base_color: The base color for the effect (defaults to blue)
            :param speed: Speed of the sweep
            :param preset: Predefined color pair to use. Invalid with color/base_color.

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.MORPH, 0x04, self.speed, self.color, self.base_color)

    class FireFX(BaseFX):
        description = Unicode("Keys on fire")
        color = ColorTrait(default_value="red").tag(config=True)
        speed = Int(default_value=0x40, min=0x10, max=0x80).tag(config=True)

        async def apply(self) -> bool:
            """
            Animated fire!

            :param color: Color scheme of the fire
            :param speed: Speed of the fire

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.FIRE, 0x01, self.speed, self.color)

    class RippleFX(BaseFX):
        description = Unicode("Ripple effect when keys are pressed")
        color = ColorTrait(default_value="green").tag(config=True)
        speed = Int(default_value=3, min=1, max=8).tag(config=True)

        async def apply(self) -> bool:
            return await self._fxmod.set_effect(FX.RIPPLE, 0x01, self.speed * 10, self.color)

    class RippleSolidFX(BaseFX):
        description = Unicode("Ripple effect on a solid background")
        color = ColorTrait(default_value="green").tag(config=True)
        speed = Int(default_value=3, min=1, max=8).tag(config=True)

        async def apply(self) -> bool:
            return await self._fxmod.set_effect(FX.RIPPLE_SOLID, 0x01, self.speed * 10, self.color)

    class StarlightFX(BaseFX):
        description = Unicode("Keys sparkle with color")
        colors = ColorSchemeTrait(minlen=0, maxlen=2).tag(config=True)
        speed = Int(default_value=1, min=1, max=4).tag(config=True)

        async def apply(self) -> bool:
            """
            Activate the "starlight" effect. Colors sparkle across the device.

            This effect allows up to two (optional) colors. If no colors are
            specified, random colors will be used.

            :param color1: First color
            :param color2: Second color
            :param speed: Speed of the effect
            :param preset: Predefined color pair, invalid when color1/color2 is supplied

            :return: True if successful
            """
            return await self._fxmod.set_effect(
                FX.STARLIGHT, Mode(len(self.colors)), self.speed, *self.colors
            )

    class BreatheFX(BaseFX):
        description = Unicode("Colors pulse in and out")
        colors = ColorSchemeTrait(minlen=0, maxlen=2).tag(config=True)

        async def apply(self) -> bool:
            """
            Activate the "breathe" effect. Colors pulse in and out.

            This effect allows up to two (optional) colors. If no colors are
            specified, random colors will be used.

            :param color1: First color
            :param color2: Second color
            :param preset: Predefined color pair, invalid when color1/color2 is supplied

            :return: True if successful
            """
            return await self._fxmod.set_effect(FX.BREATHE, Mode(len(self.colors)), *self.colors)

    class CustomFrameFX(BaseFX):
        description = Unicode("Display custom frame")
        hidden = Bool(True, read_only=True)

        async def apply(self) -> bool:
            """
            Activate the custom frame currently in the device memory

            Called by the Frame class when commit() is called.

            :return: True if successful
            """
            varstore = 0x01

            # FIXME: This doesn't work.
            if self._driver.device_type == Hardware.Type.MOUSE:
                varstore = 0x00
            return await self._fxmod.set_effect(FX.CUSTOM_FRAME, varstore)

    class RainbowFX(BaseFX):
        description = Unicode("Rainbow of hues")
        stagger = Int(default_value=4, min=0, max=100).tag(config=True)
        length = Int(default_value=75, min=20, max=360).tag(config=True)

        async def apply(self) -> bool:
            """
            Show a rainbow of colors across the device

            Uses the Frame interface. Will change when device characteristics
            are implemented.

            :return: True if successful
            """
            frame = self._driver.frame_control

            layer = frame.create_layer()

            data = []
            gradient = ColorUtils.hue_gradient(
                self.length, layer.width + (layer.height * self.stagger)
            )
            for row in range(layer.height):
                data.append([gradient[(row * self.stagger) + col] for col in range(layer.width)])

            layer.put_all(data)
            await frame.commit([layer])

            return True

    class AlignmentFX(BaseFX):
        description = Unicode("Alignment test pattern")
        hidden = Bool(True, read_only=True)
        cur_row = Int(min=0, default_value=0)
        cur_col = Int(min=0, default_value=0)

        async def apply(self) -> bool:
            first = "red"
            single = "white"
            colors = ["yellow", "green", "purple", "blue"]

            frame = self._driver.frame_control
            layer = frame.create_layer()

            for row in range(layer.height):
                for col in range(layer.width):
                    if col == 0:
                        color = first
                    else:
                        color = colors[int((col - 1) % len(colors))]
                    layer.put(row, col, color)

            layer.put(self.cur_row, self.cur_col, single)
            frame.debug_opts["debug_position"] = (self.cur_row, self.cur_col)

            await frame.commit([layer])

            return True
