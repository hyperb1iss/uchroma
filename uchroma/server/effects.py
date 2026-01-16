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
Effect definitions for Razer USB HID protocol.

This module provides effect ID mappings between legacy (Class 0x03) and
extended (Class 0x0F) effect protocols. Effects have different IDs depending
on the protocol version used by the device.

Legacy effects use command class 0x03, ID 0x0A
Extended effects use command class 0x0F, ID 0x02
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class EffectDef:
    """Definition of a lighting effect.

    Attributes:
        name: Effect name (lowercase, matches supported_fx entries)
        legacy_id: Effect ID for legacy protocol (Class 0x03), None if unsupported
        extended_id: Effect ID for extended protocol (Class 0x0F), None if unsupported
        description: Human-readable description
        max_colors: Maximum number of color parameters (0 = no color params)
        has_speed: Whether effect accepts speed parameter
        has_direction: Whether effect accepts direction parameter
    """

    name: str
    legacy_id: int | None
    extended_id: int | None
    description: str = ""
    max_colors: int = 0
    has_speed: bool = False
    has_direction: bool = False

    def supports_legacy(self) -> bool:
        """Check if effect is supported on legacy protocol."""
        return self.legacy_id is not None

    def supports_extended(self) -> bool:
        """Check if effect is supported on extended protocol."""
        return self.extended_id is not None

    def get_id(self, uses_extended: bool) -> int | None:
        """Get effect ID for the specified protocol."""
        return self.extended_id if uses_extended else self.legacy_id


class Effects:
    """Effect registry with protocol-aware mapping.

    Effects are defined with both legacy and extended protocol IDs where
    applicable. Use get_id() to retrieve the correct ID for a device's
    protocol version.

    Legacy protocol (Class 0x03, ID 0x0A):
    - Used by older devices without EXTENDED_FX_CMDS quirk
    - Effect IDs: disable=0x00, wave=0x01, reactive=0x02, etc.

    Extended protocol (Class 0x0F, ID 0x02):
    - Used by devices with EXTENDED_FX_CMDS quirk
    - Format: [varstore, LED_type, effect_id, ...params]
    - Effect IDs: disable=0x00, static=0x01, breathe=0x02, etc.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Effects supported on both protocols
    # ─────────────────────────────────────────────────────────────────────────

    DISABLE: ClassVar[EffectDef] = EffectDef(
        name="disable",
        legacy_id=0x00,
        extended_id=0x00,
        description="Disable all effects",
    )

    STATIC: ClassVar[EffectDef] = EffectDef(
        name="static",
        legacy_id=0x06,
        extended_id=0x01,
        description="Static color",
        max_colors=1,
    )

    SPECTRUM: ClassVar[EffectDef] = EffectDef(
        name="spectrum",
        legacy_id=0x04,
        extended_id=0x03,
        description="Cycle through all colors",
    )

    WAVE: ClassVar[EffectDef] = EffectDef(
        name="wave",
        legacy_id=0x01,
        extended_id=0x04,
        description="Wave animation",
        has_direction=True,
    )

    BREATHE: ClassVar[EffectDef] = EffectDef(
        name="breathe",
        legacy_id=0x03,
        extended_id=0x02,
        description="Breathing colors",
        max_colors=2,
    )

    REACTIVE: ClassVar[EffectDef] = EffectDef(
        name="reactive",
        legacy_id=0x02,
        extended_id=0x05,
        description="React to keypresses",
        max_colors=1,
        has_speed=True,
    )

    STARLIGHT: ClassVar[EffectDef] = EffectDef(
        name="starlight",
        legacy_id=0x19,
        extended_id=0x07,
        description="Sparkling effect",
        max_colors=2,
        has_speed=True,
    )

    CUSTOM_FRAME: ClassVar[EffectDef] = EffectDef(
        name="custom_frame",
        legacy_id=0x05,
        extended_id=0x08,
        description="Display custom frame from matrix buffer",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Legacy-only effects (Class 0x03 only)
    # ─────────────────────────────────────────────────────────────────────────

    GRADIENT: ClassVar[EffectDef] = EffectDef(
        name="gradient",
        legacy_id=0x0A,
        extended_id=None,
        description="Gradient effect (legacy only)",
    )

    SWEEP: ClassVar[EffectDef] = EffectDef(
        name="sweep",
        legacy_id=0x0C,
        extended_id=None,
        description="Sweep animation",
        has_direction=True,
        has_speed=True,
        max_colors=2,
    )

    HIGHLIGHT: ClassVar[EffectDef] = EffectDef(
        name="highlight",
        legacy_id=0x10,
        extended_id=None,
        description="Highlight effect (legacy only)",
    )

    MORPH: ClassVar[EffectDef] = EffectDef(
        name="morph",
        legacy_id=0x11,
        extended_id=None,
        description="Color morph effect",
        has_speed=True,
        max_colors=2,
    )

    FIRE: ClassVar[EffectDef] = EffectDef(
        name="fire",
        legacy_id=0x12,
        extended_id=None,
        description="Fire effect",
        has_speed=True,
        max_colors=1,
    )

    RIPPLE_SOLID: ClassVar[EffectDef] = EffectDef(
        name="ripple_solid",
        legacy_id=0x13,
        extended_id=None,
        description="Solid color ripple on keypress",
        has_speed=True,
        max_colors=1,
    )

    RIPPLE: ClassVar[EffectDef] = EffectDef(
        name="ripple",
        legacy_id=0x14,
        extended_id=None,
        description="Rainbow ripple on keypress",
        has_speed=True,
        max_colors=1,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Registry methods
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def get(cls, effect_name: str) -> EffectDef | None:
        """Get effect definition by name.

        Args:
            effect_name: Effect name (case-insensitive)

        Returns:
            EffectDef or None if not found
        """
        attr = getattr(cls, effect_name.upper(), None)
        return attr if isinstance(attr, EffectDef) else None

    @classmethod
    def get_id(cls, effect_name: str, uses_extended: bool) -> int | None:
        """Get effect ID for the given protocol.

        Args:
            effect_name: Effect name (case-insensitive)
            uses_extended: True for extended protocol (Class 0x0F),
                          False for legacy protocol (Class 0x03)

        Returns:
            Effect ID or None if effect not found or unsupported on protocol
        """
        effect = cls.get(effect_name)
        if effect is None:
            return None
        return effect.get_id(uses_extended)

    @classmethod
    def supports_protocol(cls, effect_name: str, uses_extended: bool) -> bool:
        """Check if effect is supported on the given protocol.

        Args:
            effect_name: Effect name (case-insensitive)
            uses_extended: True for extended protocol, False for legacy

        Returns:
            True if effect exists and is supported on the protocol
        """
        effect_id = cls.get_id(effect_name, uses_extended)
        return effect_id is not None

    @classmethod
    def get_all_effects(cls) -> list[EffectDef]:
        """Get all registered effects."""
        effects = []
        for name in dir(cls):
            if name.startswith("_"):
                continue
            attr = getattr(cls, name)
            if isinstance(attr, EffectDef):
                effects.append(attr)
        return effects

    @classmethod
    def get_legacy_effects(cls) -> list[EffectDef]:
        """Get all effects supported on legacy protocol."""
        return [e for e in cls.get_all_effects() if e.supports_legacy()]

    @classmethod
    def get_extended_effects(cls) -> list[EffectDef]:
        """Get all effects supported on extended protocol."""
        return [e for e in cls.get_all_effects() if e.supports_extended()]

    @classmethod
    def get_effect_names(cls) -> list[str]:
        """Get list of all effect names (for supported_fx matching)."""
        return [e.name for e in cls.get_all_effects()]
