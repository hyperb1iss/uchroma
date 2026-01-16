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
Centralized command definitions for Razer USB HID protocol.

This module provides a clean abstraction for hardware commands, replacing
scattered command definitions across device modules. All commands are
documented with their protocol compatibility and data format requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .protocol import ProtocolVersion


@dataclass(frozen=True)
class CommandDef:
    """Definition of a hardware command.

    Attributes:
        command_class: Command class byte (0x00-0x0F)
        command_id: Command ID within the class
        data_size: Expected response data size (None for variable)
        name: Human-readable command name
        description: Command description
        protocols: Tuple of protocol versions that support this command.
                  Empty tuple means all protocols support it.
    """

    command_class: int
    command_id: int
    data_size: int | None
    name: str
    description: str = ""
    protocols: tuple[str, ...] = field(default_factory=tuple)

    def as_tuple(self) -> tuple[int, int, int | None]:
        """Return (command_class, command_id, data_size) tuple for compatibility."""
        return (self.command_class, self.command_id, self.data_size)

    def supports_protocol(self, protocol: ProtocolVersion | str) -> bool:
        """Check if this command supports the given protocol version."""
        if not self.protocols:
            return True  # Empty means all protocols
        protocol_name = protocol.value if hasattr(protocol, "value") else str(protocol)
        return protocol_name in self.protocols


