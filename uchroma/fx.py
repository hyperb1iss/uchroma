from enum import Enum

from uchroma.color import RGB


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


    def static_color(self, rgb=None):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        return self._set_effect(FX.Type.STATIC_COLOR, rgb)


    def wave(self, direction=Direction.RIGHT):
        return self._set_effect(FX.Type.WAVE, direction)


    def spectrum(self):
        return self._set_effect(FX.Type.SPECTRUM)


    def reactive(self, rgb=None, speed=1):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_effect(FX.Type.REACTIVE, speed, rgb.red, rgb.green, rgb.blue)


    def _set_multi_mode_effect(self, effect, rgb1=None, rgb2=None, speed=None, splotch=None):
        if speed is not None and (speed < 1 or speed > 4):
            raise ValueError('Speed for effect must be between 1 and 4 (got: %d)', speed)

        if splotch is not None:
            rgb1 = splotch.value[0]
            rgb2 = splotch.value[1]

        mode = None

        if rgb1 is not None and rgb2 is not None:
            mode = FX.Mode.DUAL.value
        elif rgb1 is not None:
            mode = FX.Mode.SINGLE.value
        else:
            mode = FX.Mode.RANDOM.value

        args = [mode]

        if speed is not None:
            args.append(speed)

        if rgb1 is not None:
            args.append(rgb1)

        if rgb2 is not None:
            args.append(rgb2)

        self._set_effect(effect, *args)


    def starlight(self, rgb1=None, rgb2=None, speed=1, splotch=None):
        return self._set_multi_mode_effect(FX.Type.STARLIGHT, rgb1, rgb2, speed=speed, splotch=splotch)


    def breathe(self, rgb1=None, rgb2=None, splotch=None):
        return self._set_multi_mode_effect(FX.Type.BREATHE, rgb1, rgb2, splotch=splotch)


    def custom_frame(self):
        return self._set_effect(FX.Type.CUSTOM_FRAME, 0x01)

