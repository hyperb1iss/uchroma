from collections import OrderedDict
from typing import NamedTuple

from traitlets import HasTraits, Int, Float, Unicode, Bool
from gi.repository.GLib import Variant

from uchroma.renderer import RendererMeta
from uchroma.traits import ColorTrait, ColorSchemeTrait, ColorPresetTrait
from uchroma.util import ArgsDict, snake_to_camel


ArgSpec = NamedTuple('ArgSpec', [('direction', str), ('name', str), ('type', str)])


def variant(obj):
    sig = None

    if isinstance(obj, bool):
        sig = 'b'
    elif isinstance(obj, str):
        sig = 's'
    elif isinstance(obj, int):
        sig = 'i'
    elif isinstance(obj, float):
        sig = 'd'
    else:
        raise TypeError('Unable to create variant for %s (%s)' % (obj, type(obj)))

    return Variant(sig, obj)


class VariantDict(OrderedDict):
    def __init__(self, *args, **kwargs):
        super(VariantDict, self).__init__(*args, **kwargs)

        empty = []
        for k, v in self.items():
            if v is None:
                empty.append(k)
            else:
                self[k] = variant(v)
        for empty_key in empty:
            self.pop(empty_key)


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
    def __init__(self, obj, interface_name):
        self._interface_name = interface_name
        self._obj = obj
        self._ro_props = OrderedDict()
        self._rw_props = OrderedDict()
        self._methods = []

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


    def _parse_traits(self):
        for name, trait in self._obj.traits().items():
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
                sig = '(dddd)'
            elif isinstance(trait, ColorSchemeTrait):
                sig = 'a(dddd)'
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
            val += "    <property name='%s' type='%s' access='read' />\n" % (snake_to_camel(name), sig)

        for name, sig in self._rw_props.items():
            val += "    <property name='%s' type='%s' access='readwrite'>\n" % (snake_to_camel(name), sig)
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


        val += "    </interface>\n</node>"

        return val
