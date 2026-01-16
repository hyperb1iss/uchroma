# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.

"""Unit tests for uchroma.server.effects module."""

from __future__ import annotations

import pytest

from uchroma.server.effects import EffectDef, Effects

# ─────────────────────────────────────────────────────────────────────────────
# EffectDef Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEffectDef:
    """Tests for EffectDef dataclass."""

    def test_basic_effect_def(self):
        """EffectDef stores basic attributes correctly."""
        effect = EffectDef(
            name="test",
            legacy_id=0x01,
            extended_id=0x02,
            description="Test effect",
            max_colors=2,
            has_speed=True,
            has_direction=False,
        )
        assert effect.name == "test"
        assert effect.legacy_id == 0x01
        assert effect.extended_id == 0x02
        assert effect.description == "Test effect"
        assert effect.max_colors == 2
        assert effect.has_speed is True
        assert effect.has_direction is False

    def test_supports_legacy(self):
        """supports_legacy() returns True when legacy_id is set."""
        effect_both = EffectDef("test", legacy_id=0x01, extended_id=0x02)
        effect_legacy_only = EffectDef("test", legacy_id=0x01, extended_id=None)
        effect_extended_only = EffectDef("test", legacy_id=None, extended_id=0x02)

        assert effect_both.supports_legacy() is True
        assert effect_legacy_only.supports_legacy() is True
        assert effect_extended_only.supports_legacy() is False

    def test_supports_extended(self):
        """supports_extended() returns True when extended_id is set."""
        effect_both = EffectDef("test", legacy_id=0x01, extended_id=0x02)
        effect_legacy_only = EffectDef("test", legacy_id=0x01, extended_id=None)
        effect_extended_only = EffectDef("test", legacy_id=None, extended_id=0x02)

        assert effect_both.supports_extended() is True
        assert effect_legacy_only.supports_extended() is False
        assert effect_extended_only.supports_extended() is True

    def test_get_id_legacy(self):
        """get_id() returns legacy_id when uses_extended is False."""
        effect = EffectDef("test", legacy_id=0x06, extended_id=0x01)
        assert effect.get_id(uses_extended=False) == 0x06

    def test_get_id_extended(self):
        """get_id() returns extended_id when uses_extended is True."""
        effect = EffectDef("test", legacy_id=0x06, extended_id=0x01)
        assert effect.get_id(uses_extended=True) == 0x01

    def test_get_id_none_when_unsupported(self):
        """get_id() returns None when effect not supported on protocol."""
        effect_legacy_only = EffectDef("test", legacy_id=0x06, extended_id=None)
        assert effect_legacy_only.get_id(uses_extended=True) is None

    def test_effect_def_is_frozen(self):
        """EffectDef is immutable."""
        effect = EffectDef("test", legacy_id=0x01, extended_id=0x02)
        with pytest.raises(AttributeError):
            effect.legacy_id = 0x00


# ─────────────────────────────────────────────────────────────────────────────
# Effects Registry Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEffectsRegistry:
    """Tests for Effects registry class."""

    def test_disable_effect(self):
        """DISABLE effect has correct values."""
        effect = Effects.DISABLE
        assert effect.name == "disable"
        assert effect.legacy_id == 0x00
        assert effect.extended_id == 0x00

    def test_static_effect(self):
        """STATIC effect has correct values."""
        effect = Effects.STATIC
        assert effect.name == "static"
        assert effect.legacy_id == 0x06
        assert effect.extended_id == 0x01
        assert effect.max_colors == 1

    def test_wave_effect(self):
        """WAVE effect has correct values."""
        effect = Effects.WAVE
        assert effect.name == "wave"
        assert effect.legacy_id == 0x01
        assert effect.extended_id == 0x04
        assert effect.has_direction is True

    def test_breathe_effect(self):
        """BREATHE effect has correct values."""
        effect = Effects.BREATHE
        assert effect.name == "breathe"
        assert effect.legacy_id == 0x03
        assert effect.extended_id == 0x02
        assert effect.max_colors == 2

    def test_reactive_effect(self):
        """REACTIVE effect has correct values."""
        effect = Effects.REACTIVE
        assert effect.name == "reactive"
        assert effect.legacy_id == 0x02
        assert effect.extended_id == 0x05
        assert effect.has_speed is True
        assert effect.max_colors == 1

    def test_starlight_effect(self):
        """STARLIGHT effect has correct values."""
        effect = Effects.STARLIGHT
        assert effect.name == "starlight"
        assert effect.legacy_id == 0x19
        assert effect.extended_id == 0x07
        assert effect.has_speed is True
        assert effect.max_colors == 2

    def test_custom_frame_effect(self):
        """CUSTOM_FRAME effect has correct values."""
        effect = Effects.CUSTOM_FRAME
        assert effect.name == "custom_frame"
        assert effect.legacy_id == 0x05
        assert effect.extended_id == 0x08


