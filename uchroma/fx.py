from enum import Enum

from grapefruit import Color


class FX(object):

    # Effects
    class Type(Enum):
        DISABLE = 0x00
        WAVE = 0x01
        REACTIVE = 0x02
        BREATHE = 0x03
        SPECTRUM = 0x04
        CUSTOM_FRAME = 0x05
        STATIC_COLOR = 0x06
        STARLIGHT = 0x19


    # Modes for the Wave effect
    # The "chase" modes add a circular spin around the trackpad (if supported)
    class Direction(Enum):
        RIGHT = 0
        LEFT = 2
        LEFT_CHASE = 3
        RIGHT_CHASE = 4


    # Modes for starlight and breathe effects
    class Mode(Enum):
        RANDOM = 0
        SINGLE = 1
        DUAL = 2


    class Command(Enum):
        # device commands, class 3
        SET_EFFECT = (0x03, 0x0A, None)
        SET_CUSTOM_FRAME_DATA = (0x03, 0x0B, None)


    def __init__(self, driver):
        self._driver = driver


    def _set_effect(self, effect, *args):
        return self._driver.run_command(FX.Command.SET_EFFECT, effect, *args)


    def disable(self):
        return self._set_effect(FX.Type.DISABLE)


    def static_color(self, color=None):
        if color is None:
            color = Color.NewFromHtml('white')

        return self._set_effect(FX.Type.STATIC_COLOR, color)


    def wave(self, direction=Direction.RIGHT):
        return self._set_effect(FX.Type.WAVE, direction)


    def spectrum(self):
        return self._set_effect(FX.Type.SPECTRUM)


    def reactive(self, color=None, speed=1):
        if color is None:
            color = Color.NewFromHtml('skyblue')

        rgb = color.intTuple

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_effect(FX.Type.REACTIVE, speed, rgb[0], rgb[1], rgb[2])


    def _set_multi_mode_effect(self, effect, color1=None, color2=None, speed=None, splotch=None):
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

        self._set_effect(effect, *args)


    def starlight(self, color1=None, color2=None, speed=1, splotch=None):
        return self._set_multi_mode_effect(FX.Type.STARLIGHT, color1, color2, speed=speed, splotch=splotch)


    def breathe(self, color1=None, color2=None, splotch=None):
        return self._set_multi_mode_effect(FX.Type.BREATHE, color1, color2, splotch=splotch)


    def custom_frame(self):
        return self._set_effect(FX.Type.CUSTOM_FRAME, 0x01)


# Splotches
class Splotch(Enum):
    EARTH = (Color.NewFromHtml('green'), Color.NewFromHtml('#8b4513'))
    AIR = (Color.NewFromHtml('white'), Color.NewFromHtml('skyblue'))
    FIRE = (Color.NewFromHtml('red'), Color.NewFromHtml('orange'))
    WATER = (Color.NewFromHtml('blue'), Color.NewFromHtml('white'))
    SUN = (Color.NewFromHtml('white'), Color.NewFromHtml('yellow'))
    MOON = (Color.NewFromHtml('grey'), Color.NewFromHtml('cyan'))
    HOTPINK = (Color.NewFromHtml('hotpink'), Color.NewFromHtml('purple'))
