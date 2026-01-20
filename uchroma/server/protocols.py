#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Shared protocol definitions for server mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .commands import Commands
from .hardware import Quirks

if TYPE_CHECKING:
    from .hardware import Hardware


class HasHardwareAndCommands(Protocol):
    """
    Protocol defining the interface required by device mixins.

    Device mixins (PollingMixin, WirelessMixin, etc.) require their host
    class to provide these methods and properties for hardware interaction.
    """

    @property
    def hardware(self) -> Hardware: ...

    def has_quirk(self, *quirks: Quirks) -> bool: ...

    def run_with_result(self, command: Commands, *args: int) -> bytes | None: ...

    def run_command(self, command: Commands, *args: int) -> bool: ...
