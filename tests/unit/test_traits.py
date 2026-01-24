#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.traits module."""

from __future__ import annotations

import enum
from argparse import ArgumentParser, Namespace
from types import MappingProxyType

import pytest
from traitlets import Float, HasTraits, Int, List, TraitError

from uchroma.traits import (
    ColorPresetTrait,
    ColorSchemeTrait,
    ColorTrait,
    DefaultCaselessStrEnum,
    FrozenDict,
    UseEnumCaseless,
    WriteOnceInt,
    WriteOnceMixin,
    WriteOnceUseEnumCaseless,
    add_traits_to_argparse,
    apply_from_argparse,
    class_traits_as_dict,
    dict_as_class_traits,
    dict_as_trait,
    get_args_dict,
    is_trait_writable,
    trait_as_dict,
)

# ─────────────────────────────────────────────────────────────────────────────
# Sample Enums (not named Test* to avoid pytest collection)
# ─────────────────────────────────────────────────────────────────────────────


class SampleColorEnum(enum.Enum):
    RED = ("#ff0000",)
    GREEN = ("#00ff00",)
    BLUE = ("#0000ff",)


class SampleModeEnum(enum.Enum):
    FAST = 1
    NORMAL = 2
    SLOW = 3


# ─────────────────────────────────────────────────────────────────────────────
# ColorTrait Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestColorTrait:
    """Tests for ColorTrait."""

    def test_info_text(self):
        """ColorTrait has correct info_text."""
        trait = ColorTrait()
        assert trait.info_text == "a color"

    def test_default_value_is_black(self):
        """ColorTrait default value is 'black'."""
        trait = ColorTrait()
        assert trait.default_value == "black"

    def test_validate_none_returns_none(self):
        """Validating None returns None."""
        trait = ColorTrait()

        class Obj(HasTraits):
            color = ColorTrait(allow_none=True)

        obj = Obj()
        result = trait.validate(obj, None)
        assert result is None

    def test_validate_string_color(self):
        """Validating string color works."""

        class Obj(HasTraits):
            color = ColorTrait()

        obj = Obj()
        obj.color = "red"
        assert obj.color is not None

    def test_validate_hex_color(self):
        """Validating hex color works."""

        class Obj(HasTraits):
            color = ColorTrait()

        obj = Obj()
        obj.color = "#ff0000"
        assert obj.color is not None

    def test_validate_invalid_color_raises(self):
        """Validating invalid color raises TraitError."""

        class Obj(HasTraits):
            color = ColorTrait()

        obj = Obj()
        with pytest.raises(TraitError):
            obj.color = "not_a_valid_color_xyz"


# ─────────────────────────────────────────────────────────────────────────────
# ColorSchemeTrait Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestColorSchemeTrait:
    """Tests for ColorSchemeTrait."""

    def test_info_text(self):
        """ColorSchemeTrait has correct info_text."""
        trait = ColorSchemeTrait()
        assert trait.info_text == "a list of colors"

    def test_default_is_empty_list(self):
        """Default value is empty list."""

        class Obj(HasTraits):
            scheme = ColorSchemeTrait()

        obj = Obj()
        assert obj.scheme == []

    def test_set_color_list(self):
        """Setting a list of colors works."""

        class Obj(HasTraits):
            scheme = ColorSchemeTrait()

        obj = Obj()
        obj.scheme = ["red", "blue"]
        assert len(obj.scheme) == 2

    def test_minlen_maxlen(self):
        """minlen and maxlen are respected."""
        trait = ColorSchemeTrait(minlen=1, maxlen=3)
        assert trait._minlen == 1
        assert trait._maxlen == 3


# ─────────────────────────────────────────────────────────────────────────────
# ColorPresetTrait Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestColorPresetTrait:
    """Tests for ColorPresetTrait."""

    def test_info_text(self):
        """ColorPresetTrait has correct info_text."""
        trait = ColorPresetTrait(SampleColorEnum)
        assert trait.info_text == "a predefined color scheme"

    def test_validate_enum_member(self):
        """Validating enum member works."""

        class Obj(HasTraits):
            preset = ColorPresetTrait(SampleColorEnum, default_value=SampleColorEnum.RED)

        obj = Obj()
        obj.preset = SampleColorEnum.GREEN
        assert obj.preset == SampleColorEnum.GREEN


# ─────────────────────────────────────────────────────────────────────────────
# WriteOnceMixin Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteOnceMixin:
    """Tests for WriteOnceMixin."""

    def test_write_once_flag(self):
        """WriteOnceMixin has write_once=True."""

        class TestMixin(WriteOnceMixin, Int):
            pass

        trait = TestMixin()
        assert trait.write_once is True

    def test_first_write_succeeds(self):
        """First write to write-once trait succeeds."""

        class Obj(HasTraits):
            value = WriteOnceInt()

        obj = Obj()
        obj.value = 42
        assert obj.value == 42

    def test_second_write_fails(self):
        """Second write to write-once trait fails."""

        class Obj(HasTraits):
            value = WriteOnceInt()

        obj = Obj()
        obj.value = 42
        with pytest.raises(TraitError):
            obj.value = 100


