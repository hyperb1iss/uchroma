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

# pylint: disable=invalid-name

import os
import time
from collections import OrderedDict
from datetime import datetime

import ruamel.yaml as yaml

from uchroma.colorlib import Color
from uchroma.util import Singleton

from .config import Configuration

CONFDIR = os.path.join(os.path.expanduser("~"), ".config", "uchroma")
CONFFILE = os.path.join(CONFDIR, "preferences.yaml")


_Preferences = Configuration.create(
    "_Preferences",
    [
        ("last_updated", float),
        ("serial", str),
        ("brightness", float),
        ("leds", dict),
        ("fx", str),
        ("fx_args", OrderedDict),
        ("layers", OrderedDict),
    ],
    mutable=True,
    yaml_name="!preferences",
)


class Preferences(_Preferences):
    def _yaml_header(self) -> str:
        header = "#\n#  uChroma preferences\n#\n"
        header += "#  Updated on: {}\n".format(datetime.now().isoformat(" "))
        header += "#\n"
        return header


class PreferenceManager(metaclass=Singleton):
    """
    Hierarchical preferences holder.

    Automatically serializes to YAML when items
    are changed. This class is a singleton.
    """

    def __init__(self):
        self._root = PreferenceManager._load_prefs()
        self._root.__class__.observe(self._preferences_changed)

    def _preferences_changed(self, obj, name, value):
        if name != "last_updated":
            self._save_prefs()

    @staticmethod
    def _load_prefs():
        os.makedirs(CONFDIR, exist_ok=True)
        if os.path.isfile(CONFFILE):
            prefs = Preferences.load_yaml(CONFFILE)
            assert prefs is not None
            return prefs
        return Preferences(last_updated=time.time())

    def _save_prefs(self):
        self._root.last_updated = time.time()
        self._root.save_yaml(CONFFILE)

    def get(self, serial: str | None) -> Preferences:
        """
        Get the preference hierarchy for the given device serial number.
        """
        result = self._root.search("serial", serial)
        if not result:
            result = Preferences(parent=self._root, serial=serial)

        if isinstance(result, list) and result:
            return result[0]

        return result


def represent_color(dumper, data):
    return dumper.represent_scalar("!color", data.html)


def construct_color(loader, node):
    val = loader.construct_yaml_str(node)
    return Color.NewFromHtml(val)


yaml.RoundTripDumper.add_representer(Color, represent_color)
yaml.RoundTripLoader.add_constructor("!color", construct_color)
