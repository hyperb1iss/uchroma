#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
CLI main entry point.

This is the new uchroma command entry point. Run with:
    python -m uchroma.client.main
    or via the 'uchroma' console script
"""

import sys

from uchroma.client.cli_base import UChromaCLI
from uchroma.client.commands import COMMANDS


def main(args: list[str] | None = None) -> int:
    """
    Main CLI entry point.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    cli = UChromaCLI()

    # Register all commands
    subparsers = cli.add_subparsers()
    for cmd_cls in COMMANDS:
        cmd_cls.register(cli, subparsers)

    # Parse arguments
    parsed = cli.parse_args(args)

    # Handle no command - show help or list devices
    if not hasattr(parsed, "command") or parsed.command is None:
        # Default behavior: list devices if available, otherwise show help
        if hasattr(parsed, "cmd_instance"):
            return parsed.cmd_instance.run(parsed)
        cli.parser.print_help()
        return 0

    # Execute command
    if hasattr(parsed, "cmd_instance"):
        try:
            return parsed.cmd_instance.run(parsed)
        except KeyboardInterrupt:
            print()  # Clean line after ^C
            return 130
        except Exception as e:
            if parsed.debug:
                raise
            cli.error(str(e))
            return 1
    else:
        # Subcommand parsed but no handler (shouldn't happen)
        cli.parser.print_help()
        return 1


def cli_entry() -> None:
    """Console script entry point."""
    sys.exit(main())


if __name__ == "__main__":
    cli_entry()
