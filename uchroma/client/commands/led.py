#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
LED command — control standalone LEDs (logo, underglow, etc.).

Works entirely through D-Bus, no server-side imports.
"""

from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from typing import Any, ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class LEDInfo:
    """Parsed LED metadata and traits from D-Bus."""

    def __init__(self, name: str, traits_dict: dict):
        from uchroma.traits import dict_as_class_traits  # noqa: PLC0415

        self.name = name
        self.display_name = name.title()
        self.traits_dict = traits_dict
        self._traits = dict_as_class_traits(traits_dict) if traits_dict else None

    @property
    def traits(self):
        """Get HasTraits instance for trait introspection."""
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


class LEDCommand(Command):
    """Standalone LED control."""

    name = "led"
    help = "Control standalone LEDs (logo, underglow, etc.)"
    aliases: ClassVar[list[str]] = []

    def __init__(self, cli=None):
        super().__init__(cli)
        self._led_cache: dict[str, LEDInfo] | None = None

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("-l", "--list", action="store_true", help="list available LEDs")

        sub = parser.add_subparsers(dest="led_cmd", metavar="COMMAND")

        # list - show available LEDs
        list_p = sub.add_parser("list", help="list available LEDs", aliases=["ls"])
        list_p.add_argument("-a", "--all", action="store_true", help="show all details")

    def run(self, args: Namespace) -> int:
        # Handle --list shortcut
        if getattr(args, "list", False):
            return self._list(args)

        cmd = getattr(args, "led_cmd", None)

        if cmd is None:
            return self._list(args)

        if cmd in ("list", "ls"):
            return self._list(args)

        # Dynamic LED subcommand - handled via unparsed args
        return self._set_led(args)

    # ─────────────────────────────────────────────────────────────────────────
    # LED Info (from D-Bus)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_leds(self, args: Namespace) -> dict[str, LEDInfo] | None:
        """Get available LEDs from D-Bus, cached per command run."""
        if self._led_cache is not None:
            return self._led_cache

        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return None

        avail = service.get_available_leds(device)
        if not avail:
            return None

        self._led_cache = {}
        for name, traits_dict in sorted(avail.items()):
            self._led_cache[name] = LEDInfo(name, traits_dict)

        return self._led_cache

    def _get_led_state(self, args: Namespace, led_name: str) -> dict | None:
        """Get current state of an LED."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError:
            return None
        return service.get_led_state(device, led_name)

    # ─────────────────────────────────────────────────────────────────────────
    # Subcommands
    # ─────────────────────────────────────────────────────────────────────────

    def _calc_key_width(self, leds: dict[str, LEDInfo]) -> int:
        """Calculate max key width for table alignment."""
        keys = []
        for info in leds.values():
            keys.append(info.name)
            for name in info.traits_dict:
                keys.append(name)
        return max(len(k) for k in keys) + 1 if keys else 15

    def _list(self, args: Namespace) -> int:
        """List available LEDs with current state."""
        leds = self._get_leds(args)
        if leds is None:
            self.print(self.out.muted("No LEDs available"))
            return 0

        self.print()
        self.print(self.out.header(" Standalone LED control:"))
        self.print()

        key_width = self._calc_key_width(leds)

        for led_name, info in leds.items():
            # Get current state
            state = self._get_led_state(args, led_name) or {}

            # Header row
            self.print(self.out.table_header(key_width, info.name, f"LED: {info.display_name}"))

            # Traits section with current values
            self._show_traits_table(info.traits_dict, key_width, state)

            self.print()
            self.print()

        return 0

    def _show_traits_table(
        self, traits_dict: dict, key_width: int, values: dict | None = None
    ) -> None:
        """Display traits in table format."""
        count = 0
        for name, trait_dict in sorted(traits_dict.items()):
            metadata = trait_dict.get("metadata", {})
            if not metadata.get("config", False):
                continue

            trait_type = _get_trait_type(trait_dict)

            constraints = []
            if "min" in trait_dict:
                constraints.append(f"min: {trait_dict['min']}")
            if "max" in trait_dict:
                constraints.append(f"max: {trait_dict['max']}")
            if "values" in trait_dict:
                constraints.append(f"one of: {', '.join(v.lower() for v in trait_dict['values'])}")
            if "default_value" in trait_dict and trait_dict["default_value"] is not None:
                constraints.append(f"default: {trait_dict['default_value']}")

            if constraints:
                desc_str = f"{trait_type}: {', '.join(constraints)}"
            else:
                desc_str = trait_type

            if count == 0:
                self.print(self.out.table_sep(key_width))

            # Show current value if available
            if values is not None and name in values:
                val = values[name]
                self.print(self.out.table_row(key_width, self.out.device(name), str(val)))
                self.print(self.out.table_row(key_width, f"({trait_type})", desc_str))
                if count < len(traits_dict) - 1:
                    self.print(self.out.table_sep(key_width))
            else:
                self.print(self.out.table_row(key_width, name, desc_str))

            count += 1

    def _set_led(self, args: Namespace) -> int:
        """Set LED properties (dynamic subcommand)."""
        leds = self._get_leds(args)
        if leds is None:
            self.print(self.out.error("No LEDs available"))
            return 1

        unparsed = getattr(args, "unparsed", [])

        # Build dynamic parser for LED selection
        parser = ArgumentParser(prog="uchroma led", add_help=True)
        sub = parser.add_subparsers(dest="led_name", metavar="LED")

        for info in leds.values():
            led_parser = sub.add_parser(info.name, help=f"Control {info.display_name} LED")

            for trait_name, trait_dict in info.traits_dict.items():
                _add_trait_to_parser(led_parser, trait_name, trait_dict)

        try:
            led_args = parser.parse_args(unparsed)
        except SystemExit:
            return 1

        if not led_args.led_name:
            parser.print_help()
            return 1

        led_name = led_args.led_name
        info = leds.get(led_name)
        if info is None:
            self.print(self.out.error(f"Unknown LED: {led_name}"))
            return 1

        changed = _extract_changed_traits(led_args, info.traits_dict)

        if not changed:
            self.print(self.out.warning("No changes specified"))
            return 1

        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not service.set_led(device, led_name, changed):
            self.print(self.out.error(f"Failed to configure LED: {led_name}"))
            return 1

        self.print(self.out.success(f"Updated LED: {led_name}"))
        return 0
