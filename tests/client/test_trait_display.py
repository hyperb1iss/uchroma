#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for trait display formatting."""

from argparse import ArgumentParser

from traitlets import Bool, Float, HasTraits, Int, Unicode

from uchroma.client.output import Output
from uchroma.client.trait_display import TraitDisplay


class SampleTraits(HasTraits):
    """Sample class with various traits for testing."""

    speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)
    count = Int(default_value=10, min=1, max=100).tag(config=True)
    name = Unicode(default_value="test").tag(config=True)
    enabled = Bool(default_value=True).tag(config=True)
    hidden = Float(default_value=0.0)  # No config tag


class TestTraitInfo:
    """Test trait introspection."""

    def test_extracts_config_traits(self):
        td = TraitDisplay(Output(force_color=False))
        traits = td.get_config_traits(SampleTraits)

        assert "speed" in traits
        assert "count" in traits
        assert "name" in traits
        assert "enabled" in traits
        assert "hidden" not in traits  # No config tag

    def test_get_trait_type_name(self):
        td = TraitDisplay(Output(force_color=False))

        assert td.get_type_name(Float()) == "float"
        assert td.get_type_name(Int()) == "int"
        assert td.get_type_name(Unicode()) == "str"
        assert td.get_type_name(Bool()) == "bool"

    def test_get_constraints_float(self):
        td = TraitDisplay(Output(force_color=False))
        trait = Float(min=0.1, max=5.0)
        constraints = td.get_constraints(trait)

        assert "0.1" in constraints
        assert "5.0" in constraints

    def test_get_constraints_int(self):
        td = TraitDisplay(Output(force_color=False))
        trait = Int(min=1, max=100)
        constraints = td.get_constraints(trait)

        assert "1" in constraints
        assert "100" in constraints

    def test_get_constraints_no_limits(self):
        td = TraitDisplay(Output(force_color=False))
        trait = Float()
        constraints = td.get_constraints(trait)

        assert constraints == ""


class TestTraitFormatting:
    """Test trait value formatting."""

    def test_format_float(self):
        td = TraitDisplay(Output(force_color=False))
        result = td.format_value(Float(), 1.5)
        assert "1.5" in result

    def test_format_int(self):
        td = TraitDisplay(Output(force_color=False))
        result = td.format_value(Int(), 42)
        assert "42" in result

    def test_format_bool_true(self):
        td = TraitDisplay(Output(force_color=False))
        result = td.format_value(Bool(), True)
        assert "true" in result.lower() or "yes" in result.lower() or "on" in result.lower()

    def test_format_bool_false(self):
        td = TraitDisplay(Output(force_color=False))
        result = td.format_value(Bool(), False)
        assert "false" in result.lower() or "no" in result.lower() or "off" in result.lower()

    def test_format_string(self):
        td = TraitDisplay(Output(force_color=False))
        result = td.format_value(Unicode(), "hello")
        assert "hello" in result


class TestArgparseGeneration:
    """Test argparse argument generation from traits."""

    def test_generates_float_arg(self):
        td = TraitDisplay(Output(force_color=False))
        parser = ArgumentParser()
        trait = Float(min=0.1, max=5.0)
        trait.tag(config=True)

        td.add_trait_arg(parser, "speed", trait)
        args = parser.parse_args(["--speed", "2.5"])

        assert args.speed == 2.5

    def test_generates_int_arg(self):
        td = TraitDisplay(Output(force_color=False))
        parser = ArgumentParser()
        trait = Int(min=1, max=100)

        td.add_trait_arg(parser, "count", trait)
        args = parser.parse_args(["--count", "50"])

        assert args.count == 50

    def test_generates_bool_flag(self):
        td = TraitDisplay(Output(force_color=False))
        parser = ArgumentParser()
        trait = Bool(default_value=False)

        td.add_trait_arg(parser, "enabled", trait)
        args = parser.parse_args(["--enabled"])

        assert args.enabled is True

    def test_generates_negated_bool_flag(self):
        td = TraitDisplay(Output(force_color=False))
        parser = ArgumentParser()
        trait = Bool(default_value=True)

        td.add_trait_arg(parser, "enabled", trait)
        args = parser.parse_args(["--no-enabled"])

        assert args.enabled is False

    def test_generates_string_arg(self):
        td = TraitDisplay(Output(force_color=False))
        parser = ArgumentParser()
        trait = Unicode()

        td.add_trait_arg(parser, "name", trait)
        args = parser.parse_args(["--name", "myname"])

        assert args.name == "myname"

    def test_adds_all_config_traits(self):
        td = TraitDisplay(Output(force_color=False))
        parser = ArgumentParser()

        td.add_traits_to_parser(parser, SampleTraits)

        args = parser.parse_args(["--speed", "3.0", "--count", "20"])
        assert args.speed == 3.0
        assert args.count == 20


class TestTraitLines:
    """Test full trait line formatting."""

    def test_format_trait_line(self):
        td = TraitDisplay(Output(force_color=False))
        obj = SampleTraits()

        line = td.format_trait_line("speed", obj.traits()["speed"], obj.speed)

        assert "speed" in line
        assert "float" in line
        assert "1.0" in line  # default value

    def test_format_all_traits(self):
        td = TraitDisplay(Output(force_color=False))
        obj = SampleTraits()

        lines = td.format_all_traits(obj)

        # Should have 4 config traits
        assert len(lines) == 4
        assert any("speed" in line for line in lines)
        assert any("count" in line for line in lines)
