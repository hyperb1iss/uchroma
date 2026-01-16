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

"""Unit tests for uchroma.server.commands module."""

from __future__ import annotations

import pytest

from uchroma.server.commands import CommandDef, Commands

# ─────────────────────────────────────────────────────────────────────────────
# CommandDef Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCommandDef:
    """Tests for CommandDef dataclass."""

    def test_basic_command_def(self):
        """CommandDef stores basic attributes correctly."""
        cmd = CommandDef(0x03, 0x0A, 10, "TEST_CMD", "Test command")
        assert cmd.command_class == 0x03
        assert cmd.command_id == 0x0A
        assert cmd.data_size == 10
        assert cmd.name == "TEST_CMD"
        assert cmd.description == "Test command"
        assert cmd.protocols == ()

    def test_as_tuple(self):
        """as_tuple() returns (class, id, size) tuple."""
        cmd = CommandDef(0x03, 0x0A, 10, "TEST_CMD")
        assert cmd.as_tuple() == (0x03, 0x0A, 10)

    def test_as_tuple_with_none_size(self):
        """as_tuple() handles None data_size."""
        cmd = CommandDef(0x0F, 0x02, None, "VAR_CMD")
        assert cmd.as_tuple() == (0x0F, 0x02, None)

    def test_supports_protocol_empty_protocols(self):
        """Empty protocols tuple means all protocols supported."""
        cmd = CommandDef(0x03, 0x00, 3, "SET_LED_STATE")
        assert cmd.supports_protocol("legacy") is True
        assert cmd.supports_protocol("extended") is True
        assert cmd.supports_protocol("modern") is True

    def test_supports_protocol_specific_protocols(self):
        """Command only supports specified protocols."""
        cmd = CommandDef(0x0F, 0x02, None, "SET_EFFECT_EXTENDED", protocols=("extended", "modern"))
        assert cmd.supports_protocol("legacy") is False
        assert cmd.supports_protocol("extended") is True
        assert cmd.supports_protocol("modern") is True

    def test_command_def_is_frozen(self):
        """CommandDef is immutable."""
        cmd = CommandDef(0x03, 0x0A, 10, "TEST_CMD")
        with pytest.raises(AttributeError):
            cmd.command_id = 0x0B


# ─────────────────────────────────────────────────────────────────────────────
# Commands Registry Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCommandsRegistry:
    """Tests for Commands registry class."""

    def test_get_firmware_command(self):
        """GET_FIRMWARE command has correct values."""
        cmd = Commands.GET_FIRMWARE
        assert cmd.command_class == 0x00
        assert cmd.command_id == 0x81
        assert cmd.data_size == 0x02
        assert cmd.name == "GET_FIRMWARE"

    def test_get_serial_command(self):
        """GET_SERIAL command has correct values."""
        cmd = Commands.GET_SERIAL
        assert cmd.command_class == 0x00
        assert cmd.command_id == 0x82
        assert cmd.data_size == 0x16

    def test_set_led_state_command(self):
        """SET_LED_STATE command has correct values."""
        cmd = Commands.SET_LED_STATE
        assert cmd.command_class == 0x03
        assert cmd.command_id == 0x00
        assert cmd.data_size == 0x03

    def test_set_effect_extended_command(self):
        """SET_EFFECT_EXTENDED command is protocol-restricted."""
        cmd = Commands.SET_EFFECT_EXTENDED
        assert cmd.command_class == 0x0F
        assert cmd.command_id == 0x02
        assert cmd.supports_protocol("legacy") is False
        assert cmd.supports_protocol("extended") is True
        assert cmd.supports_protocol("modern") is True


class TestCommandsLookup:
    """Tests for Commands lookup methods."""

    def test_get_by_class_and_id_found(self):
        """get_by_class_and_id returns command when found."""
        cmd = Commands.get_by_class_and_id(0x00, 0x81)
        assert cmd is not None
        assert cmd.name == "GET_FIRMWARE"

    def test_get_by_class_and_id_not_found(self):
        """get_by_class_and_id returns None when not found."""
        cmd = Commands.get_by_class_and_id(0xFF, 0xFF)
        assert cmd is None

    def test_get_all_commands(self):
        """get_all_commands returns all registered commands."""
        cmds = Commands.get_all_commands()
        assert len(cmds) > 0
        assert all(isinstance(c, CommandDef) for c in cmds)

    def test_get_commands_for_protocol_legacy(self):
        """get_commands_for_protocol returns legacy-compatible commands."""
        cmds = Commands.get_commands_for_protocol("legacy")
        assert len(cmds) > 0
        # Legacy should NOT include extended-only commands
        assert Commands.SET_EFFECT_EXTENDED not in cmds

    def test_get_commands_for_protocol_modern(self):
        """get_commands_for_protocol returns modern-compatible commands."""
        cmds = Commands.get_commands_for_protocol("modern")
        assert len(cmds) > 0
        # Modern should include extended commands
        assert Commands.SET_EFFECT_EXTENDED in cmds


class TestCommandsByClass:
    """Tests for commands organized by class."""

    def test_class_0x00_device_info(self):
        """Class 0x00 contains device info commands."""
        cmds = [c for c in Commands.get_all_commands() if c.command_class == 0x00]
        names = [c.name for c in cmds]
        assert "GET_FIRMWARE" in names
        assert "GET_SERIAL" in names
        assert "SET_DEVICE_MODE" in names

    def test_class_0x03_led_effects(self):
        """Class 0x03 contains LED/effect commands."""
        cmds = [c for c in Commands.get_all_commands() if c.command_class == 0x03]
        names = [c.name for c in cmds]
        assert "SET_LED_STATE" in names
        assert "SET_LED_BRIGHTNESS" in names
        assert "SET_EFFECT" in names

    def test_class_0x07_power_battery(self):
        """Class 0x07 contains power/battery commands."""
        cmds = [c for c in Commands.get_all_commands() if c.command_class == 0x07]
        names = [c.name for c in cmds]
        assert "GET_BATTERY_LEVEL" in names
        assert "GET_CHARGING_STATUS" in names

    def test_class_0x0f_extended_matrix(self):
        """Class 0x0F contains extended matrix commands."""
        cmds = [c for c in Commands.get_all_commands() if c.command_class == 0x0F]
        names = [c.name for c in cmds]
        assert "SET_EFFECT_EXTENDED" in names
        assert "SET_FRAME_EXTENDED" in names
