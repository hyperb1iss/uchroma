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

from __future__ import annotations

import os
from collections import OrderedDict
from datetime import datetime
from enum import Enum, IntEnum, StrEnum
from typing import TYPE_CHECKING, NamedTuple

import ruamel.yaml as yaml

from .config import Configuration, FlowSequence, LowerCaseSeq, represent_flow_seq
from .types import LEDType

if TYPE_CHECKING:
    from .protocol import ProtocolConfig

RAZER_VENDOR_ID = 0x1532


class Quirks(IntEnum):
    """
    Various "quirks" that are found across hardware models.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Transaction codes
    # ─────────────────────────────────────────────────────────────────────────

    # Always use transaction code 0x3F
    TRANSACTION_CODE_3F = 1

    # Use transaction code 0x1F (Blade 2021+, modern devices)
    TRANSACTION_CODE_1F = 9

    # Use transaction code 0x9F (wireless keyboards)
    TRANSACTION_CODE_9F = 10

    # Use transaction code 0x08 (Naga X special case)
    TRANSACTION_CODE_08 = 11

    # ─────────────────────────────────────────────────────────────────────────
    # Command sets
    # ─────────────────────────────────────────────────────────────────────────

    # Use "extended" commands (class 0x0F instead of 0x03)
    EXTENDED_FX_CMDS = 2

    # ─────────────────────────────────────────────────────────────────────────
    # Brightness control
    # ─────────────────────────────────────────────────────────────────────────

    # Control device brightness with the scroll wheel LED
    SCROLL_WHEEL_BRIGHTNESS = 3

    # Control device brightness with the logo LED
    LOGO_LED_BRIGHTNESS = 6

    # ─────────────────────────────────────────────────────────────────────────
    # Device features
    # ─────────────────────────────────────────────────────────────────────────

    # Device has charge and dock controls (wireless capability)
    WIRELESS = 4

    # Needs transaction code 0x80 for custom frame data
    CUSTOM_FRAME_80 = 5

    # Device has individual "profile" LEDs
    PROFILE_LEDS = 7

    # Device only supports spectrum effect on the backlight LED
    BACKLIGHT_LED_FX_ONLY = 8

    # ─────────────────────────────────────────────────────────────────────────
    # New quirks for modern devices
    # ─────────────────────────────────────────────────────────────────────────

    # Device has no RGB LEDs (e.g., Viper V3 Pro, DeathAdder V3)
    NO_LED = 12

    # Device has only one LED zone
    SINGLE_LED = 13

    # Device supports HyperPolling (4000/8000Hz)
    HYPERPOLLING = 14

    # Device has analog key actuation support
    ANALOG_KEYS = 15

    # Device firmware lacks hardware effects (needs software rendering)
    SOFTWARE_EFFECTS = 16

    # Device uses USB interface 3 for control commands (modern keyboards)
    CONTROL_IFACE_3 = 18

    # Skip CRC validation on successful responses
    CRC_SKIP_ON_OK = 17


class Capability(StrEnum):
    """
    Device capabilities that can be declared in YAML configs.

    These provide a more declarative way to specify device features
    compared to quirks, and are preferred for new device entries.
    """

    # Connectivity
    WIRELESS = "wireless"  # Device has battery/charging support

    # Polling/Performance
    HYPERPOLLING = "hyperpolling"  # Supports 4000/8000Hz polling rates

    # LED Features
    NO_LED = "no_led"  # Device has no RGB LEDs
    SINGLE_LED = "single_led"  # Device has only one LED zone
    SOFTWARE_EFFECTS = "software_effects"  # Needs software-rendered effects

    # Input Features
    ANALOG_KEYS = "analog_keys"  # Analog key actuation support

    # Misc
    PROFILE_LEDS = "profile_leds"  # Device has individual profile LEDs


class MatrixType(StrEnum):
    """
    Type of LED matrix the device has.
    """

    NONE = "none"  # No LED matrix (single LED or no LEDs)
    SINGLE = "single"  # Single-row LED strip
    ROW = "row"  # Row-addressable matrix
    FULL = "full"  # Fully addressable matrix


class _ProtocolSpec(NamedTuple):
    """Protocol specification for a device (new YAML schema)."""

    version: str  # legacy | extended | modern | wireless_kb | special
    transaction_id: int  # Primary transaction ID (e.g., 0xFF, 0x3F, 0x1F)
    transaction_id_wireless: int | None  # Optional wireless transaction ID
    extended_fx: bool  # Use extended FX commands (class 0x0F)
    inter_command_delay: float  # Delay between commands in seconds


# Set defaults for ProtocolSpec fields
_ProtocolSpec.__new__.__defaults__ = (
    "legacy",  # version
    0xFF,  # transaction_id
    None,  # transaction_id_wireless
    False,  # extended_fx
    0.007,  # inter_command_delay
)


class ProtocolSpec(_ProtocolSpec):
    """Protocol specification with helper methods."""

    def _asdict(self):
        """Return as ordered dict, omitting None values."""
        return OrderedDict(
            [(k, v) for k, v in zip(self._fields, self, strict=False) if v is not None]
        )


# Marker types for YAML output
class _Point(NamedTuple):
    y: int
    x: int


class Point(_Point):
    def __repr__(self):
        return f"({self.y}, {self.x})"


class PointList(FlowSequence):
    def __new__(cls, args):
        if isinstance(args, list):
            if isinstance(args[0], int) and len(args) == 2:
                return Point(args[0], args[1])
            if isinstance(args[0], list):
                return cls([cls(arg) for arg in args])
        return super().__new__(cls, args)


class KeyMapping(OrderedDict):
    def __setitem__(self, key, value, **kwargs):
        super().__setitem__(key, PointList(value), **kwargs)


class _KeyFixupMapping(NamedTuple):
    copy: PointList
    delete: PointList
    insert: PointList


_KeyFixupMapping.__new__.__defaults__ = (None,) * len(_KeyFixupMapping._fields)


class KeyFixupMapping(_KeyFixupMapping):
    def _asdict(self):
        return OrderedDict([x for x in zip(self._fields, self, strict=False) if x[1] is not None])


class Zone(NamedTuple):
    name: str
    coord: Point
    width: int
    height: int


class HexQuad(int):
    pass


# Configuration
BaseHardware = Configuration.create(
    "BaseHardware",
    [
        ("name", str),
        ("manufacturer", str),
        ("type", "Type"),
        ("vendor_id", HexQuad),
        ("product_id", HexQuad),
        ("product_id_wireless", HexQuad),  # NEW: Paired wireless product ID
        ("dimensions", Point),
        ("supported_fx", LowerCaseSeq),
        ("supported_leds", LEDType),
        ("quirks", Quirks),
        ("zones", Zone),
        ("key_mapping", KeyMapping),
        ("key_fixup_mapping", KeyFixupMapping),
        ("key_row_offsets", tuple),
        ("macro_keys", OrderedDict),
        ("is_wireless", bool),
        ("revision", int),
        ("assets", dict),
        # ─────────────────────────────────────────────────────────────────────
        # New protocol-based schema fields (Phase 4)
        # ─────────────────────────────────────────────────────────────────────
        ("protocol", ProtocolSpec),  # NEW: Protocol specification
        ("capabilities", Capability),  # NEW: Device capabilities list
        ("matrix_type", MatrixType),  # NEW: Type of LED matrix
        ("hardware_effects", LowerCaseSeq),  # NEW: Supported hardware effects
    ],
    yaml_name="!device-config",
)


class Hardware(BaseHardware):
    """
    Static hardware configuration data

    Loaded by Configuration from YAML.
    """

    class Type(Enum):
        HEADSET = "Headset"
        KEYBOARD = "Keyboard"
        KEYPAD = "Keypad"
        LAPTOP = "Laptop"
        MOUSE = "Mouse"
        MOUSEPAD = "Mousepad"

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

    def has_capability(self, capability: Capability | str) -> bool:
        """
        Check if device has a specific capability.

        Checks both the new `capabilities` field and legacy quirks for
        backwards compatibility.

        :param capability: The capability to check (Capability enum or string)
        :return: True if the device has the capability
        """
        # Normalize to string for comparison
        cap_str = capability.value if isinstance(capability, Capability) else capability.lower()

        # Check new capabilities field first
        if self.capabilities is not None:
            caps = (
                self.capabilities
                if isinstance(self.capabilities, (list, tuple))
                else [self.capabilities]
            )
            for cap in caps:
                cap_val = cap.value if isinstance(cap, Capability) else str(cap).lower()
                if cap_val == cap_str:
                    return True

        # Fall back to legacy quirks mapping
        quirk_mapping = {
            Capability.WIRELESS.value: Quirks.WIRELESS,
            Capability.HYPERPOLLING.value: Quirks.HYPERPOLLING,
            Capability.NO_LED.value: Quirks.NO_LED,
            Capability.SINGLE_LED.value: Quirks.SINGLE_LED,
            Capability.SOFTWARE_EFFECTS.value: Quirks.SOFTWARE_EFFECTS,
            Capability.ANALOG_KEYS.value: Quirks.ANALOG_KEYS,
            Capability.PROFILE_LEDS.value: Quirks.PROFILE_LEDS,
        }

        if cap_str in quirk_mapping:
            return self.has_quirk(quirk_mapping[cap_str])

        return False

    def get_protocol_config(self) -> ProtocolConfig:
        """
        Get the protocol configuration for this device.

        If the device has a `protocol` field (new schema), use that.
        Otherwise, derive the protocol from legacy quirks.

        :return: ProtocolConfig for this device
        """
        from .protocol import (  # noqa: PLC0415 - deferred import
            ProtocolConfig,
            ProtocolVersion,
            get_protocol_from_quirks,
        )

        # If new protocol field is present, use it
        if self.protocol is not None:
            version_map = {
                "legacy": ProtocolVersion.LEGACY,
                "extended": ProtocolVersion.EXTENDED,
                "modern": ProtocolVersion.MODERN,
                "wireless_kb": ProtocolVersion.WIRELESS_KB,
                "special": ProtocolVersion.SPECIAL,
                "headset_v1": ProtocolVersion.HEADSET_V1,
                "headset_v2": ProtocolVersion.HEADSET_V2,
            }
            version = version_map.get(self.protocol.version, ProtocolVersion.LEGACY)
            return ProtocolConfig(
                version=version,
                transaction_id=self.protocol.transaction_id,
                uses_extended_fx=self.protocol.extended_fx,
                inter_command_delay=self.protocol.inter_command_delay,
            )

        # Fall back to quirks-based detection
        return get_protocol_from_quirks(self)

    @property
    def uses_extended_fx(self) -> bool:
        """
        Check if device uses extended FX commands (class 0x0F).

        Checks both the new `protocol` field and legacy EXTENDED_FX_CMDS quirk.

        :return: True if device uses extended FX commands
        """
        # Check new protocol field first
        if self.protocol is not None:
            return self.protocol.extended_fx

        # Fall back to quirk
        return self.has_quirk(Quirks.EXTENDED_FX_CMDS)

    @property
    def has_leds(self) -> bool:
        """
        Check if device has any RGB LEDs.

        :return: True if device has LEDs
        """
        if self.has_capability(Capability.NO_LED):
            return False
        return self.supported_leds is not None and len(self.supported_leds) > 0

    def get_supported_effects(self) -> tuple[str, ...]:
        """
        Get list of supported hardware effects.

        Checks both the new `hardware_effects` field and legacy `supported_fx`.

        :return: Tuple of effect names (lowercase)
        """
        # Check new hardware_effects field first
        if self.hardware_effects is not None:
            return tuple(self.hardware_effects)

        # Fall back to legacy supported_fx
        if self.supported_fx is not None:
            return tuple(self.supported_fx)

        return ()

    def supports_effect(self, effect_name: str) -> bool:
        """
        Check if device supports a specific hardware effect.

        :param effect_name: Name of the effect to check
        :return: True if the effect is supported
        """
        effects = self.get_supported_effects()
        if not effects:
            # If no effects list specified, assume all effects available
            return True
        return effect_name.lower() in effects

    @classmethod
    def get_type(cls, hw_type) -> Hardware | None:
        if hw_type is None:
            return None

        config_path = os.path.join(os.path.dirname(__file__), "data")
        yaml_path = os.path.join(config_path, f"{hw_type.name.lower()}.yaml")

        config = cls.load_yaml(yaml_path)
        assert config is not None

        return config

    @classmethod
    def _get_device(cls, product_id: int, hw_type) -> Hardware | None:
        if product_id is None:
            return None

        config = cls.get_type(hw_type)

        result = config.search("product_id", product_id)
        if not result:
            return None

        if isinstance(result, list) and len(result) == 1:
            return result[0]

        return result

    @classmethod
    def get_device(cls, product_id: int, hw_type=None) -> Hardware | None:
        if hw_type is not None:
            return cls._get_device(product_id, hw_type)

        for hw in Hardware.Type:
            device = cls._get_device(product_id, hw)
            if device is not None:
                return device

        return None

    def _yaml_header(self) -> str:
        header = "#\n#  uChroma device configuration\n#\n"
        if self.name is not None:
            header += f"#  Model: {self.name} ({self.type.value})\n"
        elif self.type is not None:
            header += f"#  Type: {self.type.name.title()}\n"
        header += "#  Updated on: {}\n".format(datetime.now().isoformat(" "))
        header += "#\n"

        return header


# YAML library configuration
def represent_hex_quad(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:int", f"0x{data:04x}")


def represent_namedtuple(dumper, data):
    return dumper.represent_ordereddict(data._asdict())


yaml.RoundTripDumper.add_representer(HexQuad, represent_hex_quad)
yaml.RoundTripDumper.add_representer(KeyFixupMapping, represent_namedtuple)
yaml.RoundTripDumper.add_representer(ProtocolSpec, represent_namedtuple)
yaml.RoundTripDumper.add_representer(Point, represent_flow_seq)
yaml.RoundTripDumper.add_representer(Zone, represent_flow_seq)
