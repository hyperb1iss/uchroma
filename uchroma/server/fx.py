#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=protected-access, no-member, invalid-name

import asyncio
import inspect
import re
from abc import abstractmethod

from frozendict import frozendict
from traitlets import Bool, HasTraits, Instance, Tuple, Unicode

from uchroma.traits import get_args_dict
from uchroma.util import camel_to_snake, ensure_future

CUSTOM = "custom_frame"


class BaseFX(HasTraits):
    # meta
    hidden = Bool(default_value=False, read_only=True)
    description = Unicode("_unimplemented_", read_only=True)

    def __init__(self, fxmod, driver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fxmod = fxmod
        self._driver = driver

    @abstractmethod
    def apply(self) -> bool:
        return False

    async def apply_async(self) -> bool:
        return await asyncio.to_thread(self.apply)


class FXModule:
    def __init__(self, driver):
        self._driver = driver
        self._available_fx = frozendict(self._load_fx())

    def _load_fx(self) -> dict:
        fx = {}
        for k, v in inspect.getmembers(
            self.__class__, lambda x: inspect.isclass(x) and issubclass(x, BaseFX)
        ):
            key = camel_to_snake(re.sub(r"FX$", "", k))
            if key in [item.lower() for item in self._driver.hardware.supported_fx]:
                fx[key] = v

        return fx

    @property
    def available_fx(self):
        return self._available_fx

    def create_fx(self, fx_name) -> BaseFX | None:
        fx_name = fx_name.lower()
        if fx_name not in self._available_fx:
            return None
        return self._available_fx[fx_name](self, self._driver)


class FXManager(HasTraits):
    """
    Manages device lighting effects
    """

    current_fx = Tuple(
        Unicode(allow_none=True),
        Instance(klass=BaseFX, allow_none=True),
        default_value=(None, None),
    )

    def __init__(self, driver, fxmod: FXModule, *args, **kwargs):
        """
        :param driver: The UChromaDevice to control
        """
        super().__init__(*args, **kwargs)
        self._driver = driver
        self._logger = driver.logger
        self._fxmod = fxmod
        self._async_lock = asyncio.Lock()

        driver.restore_prefs.connect(self._restore_prefs)

    def _restore_prefs(self, prefs):
        """
        Restore last FX from preferences
        """
        if prefs.fx is not None:
            args = {}
            if prefs.fx_args is not None:
                args = prefs.fx_args

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is None:
                asyncio.run(self.activate_async(prefs.fx, **args))
            else:
                ensure_future(self.activate_async(prefs.fx, **args), loop=loop)

    @property
    def available_fx(self):
        return self._fxmod.available_fx

    def get_fx(self, fx_name) -> BaseFX | None:
        """
        Get the requested effects implementation.

        Returns the last active object if appropriate.

        :param fx_name: The string name of the effect object
        """
        if self.current_fx[0] == fx_name:
            return self.current_fx[1]

        return self._fxmod.create_fx(fx_name)

    def disable(self) -> bool:
        if "disable" in self.available_fx:
            return self.activate("disable")
        return False

    def _activate(self, fx_name, fx, future=None):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            asyncio.run(self._activate_async(fx_name, fx))
        else:
            ensure_future(self._activate_async(fx_name, fx), loop=loop)
        return True

    async def _activate_async(self, fx_name, fx) -> bool:
        if await fx.apply_async():
            if fx_name != self.current_fx[0]:
                self.current_fx = (fx_name, fx)
            if fx_name == CUSTOM:
                return True

            self._driver.preferences.fx = fx_name
            argsdict = get_args_dict(fx)
            if not argsdict:
                argsdict = None
            self._driver.preferences.fx_args = argsdict
        return True

    def activate(self, fx_name, **kwargs) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            return asyncio.run(self.activate_async(fx_name, **kwargs))

        ensure_future(self.activate_async(fx_name, **kwargs), loop=loop)
        return True

    async def activate_async(self, fx_name, **kwargs) -> bool:
        fx = self.get_fx(fx_name)
        if fx is None:
            return False

        async with self._async_lock:
            if fx_name not in (CUSTOM, "disable"):
                for k, v in kwargs.items():
                    if fx.has_trait(k):
                        setattr(fx, k, v)

                if self._driver.is_animating:
                    await self._driver.animation_manager.stop_async()

            return await self._activate_async(fx_name, fx)

    async def disable_async(self) -> bool:
        if "disable" in self.available_fx:
            return await self.activate_async("disable")
        return False