# ─────────────────────────────────────────────────────────────────────────────
# WriteOnceInt Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteOnceInt:
    """Tests for WriteOnceInt."""

    def test_is_int(self):
        """WriteOnceInt is an Int."""

        class Obj(HasTraits):
            value = WriteOnceInt()

        obj = Obj()
        obj.value = 123
        assert obj.value == 123

    def test_rejects_non_int(self):
        """WriteOnceInt rejects non-integer."""

        class Obj(HasTraits):
            value = WriteOnceInt()

        obj = Obj()
        with pytest.raises(TraitError):
            obj.value = "not an int"


# ─────────────────────────────────────────────────────────────────────────────
# FrozenDict Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrozenDict:
    """Tests for FrozenDict."""

    def test_converts_to_MappingProxyType(self):
        """FrozenDict converts value to MappingProxyType."""

        class Obj(HasTraits):
            data = FrozenDict()

        obj = Obj()
        obj.data = {"key": "value"}
        assert isinstance(obj.data, MappingProxyType)

    def test_frozen_dict_immutable(self):
        """Resulting MappingProxyType is immutable."""

        class Obj(HasTraits):
            data = FrozenDict()

        obj = Obj()
        obj.data = {"key": "value"}
        with pytest.raises(TypeError):
            obj.data["new_key"] = "new_value"


# ─────────────────────────────────────────────────────────────────────────────
# UseEnumCaseless Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestUseEnumCaseless:
    """Tests for UseEnumCaseless."""

    def test_select_by_name_case_insensitive(self):
        """select_by_name is case insensitive."""
        trait = UseEnumCaseless(SampleModeEnum)
        result = trait.select_by_name("fast")
        assert result == SampleModeEnum.FAST

    def test_select_by_name_upper_case(self):
        """select_by_name works with upper case."""
        trait = UseEnumCaseless(SampleModeEnum)
        result = trait.select_by_name("SLOW")
        assert result == SampleModeEnum.SLOW

    def test_select_by_name_mixed_case(self):
        """select_by_name works with mixed case."""
        trait = UseEnumCaseless(SampleModeEnum)
        result = trait.select_by_name("Normal")
        assert result == SampleModeEnum.NORMAL


# ─────────────────────────────────────────────────────────────────────────────
# WriteOnceUseEnumCaseless Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteOnceUseEnumCaseless:
    """Tests for WriteOnceUseEnumCaseless."""

    def test_is_write_once(self):
        """WriteOnceUseEnumCaseless is write-once."""
        trait = WriteOnceUseEnumCaseless(SampleModeEnum)
        assert trait.write_once is True

    def test_first_write_succeeds(self):
        """First write succeeds."""

        class Obj(HasTraits):
            mode = WriteOnceUseEnumCaseless(SampleModeEnum)

        obj = Obj()
        obj.mode = SampleModeEnum.FAST
        assert obj.mode == SampleModeEnum.FAST


# ─────────────────────────────────────────────────────────────────────────────
# DefaultCaselessStrEnum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDefaultCaselessStrEnum:
    """Tests for DefaultCaselessStrEnum."""

    def test_validate_none_uses_default(self):
        """Validating None uses default value."""

        class Obj(HasTraits):
            mode = DefaultCaselessStrEnum(["fast", "slow"], default_value="fast")

        obj = Obj()
        # Trait should use default when None is passed
        trait = obj.traits()["mode"]
        result = trait.validate(obj, None)
        assert result == "fast"

    def test_validate_empty_uses_default(self):
        """Validating empty string uses default."""

        class Obj(HasTraits):
            mode = DefaultCaselessStrEnum(["fast", "slow"], default_value="slow")

        obj = Obj()
        trait = obj.traits()["mode"]
        result = trait.validate(obj, "")
        assert result == "slow"

    def test_validate_normal_value(self):
        """Validating normal value works."""

        class Obj(HasTraits):
            mode = DefaultCaselessStrEnum(["fast", "slow"], default_value="fast")

        obj = Obj()
        obj.mode = "slow"
        assert obj.mode == "slow"


# ─────────────────────────────────────────────────────────────────────────────
# is_trait_writable Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIsTraitWritable:
    """Tests for is_trait_writable function."""

    def test_normal_trait_is_writable(self):
        """Normal trait is writable."""
        trait = Int()
        assert is_trait_writable(trait) is True

    def test_read_only_trait_not_writable(self):
        """Read-only trait is not writable."""
        trait = Int()
        trait.read_only = True
        assert is_trait_writable(trait) is False

    def test_write_once_trait_not_writable(self):
        """Write-once trait is not writable."""
        trait = WriteOnceInt()
        assert is_trait_writable(trait) is False


