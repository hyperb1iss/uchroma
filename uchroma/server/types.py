# pylint: disable=invalid-name
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


class LEDType(Enum):
    """
    Enumeration of LED types

    All types not available on all devices.
    """
    SCROLL_WHEEL = 0x01
    BATTERY = 0x03
    LOGO = 0x04
    BACKLIGHT = 0x05
    MACRO = 0x07
    GAME = 0x08
    PROFILE_RED = 0x0E
    PROFILE_GREEN = 0x0C
    PROFILE_BLUE = 0x0D
