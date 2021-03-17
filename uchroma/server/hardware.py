#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

# pylint: disable=invalid-name, no-member

import os

from collections import OrderedDict
from datetime import datetime
from enum import Enum, IntEnum
from typing import NamedTuple

import ruamel.yaml as yaml

from .config import Configuration, FlowSequence, LowerCaseSeq, represent_flow_seq
from .types import LEDType


RAZER_VENDOR_ID = 0x1532


class Quirks(IntEnum):
    """
    Various "quirks" that are found across hardware models.
    """

    # Always use transaction code 0x3F
    TRANSACTION_CODE_3F = 1

    # Use "extended" commands
    EXTENDED_FX_CMDS = 2

    # Control device brightness with the scroll wheel LED
    SCROLL_WHEEL_BRIGHTNESS = 3

    # Device has charge and dock controls
    WIRELESS = 4

    # Needs transaction code 0x80 for custom frame data
    CUSTOM_FRAME_80 = 5

    # Control device brightness with the logo LED
    LOGO_LED_BRIGHTNESS = 6

    # Device has individual "profile" LEDs
    PROFILE_LEDS = 7

    # Device only supports spectrum effect on the backlight LED
    BACKLIGHT_LED_FX_ONLY = 8


# Marker types for YAML output
_Point = NamedTuple('_Point', [('y', int), ('x', int)])

class Point(_Point):
    def __repr__(self):
        return '(%s, %s)' % (self.y, self.x)


class PointList(FlowSequence):
    def __new__(cls, args):
        if isinstance(args, list):
            if isinstance(args[0], int) and len(args) == 2:
                return Point(args[0], args[1])
            if isinstance(args[0], list):
                return cls([cls(arg) for arg in args])
        return super(PointList, cls).__new__(cls, args)


class KeyMapping(OrderedDict):
    def __setitem__(self, key, value, **kwargs):
        super().__setitem__(key, PointList(value), **kwargs)

_KeyFixupMapping = NamedTuple('_KeyFixupMapping', [('copy', PointList),
                                                   ('delete', PointList),
                                                   ('insert', PointList)])
_KeyFixupMapping.__new__.__defaults__ = (None,) * len(_KeyFixupMapping._fields)
class KeyFixupMapping(_KeyFixupMapping):
    def _asdict(self):
        return OrderedDict([x for x in zip(self._fields, self) if x[1] is not None])

Zone = NamedTuple('Zone', [('name', str), ('coord', Point), ('width', int), ('height', int)])

class HexQuad(int):
    pass



# Configuration
BaseHardware = Configuration.create("BaseHardware", [ \
    ('name', str),
    ('manufacturer', str),
    ('type', 'Type'),
    ('vendor_id', HexQuad),
    ('product_id', HexQuad),
    ('dimensions', Point),
    ('supported_fx', LowerCaseSeq),
    ('supported_leds', LEDType),
    ('quirks', Quirks),
    ('zones', Zone),
    ('key_mapping', KeyMapping),
    ('key_fixup_mapping', KeyFixupMapping),
    ('key_row_offsets', tuple),
    ('macro_keys', OrderedDict),
    ('is_wireless', bool),
    ('revision', int),
    ('assets', dict)], yaml_name=u'!device-config')


class Hardware(BaseHardware):
    """
    Static hardware configuration data

    Loaded by Configuration from YAML.
    """

    class Type(Enum):
        HEADSET = 'Headset'
        KEYBOARD = 'Keyboard'
        KEYPAD = 'Keypad'
        LAPTOP = 'Laptop'
        MOUSE = 'Mouse'
        MOUSEPAD = 'Mousepad'

    @property
    def has_matrix(self) -> bool:
        """
        True if the device has an addressable key matrix
        """
        return self.dimensions is not None and self.dimensions.x > 1 and self.dimensions.y > 1


    def has_quirk(self, *quirks) -> bool:
        """
        True if quirk is required for the device

        :param: quirks The quirks to check (varargs)

        :return: True if the quirk is required
        """
        if self.quirks is None:
            return False

        for quirk in quirks:
            if isinstance(self.quirks, (list, tuple)) and quirk in self.quirks:
                return True
            if self.quirks == quirk:
                return True

        return False


    @classmethod
    def get_type(cls, hw_type) -> 'Hardware':
        if hw_type is None:
            return None

        config_path = os.path.join(os.path.dirname(__file__), 'data')
        yaml_path = os.path.join(config_path, '%s.yaml' % hw_type.name.lower())

        config = cls.load_yaml(yaml_path)
        assert config is not None

        return config


    @classmethod
    def _get_device(cls, product_id: int, hw_type) -> 'Hardware':
        if product_id is None:
            return None

        config = cls.get_type(hw_type)

        result = config.search('product_id', product_id)
        if not result:
            return None

        if isinstance(result, list) and len(result) == 1:
            return result[0]

        return result


    @classmethod
    def get_device(cls, product_id: int, hw_type=None) -> 'Hardware':
        if hw_type is not None:
            return cls._get_device(product_id, hw_type)

        for hw in Hardware.Type:
            device = cls._get_device(product_id, hw)
            if device is not None:
                return device

        return None


    def _yaml_header(self) -> str:
        header = '#\n#  uChroma device configuration\n#\n'
        if self.name is not None:
            header += '#  Model: %s (%s)\n' % (self.name, self.type.value)
        elif self.type is not None:
            header += '#  Type: %s\n' % self.type.name.title()
        header += '#  Updated on: %s\n' % datetime.now().isoformat(' ')
        header += '#\n'

        return header


# YAML library configuration
def represent_hex_quad(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:int', '0x%04x' % data)

def represent_namedtuple(dumper, data):
    return dumper.represent_ordereddict(data._asdict())

yaml.RoundTripDumper.add_representer(HexQuad, represent_hex_quad)
yaml.RoundTripDumper.add_representer(KeyFixupMapping, represent_namedtuple)
yaml.RoundTripDumper.add_representer(Point, represent_flow_seq)
yaml.RoundTripDumper.add_representer(Zone, represent_flow_seq)
