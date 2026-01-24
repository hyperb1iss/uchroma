#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=protected-access, invalid-name, no-member

import enum
import importlib
import sys
from argparse import ArgumentParser
from collections.abc import Iterable
from types import MappingProxyType

from traitlets import (
    CaselessStrEnum,
    Container,
    Dict,
    Enum,
    HasTraits,
    Int,
    List,
    TraitType,
    Undefined,
    UseEnum,
)

from uchroma.color import to_color
from uchroma.util import filter_none


class ColorTrait(TraitType):
    """
    A traitlet which encapsulates a grapefruit.Color and performs
    type coercion as needed.
    """

    info_text = "a color"
    allow_none = True
    default_value = "black"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, obj, value):
        try:
            if value is not None:
                value = to_color(value)
        except Exception:
            self.error(obj, value)
        return value


class ColorSchemeTrait(List):
    """
    A list of ColorTraits which comprise a scheme
    """

    info_text = "a list of colors"

    def __init__(self, trait=None, default_value=None, minlen=0, maxlen=sys.maxsize, **kwargs):
        if trait is None:
            trait = ColorTrait()
        if default_value is None:
            default_value = []
        super().__init__(
            trait=trait, default_value=default_value, minlen=minlen, maxlen=maxlen, **kwargs
        )


class ColorPresetTrait(UseEnum):
    """
    A trait which represents a group of color schemes defined
    as a Python Enum.
    """

    info_text = "a predefined color scheme"

    def __init__(self, enum_class, default_value=None, **kwargs):
        super().__init__(enum_class, default_value=default_value, **kwargs)


class WriteOnceMixin:
    """
    Mixin for traits which cannot be changed after an initial
    value has been set.
    """

    write_once = True

    def validate(self, obj, value):
        if self.name not in obj._trait_values or obj._trait_values[self.name] == self.default_value:
            return super().validate(obj, value)

        self.error(obj, value)


class WriteOnceInt(WriteOnceMixin, Int):
    """
    Subclass of Int which may only be written once
    """


class FrozenDict(WriteOnceMixin, Dict):
    """
    Subclass of Dict which converts the value to a MappingProxyType on
    the first setting, making it immutable.
    """

    def validate(self, obj, value):
        return MappingProxyType(super().validate(obj, value))


class UseEnumCaseless(UseEnum):
    """
    Subclass of UseEnum which allows selection of values using
    case insensitive strings
    """

    def select_by_name(self, value, default=Undefined):
        if value.startswith(self.name_prefix):
            # -- SUPPORT SCOPED-NAMES, like: "Color.red" => "red"
            value = value.replace(self.name_prefix, "", 1)

        keys = [x.lower() for x in self.enum_class.__members__]
        idx = keys.index(value.lower())
        if idx < 0:
            return Undefined
        return self.enum_class[list(self.enum_class.__members__.keys())[idx]]


class WriteOnceUseEnumCaseless(WriteOnceMixin, UseEnumCaseless):
    """
    Subclass of UseEnumCaseless which may only be written once.
    """


class DefaultCaselessStrEnum(CaselessStrEnum):
    """
    Extension of CaselessStrEnum which handles default values better
    """

    def validate(self, obj, value):
        if self.default_value and (value is None or value == ""):
            value = self.default_value

        return super().validate(obj, value)


def is_trait_writable(trait: TraitType) -> bool:
    """
    Test if a trait is writable

    :param trait: the trait to be tested
    :return: True if the trait is writable
    """
    if trait.read_only:
        return False

    return not (hasattr(trait, "write_once") and trait.write_once)


def trait_as_dict(trait: TraitType) -> dict:
    """
    Convert a trait to a dict for sending over D-Bus or the like

    :param trait: the trait to be converted
    :return: dict representing this trait
    """
    cls = trait.__class__
    tdict = {}

    for k, v in vars(trait).items():
        if k.startswith("__") or k == "this_class":
            continue
        if hasattr(cls, k) and getattr(cls, k) == v:
            continue
        if isinstance(v, Iterable) and len(v) == 0:
            continue

        if k.startswith("_"):
            tdict[k[1:]] = v
        else:
            tdict[k] = v

    if isinstance(trait, UseEnum):
        cls = CaselessStrEnum
        tdict["values"] = tuple(trait.enum_class.__members__.keys())
        tdict.pop("enum_class", None)

    for k, v in tdict.items():
        if isinstance(v, TraitType):
            tdict[k] = trait_as_dict(v)
        if isinstance(v, enum.Enum):
            tdict[k] = v.name
        if isinstance(v, type):
            tdict[k] = f"{v.__module__}.{v.__name__}"

    tdict["__class__"] = (cls.__module__, cls.__name__)
    return tdict


