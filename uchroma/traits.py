# pylint: disable=protected-access, invalid-name, no-member
import enum
import importlib
import inspect
import sys

from traitlets import CaselessStrEnum, Container, Dict, Enum, Instance, Int, HasTraits, \
        List, TraitType, Undefined, UseEnum
from frozendict import frozendict
from grapefruit import Color

from uchroma.util import ArgsDict, camel_to_snake, to_color



class ColorTrait(TraitType):
    """
    A traitlet which encapsulates a grapefruit.Color and performs
    type coercion as needed.
    """
    info_text = "A color in HTML string format (#8080ff, 'red', etc)"
    allow_none = True
    default_value = 'black'

    def __init__(self, *args, **kwargs):
        super(ColorTrait, self).__init__(*args, **kwargs)

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

    def __init__(self, trait=ColorTrait, default_value=(),
                 minlen=0, maxlen=sys.maxsize, **kwargs):
        super(ColorSchemeTrait, self).__init__(trait=trait, default_value=default_value,
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


class WriteOnceUseEnumCaseless(WriteOnceMixin, UseEnumCaseless):
    pass


def is_trait_writable(trait) -> bool:
    if trait.read_only:
        return False

    if hasattr(trait, 'write_once') and trait.write_once:
        return False

    return True


def trait_as_dict(trait) -> dict:
    """
    Convert a trait to a dict for sending over D-Bus or the like
    """
    tdict = {k: v for k, v in vars(trait).items() if not k.startswith('__')}
    for key in list(tdict.keys()):
        if key.startswith('_'):
            tdict[key[1:]] = tdict.pop(key)

    params = inspect.signature(trait.__class__).parameters
    tdict = {k: v for k, v in tdict.items() if k in params and params[k].default != v}

    if 'klass' in tdict:
        klass = tdict.pop('klass')
        tdict['klass'] = '%s.%s' % (klass.__module__, klass.__name__)

    if 'enum_class' in tdict:
        klass = tdict.pop('enum_class')
        tdict['enum_class'] = '%s.%s' % (klass.__module__, klass.__name__)

    if 'trait' in tdict:
        tdict['trait'] = trait_as_dict(tdict.pop('trait'))

    ttype = trait.__class__

    if isinstance(trait, UseEnum):
        ttype = CaselessStrEnum
        tdict['values'] = tuple(trait.enum_class.__members__.keys())

    tdict['__class__'] = (ttype.__module__, ttype.__name__)

    if isinstance(trait.default_value, enum.Enum):
        tdict['default_value'] = trait.default_value.name

    return tdict


def class_traits_as_dict(obj):
    cls_dt = {}
    traits = {}
    if type(obj) == type and hasattr(obj, 'class_traits'):
        traits = obj.class_traits()
    elif isinstance(obj, dict):
        traits = obj
    elif isinstance(obj, HasTraits):
        traits = obj.traits()
    else:
        raise TypeError("Object does not support traits")

    for k, v in traits.items():
        dt = trait_as_dict(v)
        if dt is None:
            continue
        cls_dt[k] = dt
    return cls_dt


def dict_as_trait(obj):
    """
    Create a trait from a dict (trait_as_dict).
    """
    if '__class__' not in obj:
        raise ValueError("No module and class attribute present")

    tobj = obj.copy()

    module_name, trait_class = tobj.pop('__class__')

    module = importlib.import_module(module_name)
    if not hasattr(module, trait_class):
        raise TypeError("Unknown class: %s" % trait_class)
    cls = getattr(module, trait_class)

    if 'trait' in tobj:
        tobj['trait'] = dict_as_trait(tobj.pop('trait'))

    if issubclass(cls, Enum):
        trait = cls(tobj.pop('values'), **tobj)
    else:
        trait = cls(**tobj)

    return trait


def dict_as_class_traits(obj: dict):
    if not isinstance(obj, dict):
        raise TypeError("Object must be a dict (was: %s)" % obj)

    traits = {}
    for k, v in obj.items():
        trait = dict_as_trait(v)
        if trait is None:
            continue
        traits[k] = trait

    return traits


def get_args_dict(obj, incl_all=False):
    argsdict = ArgsDict()
    for k in sorted(obj._trait_values.keys()):
        v = obj._trait_values[k]
        trait = obj.traits()[k]
        if incl_all or (not trait.get_metadata('hidden') and is_trait_writable(trait)):
            argsdict[k] = v
    return argsdict


def add_traits_to_argparse(traits: dict, parser, prefix: str=None):

    for key, trait in traits.items():
        if not isinstance(trait, TraitType):
            if isinstance(trait, dict):
                trait = dict_as_trait(trait)
            else:
                raise TypeError("A dict or instance of HasTraits is required (was: %s)" % trait)

        if trait.get_metadata('hidden'):
            continue

        if trait.read_only:
            continue

        if hasattr(trait, 'write_once') and trait.write_once:
            continue

        argname = '--%s' % key
        if prefix is not None:
            argname = '--%s.%s' % (prefix, key)

        if isinstance(trait, Container):
            parser.add_argument(argname, nargs='+', help=trait.info_text)
        elif isinstance(trait, Enum):
            parser.add_argument(argname, type=str.lower,
                                choices=[x.lower() for x in trait.values],
                                help=trait.info_text)
        else:
            argtype = str
            if hasattr(trait, 'default_value'):
                argtype = type(trait.default_value)
            parser.add_argument(argname, type=argtype, help=trait.info_text)


def apply_from_argparse(args, traits=None, target=None) -> dict:
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
    traits = traits.copy()
    for k, v in traits.items():
        if not isinstance(v, TraitType):
            if isinstance(v, dict):
                k[v] = dict_as_trait(v)
            else:
                raise TypeError("A dict or trait object must be supplied")

    if target is None:
        if traits is None:
            raise ValueError("Either traits or target must be specified")
        target = HasTraits()
        target.add_traits(**traits)

    # determine what should actually be changed
    argkeys = [k for k, v in vars(args).items() if v is not None]
    intersect = set(target.traits().keys()).intersection(set(argkeys))

    # apply the argparse flags to the target object
    for key in intersect:
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

