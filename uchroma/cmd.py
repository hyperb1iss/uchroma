# pylint: disable=protected-access,redefined-variable-type
"""
Various helper functions that are used across the library.
"""
import argparse
import logging
import sys

from uchroma.client import UChromaClient
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
        self._client = UChromaClient()


    def _list_devices(self, args):
        for dev_path in self._client.get_device_paths():
            dev = self._client.get_device(dev_path)
            serial_number = firmware_version = "Unknown"
            try:
                serial_number = dev.SerialNumber
                firmware_version = dev.FirmwareVersion
            except IOError as err:
                if self._args.debug:
                    self.print_err("Error opening device: %s" % err)

            print('[%s]: %s (%s / %s)' % (dev.Key, dev.Name, serial_number, firmware_version))
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
        print(' '.join([str(x) for x in args]) + '\n', file=sys.stderr)


    def get_driver(self, args):
        driver = None

        if args.device is not None:
            driver = self._client.get_device(args.device)
            if driver is None:
                self.print_err("Invalid device: %s" % args.device)
                sys.exit(1)

        else:
            dev_paths = self._client.get_device_paths()
            if len(dev_paths) == 1:
                driver = self._client.get_device(dev_paths[0])
            else:
                self.print_err("Multiple devices found, select one with --device")
                sys.exit(1)

        return driver


    def set_property(self, target, name, value):
        if not hasattr(target, name):
            raise ValueError("Invalid property: %s" % name)
        cls_obj = getattr(target.__class__, name)
        if hasattr(cls_obj, '_type'):
            typespec = cls_obj._type
            if typespec == 's':
                value = str(value)
            elif typespec == 'd':
                value = float(value)
            elif typespec == 'u' or typespec == 'i':
                value = int(value)
            elif typespec == 'b':
                value = bool(value)
            else:
                raise TypeError("Unable to handle type %s" % typespec)
        setattr(target, name, value)


    def run(self):
        self._args.func(self._args)
