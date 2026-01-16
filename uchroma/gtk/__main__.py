"""
UChroma GTK Entry Point

Run with: python -m uchroma.gtk
"""

import sys


def main():
    """Main entry point."""
    # Import and run application
    from .application import main as app_main
    return app_main()


if __name__ == '__main__':
    sys.exit(main())
