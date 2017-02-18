# pylint: disable=protected-access, invalid-name
import enum
import importlib
import sys

from traitlets import CaselessStrEnum, Container, Dict, Enum, Int, HasTraits, \
        List, TraitType, Undefined, UseEnum
from frozendict import frozendict

from uchroma.util import ArgsDict, camel_to_snake, to_color


MAGIC_TRAITS = ('hidden', 'meta', 'config', 'type')


class ColorTrait(TraitType):
    """
    A traitlet which encapsulates a grapefruit.Color and performs
    type coercion as needed.
    """

    info_text = "A color in HTML string format (#8080ff, 'red', etc)"

    def __init__(self, default_value='black', allow_none=False, **kwargs):
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

    def __init__(self, default_value=[], minlen=0, maxlen=sys.maxsize, **kwargs):
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


class FrozenDict(WriteOnceMixin, Dict):

    def validate(self, obj, value):
        return frozendict(super().validate(obj, value))


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
        desc['values'] = tuple(trait.enum_class.__members__.keys())

    desc['type'] = trait_type

    write_once = False
    if hasattr(trait, 'write_once'):
        write_once = trait.write_once

    desc['read_only'] = trait.read_only or write_once
    desc['info'] = trait.info_text
    desc['help'] = trait.help
    desc['allow_none'] = trait.allow_none

    value = trait.default_value
    if isinstance(value, enum.Enum):
        value = value.name
    if value is not Undefined:
        desc['default_value'] = value

    if hasattr(trait, 'min') and trait.min is not None:
        desc['min'] = trait.min
    if hasattr(trait, 'max') and trait.max is not None and trait.max < sys.maxsize:
        desc['max'] = trait.max
    if hasattr(trait, '_minlen') and trait._minlen is not None:
        desc['minlen'] = trait._minlen
    if hasattr(trait, '_maxlen') and trait._maxlen is not None and trait._maxlen < sys.maxsize:
        desc['maxlen'] = trait._maxlen

    return desc


def class_traits_as_dict(obj, incl_all=False):
    cls_dt = {}
    traits = {}
    if type(obj) == type:
        traits = obj.class_traits()
    elif isinstance(obj, dict):
        traits = obj
    else:
        traits = obj.__class__.traits()

    for k, v in traits.items():
        if k not in MAGIC_TRAITS or incl_all:
            dt = trait_as_dict(v)
            if dt is None:
                continue
            if not incl_all:
                if v.read_only or (hasattr(v, 'write_once') and v.write_once):
                    continue
            cls_dt[k] = dt
    return cls_dt


TRAITLETS = importlib.import_module('traitlets')
LOCAL_TRAITS = importlib.import_module('uchroma.traits')

def dict_as_trait(obj):
    """
    Create a trait from a dict (trait_as_dict).
    """
    trait_type = obj.pop('type', None)
    if trait_type is None:
        return None

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


def dict_as_class_traits(obj, incl_all=False):
    traits = {}
    for k, v in obj.items():
        if k not in MAGIC_TRAITS or incl_all:
            trait = dict_as_trait(v)
            if trait is None:
                continue
            if not incl_all:
                if trait.read_only or (hasattr(trait, 'write_once') and trait.write_once):
                    continue
            traits[k] = trait

    return traits


def get_args_dict(obj):
    argsdict = ArgsDict()
    for k in sorted(obj._trait_values.keys()):
        if k not in MAGIC_TRAITS:
            v = obj._trait_values[k]
            trait = obj.traits()[k]
            if trait.default_value != v and not trait.read_only \
                    and not (hasattr(trait, 'write_once') and trait.write_once):
                argsdict[k] = v
    return argsdict


def add_traits_to_argparse(traits: dict, parser, prefix: str=None):

    for key, trait in traits.items():
        if key in MAGIC_TRAITS:
            continue

        argname = '--%s' % key
        if prefix is not None:
            argname = '--%s.%s' % (prefix, key)

        if isinstance(trait, Container):
            parser.add_argument(argname, nargs='+', help=trait.info_text)
        elif isinstance(trait, Enum):
            parser.add_argument(argname, type=str,
                                choices=trait.values,
                                help=trait.info_text)
        else:
            argtype = str
            if hasattr(trait, 'default_value'):
                argtype = type(trait.default_value)
            parser.add_argument(argname, type=argtype, help=trait.info_text)


def apply_from_argparse(args, traits: dict=None, target=None) -> dict:
    """
    Applies arguments added via add_traits_to_argparse to
    a target object which implements HasTraits. If a target
    is not known, a dict of traits may be passed instead.
    Will throw TraitError if validation fails.

    :param args: Parsed args from argparse
    :param traits: Dictionary of traits (optional)
    :param target: Target object (optional)
    :return: Dict of the arguments which actually changed
    """
    # apply the traits to an empty object, which will run
    # the validators on the client
    if target is None:
        if traits is None:
            raise ValueError("Either traits or target must be specified")
        target = HasTraits()
        target.add_traits(**traits)

    # determine what should actually be changed
    argkeys = [k for k, v in args.__dict__.items() if v is not None]
    intersect = set(target.traits().keys()).intersection(set(argkeys))

    # apply the argparse flags to the target object
    for key in intersect:
        value = args.__dict__[key]
        setattr(target, key, getattr(args, key))

    # if all validators passed, return a dict of the changed args
    changed = {}
    for key in intersect:
        changed[key] = target._trait_values[key]

    return changed


class TraitsPropertiesMixin(object):
    def __init__(self, *args, **kwargs):
        super(TraitsPropertiesMixin, self).__init__(*args, **kwargs)


    def get_user_args(self) -> dict:
        return self._delegate


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
                    return ''
                return value.html
            if isinstance(trait, tuple) and hasattr(trait, '_asdict'):
                return trait._asdict()
            return value

        return super(TraitsPropertiesMixin, self).__getattribute__(name)


    def __setattr__(self, name, value):
        prop_name = camel_to_snake(name)
        if prop_name != name and self._delegate.has_trait(prop_name):
            return self._delegate.set_trait(prop_name, value)

        return super(TraitsPropertiesMixin, self).__setattr__(name, value)

