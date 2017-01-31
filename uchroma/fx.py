import logging

from enum import Enum

from uchroma.color import Splotch
from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.hardware import Hardware, Quirks
from uchroma.led import LED
from uchroma.types import BaseCommand, FX, FXType
from uchroma.util import colorarg, ColorType

from grapefruit import Color


class ExtendedFX(FXType):
    """
    Enumeration of "extended" effect types and command identifiers

    These effects use a different command structure than the standard
    effects. Should not normally be used as part of the API.

    FIXME: This functionality is incomplete and untested
    """
    DISABLE = (0x00, "Disable all effects")
    STATIC = (0x01, "Static color")
    BREATHE = (0x02, "Breathing color effect")
    SPECTRUM = (0x03, "Cycle thru all colors of the spectrum")
    WAVE = (0x04, "Waves of color")
    REACTIVE = (0x05, "Keys light up when pressed")
    STARLIGHT = (0x07, "Keys sparkle with color")
    CUSTOM_FRAME = (0x08, "Custom framebuffer")



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



class FXManager(object):
    """
    Manages device lighting effects
    """


    class Command(BaseCommand):
        """
        Commands used to apply effects

        FIXME: Provide a way to determine the current effect
        """
        SET_EFFECT = (0x03, 0x0A, None)
        SET_EFFECT_EXTENDED = (0x0F, 0x02, None)


    def __init__(self, driver: BaseUChromaDevice):
        """
        :param driver: The UChromaDevice to control
        """
        self._driver = driver
        self._logger = logging.getLogger('uchroma.fxmanager')
        self._report = None


    def _set_effect_basic(self, effect: FX, *args, transaction_id: int=None) -> bool:
        if self._report is None:
            self._report = self._driver.get_report( \
                *FXManager.Command.SET_EFFECT.value, transaction_id=transaction_id)

        self._report.args.clear()
        self._report.args.put_all([effect, *args])

        return self._driver.run_report(self._report)


    def _set_effect_extended(self, effect: ExtendedFX, *args) -> bool:
        return self._driver.run_command(FXManager.Command.SET_EFFECT_EXTENDED, 0x01,
                                        LED.Type.BACKLIGHT, effect, *args, transaction_id=0x3F)


    def _set_effect(self, effect: FXType, *args) -> bool:
        if self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS):
            if effect.name in ExtendedFX.__members__:
                return self._set_effect_extended(ExtendedFX[effect.name], *args)

            return False

        return self._set_effect_basic(effect, *args)


    def disable(self) -> bool:
        """
        Disables all running effects

        :return: True if successful
        """
        return self._set_effect(FX.DISABLE)


    @colorarg
    def static(self, color: ColorType=None) -> bool:
        """
        Sets lighting to a static color

        :param color: The color to apply

        :return: True if successful
        """
        if color is None:
            color = Color.NewFromHtml('green')

        return self._set_effect(FX.STATIC, color)


    def wave(self, direction: Direction=None) -> bool:
        """
        Activates the "wave" effect

        :param direction: Optional direction for the effect, defaults to right

        :return: True if successful
        """
        if direction is None:
            direction = Direction.RIGHT

        return self._set_effect(FX.WAVE, direction)


    def spectrum(self) -> bool:
        """
        Slowly cycles lighting thru all colors of the spectrum

        :return: True if successful
        """
        return self._set_effect(FX.SPECTRUM)


    @colorarg
    def reactive(self, color: ColorType=None, speed: int=None) -> bool:
        """
        Lights up keys when they are pressed

        :param color: Color of lighting when keys are pressed
        :param speed: Speed (1-4) at which the keys should fade out

        :return: True if successful
        """
        if color is None:
            color = Color.NewFromHtml('skyblue')

        if speed is None:
            speed = 1

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_effect(FX.REACTIVE, speed, color)


    @colorarg
    def sweep(self, color: ColorType=None, base_color: ColorType=None,
              direction: Direction=None, speed: int=None, splotch: Splotch=None) -> bool:
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
            direction = Direction.RIGHT

        if splotch is None:
            if base_color is None:
                base_color = Color.NewFromHtml('black')

            if color is None:
                color = Color.NewFromHtml('green')

        else:
            color = splotch.first
            base_color = splotch.second

        if speed is None:
            speed = 15

        return self._set_effect(FX.SWEEP, direction, speed, base_color, color)


    @colorarg
    def morph(self, color: ColorType=None, base_color: ColorType=None,
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
            color = splotch.first
            base_color = splotch.second

        if speed is None:
            speed = 2

        return self._set_effect(FX.MORPH, 0x04, speed, base_color, color)


    @colorarg
    def fire(self, color: ColorType=None, speed: int=None) -> bool:
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

        return self._set_effect(FX.FIRE, 0x01, speed, color)


    @colorarg
    def ripple(self, color: ColorType=None, speed: int=None) -> bool:

        if speed is None:
            speed = 3

        if color is None:
            color = Color.NewFromHtml('green')

        return self._set_effect(FX.RIPPLE, 0x01, speed * 10, color)


    @colorarg
    def ripple_solid(self, color: ColorType=None, speed: int=None) -> bool:

        if speed is None:
            speed = 3

        if color is None:
            color = Color.NewFromHtml('green')

        return self._set_effect(FX.RIPPLE_SOLID, 0x01, speed * 10, color)



    def _set_multi_mode_effect(self, effect: FXType, color1: Color=None, color2: Color=None,
                               speed: int=None, splotch: Splotch=None,
                               speed_range: tuple=None) -> bool:

        if speed_range is None:
            speed_range = (1, 4)

        if speed is not None and (speed < speed_range[0] or speed > speed_range[1]):
            raise ValueError('Speed for effect must be between %d and %d (got: %d)',
                             *speed_range, speed)

        if splotch is not None:
            color1 = splotch.first
            color2 = splotch.second

        mode = None

        if color1 is not None and color2 is not None:
            mode = Mode.DUAL.value
        elif color1 is not None:
            mode = Mode.SINGLE.value
        else:
            mode = Mode.RANDOM.value

        args = [mode]

        if speed is not None:
            args.append(speed)

        if color1 is not None:
            args.append(color1)

        if color2 is not None:
            args.append(color2)

        return self._set_effect(effect, *args)


    @colorarg
    def starlight(self, color1: ColorType=None, color2: ColorType=None,
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

        return self._set_multi_mode_effect(FX.STARLIGHT, color1, color2,
                                           speed=speed, splotch=splotch)


    @colorarg
    def breathe(self, color1: ColorType=None, color2: ColorType=None, splotch: Splotch=None) -> bool:
        """
        Activate the "breathe" effect. Colors pulse in and out.

        This effect allows up to two (optional) colors. If no colors are
        specified, random colors will be used.

        :param color1: First color
        :param color2: Second color
        :param splotch: Predefined color pair, invalid when color1/color2 is supplied

        :return: True if successful
        """
        return self._set_multi_mode_effect(FX.BREATHE, color1, color2, splotch=splotch)


    def custom_frame(self) -> bool:
        """
        Activate the custom frame currently in the device memory

        Called by the Frame class when commit() is called.

        :return: True if successful
        """
        varstore = 0x01
        tid = None

        # FIXME: This doesn't work.
        if self._driver.device_type == Hardware.Type.MOUSE:
            varstore = 0x00
            tid = 0x80
        return self._set_effect(FX.CUSTOM_FRAME, varstore)


    @staticmethod
    def _hue_gradient(start, length):
        step = 360 / length
        return [Color.NewFromHsv((start + (step * x)) % 360, 1, 1) for x in range(0, length)]


    def rainbow(self, stagger: int=None, length: int=None) -> bool:
        """
        Show a rainbow of colors across the device

        Uses the Frame interface. Will change when device characteristics
        are implemented.

        :return: True if successful
        """
        if not self._driver.has_matrix:
            return False

        if stagger is None:
            stagger = 4

        if length is None:
            length = 75

        frame = self._driver.frame_control

        data = []
        gradient = FXManager._hue_gradient(length, frame.width + (frame.height * stagger))
        for row in range(0, frame.height):
            data.append([gradient[(row * stagger) + col] for col in range(0, frame.width)])

        frame.put_all(data)
        frame.commit()

        return True


    def alignment(self, position: tuple=None) -> bool:
        first = 'red'
        single = 'white'
        colors = ['yellow', 'green', 'purple', 'blue']

        frame = self._driver.frame_control

        for row in range(0, frame.height):
            for col in range(0, frame.width):
                if col == 0:
                    color = first
                else:
                    color = colors[int((col - 1) % len(colors))]
                frame.put(row, col, color)

        if position is not None and len(position) == 2:
            frame.put(position[0], position[1], single)
            frame.debug_opts['debug_position'] = tuple(position)

        frame.commit()

        return True
