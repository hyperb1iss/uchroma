#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
FX command — hardware lighting effects.

Works entirely through D-Bus, no server-side imports.
"""

from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from typing import Any, ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class FXInfo:
    """Parsed FX metadata and traits from D-Bus."""

    def __init__(self, name: str, traits_dict: dict):
        from uchroma.traits import dict_as_class_traits  # noqa: PLC0415

        self.name = name
        self.traits_dict = traits_dict
        self._traits = dict_as_class_traits(traits_dict) if traits_dict else None

        # Get description from traits if available
        self.description = ""
        if self._traits and hasattr(self._traits, "description"):
            self.description = self._traits.description or ""

        # Check if hidden
        self.hidden = False
        if self._traits and hasattr(self._traits, "hidden"):
            self.hidden = self._traits.hidden

    @property
    def traits(self):
        return self._traits


def _get_trait_type(trait_dict: dict) -> str:
    """Extract type name from serialized trait dict."""
    cls_info = trait_dict.get("__class__", ("", "unknown"))
    cls_name = cls_info[1] if isinstance(cls_info, (list, tuple)) else "unknown"
    cls_lower = cls_name.lower()
    type_map = {
        "float": "float",
        "int": "int",
        "unicode": "str",
        "bool": "bool",
        "caselessstrenum": "choice",
        "defaultcaselessstrenum": "choice",
        "colortrait": "color",
        "colorschemetrait": "colors",
    }
    return type_map.get(cls_lower, "str")


def _add_trait_to_parser(parser: ArgumentParser, name: str, trait_dict: dict) -> None:
    """Add a single trait as an argparse argument from D-Bus dict."""
    metadata = trait_dict.get("metadata", {})
    if not metadata.get("config", False):
        return

    arg_name = f"--{name.replace('_', '-')}"
    trait_type = _get_trait_type(trait_dict)

    help_parts = []
    if "min" in trait_dict:
        help_parts.append(f"min: {trait_dict['min']}")
    if "max" in trait_dict:
        help_parts.append(f"max: {trait_dict['max']}")
    if "default_value" in trait_dict and trait_dict["default_value"] is not None:
        help_parts.append(f"default: {trait_dict['default_value']}")

    help_text = f"[{', '.join(help_parts)}]" if help_parts else None

    if trait_type == "bool":
        parser.add_argument(
            arg_name,
            action=BooleanOptionalAction,
            default=trait_dict.get("default_value"),
            help=help_text,
        )
    elif trait_type == "choice":
        values = trait_dict.get("values", [])
        lower_to_original = {v.lower(): v for v in values}

        def make_choice_type(lookup: dict[str, str]):
            def choice_type(s: str) -> str:
                return lookup.get(s.lower(), s)

            return choice_type

        parser.add_argument(
            arg_name,
            type=make_choice_type(lower_to_original),
            choices=values,
            default=trait_dict.get("default_value"),
            metavar=arg_name.upper().lstrip("-"),
            help=f"one of: {', '.join(v.lower() for v in values)}",
        )
    elif trait_type == "float":
        parser.add_argument(
            arg_name,
            type=float,
            default=trait_dict.get("default_value"),
            metavar="NUM",
            help=help_text,
        )
    elif trait_type == "int":
        parser.add_argument(
            arg_name,
            type=int,
            default=trait_dict.get("default_value"),
            metavar="NUM",
            help=help_text,
        )
    elif trait_type in ("color", "colors"):
        parser.add_argument(
            arg_name,
            type=str,
            default=trait_dict.get("default_value"),
            metavar="COLOR",
            help=help_text,
        )
    else:
        parser.add_argument(
            arg_name,
            type=str,
            default=trait_dict.get("default_value"),
            help=help_text,
        )


def _extract_changed_traits(args: Namespace, traits_dict: dict) -> dict[str, Any]:
    """Extract trait values that were explicitly set from args."""
    changed = {}
    for name, trait_dict in traits_dict.items():
        metadata = trait_dict.get("metadata", {})
        if not metadata.get("config", False):
            continue

        arg_name = name.replace("-", "_")
        if hasattr(args, arg_name):
            value = getattr(args, arg_name)
            default = trait_dict.get("default_value")
            if value is not None and value != default:
                changed[name] = value

    return changed


class FxCommand(Command):
    """Apply hardware lighting effects."""

    name = "fx"
    help = "Set hardware lighting effect"
    aliases: ClassVar[list[str]] = ["effect"]

    def __init__(self, cli=None):
        super().__init__(cli)
        self._fx_cache: dict[str, FXInfo] | None = None

    def configure_parser(self, parser: ArgumentParser) -> None:
        # Use add_help=False since we have dynamic subcommands
        parser.add_argument("-l", "--list", action="store_true", help="list available effects")

    def run(self, args: Namespace) -> int:
        # Handle --list shortcut
        if getattr(args, "list", False):
            return self._list(args)

        unparsed = getattr(args, "unparsed", [])

        # No args or "list" command -> show effects
        if not unparsed or unparsed[0] in ("list", "ls"):
            return self._list(args)

        # Dynamic FX subcommand - handled via unparsed args
        return self._set_fx(args)

    # ─────────────────────────────────────────────────────────────────────────
    # FX Info (from D-Bus)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_effects(self, args: Namespace) -> dict[str, FXInfo] | None:
        """Get available effects from D-Bus, cached per command run."""
        if self._fx_cache is not None:
            return self._fx_cache

        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return None

        avail = device.AvailableFX
        if not avail:
            return None

        self._fx_cache = {}
        for name, traits_dict in sorted(avail.items()):
            info = FXInfo(name, traits_dict)
            if not info.hidden:
                self._fx_cache[name] = info

        return self._fx_cache

    def _get_current_fx(self, args: Namespace) -> tuple[str, dict] | None:
        """Get current FX state."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError:
            return None
        return device.CurrentFX

    # ─────────────────────────────────────────────────────────────────────────
    # Subcommands
    # ─────────────────────────────────────────────────────────────────────────

    def _calc_key_width(self, effects: dict[str, FXInfo]) -> int:
        """Calculate max key width for table alignment."""
        keys = list(effects.keys())
        for info in effects.values():
            for name in info.traits_dict:
                keys.append(name)
        return max(len(k) for k in keys) + 1 if keys else 15

    def _list(self, args: Namespace) -> int:
        """List available effects with current state."""
        effects = self._get_effects(args)
        if effects is None:
            self.print(self.out.muted("No effects available"))
            return 0

        # Get current state
        current = self._get_current_fx(args)
        current_name = current[0] if current else None
        current_props = current[1] if current else {}

        self.print()
        self.print(self.out.header(" Built-in effects and arguments:"))
        self.print()

        key_width = self._calc_key_width(effects)

        for name, info in effects.items():
            # Skip internal effects
            if name in ("disable", "custom_frame"):
                continue

            # Header row
            is_active = name == current_name
            header_name = f"* {name}" if is_active else name
            self.print(
                self.out.table_header(key_width, header_name, info.description or name.title())
            )

            # If active, show current values
            values = current_props if is_active else None
            self._show_traits_table(info.traits_dict, key_width, values)

            self.print()
            self.print()

        return 0

    def _show_traits_table(
        self,
        traits_dict: dict,
        key_width: int,
        values: dict | None = None,
    ) -> None:
        """Display traits in table format."""
        count = 0
        for name, trait_dict in sorted(traits_dict.items()):
            metadata = trait_dict.get("metadata", {})
            if not metadata.get("config", False):
                continue

            # Skip internal traits
            if name in ("description", "hidden"):
                continue

            trait_type = _get_trait_type(trait_dict)

            constraints = []
            if "min" in trait_dict:
                constraints.append(f"min: {trait_dict['min']}")
            if "max" in trait_dict:
                constraints.append(f"max: {trait_dict['max']}")
            if "values" in trait_dict:
                choices = [v.lower() for v in trait_dict["values"]]
                if len(choices) > 4:
                    choices_str = ", ".join(choices[:4]) + ", ..."
                else:
                    choices_str = ", ".join(choices)
                constraints.append(f"one of: {choices_str}")
            if "default_value" in trait_dict and trait_dict["default_value"] is not None:
                constraints.append(f"default: {trait_dict['default_value']}")

            if constraints:
                value_str = f"{trait_type}: {', '.join(constraints)}"
            else:
                value_str = trait_type

            if count == 0:
                self.print(self.out.table_sep(key_width))

            # Show current value if available
            if values is not None and name in values:
                val = values[name]
                self.print(self.out.table_row(key_width, self.out.key(name), str(val)))
                self.print(self.out.table_row(key_width, f"({trait_type})", value_str))
                self.print(self.out.table_sep(key_width))
            else:
                self.print(self.out.table_row(key_width, name, value_str))

            count += 1

    def _set_fx(self, args: Namespace) -> int:
        """Set FX properties (dynamic subcommand)."""
        effects = self._get_effects(args)
        if effects is None:
            self.print(self.out.error("No effects available"))
            return 1

        unparsed = getattr(args, "unparsed", [])

        # Build dynamic parser for FX selection
        parser = ArgumentParser(prog="uchroma fx", add_help=True)
        sub = parser.add_subparsers(dest="effect", metavar="EFFECT")

        for name, info in effects.items():
            if name in ("disable", "custom_frame"):
                continue

            fx_parser = sub.add_parser(name, help=info.description or name.title())

            for trait_name, trait_dict in info.traits_dict.items():
                _add_trait_to_parser(fx_parser, trait_name, trait_dict)

        try:
            fx_args = parser.parse_args(unparsed)
        except SystemExit:
            return 1

        if not fx_args.effect:
            parser.print_help()
            return 1

        effect_name = fx_args.effect
        info = effects.get(effect_name)
        if info is None:
            self.print(self.out.error(f"Unknown effect: {effect_name}"))
            return 1

        changed = _extract_changed_traits(fx_args, info.traits_dict)

        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        # Use the device's SetFX method
        from uchroma.dbus_utils import dbus_prepare  # noqa: PLC0415

        prepared, _ = dbus_prepare(changed, variant=True)
        if not device.SetFX(effect_name, prepared):
            self.print(self.out.error(f"Failed to set effect: {effect_name}"))
            return 1

        self.print(self.out.success(f"Effect: {effect_name}"))
        return 0