# ─────────────────────────────────────────────────────────────────────────────
# trait_as_dict Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestTraitAsDict:
    """Tests for trait_as_dict function."""

    def test_returns_dict(self):
        """trait_as_dict returns a dict."""
        trait = Int(default_value=42)
        result = trait_as_dict(trait)
        assert isinstance(result, dict)

    def test_includes_class_info(self):
        """Result includes __class__ info."""
        trait = Int()
        result = trait_as_dict(trait)
        assert "__class__" in result
        assert result["__class__"][1] == "Int"

    def test_includes_default_value(self):
        """Result includes default_value."""
        trait = Int(default_value=100)
        result = trait_as_dict(trait)
        assert result.get("default_value") == 100

    def test_enum_trait_includes_values(self):
        """UseEnum trait includes values tuple."""
        trait = UseEnumCaseless(SampleModeEnum)
        result = trait_as_dict(trait)
        assert "values" in result
        assert set(result["values"]) == {"FAST", "NORMAL", "SLOW"}


# ─────────────────────────────────────────────────────────────────────────────
# class_traits_as_dict Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestClassTraitsAsDict:
    """Tests for class_traits_as_dict function."""

    def test_from_instance(self):
        """Works with HasTraits instance."""

        class Obj(HasTraits):
            value = Int(default_value=10)

        obj = Obj()
        obj.value = 20
        result = class_traits_as_dict(obj)
        assert "value" in result
        assert result["value"]["__value__"] == 20

    def test_from_class(self):
        """Works with HasTraits class."""

        class Obj(HasTraits):
            value = Int(default_value=10)

        result = class_traits_as_dict(Obj)
        assert "value" in result

    def test_from_dict(self):
        """Works with dict of traits."""
        traits = {"count": Int(default_value=5)}
        result = class_traits_as_dict(traits)
        assert "count" in result

    def test_invalid_type_raises(self):
        """Invalid type raises TypeError."""
        with pytest.raises(TypeError, match="does not support traits"):
            class_traits_as_dict("not a valid type")


# ─────────────────────────────────────────────────────────────────────────────
# dict_as_trait Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDictAsTrait:
    """Tests for dict_as_trait function."""

    def test_roundtrip_int_trait(self):
        """Int trait survives roundtrip."""
        original = Int(default_value=42)
        as_dict = trait_as_dict(original)
        restored = dict_as_trait(as_dict)
        assert isinstance(restored, Int)
        assert restored.default_value == 42

    def test_missing_class_raises(self):
        """Missing __class__ raises ValueError."""
        with pytest.raises(ValueError, match="No module and class"):
            dict_as_trait({"default_value": 10})

    def test_unknown_class_raises(self):
        """Unknown class raises TypeError."""
        with pytest.raises(TypeError, match="Unknown class"):
            dict_as_trait({"__class__": ("traitlets", "NonExistentClass")})


# ─────────────────────────────────────────────────────────────────────────────
# dict_as_class_traits Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDictAsClassTraits:
    """Tests for dict_as_class_traits function."""

    def test_creates_has_traits_instance(self):
        """Creates a HasTraits instance."""
        trait_dict = {"count": trait_as_dict(Int(default_value=5))}
        result = dict_as_class_traits(trait_dict)
        assert isinstance(result, HasTraits)
        assert hasattr(result, "count")

    def test_restores_values(self):
        """Restores trait values."""
        trait_dict = {"count": trait_as_dict(Int(default_value=5))}
        trait_dict["count"]["__value__"] = 99
        result = dict_as_class_traits(trait_dict)
        assert result.count == 99

    def test_non_dict_raises(self):
        """Non-dict input raises TypeError."""
        with pytest.raises(TypeError, match="must be a dict"):
            dict_as_class_traits("not a dict")


