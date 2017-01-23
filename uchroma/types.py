"""
Common types and enumerations which are used by everything.
"""

from enum import Enum


class BaseCommand(Enum):
    """
    Base class for Command enumerations

    Tuples, in the form of:
        (command_class, command_id, data_length)
    """


# Effects
class FXType(Enum):
    """
    Base class for effect enumerations
    """
    def __init__(self, opcode, description):
        self._opcode = opcode
        self._description = description

    @property
    def opcode(self):
        return self._opcode

    @property
    def description(self):
        return self._description

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.name < other.name
        return NotImplemented



class FX(FXType):
    """
    All known lighting effects.

    Not all effects are available on all devices.
    """
    DISABLE = (0x00, "Disable all effects")
    WAVE = (0x01, "Waves of color")
    REACTIVE = (0x02, "Keys light up when pressed")
    BREATHE = (0x03, "Breathing color effect")
    SPECTRUM = (0x04, "Cycle thru all colors of the spectrum")
    CUSTOM_FRAME = (0x05, "Custom framebuffer")
    STATIC = (0x06, "Static color")
    GRADIENT = (0x0A, "Colors move in a gradient")
    SWEEP = (0x0C, "Color sweeping across the device")
    CIRCLE = (0x0D, "Color pulsing out from center")
    HIGHLIGHT = (0x10, "Highlight rows in succession")
    MORPH = (0x11, "Morphing colors when keys are pressed")
    FIRE = (0x12, "Keys on fire")
    RIPPLE_SOLID = (0x13, "Inverted ripple effect")
    RIPPLE = (0x14, "Ripple effect when keys are pressed")
    SPECTRUM_BLADE = (0x1C, "Specturm effect with extra touchpad effects")
    STARLIGHT = (0x19, "Keys sparkle with color")

    ALIGNMENT = (0xFE, "Alignment test pattern")
    RAINBOW = (0xFF, "Rainbow of hues")

