# pylint: disable=protected-access
import importlib
import sys

from enum import Enum

from traitlets import CaselessStrEnum, Int, List, TraitType, Undefined, UseEnum

from uchroma.util import ArgsDict, camel_to_snake, to_color


class ColorTrait(TraitType):
    """
    A traitlet which encapsulates a grapefruit.Color and performs
    type coercion as needed.
    """

    default_value = None
    info_text = "A color in HTML string format (#8080ff, 'red', etc)"

    def __init__(self, default_value=Undefined, allow_none=True, **kwargs):
        super(ColorTrait, self).__init__(default_value=default_value,
                                         allow_none=allow_none, **kwargs)

    def validate(self, obj, value):
        try:
            if value is not None:
                value = to_color(value)
        except:
            self.error(obj, value)
        return value



class ColorSchemeTrait(List):
    """
    A list of ColorTraits which comprise a scheme
    """
    info_text = 'A list of colors to use, in HTML string format'

    def __init__(self, default_value=(), minlen=0, maxlen=sys.maxsize, **kwargs):
        super(ColorSchemeTrait, self).__init__(trait=ColorTrait,
                                               default_value=default_value,
                                               minlen=minlen, maxlen=maxlen, **kwargs)


class ColorPresetTrait(UseEnum):
    """
    A trait which represents a group of color schemes defined
    as a Python Enum.
    """
    info_text = 'A predefined color scheme'

    def __init__(self, enum_class, default_value=None, **kwargs):
        super(ColorPresetTrait, self).__init__(enum_class, default_value=default_value, **kwargs)



class WriteOnceMixin(object):
    write_once = True

    def validate(self, obj, value):
        if self.name not in obj._trait_values or obj._trait_values[self.name] == self.default_value:
            return super().validate(obj, value)
        self.error(obj, value)


class WriteOnceInt(WriteOnceMixin, Int):
    pass


class UseEnumCaseless(UseEnum):
    def select_by_name(self, value, default=Undefined):
        if value.startswith(self.name_prefix):
            # -- SUPPORT SCOPED-NAMES, like: "Color.red" => "red"
            value = value.replace(self.name_prefix, "", 1)

        keys = [x.lower() for x in self.enum_class.__members__.keys()]
        idx = keys.index(value.lower())
        if idx < 0:
            return Undefined
        return self.enum_class[list(self.enum_class.__members__.keys())[idx]]


def trait_as_dict(trait) -> dict:
    """
    Convert a trait to a dict for sending over D-Bus or the like
    """
    desc = {}
    desc['name'] = trait.name

    trait_type = trait.__class__.__name__
    if isinstance(trait, UseEnum):
        trait_type = CaselessStrEnum.__name__
        desc['values'] = list(trait.enum_class.__members__.keys())

    desc['type'] = trait_type

    write_once = False
    if hasattr(trait, 'write_once'):
        write_once = trait.write_once

    desc['read_only'] = trait.read_only or write_once
    desc['info'] = trait.info_text
    desc['help'] = trait.help
    desc['allow_none'] = trait.allow_none

    value = trait.default_value
    if isinstance(value, Enum):
        value = value.name
    if value is not Undefined:
        desc['default_value'] = value

    if hasattr(trait, 'min'):
        desc['min'] = trait.min
    if hasattr(trait, 'max'):
        desc['max'] = trait.max
    if hasattr(trait, '_minlen'):
        desc['minlen'] = trait._minlen
    if hasattr(trait, '_maxlen'):
        desc['maxlen'] = trait._maxlen
    return desc


TRAITLETS = importlib.import_module('traitlets')
LOCAL_TRAITS = importlib.import_module('uchroma.traits')

def dict_as_trait(obj):
    """
    Create a trait from a dict (trait_as_dict).
    """
    trait_type = obj.pop('type')
    cls = None
    if hasattr(LOCAL_TRAITS, trait_type):
        cls = getattr(LOCAL_TRAITS, trait_type)
    elif hasattr(TRAITLETS, trait_type):
        cls = getattr(TRAITLETS, trait_type)
    if cls is None:
        raise ValueError("Unknown trait: %s [%s]" % (trait_type, obj))

    if cls == CaselessStrEnum:
        return cls(obj.pop('values'), **obj)

    return cls(**obj)


def dict_as_class_traits(obj):
    traits = {}
    for k, v in obj.items():
        traits[k] = dict_as_trait(v)
    return traits


def get_args_dict(obj):
    argsdict = ArgsDict()
    for k in sorted(obj._trait_values.keys()):
        if k not in ('description', 'hidden', 'meta'):
            v = obj._trait_values[k]
            trait = obj.traits()[k]
            if trait.default_value != v and not trait.read_only \
                    and not (hasattr(trait, 'write_once') and trait.write_once):
                argsdict[k] = v
    return argsdict


class TraitsPropertiesMixin(object):
    def __init__(self, *args, **kwargs):
        super(TraitsPropertiesMixin, self).__init__(*args, **kwargs)


    def get_user_args(self) -> dict:
        return (self._delegate)


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
                return [tuple(x) for x in value]
            if isinstance(trait, ColorTrait):
                return tuple(value)
            if isinstance(trait, tuple) and hasattr(trait, '_asdict'):
                return trait._asdict()
            return value

        return super(TraitsPropertiesMixin, self).__getattribute__(name)


    def __setattr__(self, name, value):
        prop_name = camel_to_snake(name)
        if prop_name != name and self._delegate.has_trait(prop_name):
            return self._delegate.set_trait(prop_name, value)

        return super(TraitsPropertiesMixin, self).__setattr__(name, value)