class TestEffectsLegacyOnly:
    """Tests for legacy-only effects."""

    def test_gradient_legacy_only(self):
        """GRADIENT is legacy-only."""
        effect = Effects.GRADIENT
        assert effect.supports_legacy() is True
        assert effect.supports_extended() is False

    def test_sweep_legacy_only(self):
        """SWEEP is legacy-only."""
        effect = Effects.SWEEP
        assert effect.supports_legacy() is True
        assert effect.supports_extended() is False

    def test_morph_legacy_only(self):
        """MORPH is legacy-only."""
        effect = Effects.MORPH
        assert effect.supports_legacy() is True
        assert effect.supports_extended() is False

    def test_fire_legacy_only(self):
        """FIRE is legacy-only."""
        effect = Effects.FIRE
        assert effect.supports_legacy() is True
        assert effect.supports_extended() is False

    def test_ripple_legacy_only(self):
        """RIPPLE is legacy-only."""
        effect = Effects.RIPPLE
        assert effect.supports_legacy() is True
        assert effect.supports_extended() is False


class TestEffectsLookup:
    """Tests for Effects lookup methods."""

    def test_get_by_name(self):
        """get() returns effect by name."""
        effect = Effects.get("static")
        assert effect is not None
        assert effect.name == "static"

    def test_get_by_name_case_insensitive(self):
        """get() is case-insensitive."""
        effect1 = Effects.get("STATIC")
        effect2 = Effects.get("Static")
        effect3 = Effects.get("static")
        assert effect1 == effect2 == effect3

    def test_get_nonexistent_returns_none(self):
        """get() returns None for unknown effect."""
        effect = Effects.get("nonexistent")
        assert effect is None

    def test_get_id_legacy(self):
        """get_id() returns legacy ID."""
        assert Effects.get_id("static", uses_extended=False) == 0x06
        assert Effects.get_id("wave", uses_extended=False) == 0x01

    def test_get_id_extended(self):
        """get_id() returns extended ID."""
        assert Effects.get_id("static", uses_extended=True) == 0x01
        assert Effects.get_id("wave", uses_extended=True) == 0x04

    def test_get_id_nonexistent(self):
        """get_id() returns None for unknown effect."""
        assert Effects.get_id("nonexistent", uses_extended=False) is None

    def test_supports_protocol_legacy(self):
        """supports_protocol() checks legacy support."""
        assert Effects.supports_protocol("static", uses_extended=False) is True
        assert Effects.supports_protocol("gradient", uses_extended=False) is True

    def test_supports_protocol_extended(self):
        """supports_protocol() checks extended support."""
        assert Effects.supports_protocol("static", uses_extended=True) is True
        assert Effects.supports_protocol("gradient", uses_extended=True) is False


class TestEffectsCollections:
    """Tests for Effects collection methods."""

    def test_get_all_effects(self):
        """get_all_effects() returns all registered effects."""
        effects = Effects.get_all_effects()
        assert len(effects) > 0
        assert all(isinstance(e, EffectDef) for e in effects)

    def test_get_legacy_effects(self):
        """get_legacy_effects() returns legacy-compatible effects."""
        effects = Effects.get_legacy_effects()
        assert len(effects) > 0
        assert all(e.supports_legacy() for e in effects)

    def test_get_extended_effects(self):
        """get_extended_effects() returns extended-compatible effects."""
        effects = Effects.get_extended_effects()
        assert len(effects) > 0
        assert all(e.supports_extended() for e in effects)

    def test_get_effect_names(self):
        """get_effect_names() returns list of effect names."""
        names = Effects.get_effect_names()
        assert "static" in names
        assert "wave" in names
        assert "breathe" in names
        assert "disable" in names

    def test_more_legacy_than_extended(self):
        """Legacy protocol supports more effects than extended."""
        legacy = Effects.get_legacy_effects()
        extended = Effects.get_extended_effects()
        assert len(legacy) > len(extended)
