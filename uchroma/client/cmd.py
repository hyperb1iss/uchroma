#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

# pylint: disable=protected-access,redefined-variable-type

"""
Various helper functions that are used across the library.
"""

import logging
from argparse import ArgumentParser

from argcomplete import autocomplete

from uchroma.dbus_utils import dbus_prepare, snake_to_camel
from uchroma.version import __version__

from .dbus_client import UChromaClient


class UChromaConsoleUtil:
    """
    A base class for command-line utilities
    """

    def __init__(self):
        self._parser = ArgumentParser(description=self.description, add_help=False)

        self._parser.add_argument("-v", "--version", action="version", version=self.version)
        self._parser.add_argument("-g", "--debug", action="store_true", help="Enable debug output")
        self._parser.add_argument(
            "-d", "--device", type=str, help="Select target device name or index"
        )
        self._parser.add_argument(
            "-l", "--list", action="store_true", help="List available devices"
        )

        self._args, self._unparsed = self._parser.parse_known_args()

        if self._args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        self._client = UChromaClient()

        if self._args.list:
            self._list_devices(self._args)
            self._parser.exit()

        sub = self._parser.add_subparsers(title="Subcommands")

        self._add_subparsers(sub)

        autocomplete(self._parser)
        self._args, self._unparsed = self._parser.parse_known_args(self._unparsed, self._args)

        if not hasattr(self._args, "func"):
            self._parser.print_help()
            self._parser.exit(1)

    def _list_devices(self, args):
        for dev_path in self._client.get_device_paths():
            dev = self._client.get_device(dev_path)
            serial_number = firmware_version = "Unknown"
            try:
                serial_number = dev.SerialNumber
                firmware_version = dev.FirmwareVersion
            except OSError as err:
                if self._args.debug:
                    args.parser.error(f"Error opening device: {err}")

            print(f"[{dev.Key}]: {dev.Name} ({serial_number} / {firmware_version})")

    @property
    def description(self):
        return "Color control for Razer Chroma peripherals"

    @property
    def version(self):
        return f"uchroma-{__version__}"

    def _add_subparsers(self, sub):
        pass

    def get_driver(self):
        if hasattr(self._args, "device") and self._args.device is not None:
            driver = self._client.get_device(self._args.device)
            if driver is None:
                self._parser.error(f"Invalid device: {self._args.device}")

        else:
            dev_paths = self._client.get_device_paths()
            if len(dev_paths) == 1:
                driver = self._client.get_device(dev_paths[0])
            else:
                self._list_devices(self._args)
                self._parser.error("Multiple devices found, select one with --device")

        return driver

    def set_property(self, target, name, value):
        name = snake_to_camel(name)
        if not hasattr(target, name):
            raise ValueError(f"Invalid property: {name}")
        cls_obj = getattr(target.__class__, name)
        if hasattr(cls_obj, "_type"):
            typespec = cls_obj._type
            if typespec == "s":
                value = str(value)
            elif typespec == "d":
                value = float(value)
            elif typespec == "u" or typespec == "i":
                value = int(value)
            elif typespec == "b":
                value = bool(value)
            else:
                value = dbus_prepare(value)[0]
        setattr(target, name, value)

    def run(self):
        self._args.unparsed = self._unparsed
        self._args.func(self._args)
