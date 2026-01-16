#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
CLI command implementations.

Each command module registers itself via the COMMANDS list.
"""

from uchroma.client.commands.base import Command
from uchroma.client.commands.brightness import BrightnessCommand
from uchroma.client.commands.devices import ListCommand
from uchroma.client.commands.dump import DumpCommand
from uchroma.client.commands.fx import FxCommand

# All available commands — order determines help output order
COMMANDS: list[type[Command]] = [
    ListCommand,
    BrightnessCommand,
    FxCommand,
    DumpCommand,
]

__all__ = ["COMMANDS", "Command"]