def class_traits_as_dict(
    obj: HasTraits | dict[str, TraitType] | type, values: dict[str, object] | None = None
) -> dict:
    """
    Create a dict which represents all traits of the given object.
    This dict itself can be inspected in a generic API, or it
    may be converted back to a (stub) instance of HasTraits. This
    facilitates the sending of configurable object properties over
    an interface such as D-Bus.

    :param obj: an instance of HasTraits
    :param value: optional dict of trait values (pulled from obj by default)
    :return: dict representing all traits in obj
    """
    cls_dt: dict = {}
    traits: dict[str, TraitType] = {}
    if isinstance(obj, type) and hasattr(obj, "class_traits"):
        traits = obj.class_traits()  # type: ignore[call-non-callable]
    elif isinstance(obj, dict):
        traits = obj  # type: ignore[invalid-assignment]
    elif isinstance(obj, HasTraits):
        traits = obj.traits()
        values = obj._trait_values
    else:
        raise TypeError("Object does not support traits")

    for k, v in traits.items():
        dt = trait_as_dict(v)
        if dt is None:
            continue
        if values is not None and k in values:
            dt["__value__"] = values[k]
        cls_dt[k] = dt
    return cls_dt


def dict_as_trait(obj: dict) -> TraitType:
    """
    Create a trait from a dict (trait_as_dict).
    """
    if "__class__" not in obj:
        raise ValueError("No module and class attribute present")

    tobj = obj.copy()

    module_name, trait_class = tobj.pop("__class__")

    module = importlib.import_module(module_name)
    if not hasattr(module, trait_class):
        raise TypeError(f"Unknown class: {trait_class}")
    cls = getattr(module, trait_class)

    if "trait" in tobj:
        tobj["trait"] = dict_as_trait(tobj.pop("trait"))

    metadata = {}
    if "metadata" in tobj:
        metadata.update(tobj.pop("metadata"))

    if issubclass(cls, Enum):
        trait = cls(tobj.pop("values"), **tobj)
    else:
        trait = cls(**tobj)

    for k in list(metadata.keys()):
        if k in ("name", "default_args", "default_kwargs"):
            setattr(trait, k, metadata.pop(k))

    trait.metadata = metadata

    return trait


def dict_as_class_traits(obj: dict) -> HasTraits:
    """
    Convert a dict of unpacked traits to a HasTraits instance.
    Useful for remote parameter inspection and validation.

    :param obj: dict of unpacked traits
    :return: the stub HasTraits instance
    """
    if not isinstance(obj, dict):
        raise TypeError(f"Object must be a dict (was: {obj})")

    traits = {}
    values = {}
    for k, v in obj.items():
        if "__value__" in v:
            values[k] = v.pop("__value__")

        trait = dict_as_trait(v)
        if trait is None:
            continue
        traits[k] = trait

    cls = HasTraits()
    cls.add_traits(**traits)

    for k, v in values.items():
        setattr(cls, k, v)

    return cls


def get_args_dict(obj: HasTraits, incl_all=False):
    """
    Return a dict of user-configurable traits for an object

    :param obj: an instance of HasTraits
    :param incl_all: If all items should be included, regardless of RO status
    :return: dict of arguments
    """
    result = {}
    for k in sorted(obj._trait_values.keys()):
        v = obj._trait_values[k]
        trait = obj.traits()[k]
        # Only include traits marked as config=True (user-configurable)
        if not trait.get_metadata("config"):
            continue
        if incl_all or (not trait.get_metadata("hidden") and is_trait_writable(trait)):
            result[k] = v
    return filter_none(result)


def add_traits_to_argparse(obj: HasTraits, parser: ArgumentParser, prefix: str | None = None):
    """
    Add all traits from the given object to the argparse context.

    :param obj: an instance of HasTraits
    :param parser: argparse parser
    :param prefix: string to prefix keys with
    """
    for key, trait in obj.traits().items():
        if trait.get_metadata("config") is not True:
            continue

        argname = f"--{key}"
        if prefix is not None:
            argname = f"--{prefix}.{key}"

        if isinstance(trait, Container):
            parser.add_argument(argname, nargs="+", help=trait.info_text)
        elif isinstance(trait, Enum):
            trait_values: tuple[str, ...] = trait.values  # type: ignore[assignment]
            parser.add_argument(
                argname,
                type=str.lower,
                choices=[x.lower() for x in trait_values],
                help=trait.info_text,
            )
        else:
            argtype = str
            if hasattr(trait, "default_value"):
                argtype = type(trait.default_value)
            parser.add_argument(argname, type=argtype, help=trait.info_text)


def apply_from_argparse(args, traits=None, target: HasTraits | None = None) -> dict:
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
    if isinstance(traits, HasTraits):
        traits = traits.traits()

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
        if target.traits()[key].get_metadata("config") is not True:
            raise ValueError(f"Trait is not marked as configurable: {key}")

        setattr(target, key, getattr(args, key))

    # if all validators passed, return a dict of the changed args
    changed = {}
    for key in intersect:
        changed[key] = target._trait_values[key]

    return changed
