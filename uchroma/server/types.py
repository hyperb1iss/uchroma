#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name

"""
Common types and enumerations which are used by everything.
"""

from enum import Enum

from uchroma.colorlib import Color


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

    SCROLL_WHEEL = (0x01, {"rgb": True, "has_modes": True})
    MISC = (0x02, {"rgb": True, "has_modes": True})
    BATTERY = (0x03, {"rgb": True})
    LOGO = (0x04, {})
    BACKLIGHT = (0x05, {})
    MACRO = (0x07, {"rgb": True, "has_modes": True})
    GAME = (0x08, {"rgb": True, "has_modes": True})
    PROFILE_RED = (0x0E, {"rgb": True, "color": "red"})
    PROFILE_GREEN = (0x0C, {"rgb": True, "color": "green"})
    PROFILE_BLUE = (0x0D, {"rgb": True, "color": "blue"})

    def __init__(self, hwid, caps):
        self._hardware_id = hwid
        self._rgb = caps.get("rgb", False)
        self._color = Color.NewFromHtml(caps.get("color", "green"))
        self._has_modes = caps.get("has_modes", False)

    @property
    def hardware_id(self) -> int:
        return self._hardware_id

    @property
    def rgb(self) -> bool:
        return self._rgb

    @property
    def default_color(self) -> Color:
        return self._color

    @property
    def has_modes(self) -> bool:
        return self._has_modes
