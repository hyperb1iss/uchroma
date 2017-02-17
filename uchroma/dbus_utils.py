# pylint: disable=invalid-name
import enum

from collections import OrderedDict
from typing import NamedTuple

from frozendict import frozendict
from gi.repository.GLib import Variant
from grapefruit import Color
from traitlets import HasTraits, Int, Float, Unicode, Bool, TraitType

import numpy as np

from uchroma.renderer import RendererMeta
from uchroma.traits import ColorTrait, ColorSchemeTrait, ColorPresetTrait, trait_as_dict
from uchroma.util import get_logger, snake_to_camel


ArgSpec = NamedTuple('ArgSpec', [('direction', str), ('name', str), ('type', str)])

logger = get_logger('uchroma.util')

def dbus_prepare(obj, variant: bool=False, camel_keys: bool=False) -> tuple:
    """
    Recursively walks obj and builds a D-Bus signature
    by inspecting types. Variant types are created as
    necessary, and the returned obj may have changed.

    :param obj: An arbitrary primitive or container type
    :param variant: Force wrapping contained objects with variants
    :param camel_keys: Convert dict keys to CamelCase
    """
    sig = ''
    v_force = variant

    try:
        if isinstance(obj, bool):
            sig = 'b'

        elif isinstance(obj, str):
            sig = 's'

        elif isinstance(obj, int):
            sig = 'x'

        elif isinstance(obj, float):
            sig = 'd'

        elif isinstance(obj, Color):
            sig = 's'
            obj = obj.html

        elif isinstance(obj, TraitType):
            obj, sig = dbus_prepare(trait_as_dict(obj))

        elif hasattr(obj, '_asdict') and hasattr(obj, '_field_types'):
            # typing.NamedTuple
            obj, sig = dbus_prepare(obj._asdict())

        elif isinstance(obj, enum.EnumMeta):
            # top level enum, tuple of string keys
            obj = tuple(obj.__members__.keys())
            sig = '(%s)' % ('s' * len(obj))

        elif isinstance(obj, enum.Enum):
            obj = obj.name
            sig = 's'

        elif isinstance(obj, tuple):
            if len(obj) > 0:
                tmp = []
                sig = '('
                for item in obj:
                    # struct of all items
                    r_obj, r_sig = dbus_prepare(item)
                    sig += r_sig
                    tmp.append(r_obj)
                sig += ')'
                obj = tuple(tmp)

        elif isinstance(obj, list):
            if len(obj) > 0:
                tmp = []
                sig = 'a'
                if not v_force and all(isinstance(x, type(obj[0])) for x in obj):
                    # all items same type
                    for item in obj:
                        if item is None:
                            continue
                        r_obj, r_sig = dbus_prepare(item)
                        tmp.append(r_obj)
                    sig += dbus_prepare(tmp[0])[1]
                else:
                    # wrap items with variants
                    for item in obj:
                        if item is None:
                            continue
                        r_obj, r_sig = dbus_prepare(item, variant=v_force)
                        if r_obj is None:
                            tmp.append(None)
                        else:
                            tmp.append(Variant(r_sig, r_obj))
                    sig += 'v'
                obj = tmp

        elif isinstance(obj, (dict, frozendict)):
            if len(obj) > 0:
                if isinstance(obj, frozendict):
                    tmp = {}
                else:
                    tmp = obj.__class__()
                vals = list(obj.values())
                sig = 'a{s'

                if not variant and all(isinstance(x, type(vals[0])) for x in vals):
                    # all values same type
                    for k, v in obj.items():
                        if v is None:
                            continue
                        r_obj, r_sig = dbus_prepare(v, variant=v_force)
                        if camel_keys:
                            k = snake_to_camel(k)
                        tmp[k] = r_obj
                    if len(tmp) > 0:
                        sig += dbus_prepare(vals[0])[1]
                else:
                    # wrap values with variants
                    for k, v in obj.items():
                        if v is None:
                            continue
                        r_obj, r_sig = dbus_prepare(v, variant=v_force)
                        if camel_keys:
                            k = snake_to_camel(k)
                        if r_obj is None:
                            tmp[k] = None
                        else:
                            tmp[k] = Variant(r_sig, r_obj)
                    sig += 'v'
                obj = tmp
                sig += '}'

        elif isinstance(obj, type):
            obj = obj.__name__
            sig = 's'

    except Exception as err:
        logger.exception('obj: %s  sig: %s', obj, sig, exc_info=err)
        raise

    return obj, sig


