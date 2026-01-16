#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
CLI command implementations.

Each command module registers itself via the COMMANDS list.
"""

from uchroma.client.commands.anim import AnimCommand
from uchroma.client.commands.base import Command
from uchroma.client.commands.battery import BatteryCommand
from uchroma.client.commands.brightness import BrightnessCommand
from uchroma.client.commands.devices import ListCommand
from uchroma.client.commands.dump import DumpCommand
from uchroma.client.commands.fx import FxCommand
from uchroma.client.commands.led import LEDCommand
from uchroma.client.commands.power import PowerCommand

# All available commands — order determines help output order
COMMANDS: list[type[Command]] = [
    ListCommand,
    BrightnessCommand,
    FxCommand,
    LEDCommand,
    PowerCommand,
    BatteryCommand,
    AnimCommand,
    DumpCommand,
]

__all__ = ["COMMANDS", "Command"]
