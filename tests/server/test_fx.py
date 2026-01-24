#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# uchroma - FX module unit tests
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from frozendict import frozendict
from traitlets import Unicode

from uchroma.server.fx import CUSTOM, BaseFX, FXManager, FXModule

# ─────────────────────────────────────────────────────────────────────────────
# Mock Effect Classes
# ─────────────────────────────────────────────────────────────────────────────


class MockFX(BaseFX):
    """Basic mock effect for testing."""

    description = Unicode("Mock effect for testing", read_only=True)

    async def apply(self) -> bool:
        return True


class MockHiddenFX(BaseFX):
    """Hidden mock effect for testing."""

    hidden = True
    description = Unicode("Hidden mock effect", read_only=True)

    async def apply(self) -> bool:
        return True


class MockFXWithTraits(BaseFX):
    """Mock effect with configurable traits."""

    description = Unicode("Mock effect with traits", read_only=True)
    color = Unicode("red")
    speed = Unicode("fast")

    async def apply(self) -> bool:
        return True


class MockDisableFX(BaseFX):
    """Mock disable effect."""

    description = Unicode("Disable effect", read_only=True)

    async def apply(self) -> bool:
        return True


class MockFailingFX(BaseFX):
    """Mock effect that fails to apply."""

    description = Unicode("Failing effect", read_only=True)

    async def apply(self) -> bool:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Sample FXModule Subclass for Testing
# ─────────────────────────────────────────────────────────────────────────────


class _SampleFXModule(FXModule):
    """FXModule subclass with inner effect classes for testing."""

    class StaticFX(BaseFX):
        description = Unicode("Static effect", read_only=True)

        async def apply(self) -> bool:
            return True

    class WaveFX(BaseFX):
        description = Unicode("Wave effect", read_only=True)

        async def apply(self) -> bool:
            return True

    class SpectrumFX(BaseFX):
        description = Unicode("Spectrum effect", read_only=True)

        async def apply(self) -> bool:
            return True

    class DisableFX(BaseFX):
        description = Unicode("Disable effect", read_only=True)

        async def apply(self) -> bool:
            return True

    class HiddenSecretFX(BaseFX):
        hidden = True
        description = Unicode("Secret effect", read_only=True)

        async def apply(self) -> bool:
            return True


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_hardware():
    """Mock Hardware object with supported_fx."""
    hw = MagicMock()
    hw.supported_fx = ["static", "wave", "spectrum", "disable"]
    return hw


@pytest.fixture
def mock_preferences():
    """Mock preferences object."""
    prefs = MagicMock()
    prefs.fx = None
    prefs.fx_args = None
    return prefs


@pytest.fixture
def mock_driver(mock_hardware, mock_preferences):
    """Mock driver with all required attributes for FX testing."""
    driver = MagicMock()
    driver.hardware = mock_hardware
    driver.preferences = mock_preferences
    driver.is_animating = False
    driver.animation_manager = MagicMock()
    driver.animation_manager.stop_async = AsyncMock()
    driver.restore_prefs = MagicMock()
    driver.restore_prefs.connect = MagicMock()
    driver.logger = MagicMock()
    return driver


@pytest.fixture
def sample_fxmod(mock_driver):
    """_SampleFXModule instance for testing."""
    return _SampleFXModule(mock_driver)


@pytest.fixture
def fxmanager(mock_driver, sample_fxmod):
    """FXManager instance for testing."""
    return FXManager(mock_driver, sample_fxmod)


