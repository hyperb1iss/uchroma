# pylint: disable=protected-access, no-member, invalid-name
import functools
import inspect
import re

from abc import abstractmethod

from frozendict import frozendict
from traitlets import Bool, HasTraits, Instance, Tuple, Unicode

from uchroma.traits import get_args_dict
from uchroma.util import camel_to_snake


CUSTOM = 'custom_frame'


class BaseFX(HasTraits, object):

    # meta
    hidden = Bool(default_value=False, read_only=True)
    description = Unicode('_unimplemented_', read_only=True)


    def __init__(self, fxmod, driver, *args, **kwargs):
        super(BaseFX, self).__init__(*args, **kwargs)
        self._fxmod = fxmod
        self._driver = driver

    @abstractmethod
    def apply(self) -> bool:
        return False



class FXModule(object):
    def __init__(self, driver):
        self._driver = driver
        self._available_fx = frozendict(self._load_fx())


    def _load_fx(self) -> dict:
        fx = {}
        for k, v in inspect.getmembers(self.__class__, \
                lambda x: inspect.isclass(x) and issubclass(x, BaseFX)):
            key = camel_to_snake(re.sub(r'FX$', '', k))
            if key in [item.lower() for item in self._driver.hardware.supported_fx]:
                fx[key] = v

        return fx


    @property
    def available_fx(self):
        return self._available_fx


    def create_fx(self, fx_name) -> BaseFX:
        fx_name = fx_name.lower()
        if fx_name not in self._available_fx:
            return None
        return self._available_fx[fx_name](self, self._driver)



class FXManager(HasTraits):
    """
    Manages device lighting effects
    """
    current_fx = Tuple(Unicode(allow_none=True),
                       Instance(klass=BaseFX, allow_none=True),
                       default_value=(None, None))


    def __init__(self, driver, fxmod: FXModule, *args, **kwargs):
        """
        :param driver: The UChromaDevice to control
        """
        super(FXManager, self).__init__(*args, **kwargs)
        self._driver = driver
        self._logger = driver.logger
        self._fxmod = fxmod


    def restore_prefs(self, prefs):
        """
        Restore last FX from preferences
        """
        if prefs.fx is not None:
            args = {}
            if prefs.fx_args is not None:
                args = prefs.fx_args

            self.activate(prefs.fx, **args)


    @property
    def available_fx(self):
        return self._fxmod.available_fx


    def get_fx(self, fx_name) -> BaseFX:
        """
        Get the requested effects implementation.

        Returns the last active object if appropriate.

        :param fx_name: The string name of the effect object
        """
        if self.current_fx[0] == fx_name:
            return self.current_fx[1]

        fx = self._fxmod.create_fx(fx_name)
        if fx is not None:
            self.current_fx = (fx_name, fx)
        return fx

    def disable(self) -> bool:
        if 'disable' in self.available_fx:
            return self.activate('disable')
        return False


    def _activate(self, fx_name, fx, future=None):
        # need to do this as a callback if an animation
        # is shutting down
        if fx.apply():
            if fx_name == CUSTOM:
                return True

            self._driver.preferences.fx = fx_name
            argsdict = get_args_dict(fx)
            if len(argsdict) == 0:
                argsdict = None
            self._driver.preferences.fx_args = argsdict
        return True


    def activate(self, fx_name, **kwargs) -> bool:
        fx = self.get_fx(fx_name)
        if fx is None:
            return False

        if fx_name != CUSTOM and fx_name != 'disable':
            for k, v in kwargs.items():
                if fx.has_trait(k):
                    setattr(fx, k, v)

            self._logger.debug("activate fx: %s traits: %s", fx_name, fx._trait_values)
            if self._driver.is_animating:
                self._driver.animation_manager.stop( \
                        cb=functools.partial(self._activate, fx_name, fx))
                return True

        return self._activate(fx_name, fx)
