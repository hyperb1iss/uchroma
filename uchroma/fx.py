from enum import Enum

from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.led import LED

from grapefruit import Color


class Splotch(Enum):
    """
    Predefined color pairs
    """
    EARTH = (Color.NewFromHtml('green'), Color.NewFromHtml('#8b4513'))
    AIR = (Color.NewFromHtml('white'), Color.NewFromHtml('skyblue'))
    FIRE = (Color.NewFromHtml('red'), Color.NewFromHtml('orange'))
    WATER = (Color.NewFromHtml('blue'), Color.NewFromHtml('white'))
    SUN = (Color.NewFromHtml('white'), Color.NewFromHtml('yellow'))
    MOON = (Color.NewFromHtml('grey'), Color.NewFromHtml('cyan'))
    HOTPINK = (Color.NewFromHtml('hotpink'), Color.NewFromHtml('purple'))


class FX(object):
    """
    Manages device lighting effects
    """

    # Effects
    class Type(Enum):
        """
        Enumeration of effect types and command identifiers

        Not all effects are available on all devices.
        TODO: provide hardware-specific capabilities
        """
        DISABLE = 0x00
        WAVE = 0x01
        REACTIVE = 0x02
        BREATHE = 0x03
        SPECTRUM = 0x04
        CUSTOM_FRAME = 0x05
        STATIC_COLOR = 0x06
        GRADIENT = 0x0A
        WASH = 0x0C
        CIRCLE = 0x0D
        HIGHLIGHT = 0x10
        MORPH = 0x11
        FIRE = 0x12
        RIPPLE_SOLID = 0x13
        RIPPLE = 0x14
        STARLIGHT = 0x19
        SPECTRUM_BLADE = 0x1C
        RAINBOW = 0xFF


    class ExtendedType(Enum):
        """
        Enumeration of "extended" effect types and command identifiers

        Should not normally be used as part of the API.

        FIXME: This functionality is incomplete and untested
        """
        DISABLE = 0x00
        STATIC_COLOR = 0x01
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
        RIGHT = 0
        LEFT = 2
        LEFT_CHASE = 3
        RIGHT_CHASE = 4


    # Modes for starlight and breathe effects
    class Mode(Enum):
        """
        Enumeration of modes and arguments for some animated effects which
        accept a variable number of colors.
        """
        RANDOM = 0
        SINGLE = 1
        DUAL = 2


    class Command(BaseCommand):
        """
        Commands used to apply effects

        FIXME: Provide a way to determine the current effect
        """
        SET_EFFECT = (0x03, 0x0A, None)
        SET_CUSTOM_FRAME_DATA = (0x03, 0x0B, None)
        SET_EFFECT_EXTENDED = (0x0F, 0x02, None)


    def __init__(self, driver: BaseUChromaDevice):
        """
        :param driver: The UChromaDevice to control
        """
        self._driver = driver


    def _set_effect(self, effect: Type, *args) -> bool:
        return self._driver.run_command(FX.Command.SET_EFFECT, effect, *args)


    def _set_effect_extended(self, effect: ExtendedType, *args) -> bool:
        return self._driver.run_command(FX.Command.SET_EFFECT_EXTENDED, 0x01,
                                        LED.Type.BACKLIGHT, effect, *args, transaction_id=0x3F)


    def disable(self) -> bool:
        """
        Disables all running effects

        :return: True if successful
        """
        return self._set_effect(FX.Type.DISABLE)


    def static_color(self, color: Color=None) -> bool:
        """
        Sets lighting to a static color

        :param color: The color to apply

        :return: True if successful
        """
        if color is None:
            color = Color.NewFromHtml('white')

        return self._set_effect(FX.Type.STATIC_COLOR, color)


    def wave(self, direction: Direction=None) -> bool:
        """
        Activates the "wave" effect

        :param direction: Optional direction for the effect, defaults to right

        :return: True if successful
        """
        if direction is None:
            direction = FX.Direction.RIGHT

        return self._set_effect(FX.Type.WAVE, direction)


    def spectrum(self) -> bool:
        """
        Slowly cycles lighting thru all colors of the spectrum

        :return: True if successful
        """
        return self._set_effect(FX.Type.SPECTRUM)


    def reactive(self, color: Color=None, speed: int=1) -> bool:
        """
        Lights up keys when they are pressed

        :param color: Color of lighting when keys are pressed
        :param speed: Speed (1-4) at which the keys should fade out

        :return: True if successful
        """
        if color is None:
            color = Color.NewFromHtml('skyblue')

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_effect(FX.Type.REACTIVE, speed, color)


    def sweep(self, color: Color=None, base_color: Color=None, direction: Direction=None,
              speed: int=None, splotch: Splotch=None) -> bool:
        """
        Produces colors which sweep across the device

        :param color: The color to sweep with (defaults to light blue)
        :param base_color: The base color for the effect (defaults to black)
        :param direction: The direction for the sweep
        :param speed: Speed of the sweep
        :param splotch: Predefined color pair to use. Invalid with color/base_color.

        :return: True if successful
        """
        if direction is None:
            direction = FX.Direction.RIGHT

        if splotch is None:
            if base_color is None:
                base_color = Color.NewFromHtml('black')

            if color is None:
                color = Color.NewFromHtml('skyblue')

        else:
            color = splotch.value[0]
            base_color = splotch.value[1]

        if speed is None:
            speed = 15

        return self._set_effect(FX.Type.WASH, direction, speed, base_color, color)


    def morph(self, color: Color=None, base_color: Color=None,
              speed: int=None, splotch: Splotch=None) -> bool:
        """
        A "morphing" color effect when keys are pressed

        :param color: The color when keys are pressed (defaults to magenta)
        :param base_color: The base color for the effect (defaults to blue)
        :param speed: Speed of the sweep
        :param splotch: Predefined color pair to use. Invalid with color/base_color.

        :return: True if successful
        """
        if splotch is None:
            if base_color is None:
                base_color = Color.NewFromHtml('blue')

            if color is None:
                color = Color.NewFromHtml('magenta')

        else:
            color = splotch.value[0]
            base_color = splotch.value[1]

        if speed is None:
            speed = 2

        return self._set_effect(FX.Type.MORPH, 0x04, speed, base_color, color)


    def fire(self, color: Color=None, speed: int=None) -> bool:
        """
        Animated fire!

        :param color: Color scheme of the fire
        :param speed: Speed of the fire

        :return: True if successful
        """
        if color is None:
            color = Color.NewFromHtml('red')

        if speed is None:
            speed = 0x40

        return self._set_effect(FX.Type.FIRE, 0x01, speed, color)


    def _set_multi_mode_effect(self, effect: Type, color1: Color=None, color2: Color=None,
                               speed: int=None, splotch: Splotch=None) -> bool:
        if speed is not None and (speed < 1 or speed > 4):
            raise ValueError('Speed for effect must be between 1 and 4 (got: %d)', speed)

        if splotch is not None:
            color1 = splotch.value[0]
            color2 = splotch.value[1]

        mode = None

        if color1 is not None and color2 is not None:
            mode = FX.Mode.DUAL.value
        elif color1 is not None:
            mode = FX.Mode.SINGLE.value
        else:
            mode = FX.Mode.RANDOM.value

        args = [mode]

        if speed is not None:
            args.append(speed)

        if color1 is not None:
            args.append(color1)

        if color2 is not None:
            args.append(color2)

        return self._set_effect(effect, *args)


    def starlight(self, color1: Color=None, color2: Color=None,
                  speed: int=None, splotch: Splotch=None) -> bool:
        """
        Activate the "starlight" effect. Colors sparkle across the device.

        This effect allows up to two (optional) colors. If no colors are
        specified, random colors will be used.

        :param color1: First color
        :param color2: Second color
        :param speed: Speed of the effect
        :param splotch: Predefined color pair, invalid when color1/color2 is supplied

        :return: True if successful
        """
        if speed is None:
            speed = 1

        return self._set_multi_mode_effect(FX.Type.STARLIGHT, color1, color2,
                                           speed=speed, splotch=splotch)


    def breathe(self, color1: Color=None, color2: Color=None, splotch: Splotch=None) -> bool:
        """
        Activate the "breathe" effect. Colors pulse in and out.

        This effect allows up to two (optional) colors. If no colors are
        specified, random colors will be used.

        :param color1: First color
        :param color2: Second color
        :param splotch: Predefined color pair, invalid when color1/color2 is supplied

        :return: True if successful
        """
        return self._set_multi_mode_effect(FX.Type.BREATHE, color1, color2, splotch=splotch)


    def custom_frame(self) -> bool:
        """
        Activate the custom frame currently in the device memory

        Called by the Frame class when flip() is called.

        :return: True if successful
        """
        return self._set_effect(FX.Type.CUSTOM_FRAME, 0x01)


    @staticmethod
    def _hue_gradient(start, length):
        step = 360 / length
        return [Color.NewFromHsv((start + (step * x)) % 360, 1, 1) for x in range(0, length)]


    def rainbow(self, width=24, height=6, stagger=30) -> bool:
        """
        Show a rainbow of colors across the device

        Uses the Frame interface. Will change when device characteristics
        are implemented.

        :return: True if successful
        """
        frame = self._driver.get_frame_control(width, height)
        gradient = FX._hue_gradient(75, width + (height * stagger))
        for row in range(0, height):
            for col in range(0, width):
                frame.put(row, col, gradient[(row * stagger) + col])

        frame.flip()
