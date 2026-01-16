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

# pylint: disable=invalid-name, redefined-variable-type

import enum
from collections import OrderedDict
from typing import NamedTuple

import numpy as np
from dbus_fast import Variant
from frozendict import frozendict
from traitlets import HasTraits, TraitType, Undefined, UseEnum

from uchroma.colorlib import Color
from uchroma.log import Log
from uchroma.traits import ColorSchemeTrait, ColorTrait, class_traits_as_dict, trait_as_dict
from uchroma.util import camel_to_snake, snake_to_camel


class ArgSpec(NamedTuple):
    direction: str
    name: str
    type: str


logger = Log.get("uchroma.util")


def _check_variance(items: list):
    if len(items) == 0:
        return True

    if len(items) == 1:
        return False

    first_sig = dbus_prepare(items[0])[1]

    return not all(dbus_prepare(x)[1] == first_sig for x in items)


def dbus_prepare(obj, variant: bool = False, camel_keys: bool = False) -> tuple:
    """
    Recursively walks obj and builds a D-Bus signature
    by inspecting types. Variant types are created as
    necessary, and the returned obj may have changed.

    :param obj: An arbitrary primitive or container type
    :param variant: Force wrapping contained objects with variants
    :param camel_keys: Convert dict keys to CamelCase
    """
    sig = ""
    use_variant = variant

    try:
        if isinstance(obj, Variant):
            sig = "v"

        elif isinstance(obj, bool):
            sig = "b"

        elif isinstance(obj, str):
            sig = "s"

        elif isinstance(obj, int):
            if obj < pow(2, 16):
                sig = "n"
            elif obj < pow(2, 32):
                sig = "i"
            else:
                sig = "x"

        elif isinstance(obj, float):
            sig = "d"

        elif isinstance(obj, Color):
            sig = "s"
            obj = obj.html

        elif isinstance(obj, TraitType):
            obj, sig = dbus_prepare(trait_as_dict(obj), variant=True)

        elif isinstance(obj, HasTraits):
            obj, sig = dbus_prepare(class_traits_as_dict(obj), variant=True)

        elif hasattr(obj, "_asdict") and (
            hasattr(obj, "_field_types") or hasattr(obj, "__annotations__")
        ):
            # typing.NamedTuple (Python 3.13+ uses __annotations__, older used _field_types)
            obj, sig = dbus_prepare(obj._asdict(), variant=True)

        elif isinstance(obj, type) and issubclass(obj, enum.Enum):
            # top level enum, tuple of string keys
            obj = tuple(obj.__members__.keys())
            sig = "(%s)" % ("s" * len(obj))

        elif isinstance(obj, enum.Enum):
            obj = obj.name
            sig = "s"

        elif isinstance(obj, np.ndarray):
            dtype = obj.dtype.kind
            if dtype == "f":
                dtype = "d"
            sig = "a" * obj.ndim + dtype
            obj = obj.tolist()

        elif isinstance(obj, tuple):
            tmp = []
            sig = "("

            for item in obj:
                if item is None and use_variant:
                    continue
                # struct of all items
                r_obj, r_sig = dbus_prepare(item)
                if r_obj is None:
                    continue
                sig += r_sig
                tmp.append(r_obj)
            if len(tmp) > 0:
                sig += ")"
                obj = tuple(tmp)
            else:
                sig = ""
                obj = None

        elif isinstance(obj, list):
            tmp = []
            sig = "a"
            is_variant = use_variant or _check_variance(obj)

            for item in obj:
                if item is None and is_variant:
                    continue
                r_obj, r_sig = dbus_prepare(item, variant=is_variant)
                if r_obj is None:
                    continue

                tmp.append(r_obj)

            if is_variant:
                sig += "v"
            else:
                sig += dbus_prepare(tmp[0])[1]

            obj = tmp

        elif isinstance(obj, (dict, frozendict)):
            if isinstance(obj, frozendict):
                tmp = {}
            else:
                tmp = obj.__class__()
            sig = "a{s"
            vals = [x for x in obj.values() if x is not None]
            is_variant = use_variant or _check_variance(vals)

            for k, v in obj.items():
                if v is None:
                    continue
                r_obj, r_sig = dbus_prepare(v)
                if r_obj is None:
                    continue
                if camel_keys:
                    k = snake_to_camel(k)
                if is_variant:
                    tmp[k] = Variant(r_sig, r_obj)
                else:
                    tmp[k] = r_obj

            if is_variant:
                sig += "v"
            else:
                sig += dbus_prepare(vals[0])[1]

            obj = tmp
            sig += "}"

        elif isinstance(obj, type):
            obj = obj.__name__
            sig = "s"

    except Exception as err:
        logger.exception("obj: %s  sig: %s variant: %s", obj, sig, variant, exc_info=err)
        raise

    return obj, sig


