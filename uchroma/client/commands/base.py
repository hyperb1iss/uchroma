#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Base command class for CLI commands.
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.cli_base import UChromaCLI


class Command(ABC):
    """
    Base class for CLI commands.

    Subclasses must implement:
    - name: Command name (used as subparser name)
    - help: Short help text
    - configure_parser(): Add command-specific arguments
    - run(): Execute the command
    """

    name: ClassVar[str]
    help: ClassVar[str]
    aliases: ClassVar[list[str]] = []

    def __init__(self, cli: UChromaCLI):
        self.cli = cli
        self.out = cli.out

    @classmethod
    def register(cls, cli: UChromaCLI, subparsers) -> "Command":
        """
        Register this command with the CLI.

        Creates the subparser and returns a command instance.
        """
        instance = cls(cli)

        parser = subparsers.add_parser(
            cls.name,
            help=cls.help,
            aliases=cls.aliases,
        )
        instance.configure_parser(parser)
        parser.set_defaults(cmd_instance=instance)

        return instance

    @abstractmethod
    def configure_parser(self, parser: ArgumentParser) -> None:
        """Add command-specific arguments to the parser."""
        ...

    @abstractmethod
    def run(self, args: Namespace) -> int:
        """
        Execute the command.

        Args:
            args: Parsed arguments

        Returns:
            Exit code (0 for success)
        """
        ...

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def require_device(self, args: Namespace):
        """
        Get the selected device, erroring if none.

        Returns the device proxy/object.
        """
        # This will be implemented when we integrate with D-Bus client
        # For now, placeholder that checks device_spec
        if not hasattr(args, "device_spec") or args.device_spec is None:
            # Try auto-select if single device
            pass
        return args.device_spec

    def print(self, *args, **kwargs):
        """Print to stdout."""
        print(*args, **kwargs)

    def error(self, message: str) -> int:
        """Print error and return exit code 1."""
        print(self.out.error(message))
        return 1

    def success(self, message: str) -> int:
        """Print success and return exit code 0."""
        print(self.out.success(message))
        return 0