# ─────────────────────────────────────────────────────────────────────────────
# get_args_dict Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetArgsDict:
    """Tests for get_args_dict function."""

    def test_only_returns_config_traits(self):
        """Only returns traits marked with config=True."""

        class Obj(HasTraits):
            configurable = Int(default_value=10).tag(config=True)
            not_configurable = Int(default_value=20)

        obj = Obj()
        obj.configurable = 25
        obj.not_configurable = 30
        result = get_args_dict(obj)
        assert "configurable" in result
        assert result["configurable"] == 25
        assert "not_configurable" not in result

    def test_excludes_hidden_config_traits(self):
        """Excludes traits that are both config=True and hidden=True."""

        class Obj(HasTraits):
            visible = Int(default_value=10).tag(config=True)
            hidden = Int(default_value=0).tag(config=True, hidden=True)

        obj = Obj()
        obj.visible = 25
        obj.hidden = 5
        result = get_args_dict(obj)
        assert "visible" in result
        assert "hidden" not in result

    def test_incl_all_includes_hidden_config_traits(self):
        """incl_all=True includes hidden traits that have config=True."""

        class Obj(HasTraits):
            visible = Int(default_value=10).tag(config=True)
            hidden = Int(default_value=0).tag(config=True, hidden=True)

        obj = Obj()
        obj.hidden = 5
        result = get_args_dict(obj, incl_all=True)
        assert "hidden" in result

    def test_excludes_runtime_state_traits(self):
        """Excludes runtime state traits like running and zindex."""

        class Obj(HasTraits):
            speed = Float(default_value=1.0).tag(config=True)
            running = Int(default_value=0)  # No config=True
            zindex = Int(default_value=-1)  # No config=True

        obj = Obj()
        obj.speed = 2.0
        obj.running = 1
        obj.zindex = 0
        result = get_args_dict(obj)
        assert "speed" in result
        assert "running" not in result
        assert "zindex" not in result

    def test_excludes_write_once_traits(self):
        """Excludes write-once traits even if config=True."""

        class Obj(HasTraits):
            normal = Int(default_value=10).tag(config=True)
            once = WriteOnceInt().tag(config=True)

        obj = Obj()
        obj.normal = 25
        obj.once = 100
        result = get_args_dict(obj)
        assert "normal" in result
        assert "once" not in result  # Write-once is not writable


# ─────────────────────────────────────────────────────────────────────────────
# add_traits_to_argparse Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAddTraitsToArgparse:
    """Tests for add_traits_to_argparse function."""

    def test_adds_config_traits(self):
        """Adds traits marked config=True."""

        class Obj(HasTraits):
            speed = Float(default_value=1.0).tag(config=True)
            hidden = Int(default_value=0)

        obj = Obj()
        parser = ArgumentParser()
        add_traits_to_argparse(obj, parser)

        # Parse with --speed
        args = parser.parse_args(["--speed", "2.5"])
        assert args.speed == 2.5

    def test_with_prefix(self):
        """Adds prefix to argument names."""

        class Obj(HasTraits):
            value = Int(default_value=1).tag(config=True)

        obj = Obj()
        parser = ArgumentParser()
        add_traits_to_argparse(obj, parser, prefix="test")

        args = parser.parse_args(["--test.value", "42"])
        assert getattr(args, "test.value") == 42

    def test_list_trait_uses_nargs(self):
        """List trait uses nargs='+'."""

        class Obj(HasTraits):
            colors = List(default_value=[]).tag(config=True)

        obj = Obj()
        parser = ArgumentParser()
        add_traits_to_argparse(obj, parser)

        args = parser.parse_args(["--colors", "red", "blue"])
        assert args.colors == ["red", "blue"]


# ─────────────────────────────────────────────────────────────────────────────
# apply_from_argparse Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestApplyFromArgparse:
    """Tests for apply_from_argparse function."""

    def test_applies_args_to_target(self):
        """Applies args to target object."""

        class Obj(HasTraits):
            speed = Float(default_value=1.0).tag(config=True)

        obj = Obj()
        traits = obj.traits()
        args = Namespace(speed=2.5)
        changed = apply_from_argparse(args, traits=traits, target=obj)

        assert obj.speed == 2.5
        assert changed["speed"] == 2.5

    def test_only_returns_changed(self):
        """Only returns changed traits."""

        class Obj(HasTraits):
            speed = Float(default_value=1.0).tag(config=True)
            count = Int(default_value=5).tag(config=True)

        obj = Obj()
        traits = obj.traits()
        args = Namespace(speed=2.5, count=None)
        changed = apply_from_argparse(args, traits=traits, target=obj)

        assert "speed" in changed
        assert "count" not in changed

    def test_raises_on_non_config_trait(self):
        """Raises when trying to set non-config trait."""

        class Obj(HasTraits):
            speed = Float(default_value=1.0)  # Not config=True

        obj = Obj()
        traits = obj.traits()
        args = Namespace(speed=2.5)

        with pytest.raises(ValueError, match="not marked as configurable"):
            apply_from_argparse(args, traits=traits, target=obj)

    def test_with_traits_dict_only(self):
        """Works with traits dict instead of target."""
        traits = {"speed": Float(default_value=1.0).tag(config=True)}
        args = Namespace(speed=2.5)

        changed = apply_from_argparse(args, traits=traits)
        assert changed["speed"] == 2.5

    def test_crashes_without_traits(self):
        """Crashes when traits is None (AttributeError before check)."""
        # Note: The function has a bug - it calls traits.copy() before
        # checking if traits is None. This test documents actual behavior.
        args = Namespace(speed=2.5)

        with pytest.raises(AttributeError):
            apply_from_argparse(args, traits=None, target=None)