class DescriptorBuilder:
    """
    Helper class for creating D-BUS XML descriptors

    Introspects traitlets and generates XML descriptors dynamically.
    Useful for creating interfaces based on runtime class inspection.
    """

    def __init__(self, obj, interface_name, exclude=None):
        self._interface_name = interface_name
        self._obj = obj
        self._ro_props = OrderedDict()
        self._rw_props = OrderedDict()
        self._methods = []
        self._signals = []
        self._exclude = exclude

        if isinstance(obj, HasTraits):
            self._parse_traits()

    def add_property(self, name: str, signature: str, writable: bool = False):
        if writable:
            self._rw_props[name] = signature
        else:
            self._ro_props[name] = signature
        return self

    def add_method(self, method, *argspecs):
        opts = {}
        opts["name"] = method
        if argspecs is not None and len(argspecs) > 0:
            opts["args"] = argspecs

        self._methods.append(opts)
        return self

    def add_signal(self, signal, *argspecs):
        opts = {}
        opts["name"] = signal
        if argspecs is not None and len(argspecs) > 0:
            opts["args"] = argspecs

        self._signals.append(opts)
        return self

    def _parse_traits(self):
        for name, trait in self._obj.traits().items():
            if self._exclude is not None and name in self._exclude:
                continue

            sig = None
            if hasattr(self._obj, name):
                sig = dbus_prepare(getattr(self._obj, name))[1]

            write_once = False
            if hasattr(trait, "write_once"):
                write_once = trait.write_once

            self.add_property(snake_to_camel(name), sig, not (trait.read_only or write_once))

    def build(self) -> str:
        val = "<node>\n  <interface name='%s'>\n" % self._interface_name

        for name, sig in self._ro_props.items():
            val += "    <property name='%s' type='%s' access='read' />\n" % (
                snake_to_camel(name),
                sig,
            )

        for name, sig in self._rw_props.items():
            val += "    <property name='%s' type='%s' access='readwrite'>\n" % (
                snake_to_camel(name),
                sig,
            )
            val += "      <annotation name='org.freedesktop.DBus.Property.EmitsChangedSignal' value='true' />\n"
            val += "    </property>\n"

        for method in self._methods:
            name = snake_to_camel(method["name"])
            if "args" not in method:
                val += "    <method name='%s' />\n" % name
            else:
                val += "    <method name='%s'>\n" % name
                for argspec in method["args"]:
                    val += "      <arg direction='%s' type='%s' name='%s' />\n" % (
                        argspec.direction,
                        argspec.type,
                        argspec.name,
                    )
                val += "    </method>\n"

        for signal in self._signals:
            name = snake_to_camel(signal["name"])
            if "args" not in signal:
                val += "    <signal name='%s' />\n" % name
            else:
                val += "    <signal name='%s'>\n" % name
                for argspec in signal["args"]:
                    val += "      <arg direction='%s' type='%s' name='%s' />\n" % (
                        argspec.direction,
                        argspec.type,
                        argspec.name,
                    )
                val += "    </signal>\n"

        val += "  </interface>\n</node>"

        return val


class TraitsPropertiesMixin:
    def __init__(self, *args, **kwargs):
        super(TraitsPropertiesMixin, self).__init__(*args, **kwargs)

    def __getattribute__(self, name):
        # Intercept everything and delegate to the device class by converting
        # names between the D-Bus conventions to Python conventions.
        prop_name = camel_to_snake(name)
        if prop_name != name and self._delegate.has_trait(prop_name):
            value = getattr(self._delegate, prop_name)
            trait = self._delegate.traits()[prop_name]
            if isinstance(trait, UseEnum):
                return value.name.title()
            if isinstance(trait, ColorSchemeTrait):
                return [x.html for x in value]
            if isinstance(trait, ColorTrait):
                if value is None or value is Undefined:
                    return ""
                return value.html
            if isinstance(trait, tuple) and hasattr(trait, "_asdict"):
                return trait._asdict()
            return value

        return super(TraitsPropertiesMixin, self).__getattribute__(name)

    def __setattr__(self, name, value):
        prop_name = camel_to_snake(name)
        if prop_name != name and self._delegate.has_trait(prop_name):
            return self._delegate.set_trait(prop_name, value)

        return super(TraitsPropertiesMixin, self).__setattr__(name, value)
