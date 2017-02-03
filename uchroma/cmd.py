"""
Various helper functions that are used across the library.
"""
import argparse
import logging
import re
import sys

from uchroma.device_manager import UChromaDeviceManager
from uchroma.version import __version__


class UChromaConsoleUtil(object):
    """
    A base class for command-line utilities
    """
    def __init__(self):
        parser = argparse.ArgumentParser(description=self.description)

        parser.add_argument("-v", "--version", action='version', version='self.version')
        parser.add_argument("--debug", action='store_true', help='Enable debug output')

        sub = parser.add_subparsers(title='Subcommands')

        list_devs = sub.add_parser('list', help='List devices')
        list_devs.set_defaults(func=self._list_devices)

        self._add_subparsers(sub)

        self._args = parser.parse_args()

        if self._args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        if not hasattr(self._args, 'func'):
            parser.print_help()
            sys.exit(1)

        self._parser = parser
        self._dm = UChromaDeviceManager()


    def _list_devices(self, args):
        for key in self._dm.devices:
            d = self._dm.devices[key]
            serial_number = firmware_version = "Unknown"
            try:
                serial_number = d.serial_number
                firmware_version = d.firmware_version
            except IOError as err:
                if self._args.debug:
                    print_err("Error opening device: %s" % err)

            print('[%s]: %s (%s / %s)' % (key, d.name, serial_number, firmware_version))
        sys.exit(0)


    @property
    def description(self):
        return 'Color control for Razer Chroma peripherals'


    @property
    def version(self):
        return 'uChroma-%s' % __version__


    def _add_subparsers(self, sub):
        list_devs = sub.add_parser('list', help='List devices')
        list_devs.set_defaults(func=self._list_devices)


    def print_err(self, *args):
        sys.stderr.write(' '.join(map(str, args)) + '\n')


    def get_driver(self, args):
        driver = None

        if args.device is not None:
            key = args.device

            if not re.match(r'\w{4}:\w{4}.\d{2}', key):
                index = int(args.device)
                key = list(self._dm.devices.keys())[index]
                if key is None:
                    self.print_err("Invalid device: %s" % args.device)
                    sys.exit(1)

            if key not in self._dm.devices:
                sys.exit(1)

            driver = self._dm.devices[key]

        elif len(self._dm.devices) == 1:
            driver = self._dm.devices[list(self._dm.devices.keys())[0]]
        else:
            self.print_err("Multiple devices found, select one with --device")
            sys.exit(1)

        driver.defer_close = False

        return driver


    def run(self):
        self._args.func(self._args)