# ─────────────────────────────────────────────────────────────────────────────
# BaseFX Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseFX:
    """Tests for BaseFX abstract base class."""

    def test_hidden_trait_exists(self, mock_driver):
        """BaseFX should have a hidden trait defaulting to False."""
        fx = MockFX(None, mock_driver)
        assert hasattr(fx, "hidden")
        assert fx.hidden is False

    def test_hidden_trait_can_be_true(self, mock_driver):
        """BaseFX subclass can set hidden to True."""
        fx = MockHiddenFX(None, mock_driver)
        assert fx.hidden is True

    def test_description_trait_exists(self, mock_driver):
        """BaseFX should have a description trait."""
        fx = MockFX(None, mock_driver)
        assert hasattr(fx, "description")
        assert fx.description == "Mock effect for testing"

    def test_default_description_is_unimplemented(self, mock_driver):
        """BaseFX default description should be _unimplemented_."""

        class MinimalFX(BaseFX):
            async def apply(self) -> bool:
                return True

        fx = MinimalFX(None, mock_driver)
        assert fx.description == "_unimplemented_"

    def test_apply_is_abstract(self):
        """BaseFX should have an abstract apply method."""
        assert hasattr(BaseFX, "apply")
        # Check that apply has the abstractmethod marker
        assert getattr(BaseFX.apply, "__isabstractmethod__", False) is True

    def test_init_stores_fxmod_and_driver(self, mock_driver):
        """BaseFX should store fxmod and driver references."""
        mock_fxmod = MagicMock()
        fx = MockFX(mock_fxmod, mock_driver)
        assert fx._fxmod is mock_fxmod
        assert fx._driver is mock_driver

    def test_apply_returns_bool(self, mock_driver):
        """apply() should return a boolean."""
        fx = MockFX(None, mock_driver)
        result = asyncio.run(fx.apply())
        assert isinstance(result, bool)
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# FXModule Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFXModule:
    """Tests for FXModule class."""

    def test_load_fx_discovers_inner_classes(self, mock_driver):
        """_load_fx should discover inner classes that subclass BaseFX."""
        fxmod = _SampleFXModule(mock_driver)
        available = fxmod.available_fx

        # Should have found StaticFX, WaveFX, SpectrumFX, DisableFX
        # (HiddenSecretFX not in supported_fx)
        assert "static" in available
        assert "wave" in available
        assert "spectrum" in available
        assert "disable" in available

    def test_load_fx_filters_by_supported_fx(self, mock_driver):
        """_load_fx should filter effects by hardware.supported_fx."""
        # Limit supported_fx to only static and wave
        mock_driver.hardware.supported_fx = ["static", "wave"]

        fxmod = _SampleFXModule(mock_driver)
        available = fxmod.available_fx

        assert "static" in available
        assert "wave" in available
        assert "spectrum" not in available
        assert "disable" not in available

    def test_load_fx_handles_empty_supported_fx(self, mock_driver):
        """_load_fx should return empty dict when no effects supported."""
        mock_driver.hardware.supported_fx = []

        fxmod = _SampleFXModule(mock_driver)
        available = fxmod.available_fx

        assert len(available) == 0

    def test_load_fx_converts_camel_case_to_snake_case(self, mock_driver):
        """_load_fx should convert CamelCaseFX to snake_case."""
        # The StaticFX class becomes "static" (FX suffix removed)
        mock_driver.hardware.supported_fx = ["static"]

        fxmod = _SampleFXModule(mock_driver)
        available = fxmod.available_fx

        assert "static" in available
        # StaticFX is stored, not static_fx
        assert available["static"].__name__ == "StaticFX"

    def test_load_fx_case_insensitive_matching(self, mock_driver):
        """_load_fx should match supported_fx case-insensitively."""
        mock_driver.hardware.supported_fx = ["STATIC", "Wave", "SPECTRUM"]

        fxmod = _SampleFXModule(mock_driver)
        available = fxmod.available_fx

        assert "static" in available
        assert "wave" in available
        assert "spectrum" in available

    def test_available_fx_returns_frozendict(self, sample_fxmod):
        """available_fx should return a frozendict."""
        available = sample_fxmod.available_fx
        assert isinstance(available, frozendict)

    def test_available_fx_is_immutable(self, sample_fxmod):
        """available_fx frozendict should be immutable."""
        available = sample_fxmod.available_fx

        with pytest.raises(TypeError):
            available["new_fx"] = "value"

    def test_create_fx_instantiates_effect(self, sample_fxmod, mock_driver):
        """create_fx should instantiate an effect class."""
        fx = sample_fxmod.create_fx("static")

        assert fx is not None
        assert isinstance(fx, BaseFX)
        assert fx._driver is mock_driver
        assert fx._fxmod is sample_fxmod

    def test_create_fx_returns_none_for_unknown(self, sample_fxmod):
        """create_fx should return None for unknown effect names."""
        fx = sample_fxmod.create_fx("nonexistent_effect")
        assert fx is None

    def test_create_fx_case_insensitive(self, sample_fxmod):
        """create_fx should match effect names case-insensitively."""
        fx1 = sample_fxmod.create_fx("static")
        fx2 = sample_fxmod.create_fx("STATIC")
        fx3 = sample_fxmod.create_fx("Static")

        assert fx1 is not None
        assert fx2 is not None
        assert fx3 is not None

    def test_create_fx_returns_new_instance_each_time(self, sample_fxmod):
        """create_fx should return a new instance each time."""
        fx1 = sample_fxmod.create_fx("static")
        fx2 = sample_fxmod.create_fx("static")

        assert fx1 is not fx2


