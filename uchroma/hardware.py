# pylint: disable=invalid-name, no-member
import os

from collections import OrderedDict
from enum import Enum, IntEnum
from typing import NamedTuple

import ruamel.yaml as yaml

from uchroma.config import Configuration


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
class FlowSequence(tuple):
    pass

class _PointList(object):
    def __new__(cls, args):
        if isinstance(args, list):
            if isinstance(args[0], int) and len(args) == 2:
                return Point(y=args[0], x=args[1])
            elif isinstance(args[0], list):
                return _PointList([PointList(arg) for arg in args])
        return tuple(args)

class PointList(FlowSequence, _PointList):
    pass

class KeyMapping(OrderedDict):
    def __setitem__(self, key, value):
        super().__setitem__(key, PointList(value))

class BlockMapping(OrderedDict):
    pass


_KeyFixupMapping = NamedTuple('_KeyFixupMapping', [('copy', PointList),
                                                   ('delete', PointList),
                                                   ('insert', PointList)])
_KeyFixupMapping.__new__.__defaults__ = (None,) * len(_KeyFixupMapping._fields)
class KeyFixupMapping(_KeyFixupMapping):
    def _asdict(self):
        return BlockMapping([x for x in zip(self._fields, self) if x[1] is not None])

Point = NamedTuple('Point', [('y', int), ('x', int)])

Zone = NamedTuple('Zone', [('name', str), ('coord', Point), ('width', int), ('height', int)])

class HexQuad(int):
    pass



# Configuration
BaseHardware = Configuration.create("Hardware", [ \
    ('name', str),
    ('manufacturer', str),
    ('type', 'Type'),
    ('vendor_id', HexQuad),
    ('product_id', HexQuad),
    ('dimensions', Point),
    ('supported_fx', 'FX'),
    ('quirks', Quirks),
    ('zones', Zone),
    ('key_mapping', KeyMapping),
    ('key_fixup_mapping', KeyFixupMapping),
    ('key_row_offsets', tuple),
    ('supported_leds', tuple),
    ('has_macro_keys', bool),
    ('is_wireless', bool),
    ('revision', int),
    ('assets', dict),
    ('parent', 'BaseHardware')])


class Hardware(BaseHardware):
    """
    Static hardware configuration data

    Loaded by Configuration from YAML.
    """

    class Type(Enum):
        HEADSET = 'Headset'
        KEYBOARD = 'Keyboard'
        LAPTOP = 'Laptop'
        MOUSE = 'Mouse'
        MOUSEPAD = 'Mousepad'

    @property
    def has_matrix(self) -> bool:
        """
        True if the device has an addressable key matrix
        """
        return self.dimensions is not None


    def has_quirk(self, *quirks) -> bool:
        """
        True if quirk is required for the device

        :param quirks The quirks to check (varargs)

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
    def _get_device(cls, product_id: int, hw_type) -> 'Hardware':
        if product_id is None or hw_type is None:
            return None

        config_path = os.path.join(os.path.dirname(__file__), 'data')
        yaml_path = os.path.join(config_path, '%s.yaml' % hw_type.name.lower())

        config = cls.load_yaml(yaml_path)
        assert config is not None

        result = config.search('product_id', product_id)
        if result is None or len(result) == 0:
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



# YAML library configuration
def represent_hardware(dumper, data):
    return dumper.represent_mapping(u'!device-config', data.sparsedict(deep=False))

def represent_hex_quad(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:int', '0x%04x' % data)

def represent_flow_seq(dumper, data):
    return dumper.represent_sequence(u'tag:yaml.org,2002:seq', data, flow_style=True)

def represent_dict_block_map(dumper, data):
    return dumper.represent_mapping(u'tag:yaml.org,2002:map', data._asdict(), flow_style=False)

def represent_block_map(dumper, data):
    return dumper.represent_mapping(u'tag:yaml.org,2002:map', data, flow_style=False)

def represent_enum_str(dumper, data):
    return dumper.represent_str(data.name)

yaml.RoundTripLoader.add_constructor(u'!device-config', yaml.RoundTripLoader.construct_yaml_map)

yaml.RoundTripDumper.ignore_aliases = lambda *x: True

yaml.RoundTripDumper.add_multi_representer(Enum, represent_enum_str)
yaml.RoundTripDumper.add_multi_representer(FlowSequence, represent_flow_seq)
yaml.RoundTripDumper.add_multi_representer(BlockMapping, represent_block_map)

yaml.RoundTripDumper.add_representer(KeyMapping, represent_block_map)
yaml.RoundTripDumper.add_representer(Hardware, represent_hardware)
yaml.RoundTripDumper.add_representer(HexQuad, represent_hex_quad)
yaml.RoundTripDumper.add_representer(KeyFixupMapping, represent_dict_block_map)
yaml.RoundTripDumper.add_representer(Point, represent_flow_seq)
yaml.RoundTripDumper.add_representer(Zone, represent_flow_seq)
