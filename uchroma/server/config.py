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

# pylint: disable=no-member,protected-access, too-many-nested-blocks

import os
import sys
import tempfile

from collections import Iterable, OrderedDict
from contextlib import contextmanager
from itertools import chain

from enum import Enum

import ruamel.yaml as yaml

from uchroma.util import ArgsDict


class Configuration:
    """
    Configuration hierarchy

    This is a hierarchical object with attribute access. When a
    null attribute is queried, ask for the parent recursively.
    Supports key search, conversion to dict, change observation,
    and may be mutable or immutable. May be serialized to and
    from YAML. Attributes are forcibly coerced to the desired
    types when set.

    The format of the YAML output may be customized by adding
    parsers and representers, see the users of this class for
    examples.

    Call "create" to generate a derived type.
    """
    __slots__ = ()


    @classmethod
    def create(cls, name: str, fields: list, yaml_name: str = None, mutable: bool = False):
        """
        Derive a new Configuration class type.

        :param name: Name of the new type
        :param fields: List of fields and types
        :param yaml_name: Tag name for YAML serialization
        :param mutable: True if the object can be modified

        :return: The derived Configuration class
        """
        field_names = [n for n, t in fields]

        derived = cls.__class__(name, (cls, object), \
            {'__slots__': (*field_names, 'parent', '_children'),
             '_mutable': mutable,
             '_notify': True,
             '_traverse': True,
             '_yaml_cache': {},
             '_observers': set(),
             '_field_types': dict(fields)})

        derived._field_types['parent'] = derived

        if yaml_name is None:
            yaml_name = u'!%s' % derived.__name__.lower()

        def represent_config(dumper, data):
            """
            Dumps the object with a custom tag in sparse format
            """
            return dumper.represent_mapping(yaml_name, data.sparsedict(deep=False))

        yaml.RoundTripLoader.add_constructor(yaml_name, yaml.RoundTripLoader.construct_yaml_map)
        yaml.RoundTripDumper.add_multi_representer(derived, represent_config)

        return derived


    def __init__(self, parent=None, *args, **kwargs):
        slots = self.__slots__
        for k in slots:
            super().__setattr__(k, kwargs.get(k))

        if 'parent' not in slots:
            raise TypeError('Call create() to create a derived Configuration')

        super().__setattr__('parent', parent)
        if isinstance(parent, self.__class__) and hasattr(parent, '_add_child'):
            parent._add_child(self)


    def __del__(self):
        if hasattr(self, 'parent') and self.parent is not None:
            self.parent._remove_child(self)


    def __str__(self):
        clsname = self.__class__.__name__
        values = ', '.join('%s=%r' % (k, getattr(self, k)) \
            for k in self.__slots__ if k != 'parent' \
                and hasattr(self, k) and getattr(self, k) is not None)

        return '%s(%s)' % (clsname, values)


    __repr__ = __str__


    def __iter__(self):
        if self._children:
            return chain.from_iterable(self.flatten())
        return iter((self,))


    @contextmanager
    def observers_paused(self):
        self.__class__._notify = False
        yield
        self.__class__._notify = True


    @classmethod
    def observe(cls, observer):
        """
        Add an observer to this type

        The observer will fire when ANY instance of the type is changed.
        """
        cls._observers.add(observer)


    @classmethod
    def unobserve(cls, observer):
        """
        Remove a previously added observer from this type
        """
        cls._observers.discard(observer)


    @property
    def children(self) -> tuple:
        """
        Children which inherit properties of this instance
        """
        return self._children


    def _add_child(self, child):
        if self._children is None:
            super().__setattr__('_children', (child,))
        else:
            super().__setattr__('_children', (*self._children, child))


    def __setattr__(self, name, value):
        if not self.__class__._mutable:
            raise AttributeError('\'%s\' object is read-only (attr=\'%s\')' % \
                (self.__class__.__name__, name))
        super().__setattr__(name, value)

        if self.__class__._mutable and self.__class__._notify:
            for observer in self.__class__._observers:
                observer(self, name, value)


    def _remove_child(self, child):
        if self._children is None or child not in self._children:
            return

        super().__setattr__('_children', tuple([x for x in self._children if x != child]))


    def __getattribute__(self, key):
        item = object.__getattribute__(self, key)
        traverse = object.__getattribute__(self, '__class__')._traverse

        if not traverse or item is not None or \
                key in ('parent', 'children') or key.startswith('_'):
            return item

        if hasattr(self, 'parent') and self.parent is not None:
            return self.parent.__getattribute__(key)

        return None


    def __getitem__(self, key):
        """
        Intercepts calls to fetch from the tuple and searches up the
        hierarchy if necessary to populate fields.
        """
        if key <= len(self.__slots__):
            return getattr(self, self.__slots__[key])

        raise AttributeError('Invalid index: %s' % key)


    def get(self, key: str, default=None):
        """
        Get a field by name

        :param key: Field name
        :param default: Default value if None
        :return: Value of the field
        """
        value = self.__getitem__(self.__slots__.index(key))
        if value is None:
            return default
        return value


    def search(self, key: str, value: str):
        """
        Search for entries in the hierarchy

        :param key: Field name
        :param value: Field value
        :return: The matching field
        """
        def search_recursive(obj, key, value):
            """
            Recursive search
            """
            if obj.get(key) == value:
                yield obj
            if obj.children:
                for child in obj.children:
                    yield from search_recursive(child, key, value)
        return [x for x in search_recursive(self, key, value)]


    def flatten(self) -> list:
        """
        Flattens the hierarchy to a list of concrete objects.

        :return: The list of hardware objects
        """
        flat = []
        if self.children and isinstance(self.children, tuple):
            flat.extend([child.flatten() for child in self.children])
        else:
            tmp = {}
            for field in self.__slots__:
                if field not in ['parent', '_children']:
                    tmp[field] = self.get(field)
            return self.__class__(**tmp)
        return tuple(flat)


    def _asdict(self) -> OrderedDict:
        od = OrderedDict()
        for slot in self.__slots__:
            if slot in ('parent', '_children'):
                continue
            value = getattr(self, slot)
            if value is None:
                continue
            od[slot] = value
        return od


    def sparsedict(self, deep=True) -> OrderedDict:
        """
        Returns a "sparse" ordereddict with the parent->child relationships
        represented. This is used for serialization.

        :return: The sparse dict representation
        """
        self.__class__._traverse = False

        fields = tuple([x for x in self.__slots__ if x not in ['parent', '_children']])

        odict = ArgsDict({x: getattr(self, x) for x in fields})

        if self._children is not None:
            if deep:
                odict['children'] = [child.sparsedict() for child in self._children]
            else:
                odict['children'] = self._children

        self.__class__._traverse = True
        return odict


    @classmethod
    def _coerce_types(cls, mapping):
        """
        Convert simple types where necessary and ensure ordering
        """
        odict = OrderedDict()
        for field, field_type in cls._field_types.items():
            if field in mapping:
                val = mapping[field]
                if val is None:
                    continue

                if field_type is not None:
                    if isinstance(field_type, str):
                        scope = cls
                        if not hasattr(cls, field_type):
                            module = sys.modules[cls.__module__.split('.')[0]]
                            if hasattr(module, field_type):
                                scope = module
                            else:
                                raise ValueError("Can't convert field type '%s' in scope %s" \
                                    % (field_type, scope))
                        field_type = getattr(scope, field_type)

                    if isinstance(val, field_type):
                        odict[field] = val
                        continue

                    try:
                        if isinstance(val, dict) and issubclass(field_type, dict):
                            odict[field] = field_type(val.items())
                        elif isinstance(val, dict) and issubclass(field_type, tuple):
                            odict[field] = field_type(**val)
                        elif isinstance(val, Iterable) and issubclass(field_type, Iterable):
                            if hasattr(field_type, '__slots__'):
                                # namedtuple
                                odict[field] = field_type(*val)
                            else:
                                odict[field] = field_type(val)
                        elif isinstance(val, str) and issubclass(field_type, Enum):
                            odict[field] = field_type[val.upper()]
                        else:
                            if isinstance(val, list):
                                if issubclass(field_type, Enum):
                                    odict[field] = tuple([field_type[x.upper()] for x in val])
                                else:
                                    odict[field] = tuple([field_type(x) for x in val])
                            else:
                                odict[field] = field_type(val)

                    except (TypeError, ValueError):
                        raise ValueError("Can't coerce %s to type %s (from %s [%s])" %
                                         (field, field_type, val, type(val)))
                else:
                    odict[field] = val
        return odict


    @classmethod
    def load_yaml(cls, filename: str):
        """
        Load a hierarchy of sparse objects from a YAML file.

        :param filename: The filename to open.
        :return: The configuration object hierarchy
        """
        def unpack(mapping, parent=None):
            """
            Recursively create Configuration objects with the parent
            correctly set, returning the top-most parent.
            """
            if mapping is None:
                return None

            children = config = None

            if not isinstance(mapping, cls):
                children = mapping.pop('children', None)
                config = cls(**cls._coerce_types(mapping), parent=parent)

            if children:
                for child in children:
                    unpack(child, parent=config)
            return config

        if filename in cls._yaml_cache:
            return cls._yaml_cache[filename]

        data = None
        with open(filename, 'r') as yaml_file:
            data = unpack(yaml.round_trip_load(yaml_file.read()))

        if data is not None:
            cls._yaml_cache[filename] = data

        return data


    @property
    def yaml(self) -> str:
        """
        Get the YAML representation of this object as a string
        """
        return yaml.round_trip_dump(self)


    def _yaml_header(self) -> str:
        return None


    def save_yaml(self, filename: str = None):
        """
        Serialize the hierarchy to a file.

        :param filename: Target filename, autogenerated if None
        """
        if filename is None:
            filename = self.config_filename

        with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(filename),
                                         delete=False) as temp:
            header = self._yaml_header()
            if header is not None:
                temp.write(header)
            yaml.round_trip_dump(self, stream=temp)
            tempname = temp.name
        os.rename(tempname, filename)

        if filename in self.__class__._yaml_cache:
            del self.__class__._yaml_cache[filename]


# YAML library configuration
def represent_flow_seq(dumper, data):
    """
    Dump sequences in flow style
    """
    return dumper.represent_sequence(u'tag:yaml.org,2002:seq', data, flow_style=True)

def represent_enum_str(dumper, data):
    """
    Dump enums as string keys
    """
    return dumper.represent_str(data.name)

class FlowSequence(tuple):
    """
    A YAML sequence created from a tuple which will be represented
    in flowed style.
    """
    pass

class LowerCaseSeq(FlowSequence):
    """
    A YAML sequence which will always render in lowercase, in flow style.
    """
    def __new__(cls, args):
        items = []
        for x, _ in enumerate(args):
            items.append(_.lower())
        return super().__new__(cls, args)

yaml.RoundTripDumper.ignore_aliases = lambda *x: True
yaml.RoundTripDumper.add_multi_representer(Enum, represent_enum_str)
yaml.RoundTripDumper.add_multi_representer(FlowSequence, represent_flow_seq)

yaml.RoundTripDumper.add_multi_representer(OrderedDict, yaml.RoundTripDumper.represent_ordereddict)
