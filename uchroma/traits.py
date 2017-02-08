import sys

from traitlets import Int, List, TraitType, Undefined, UseEnum
from grapefruit import Color

from uchroma.util import camel_to_snake, to_color


class ColorTrait(TraitType):
    """
    A traitlet which encapsulates a grapefruit.Color and performs
    type coercion as needed.
    """

    default_value = None
    info_text = "Color"

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

    def __init__(self, default_value=Undefined, minlen=0, maxlen=sys.maxsize, **kwargs):
        super(ColorSchemeTrait, self).__init__(trait=ColorTrait,
                                               default_value=default_value,
                                               minlen=minlen, maxlen=maxlen, **kwargs)


class ColorPresetTrait(UseEnum):
    """
    A trait which represents a group of color schemes defined
    as a Python Enum.
    """

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


def trait_user_args(trait) -> dict:
    """
    Get a dict that describes how to interact with this trait
    """
    desc = {}
    desc['name'] = trait.name

    trait_type = trait.__class__.__name__.lower()
    if trait_type == 'unicode':
        trait_type = 'string'
    desc['type'] = trait_type

    write_once = False
    if hasattr(trait, 'write_once'):
        write_once = trait.write_once

    desc['read_only'] = trait.read_only or trait.write_once
    desc['info'] = trait.info_text
    desc['help'] = trait.help
    desc['allow_none'] = trait.allow_none
    if hasattr(trait, 'min'):
        desc['min'] = trait.min
    if hasattr(trait, 'max'):
        desc['max'] = trait.max
    if hasattr(trait, 'minlen'):
        desc['minlen'] = trait.minlen
    if hasattr(trait, 'maxlen'):
        desc['maxlen'] = trait.maxlen

    return desc


class TraitsPropertiesMixin(object):
    def __init__(self, *args, **kwargs):
        super(TraitsPropertiesMixin, self).__init__(*args, **kwargs)


    def get_user_args(self) -> dict:
        desc = {}
        for name, trait in self._delegate.traits().items():
            desc[name] = trait_user_args(trait)
        return desc

            
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

