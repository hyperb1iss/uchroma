#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
CLI base infrastructure.

Provides the foundation for uchroma CLI with:
- Device selection (@device syntax or --device flag)
- Output styling integration
- Subcommand registration
"""

import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter

from uchroma.client.output import Output
from uchroma.version import __version__


class UChromaCLI:
    """
    Base CLI handler with device selection and semantic output.

    Usage:
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        # Register commands...
        args = cli.parse_args()
    """

    def __init__(self):
        self.out = Output()
        self.parser = self._create_parser()
        self._subparsers = None

    def _create_parser(self) -> ArgumentParser:
        """Create the root argument parser."""
        parser = ArgumentParser(
            prog="uchroma",
            description="RGB control for Razer Chroma peripherals",
            formatter_class=RawDescriptionHelpFormatter,
            epilog=self._epilog(),
        )

        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"uchroma {__version__}",
        )
        parser.add_argument(
            "-d",
            "--device",
            type=str,
            metavar="DEVICE",
            help="device name, index, or key (or use @device prefix)",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="enable debug output",
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="disable colored output",
        )

        return parser

    def _epilog(self) -> str:
        """Generate help epilog with examples."""
        return """\
Device Selection:
  @blackwidow    Select by name (fuzzy match)
  @0             Select by index
  1532:0226      Select by USB ID
  -d NAME        Explicit flag

Examples:
  uchroma                      List devices
  uchroma @blackwidow          Show device status
  uchroma brightness 80        Set brightness (auto-select device)
  uchroma fx plasma --speed 2  Activate plasma effect
  uchroma anim add rainbow     Add animation layer
"""

    def _extract_device_spec(self, args: list[str]) -> tuple[str | None, list[str]]:
        """
        Extract @device specifier from argument list.

        Only extracts the first @-prefixed argument.

        Returns:
            (device_spec, remaining_args)
        """
        device_spec = None
        remaining = []

        for arg in args:
            if arg.startswith("@") and device_spec is None:
                device_spec = arg[1:]  # Strip @ prefix
            else:
                remaining.append(arg)

        return device_spec, remaining

    def add_subparsers(self):
        """
        Add subparser container for commands.

        Call this before registering commands. Returns the same
        subparsers object on subsequent calls.
        """
        if self._subparsers is None:
            self._subparsers = self.parser.add_subparsers(
                title="commands",
                dest="command",
                metavar="COMMAND",
            )
        return self._subparsers

    def parse_args(self, args: list[str] | None = None) -> Namespace:
        """
        Parse command line arguments.

        Handles @device extraction before standard parsing.
        The --device flag takes precedence over @device syntax.

        Uses parse_known_args to support commands with dynamic subparsers.
        Unparsed args are stored in parsed.unparsed for the command to handle.
        """
        if args is None:
            args = sys.argv[1:]

        # Extract @device specifier
        at_device_spec, remaining = self._extract_device_spec(args)

        # Parse remaining args - use parse_known_args for dynamic subcommands
        parsed, unparsed = self.parser.parse_known_args(remaining)
        parsed.unparsed = unparsed

        # Merge device_spec: --device flag takes precedence
        if parsed.device is not None:
            parsed.device_spec = parsed.device
        else:
            parsed.device_spec = at_device_spec

        # Handle --no-color
        if parsed.no_color:
            self.out = Output(force_color=False)

        return parsed

    # ─────────────────────────────────────────────────────────────────────────
    # Output helpers
    # ─────────────────────────────────────────────────────────────────────────

    def error(self, message: str) -> None:
        """Print error message and exit with code 1."""
        print(self.out.error(message), file=sys.stderr)
        sys.exit(1)

    def print_success(self, message: str) -> None:
        """Print success message."""
        print(self.out.success(message))

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        print(self.out.warning(message))
