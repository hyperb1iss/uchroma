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
"""
Protocol version abstraction for Razer devices.

Provides a clean way to handle different protocol versions based on
transaction IDs and command structures, replacing ad-hoc quirks checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .hardware import Hardware


class ProtocolVersion(Enum):
    """Protocol versions based on transaction ID and command structure."""

    LEGACY = "legacy"  # 0xFF, standard commands (class 0x03)
    EXTENDED = "extended"  # 0x3F, extended FX commands (class 0x0F)
    MODERN = "modern"  # 0x1F, latest devices
    WIRELESS_KB = "wireless_kb"  # 0x9F, wireless keyboards
    SPECIAL = "special"  # Device-specific (e.g., Naga X with 0x08)
    HEADSET_V1 = "headset_v1"  # Rainie protocol (memory read/write)
    HEADSET_V2 = "headset_v2"  # Kylie protocol (memory read/write)


@dataclass(frozen=True)
class ProtocolConfig:
    """Protocol configuration for a device."""

    version: ProtocolVersion
    transaction_id: int
    uses_extended_fx: bool = False
    inter_command_delay: float = 0.007  # seconds
    crc_skip_on_ok: bool = False

    # Predefined configurations (initialized after class definition)
    LEGACY: ClassVar[ProtocolConfig]
    EXTENDED: ClassVar[ProtocolConfig]
    MODERN: ClassVar[ProtocolConfig]
    WIRELESS_KB: ClassVar[ProtocolConfig]
    SPECIAL_08: ClassVar[ProtocolConfig]


# Static configurations
ProtocolConfig.LEGACY = ProtocolConfig(
    version=ProtocolVersion.LEGACY,
    transaction_id=0xFF,
    uses_extended_fx=False,
)

ProtocolConfig.EXTENDED = ProtocolConfig(
    version=ProtocolVersion.EXTENDED,
    transaction_id=0x3F,
    uses_extended_fx=True,
)

ProtocolConfig.MODERN = ProtocolConfig(
    version=ProtocolVersion.MODERN,
    transaction_id=0x1F,
    uses_extended_fx=True,
)

ProtocolConfig.WIRELESS_KB = ProtocolConfig(
    version=ProtocolVersion.WIRELESS_KB,
    transaction_id=0x9F,
    uses_extended_fx=True,
)

ProtocolConfig.SPECIAL_08 = ProtocolConfig(
    version=ProtocolVersion.SPECIAL,
    transaction_id=0x08,
    uses_extended_fx=True,
)


def get_protocol_from_quirks(hardware: Hardware) -> ProtocolConfig:
    """
    Determine protocol configuration from hardware quirks.

    This provides backwards compatibility with the existing quirks system
    while allowing gradual migration to the new protocol abstraction.

    Args:
        hardware: Hardware configuration object

    Returns:
        ProtocolConfig for the device
    """
    from .hardware import Quirks  # noqa: PLC0415 - deferred import for circular dependency

    # Check quirks in order of specificity
    if hardware.has_quirk(Quirks.TRANSACTION_CODE_9F):
        return ProtocolConfig.WIRELESS_KB
    elif hardware.has_quirk(Quirks.TRANSACTION_CODE_08):
        return ProtocolConfig.SPECIAL_08
    elif hardware.has_quirk(Quirks.TRANSACTION_CODE_1F):
        return ProtocolConfig.MODERN
    elif hardware.has_quirk(Quirks.TRANSACTION_CODE_3F):
        return ProtocolConfig.EXTENDED
    else:
        return ProtocolConfig.LEGACY


def get_transaction_id(hardware: Hardware) -> int:
    """
    Get the transaction ID for a device.

    Convenience function that returns just the transaction ID.

    Args:
        hardware: Hardware configuration object

    Returns:
        Transaction ID byte (0xFF, 0x3F, 0x1F, 0x9F, or 0x08)
    """
    return get_protocol_from_quirks(hardware).transaction_id


def uses_extended_fx(hardware: Hardware) -> bool:
    """
    Check if device uses extended FX commands (class 0x0F).

    Args:
        hardware: Hardware configuration object

    Returns:
        True if device uses extended FX commands
    """
    from .hardware import Quirks  # noqa: PLC0415 - deferred import for circular dependency

    # Check both the new protocol system and legacy quirk
    protocol = get_protocol_from_quirks(hardware)
    return protocol.uses_extended_fx or hardware.has_quirk(Quirks.EXTENDED_FX_CMDS)
