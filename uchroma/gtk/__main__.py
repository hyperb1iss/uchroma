#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
UChroma GTK Entry Point

Run with: python -m uchroma.gtk
"""

import argparse
import logging
import sys

from uchroma.log import Log


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="UChroma GTK frontend")
    parser.add_argument(
        "-d", "--debug", action="append_const", const=True, help="Increase logging verbosity"
    )
    parser.add_argument("-C", "--colorlog", action="store_true", help="Use colored log output")

    args, remaining = parser.parse_known_args()

    # Set up logging
    level = logging.WARNING
    if args.debug is not None:
        if len(args.debug) >= 2:
            level = logging.DEBUG
        elif len(args.debug) == 1:
            level = logging.INFO

    Log.enable_color(args.colorlog or False)
    logging.getLogger().setLevel(level)

    # Replace sys.argv with remaining args for GTK
    sys.argv = [sys.argv[0]] + remaining

    # Import and run application
    from .application import main as app_main  # noqa: PLC0415

    return app_main()


if __name__ == "__main__":
    sys.exit(main())
