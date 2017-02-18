# pylint: disable=protected-access,redefined-variable-type
"""
Various helper functions that are used across the library.
"""
import logging
import sys

from argparse import ArgumentParser

from uchroma.client import UChromaClient
from uchroma.dbus_utils import dbus_prepare, snake_to_camel
from uchroma.version import __version__


class UChromaConsoleUtil(object):
    """
    A base class for command-line utilities
    """
    def __init__(self):
        self._parser = ArgumentParser(description=self.description, add_help=False)

        self._parser.add_argument('-v', '--version', action='version', version='self.version')
        self._parser.add_argument('--debug', action='store_true', help="Enable debug output")
        self._parser.add_argument('-d', '--device', type=str,
                                  help="Select target device name or index")

        sub = self._parser.add_subparsers(title='Subcommands')

        list_devs = sub.add_parser('list', help='List devices')
        list_devs.set_defaults(func=self._list_devices)

        self._add_subparsers(sub)

        self._args, self._unparsed = self._parser.parse_known_args()

        if self._args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        if not hasattr(self._args, 'func'):
            self._parser.print_help()
            sys.exit(1)

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
                    self.error("Error opening device: %s" % err)

            print('[%s]: %s (%s / %s)' % (dev.Key, dev.Name, serial_number, firmware_version))
        sys.exit(0)


    def error(self, message):
        self._parser.error(message)


    @property
    def description(self):
        return 'Color control for Razer Chroma peripherals'


    @property
    def version(self):
        return 'uChroma-%s' % __version__


    def _add_subparsers(self, sub):
        list_devs = sub.add_parser('list', help='List devices')
        list_devs.set_defaults(func=self._list_devices)


    def get_driver(self):
        driver = None

        if hasattr(self._args, 'device') and self._args.device is not None:
            driver = self._client.get_device(self._args.device)
            if driver is None:
                self.error("Invalid device: %s" % self._args.device)
                sys.exit(1)

        else:
            dev_paths = self._client.get_device_paths()
            if len(dev_paths) == 1:
                driver = self._client.get_device(dev_paths[0])
            else:
                self.error("Multiple devices found, select one with --device")
                sys.exit(1)

        return driver


    def set_property(self, target, name, value):
        name = snake_to_camel(name)
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
                value = dbus_prepare(value)[0]
        setattr(target, name, value)


    def run(self):
        self._args.func(self._args)
