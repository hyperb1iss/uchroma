# pylint: disable=no-member, protected-access
import getpass
import os
import sys
import tempfile

from collections import Iterable, OrderedDict
from typing import NamedTuple

from datetime import datetime
from enum import Enum

import ruamel.yaml as yaml


class Configuration(object):
    """
    Configuration hierarchy

    This is a hierarchical hack to namedtuple. When a null attribute
    is queried, ask for the parent recursively.

    Also supports recursive serialization to/from YAML and type coercion.

    Call "create" to generate an instance.
    """

    __yaml_cache = {}
    _children = None

    @classmethod
    def create(cls, name, fields):
        """
        Create a new Configuration class type.
        """
        mixin_name = "_%sMixin" % name
        mixin = NamedTuple(mixin_name, fields)
        mixin.__new__.__defaults__ = (None,) * len(mixin._fields)

        derived = cls.__class__(name, (cls, mixin, object), {})

        return derived


    def __init__(self, parent=None, *args, **kwargs):
        if isinstance(parent, self.__class__) and hasattr(parent, '_add_child'):
            parent._add_child(self)


    def __del__(self):
        if self.parent is not None:
            self.parent._remove_child(self)


    @property
    def children(self) -> str:
        """
        Children which inherit properties of this instance
        """
        return self._children


    def _add_child(self, child):
        if self._children is None:
            self._children = (child,)
        else:
            self._children = (*self._children, child)


    def _remove_child(self, child):
        if self._children is None or child not in self._children:
            return

        self._children = tuple([x for x in self._children if x != child])


    def __getitem__(self, key):
        """
        Intercepts calls to fetch from the tuple and searches up the
        hierarchy if necessary to populate fields.
        """
        item = super().__getitem__(key)

        if key != self._fields.index('parent') and item is None and self.parent is not None:
            return self.parent.__getitem__(key)

        return item


    def get(self, key: str, default=None):
        """
        Get a field by name

        :param key: Field name
        :param default: Default value if None
        :return: Value of the field
        """
        value = self.__getitem__(self._fields.index(key))
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
            if obj.get(key) == value:
                yield obj
            if obj.children is not None and len(obj.children) > 0:
                for child in obj.children:
                    yield from search_recursive(child, key, value)
        return [x for x in search_recursive(self, key, value)]


    def flatten(self) -> list:
        """
        Flattens the hierarchy to a list of concrete objects.

        :return: The list of hardware objects
        """
        flat = []
        if self.children is not None and len(self.children) > 0:
            flat.extend([child.flatten() for child in self.children])
        else:
            tmp = {}
            for field in self._fields:
                if field not in ['parent', '_children']:
                    tmp[field] = self.get(field)
            return self.__class__(**tmp)
        return flat


    def sparsedict(self, deep=True) -> OrderedDict:
        """
        Returns a "sparse" ordereddict with the parent->child relationships
        represented. This is used for serialization.

        :return: The sparse dict representation
        """
        fields = tuple([x for x in self._fields if x not in ['parent', '_children']])

        odict = OrderedDict([x for x in zip(fields, self) if x[1] is not None])

        if self._children is not None:
            if deep:
                odict['children'] = [child.sparsedict() for child in self._children]
            else:
                odict['children'] = self._children

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
                        if isinstance(val, dict) and (issubclass(field_type, tuple) or \
                                                      issubclass(field_type, dict)):
                            odict[field] = field_type(**val)
                        elif isinstance(val, Iterable) and issubclass(field_type, Iterable):
                            odict[field] = field_type(*val)
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

            if children is not None and len(children) > 0:
                for child in children:
                    unpack(child, parent=config)
            return config

        if filename in cls.__yaml_cache:
            return cls.__yaml_cache[filename]

        data = None
        with open(filename, 'r') as yaml_file:
            data = unpack(yaml.round_trip_load(yaml_file.read()))

        if data is not None:
            cls.__yaml_cache[filename] = data

        return data


    @property
    def yaml(self):
        return yaml.round_trip_dump(self)


    def save_yaml(self, filename: str=None):
        """
        Serialize the hierarchy to a file.

        :param filename: Target filename, autogenerated if None
        """
        if filename is None:
            filename = self.config_filename

        with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(filename),
                                         delete=False) as temp:
            temp.write('#\n')
            temp.write('#  uChroma device configuration\n')
            temp.write('#\n')
            if self.name is not None:
                temp.write('#  Model: %s (%s)\n' % \
                    (self.name, self.type.value))
            elif self.type is not None:
                temp.write('#  Type: %s\n' % self.type)
            temp.write('#  Created by %s on %s\n' % \
                (getpass.getuser(), datetime.now().isoformat(' ')))
            temp.write('#\n')
            yaml.round_trip_dump(self, stream=temp)
            tempname = temp.name
        os.rename(tempname, filename)

        if filename in self.__class__.__yaml_cache:
            del self.__class__.__yaml_cache[filename]

