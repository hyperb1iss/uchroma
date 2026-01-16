#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Trait display and argparse generation.

Converts traitlets to CLI arguments and formats trait values for display.
"""

import math
from argparse import ArgumentParser, BooleanOptionalAction
from typing import Any

from traitlets import Bool, Float, HasTraits, Int, TraitType, Unicode

from uchroma.client.output import Output


class TraitDisplay:
    """
    Handles trait introspection, display, and argparse generation.

    Bridges traitlets and the CLI by:
    - Extracting config-tagged traits
    - Generating argparse arguments from traits
    - Formatting trait values for display
    """

    def __init__(self, out: Output):
        self.out = out

    # ─────────────────────────────────────────────────────────────────────────
    # Trait Introspection
    # ─────────────────────────────────────────────────────────────────────────

    def get_config_traits(self, cls: type[HasTraits]) -> dict[str, TraitType]:
        """
        Get all traits tagged with config=True.

        Args:
            cls: A HasTraits class (not instance)

        Returns:
            Dict of trait name -> trait object
        """
        result = {}
        for name, trait in cls.class_traits().items():
            if trait.metadata.get("config", False):
                result[name] = trait
        return result

    def get_type_name(self, trait: TraitType) -> str:
        """Get human-readable type name for a trait."""
        type_map = {
            Float: "float",
            Int: "int",
            Unicode: "str",
            Bool: "bool",
        }

        for trait_cls, name in type_map.items():
            if isinstance(trait, trait_cls):
                return name

        # Fallback to class name
        return trait.__class__.__name__.lower()

    def get_constraints(self, trait: TraitType) -> str:
        """
        Get constraint string for a trait (min/max/choices).

        Returns empty string if no constraints.
        """
        parts = []

        # Handle min/max for numeric traits
        if isinstance(trait, (Float, Int)):
            # Skip infinite bounds (default values)
            min_val = trait.min
            max_val = trait.max
            if min_val is not None and not math.isinf(min_val):
                parts.append(f"min: {min_val}")
            if max_val is not None and not math.isinf(max_val):
                parts.append(f"max: {max_val}")

        if not parts:
            return ""

        return f"[{', '.join(parts)}]"

    # ─────────────────────────────────────────────────────────────────────────
    # Value Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def format_value(self, trait: TraitType, value: Any) -> str:
        """
        Format a trait value for display.

        Uses semantic styling from Output.
        """
        if isinstance(trait, Bool):
            display = "on" if value else "off"
        elif value is None:
            display = "none"
        else:
            display = str(value)

        return self.out.value(display)

    # ─────────────────────────────────────────────────────────────────────────
    # Argparse Generation
    # ─────────────────────────────────────────────────────────────────────────

    def add_trait_arg(self, parser: ArgumentParser, name: str, trait: TraitType) -> None:
        """
        Add a single trait as an argparse argument.

        Handles type conversion, defaults, and bool negation.
        """
        arg_name = f"--{name.replace('_', '-')}"
        help_parts = []

        # Get constraints for help text
        constraints = self.get_constraints(trait)
        if constraints:
            help_parts.append(constraints)

        # Handle by trait type
        if isinstance(trait, Bool):
            # BooleanOptionalAction gives --flag and --no-flag
            parser.add_argument(
                arg_name,
                action=BooleanOptionalAction,
                default=trait.default(),
                help=" ".join(help_parts) if help_parts else None,
            )
        elif isinstance(trait, Float):
            parser.add_argument(
                arg_name,
                type=float,
                default=trait.default(),
                metavar="NUM",
                help=" ".join(help_parts) if help_parts else None,
            )
        elif isinstance(trait, Int):
            parser.add_argument(
                arg_name,
                type=int,
                default=trait.default(),
                metavar="NUM",
                help=" ".join(help_parts) if help_parts else None,
            )
        elif isinstance(trait, Unicode):
            parser.add_argument(
                arg_name,
                type=str,
                default=trait.default(),
                metavar="TEXT",
                help=" ".join(help_parts) if help_parts else None,
            )
        else:
            # Generic fallback
            parser.add_argument(
                arg_name,
                default=trait.default(),
                help=" ".join(help_parts) if help_parts else None,
            )

    def add_traits_to_parser(
        self, parser: ArgumentParser, cls: type[HasTraits]
    ) -> dict[str, TraitType]:
        """
        Add all config traits from a class to a parser.

        Returns the dict of added traits for reference.
        """
        traits = self.get_config_traits(cls)
        for name, trait in traits.items():
            self.add_trait_arg(parser, name, trait)
        return traits

    # ─────────────────────────────────────────────────────────────────────────
    # Trait Line Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def format_trait_line(self, name: str, trait: TraitType, value: Any) -> str:
        """
        Format a single trait for display.

        Returns a line like:
            speed (float) = 1.0 [min: 0.1, max: 5.0]
        """
        type_name = self.get_type_name(trait)
        constraints = self.get_constraints(trait)
        formatted_value = self.format_value(trait, value)

        return self.out.trait_line(name, type_name, formatted_value, constraints)

    def format_all_traits(self, obj: HasTraits) -> list[str]:
        """
        Format all config traits of an instance for display.

        Returns list of formatted lines.
        """
        lines = []
        traits = self.get_config_traits(type(obj))

        for name, trait in sorted(traits.items()):
            value = getattr(obj, name)
            lines.append(self.format_trait_line(name, trait, value))

        return lines