class Commands:
    """Centralized command registry for Razer devices.

    Commands are organized by class:
    - Class 0x00: Device Info & Control
    - Class 0x02: Key Remapping
    - Class 0x03: Standard LED/Effects
    - Class 0x04: DPI / Mouse Settings
    - Class 0x05: Profile Management
    - Class 0x07: Power & Battery
    - Class 0x0B: Calibration
    - Class 0x0D: Laptop Fan/Power (EC Control)
    - Class 0x0F: Extended Matrix Effects
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x00 - Device Info & Control
    # ─────────────────────────────────────────────────────────────────────────

    GET_FIRMWARE: ClassVar[CommandDef] = CommandDef(
        0x00, 0x81, 0x02, "GET_FIRMWARE", "Query firmware version"
    )
    GET_SERIAL: ClassVar[CommandDef] = CommandDef(
        0x00, 0x82, 0x16, "GET_SERIAL", "Query serial number"
    )
    SET_DEVICE_MODE: ClassVar[CommandDef] = CommandDef(
        0x00, 0x04, 0x02, "SET_DEVICE_MODE", "Set driver mode (0x00=normal, 0x03=driver)"
    )
    GET_DEVICE_MODE: ClassVar[CommandDef] = CommandDef(
        0x00, 0x84, 0x02, "GET_DEVICE_MODE", "Query current mode"
    )
    SET_POLLING_RATE: ClassVar[CommandDef] = CommandDef(
        0x00, 0x05, 0x01, "SET_POLLING_RATE", "Set polling rate (1=1000Hz, 2=500Hz, 8=125Hz)"
    )
    GET_POLLING_RATE: ClassVar[CommandDef] = CommandDef(
        0x00, 0x85, 0x01, "GET_POLLING_RATE", "Query polling rate"
    )
    SET_POLLING_RATE_V2: ClassVar[CommandDef] = CommandDef(
        0x00,
        0x40,
        None,
        "SET_POLLING_RATE_V2",
        "Extended polling rate (HyperPolling: 2=4000Hz, 4=2000Hz, 8=1000Hz)",
        protocols=("modern",),
    )
    GET_POLLING_RATE_V2: ClassVar[CommandDef] = CommandDef(
        0x00, 0xC0, None, "GET_POLLING_RATE_V2", "Query extended polling", protocols=("modern",)
    )
    PAIRING_STEP: ClassVar[CommandDef] = CommandDef(
        0x00,
        0x41,
        0x03,
        "PAIRING_STEP",
        "Wireless pairing initiation",
        protocols=("extended", "modern", "wireless_kb"),
    )
    UNPAIR: ClassVar[CommandDef] = CommandDef(
        0x00,
        0x42,
        0x02,
        "UNPAIR",
        "Wireless unpairing",
        protocols=("extended", "modern", "wireless_kb"),
    )
    PAIRING_SCAN: ClassVar[CommandDef] = CommandDef(
        0x00,
        0x46,
        0x01,
        "PAIRING_SCAN",
        "Start pairing scan",
        protocols=("extended", "modern", "wireless_kb"),
    )
    GET_PAIRED_DEVICES: ClassVar[CommandDef] = CommandDef(
        0x00,
        0xBF,
        0x1F,
        "GET_PAIRED_DEVICES",
        "Query paired device list",
        protocols=("extended", "modern", "wireless_kb"),
    )
    GET_PAIRED_STATUS: ClassVar[CommandDef] = CommandDef(
        0x00,
        0xC5,
        None,
        "GET_PAIRED_STATUS",
        "Query paired device status",
        protocols=("extended", "modern", "wireless_kb"),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x02 - Key Remapping
    # ─────────────────────────────────────────────────────────────────────────

    SET_KEY_REMAP: ClassVar[CommandDef] = CommandDef(
        0x02, 0x0D, None, "SET_KEY_REMAP", "Key remapping (non-analog keyboards)"
    )
    SET_KEY_REMAP_ANALOG: ClassVar[CommandDef] = CommandDef(
        0x02,
        0x12,
        None,
        "SET_KEY_REMAP_ANALOG",
        "Key remapping (analog keyboards)",
        protocols=("modern",),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x03 - Standard LED/Effects
    # ─────────────────────────────────────────────────────────────────────────

    SET_LED_STATE: ClassVar[CommandDef] = CommandDef(
        0x03, 0x00, 0x03, "SET_LED_STATE", "Enable/disable LED"
    )
    GET_LED_STATE: ClassVar[CommandDef] = CommandDef(
        0x03, 0x80, 0x03, "GET_LED_STATE", "Query LED state"
    )
    SET_LED_COLOR: ClassVar[CommandDef] = CommandDef(
        0x03, 0x01, 0x05, "SET_LED_COLOR", "Set LED color (RGB)"
    )
    GET_LED_COLOR: ClassVar[CommandDef] = CommandDef(
        0x03, 0x81, 0x05, "GET_LED_COLOR", "Query LED color"
    )
    SET_LED_MODE: ClassVar[CommandDef] = CommandDef(
        0x03, 0x02, 0x03, "SET_LED_MODE", "Set LED effect mode"
    )
    GET_LED_MODE: ClassVar[CommandDef] = CommandDef(
        0x03, 0x82, 0x03, "GET_LED_MODE", "Query LED mode"
    )
    SET_LED_BRIGHTNESS: ClassVar[CommandDef] = CommandDef(
        0x03, 0x03, 0x03, "SET_LED_BRIGHTNESS", "Set brightness level (0-255)"
    )
    GET_LED_BRIGHTNESS: ClassVar[CommandDef] = CommandDef(
        0x03, 0x83, 0x03, "GET_LED_BRIGHTNESS", "Query brightness"
    )
    SET_EFFECT: ClassVar[CommandDef] = CommandDef(
        0x03, 0x0A, None, "SET_EFFECT", "Apply lighting effect", protocols=("legacy",)
    )
    SET_FRAME_DATA_MATRIX: ClassVar[CommandDef] = CommandDef(
        0x03, 0x0B, None, "SET_FRAME_DATA_MATRIX", "Custom frame (multi-row keyboards)"
    )
    SET_FRAME_DATA_SINGLE: ClassVar[CommandDef] = CommandDef(
        0x03, 0x0C, None, "SET_FRAME_DATA_SINGLE", "Custom frame (single row)"
    )
    SET_DOCK_CHARGE_EFFECT: ClassVar[CommandDef] = CommandDef(
        0x03,
        0x10,
        0x01,
        "SET_DOCK_CHARGE_EFFECT",
        "Dock charging LED",
        protocols=("extended", "modern"),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x04 - DPI / Mouse Settings
    # ─────────────────────────────────────────────────────────────────────────

    SET_DPI_XY: ClassVar[CommandDef] = CommandDef(
        0x04, 0x05, 0x07, "SET_DPI_XY", "Set X/Y DPI values"
    )
    GET_DPI_XY: ClassVar[CommandDef] = CommandDef(
        0x04, 0x85, 0x07, "GET_DPI_XY", "Query current DPI"
    )
    SET_DPI_STAGES: ClassVar[CommandDef] = CommandDef(
        0x04, 0x06, None, "SET_DPI_STAGES", "Set DPI stage presets"
    )
    GET_DPI_STAGES: ClassVar[CommandDef] = CommandDef(
        0x04, 0x86, None, "GET_DPI_STAGES", "Query DPI stages"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x05 - Profile Management
    # ─────────────────────────────────────────────────────────────────────────

    SET_PROFILE: ClassVar[CommandDef] = CommandDef(
        0x05,
        0x02,
        None,
        "SET_PROFILE",
        "Switch to profile slot (0=no-store, 1=default, 2=red, 3=green, 4=blue, 5=cyan)",
    )
    GET_PROFILE: ClassVar[CommandDef] = CommandDef(
        0x05, 0x03, None, "GET_PROFILE", "Query current profile"
    )
    WRITE_PROFILE_DATA: ClassVar[CommandDef] = CommandDef(
        0x05, 0x08, None, "WRITE_PROFILE_DATA", "Write data to profile slot"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x07 - Power & Battery
    # ─────────────────────────────────────────────────────────────────────────

    SET_LOW_BATTERY: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x01,
        0x01,
        "SET_LOW_BATTERY",
        "Set low battery threshold",
        protocols=("extended", "modern"),
    )
    GET_LOW_BATTERY: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x81,
        0x01,
        "GET_LOW_BATTERY",
        "Query low battery threshold",
        protocols=("extended", "modern"),
    )
    SET_DOCK_BRIGHTNESS: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x02,
        0x01,
        "SET_DOCK_BRIGHTNESS",
        "Set dock LED brightness",
        protocols=("extended", "modern"),
    )
    GET_DOCK_BRIGHTNESS: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x82,
        0x01,
        "GET_DOCK_BRIGHTNESS",
        "Query dock brightness",
        protocols=("extended", "modern"),
    )
    SET_IDLE_TIME: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x03,
        0x02,
        "SET_IDLE_TIME",
        "Set idle timeout (60-900 seconds)",
        protocols=("extended", "modern"),
    )
    GET_IDLE_TIME: ClassVar[CommandDef] = CommandDef(
        0x07, 0x83, 0x02, "GET_IDLE_TIME", "Query idle timeout", protocols=("extended", "modern")
    )
    SET_DONGLE_LED: ClassVar[CommandDef] = CommandDef(
        0x07, 0x10, 0x01, "SET_DONGLE_LED", "Set HyperSpeed dongle LED mode", protocols=("modern",)
    )
    GET_BATTERY_LEVEL: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x80,
        0x02,
        "GET_BATTERY_LEVEL",
        "Query battery level (0-255)",
        protocols=("extended", "modern"),
    )
    GET_CHARGING_STATUS: ClassVar[CommandDef] = CommandDef(
        0x07,
        0x84,
        0x02,
        "GET_CHARGING_STATUS",
        "Query charging (0=no, 1=yes)",
        protocols=("extended", "modern"),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x0B - Calibration
    # ─────────────────────────────────────────────────────────────────────────

    SET_CALIBRATION: ClassVar[CommandDef] = CommandDef(
        0x0B, 0x03, None, "SET_CALIBRATION", "Surface calibration mode"
    )
    GET_CALIBRATION: ClassVar[CommandDef] = CommandDef(
        0x0B, 0x85, None, "GET_CALIBRATION", "Query calibration data"
    )
    SET_LIFTOFF: ClassVar[CommandDef] = CommandDef(
        0x0B, 0x05, None, "SET_LIFTOFF", "Lift-off distance"
    )
    START_CALIBRATION: ClassVar[CommandDef] = CommandDef(
        0x0B, 0x09, None, "START_CALIBRATION", "Begin calibration"
    )
    FINALIZE_CALIBRATION: ClassVar[CommandDef] = CommandDef(
        0x0B, 0x0B, None, "FINALIZE_CALIBRATION", "Complete calibration"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x0D - Laptop Fan/Power (EC Control)
    # ─────────────────────────────────────────────────────────────────────────

    SET_FAN_MODE: ClassVar[CommandDef] = CommandDef(
        0x0D, 0x02, None, "SET_FAN_MODE", "Fan control mode"
    )
    GET_FAN_RPM: ClassVar[CommandDef] = CommandDef(
        0x0D, 0x82, None, "GET_FAN_RPM", "Query fan speed"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class 0x0F - Extended Matrix Effects
    # ─────────────────────────────────────────────────────────────────────────

    SET_EFFECT_EXTENDED: ClassVar[CommandDef] = CommandDef(
        0x0F,
        0x02,
        None,
        "SET_EFFECT_EXTENDED",
        "Apply extended effect [varstore, LED_type, effect_id, ...params]",
        protocols=("extended", "modern"),
    )
    GET_EFFECT_EXTENDED: ClassVar[CommandDef] = CommandDef(
        0x0F,
        0x80,
        None,
        "GET_EFFECT_EXTENDED",
        "Query current effect",
        protocols=("extended", "modern"),
    )
    SET_FRAME_EXTENDED: ClassVar[CommandDef] = CommandDef(
        0x0F,
        0x03,
        None,
        "SET_FRAME_EXTENDED",
        "Extended custom frame",
        protocols=("extended", "modern"),
    )
    GET_MATRIX_EFFECT: ClassVar[CommandDef] = CommandDef(
        0x0F,
        0x82,
        None,
        "GET_MATRIX_EFFECT",
        "Query matrix state",
        protocols=("extended", "modern"),
    )
    SET_BRIGHTNESS_EXTENDED: ClassVar[CommandDef] = CommandDef(
        0x0F,
        0x04,
        0x03,
        "SET_BRIGHTNESS_EXTENDED",
        "Set brightness (extended)",
        protocols=("extended", "modern"),
    )
    GET_BRIGHTNESS_EXTENDED: ClassVar[CommandDef] = CommandDef(
        0x0F,
        0x84,
        0x03,
        "GET_BRIGHTNESS_EXTENDED",
        "Query brightness (extended)",
        protocols=("extended", "modern"),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Class lookup
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def get_by_class_and_id(cls, command_class: int, command_id: int) -> CommandDef | None:
        """Look up a command by class and ID."""
        for name in dir(cls):
            if name.startswith("_"):
                continue
            attr = getattr(cls, name)
            if (
                isinstance(attr, CommandDef)
                and attr.command_class == command_class
                and attr.command_id == command_id
            ):
                return attr
        return None

    @classmethod
    def get_all_commands(cls) -> list[CommandDef]:
        """Get all registered commands."""
        commands = []
        for name in dir(cls):
            if name.startswith("_"):
                continue
            attr = getattr(cls, name)
            if isinstance(attr, CommandDef):
                commands.append(attr)
        return commands

    @classmethod
    def get_commands_for_protocol(cls, protocol: ProtocolVersion | str) -> list[CommandDef]:
        """Get all commands supported by a specific protocol."""
        return [cmd for cmd in cls.get_all_commands() if cmd.supports_protocol(protocol)]