class DescriptorBuilder(object):
    """
    Helper class for creating D-BUS XML descriptors

    While pydbus allows inline specification of the descriptor,
    frequently the descriptor needs to be dynamic or based on class
    introspection. This builder lets us create it at runtime
    with a simple interface. Additionally, we inspect traitlets
    from the target object and generate properties to match.

    The descriptor needs to be placed in the 'dbus' attribute of the
    type before registering the object on the bus. Example:

      api.__class__.dbus = builder.build()
      bus.register_object(path, api, None)
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


    def add_property(self, name: str, signature: str, writable: bool=False):
        if writable:
            self._rw_props[name] = signature
        else:
            self._ro_props[name] = signature
        return self


    def add_method(self, method, *argspecs):
        opts = {}
        opts['name'] = method
        if argspecs is not None and len(argspecs) > 0:
            opts['args'] = argspecs

        self._methods.append(opts)
        return self


    def add_signal(self, signal, *argspecs):
        opts = {}
        opts['name'] = signal
        if argspecs is not None and len(argspecs) > 0:
            opts['args'] = argspecs

        self._signals.append(opts)
        return self


    def _parse_traits(self):
        for name, trait in self._obj.traits().items():
            if self._exclude is not None and name in self._exclude:
                continue

            sig = None
            if isinstance(trait, Unicode):
                sig = 's'
            elif isinstance(trait, Int):
                if trait.min is None or trait.min < 0:
                    sig = 'i'
                else:
                    sig = 'u'
            elif isinstance(trait, Float):
                sig = 'd'
            elif isinstance(trait, Bool):
                sig = 'b'
            elif isinstance(trait, ColorTrait):
                sig = 's'
            elif isinstance(trait, ColorSchemeTrait):
                sig = 'as'
            elif isinstance(trait, ColorPresetTrait):
                sig = 's'
            elif isinstance(trait, RendererMeta):
                sig = 'a{ss}'

            write_once = False
            if hasattr(trait, 'write_once'):
                write_once = trait.write_once

            self.add_property(snake_to_camel(name), sig, not (trait.read_only or write_once))


    def with_user_args(self, method_name):
        self.add_method(method_name, ArgSpec('out', 'traits', 'a{sa{sv}}'))
        return self


    def build(self) -> str:
        val = "<node>\n  <interface name='%s'>\n" % self._interface_name

        for name, sig in self._ro_props.items():
            val += "    <property name='%s' type='%s' access='read' />\n" % \
                (snake_to_camel(name), sig)

        for name, sig in self._rw_props.items():
            val += "    <property name='%s' type='%s' access='readwrite'>\n" % \
                (snake_to_camel(name), sig)
            val += "      <annotation name='org.freedesktop.DBus.Property.EmitsChangedSignal' value='true' />\n"
            val += "    </property>\n"

        for method in self._methods:
            name = snake_to_camel(method['name'])
            if not 'args' in method:
                val += "    <method name='%s' />\n" % name
            else:
                val += "    <method name='%s'>\n" % name
                for argspec in method['args']:
                    val += "      <arg direction='%s' type='%s' name='%s' />\n" % \
                        (argspec.direction, argspec.type, argspec.name)
                val += "    </method>\n"

        for signal in self._signals:
            name = snake_to_camel(signal['name'])
            if not 'args' in signal:
                val += "    <signal name='%s' />\n" % name
            else:
                val += "    <signal name='%s'>\n" % name
                for argspec in signal['args']:
                    val += "      <arg direction='%s' type='%s' name='%s' />\n" % \
                        (argspec.direction, argspec.type, argspec.name)
                val += "    </signal>\n"


        val += "  </interface>\n</node>"

        return val