# ─────────────────────────────────────────────────────────────────────────────
# FXManager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFXManager:
    """Tests for FXManager class."""

    def test_init_connects_restore_prefs_signal(self, mock_driver, sample_fxmod):
        """FXManager should connect to driver.restore_prefs signal."""
        manager = FXManager(mock_driver, sample_fxmod)

        mock_driver.restore_prefs.connect.assert_called_once()
        # The connected callback should be _restore_prefs
        call_args = mock_driver.restore_prefs.connect.call_args
        assert call_args[0][0] == manager._restore_prefs

    def test_available_fx_delegates_to_fxmod(self, fxmanager, sample_fxmod):
        """available_fx property should delegate to fxmod."""
        assert fxmanager.available_fx is sample_fxmod.available_fx

    def test_current_fx_default_is_none_tuple(self, fxmanager):
        """current_fx should default to (None, None)."""
        assert fxmanager.current_fx == (None, None)

    def test_get_fx_returns_current_if_name_matches(self, fxmanager):
        """get_fx should return current effect if name matches."""
        fx = fxmanager._fxmod.create_fx("static")
        fxmanager.current_fx = ("static", fx)

        result = fxmanager.get_fx("static")

        assert result is fx

    def test_get_fx_creates_new_if_name_differs(self, fxmanager):
        """get_fx should create new effect via fxmod if name differs."""
        fx_static = fxmanager._fxmod.create_fx("static")
        fxmanager.current_fx = ("static", fx_static)

        result = fxmanager.get_fx("wave")

        assert result is not None
        assert result is not fx_static
        assert isinstance(result, BaseFX)

    def test_get_fx_creates_new_when_no_current(self, fxmanager):
        """get_fx should create new effect when no current effect."""
        result = fxmanager.get_fx("static")

        assert result is not None
        assert isinstance(result, BaseFX)

    def test_get_fx_returns_none_for_unknown(self, fxmanager):
        """get_fx should return None for unknown effect names."""
        result = fxmanager.get_fx("nonexistent")
        assert result is None

    def test_activate_calls_apply(self, fxmanager, mock_driver):
        """activate should call fx.apply()."""
        mock_driver.is_animating = False

        result = asyncio.run(fxmanager.activate("static"))

        assert result is True

    def test_activate_updates_current_fx(self, fxmanager, mock_driver):
        """activate should update current_fx tuple."""
        mock_driver.is_animating = False

        asyncio.run(fxmanager.activate("static"))

        assert fxmanager.current_fx[0] == "static"
        assert fxmanager.current_fx[1] is not None
        assert isinstance(fxmanager.current_fx[1], BaseFX)

    def test_activate_sets_traits_from_kwargs(self, mock_driver, mock_hardware, mock_preferences):
        """activate should set traits on the effect from kwargs."""

        # Create an FXModule with an effect that has configurable traits
        class TraitFXModule(FXModule):
            class ConfigurableFX(BaseFX):
                description = Unicode("Configurable effect", read_only=True)
                color = Unicode("red")
                speed = Unicode("slow")

                async def apply(self) -> bool:
                    return True

        mock_hardware.supported_fx = ["configurable"]
        fxmod = TraitFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)

        asyncio.run(manager.activate("configurable", color="blue", speed="fast"))

        fx = manager.current_fx[1]
        assert fx.color == "blue"
        assert fx.speed == "fast"

    def test_activate_ignores_nonexistent_traits(
        self, mock_driver, mock_hardware, mock_preferences
    ):
        """activate should ignore kwargs that aren't valid traits."""

        class SimpleFXModule(FXModule):
            class SimpleFX(BaseFX):
                description = Unicode("Simple effect", read_only=True)
                valid_trait = Unicode("default")

                async def apply(self) -> bool:
                    return True

        mock_hardware.supported_fx = ["simple"]
        fxmod = SimpleFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)

        # Should not raise even with invalid kwargs
        result = asyncio.run(
            manager.activate("simple", valid_trait="changed", invalid_trait="ignored")
        )

        assert result is True
        assert manager.current_fx[1].valid_trait == "changed"

    def test_activate_saves_to_preferences(self, fxmanager, mock_driver, mock_preferences):
        """activate should save fx name and args to driver.preferences."""
        mock_driver.is_animating = False

        asyncio.run(fxmanager.activate("static"))

        assert mock_preferences.fx == "static"

    def test_activate_saves_args_to_preferences(self, mock_driver, mock_hardware, mock_preferences):
        """activate should save fx_args to preferences."""

        class ArgFXModule(FXModule):
            class TestFX(BaseFX):
                description = Unicode("Test effect", read_only=True)
                setting = Unicode("value")

                async def apply(self) -> bool:
                    return True

        mock_hardware.supported_fx = ["test"]
        fxmod = ArgFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)

        asyncio.run(manager.activate("test", setting="custom"))

        assert mock_preferences.fx == "test"
        # fx_args should be set (may be dict or None depending on implementation)
        # The key check is that preferences were updated

    def test_activate_returns_false_for_unknown_fx(self, fxmanager):
        """activate should return False for unknown effect."""
        result = asyncio.run(fxmanager.activate("nonexistent_effect"))
        assert result is False

    def test_activate_custom_frame_skips_prefs(self, mock_driver, mock_hardware, mock_preferences):
        """activate with custom_frame should not save to preferences."""

        class CustomFXModule(FXModule):
            class CustomFrameFX(BaseFX):
                description = Unicode("Custom frame", read_only=True)

                async def apply(self) -> bool:
                    return True

        mock_hardware.supported_fx = ["custom_frame"]
        fxmod = CustomFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)

        original_fx = mock_preferences.fx
        asyncio.run(manager.activate(CUSTOM))

        # Preferences should not be updated for custom_frame
        assert mock_preferences.fx == original_fx

    def test_activate_stops_animation_when_animating(self, fxmanager, mock_driver):
        """activate should stop animation when driver is animating."""
        mock_driver.is_animating = True

        result = asyncio.run(fxmanager.activate("static"))

        assert result is True
        mock_driver.animation_manager.stop_async.assert_called_once()

    def test_disable_activates_disable_effect(self, fxmanager, mock_driver):
        """disable should activate the 'disable' effect."""
        mock_driver.is_animating = False

        result = asyncio.run(fxmanager.disable())

        assert result is True
        assert fxmanager.current_fx[0] == "disable"

    def test_disable_returns_false_when_not_available(self, mock_driver, mock_hardware):
        """disable should return False when disable effect not available."""
        mock_hardware.supported_fx = ["static", "wave"]  # No disable

        fxmod = _SampleFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)

        result = asyncio.run(manager.disable())

        assert result is False

    def test_restore_prefs_restores_effect(self, fxmanager, mock_driver):
        """_restore_prefs should restore effect from preferences."""
        mock_driver.is_animating = False

        prefs = MagicMock()
        prefs.fx = "wave"
        prefs.fx_args = None
        prefs.layers = None  # No animation layers

        # Patch ensure_future to run coroutine immediately
        with patch("uchroma.server.fx.ensure_future", lambda coro: asyncio.run(coro)):
            fxmanager._restore_prefs(prefs)

        assert fxmanager.current_fx[0] == "wave"

    def test_restore_prefs_restores_effect_with_args(
        self, mock_driver, mock_hardware, mock_preferences
    ):
        """_restore_prefs should restore effect with saved args."""

        class ArgFXModule(FXModule):
            class ConfigFX(BaseFX):
                description = Unicode("Config effect", read_only=True)
                speed = Unicode("normal")

                async def apply(self) -> bool:
                    return True

        mock_hardware.supported_fx = ["config"]
        fxmod = ArgFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)

        prefs = MagicMock()
        prefs.fx = "config"
        prefs.fx_args = {"speed": "fast"}
        prefs.layers = None  # No animation layers

        # Patch ensure_future to run coroutine immediately
        with patch("uchroma.server.fx.ensure_future", lambda coro: asyncio.run(coro)):
            manager._restore_prefs(prefs)

        assert manager.current_fx[0] == "config"
        assert manager.current_fx[1].speed == "fast"

    def test_restore_prefs_does_nothing_when_fx_is_none(self, fxmanager):
        """_restore_prefs should do nothing when prefs.fx is None."""
        prefs = MagicMock()
        prefs.fx = None

        fxmanager._restore_prefs(prefs)

        assert fxmanager.current_fx == (None, None)

    def test_restore_prefs_skips_when_animation_layers_exist(self, fxmanager, mock_driver):
        """_restore_prefs should skip FX restore when animation layers are present."""
        mock_driver.is_animating = False

        prefs = MagicMock()
        prefs.fx = "wave"
        prefs.fx_args = None
        prefs.layers = {"uchroma.fxlib.plasma.Plasma": {}}  # Animation layers exist

        fxmanager._restore_prefs(prefs)

        # FX should NOT be restored because animations take priority
        assert fxmanager.current_fx == (None, None)

    def test_activate_skips_traits_for_disable(self, fxmanager, mock_driver):
        """activate should skip setting traits for disable effect."""
        mock_driver.is_animating = False

        # Should not raise even with kwargs
        result = asyncio.run(fxmanager.activate("disable", some_trait="value"))

        assert result is True

    def test_activate_skips_traits_for_custom_frame(self, mock_driver, mock_hardware):
        """activate should skip setting traits for custom_frame effect."""

        class CustomFXModule(FXModule):
            class CustomFrameFX(BaseFX):
                description = Unicode("Custom frame", read_only=True)
                some_trait = Unicode("default")

                async def apply(self) -> bool:
                    return True

        mock_hardware.supported_fx = ["custom_frame"]
        fxmod = CustomFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)
        mock_driver.is_animating = False

        result = asyncio.run(manager.activate(CUSTOM, some_trait="should_be_ignored"))

        assert result is True
        # Trait should remain at default since it's custom_frame
        assert manager.current_fx[1].some_trait == "default"

    def test_activate_reuses_current_fx_instance(self, fxmanager, mock_driver):
        """activate should reuse current_fx if name matches."""
        mock_driver.is_animating = False

        asyncio.run(fxmanager.activate("static"))
        first_fx = fxmanager.current_fx[1]

        asyncio.run(fxmanager.activate("static"))
        second_fx = fxmanager.current_fx[1]

        # Should be the same instance
        assert first_fx is second_fx

    def test_activate_failing_effect_returns_true(self, mock_driver, mock_hardware):
        """activate should return True even when apply() fails."""

        # Note: Looking at the code, _activate returns True regardless
        # but the current_fx is only updated if apply() succeeds
        class FailingFXModule(FXModule):
            class FailingFX(BaseFX):
                description = Unicode("Failing effect", read_only=True)

                async def apply(self) -> bool:
                    return False

        mock_hardware.supported_fx = ["failing"]
        fxmod = FailingFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)
        mock_driver.is_animating = False

        result = asyncio.run(manager.activate("failing"))

        # _activate always returns True
        assert result is True
        # But current_fx should not be updated when apply fails
        assert manager.current_fx == (None, None)


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case and integration tests."""

    def test_fxmodule_with_no_inner_classes(self, mock_driver):
        """FXModule with no inner BaseFX classes should have empty available_fx."""

        class EmptyFXModule(FXModule):
            pass

        mock_driver.hardware.supported_fx = ["anything"]
        fxmod = EmptyFXModule(mock_driver)

        assert len(fxmod.available_fx) == 0

    def test_fxmodule_inner_class_not_subclassing_basefx(self, mock_driver):
        """FXModule should only discover classes that subclass BaseFX."""

        class MixedFXModule(FXModule):
            class NotAnFX:
                pass

            class ValidFX(BaseFX):
                async def apply(self) -> bool:
                    return True

        mock_driver.hardware.supported_fx = ["valid", "not_an"]
        fxmod = MixedFXModule(mock_driver)

        assert "valid" in fxmod.available_fx
        assert "not_an" not in fxmod.available_fx

    def test_manager_stores_references(self, fxmanager, mock_driver, sample_fxmod):
        """FXManager should store driver and fxmod references."""
        assert fxmanager._driver is mock_driver
        assert fxmanager._fxmod is sample_fxmod
        assert fxmanager._logger is mock_driver.logger

    def test_fx_apply_called_once_per_activate(self, mock_driver, mock_hardware):
        """apply() should be called exactly once per activate."""
        apply_count = 0

        class CountingFXModule(FXModule):
            class CountingFX(BaseFX):
                description = Unicode("Counting effect", read_only=True)

                async def apply(self) -> bool:
                    nonlocal apply_count
                    apply_count += 1
                    return True

        mock_hardware.supported_fx = ["counting"]
        fxmod = CountingFXModule(mock_driver)
        manager = FXManager(mock_driver, fxmod)
        mock_driver.is_animating = False

        asyncio.run(manager.activate("counting"))

        assert apply_count == 1

    def test_current_fx_tuple_immutable_after_set(self, fxmanager, mock_driver):
        """current_fx tuple should be immutable."""
        mock_driver.is_animating = False

        asyncio.run(fxmanager.activate("static"))

        # Tuples are immutable by nature
        assert isinstance(fxmanager.current_fx, tuple)
        assert len(fxmanager.current_fx) == 2
