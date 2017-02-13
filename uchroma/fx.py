# pylint: disable=protected-access, no-member, invalid-name
import inspect
import re

from abc import abstractmethod

from traitlets import Bool, HasTraits, Unicode

from uchroma.traits import get_args_dict
from uchroma.util import camel_to_snake


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
        self._available_fx = self._load_fx()
        self._user_args = self._load_traits()


    def _load_fx(self) -> dict:
        fx = {}
        for k, v in inspect.getmembers(self.__class__, \
                lambda x: inspect.isclass(x) and issubclass(x, BaseFX)):
            key = camel_to_snake(re.sub(r'FX$', '', k))
            if key in [item.lower() for item in self._driver.hardware.supported_fx]:
                fx[key] = v

        return fx


    def _load_traits(self) -> dict:
        args = {}
        for k, v in self._available_fx.items():
            args[k] = v.class_traits()
        return args


    @property
    def available_fx(self):
        return tuple(self._available_fx.keys())


    @property
    def user_args(self):
        return self._user_args


    def create_fx(self, fx_name) -> BaseFX:
        fx_name = fx_name.lower()
        if fx_name not in self._available_fx:
            return None
        return self._available_fx[fx_name](self, self._driver)



class FXManager(object):
    """
    Manages device lighting effects
    """

    def __init__(self, driver, fxmod: FXModule):
        """
        :param driver: The UChromaDevice to control
        """
        self._driver = driver
        self._fxmod = fxmod
        self._current_fx = (None, None)


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
        return tuple(self._fxmod.available_fx)


    @property
    def user_args(self):
        return self._fxmod.user_args


    def get_fx(self, fx_name) -> BaseFX:
        """
        Get the requested effects implementation.

        Returns the last active object if appropriate.

        :param fx_name: The string name of the effect object
        """
        if self._current_fx[0] == fx_name:
            return self._current_fx[1]

        return self._fxmod.create_fx(fx_name)


    def disable(self) -> bool:
        if 'disable' in self.available_fx:
            return self.activate('disable')
        return False


    def activate(self, fx_name, **kwargs) -> bool:
        fx = self.get_fx(fx_name)
        if fx is None:
            return False

        for k, v in kwargs.items():
            if fx.has_trait(k):
                setattr(fx, k, v)

        if fx_name not in ('custom_frame', 'disable') and self._driver.is_animating:
            self._driver.animation_manager.reset()

        if fx.apply():
            self._current_fx = (fx_name, fx)

            if fx_name != 'custom_frame':
                self._driver.preferences.fx = fx_name
                self._driver.preferences.fx_args = get_args_dict(fx)

            return True

        return False
