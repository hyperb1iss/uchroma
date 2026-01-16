#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Animation command — manage custom animation layers.

Works entirely through D-Bus, no server-side imports.
"""

from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service

if TYPE_CHECKING:
    from uchroma.client.cli_base import UChromaCLI


class RendererInfo:
    """Parsed renderer metadata and traits from D-Bus."""

    def __init__(self, full_name: str, meta: dict | tuple, traits_dict: dict):
        from uchroma.traits import dict_as_class_traits  # noqa: PLC0415

        self.full_name = full_name
        self.traits_dict = traits_dict

        # Parse meta - can be dict or tuple (legacy)
        if isinstance(meta, dict):
            self.display_name = meta.get("display_name", full_name.split(".")[-1])
            self.description = meta.get("description", "")
            self.author = meta.get("author", "")
            self.version = meta.get("version", "")
        else:
            # Legacy tuple format: (display_name, description, author, version)
            self.display_name = meta[0] if len(meta) > 0 else full_name.split(".")[-1]
            self.description = meta[1] if len(meta) > 1 else ""
            self.author = meta[2] if len(meta) > 2 else ""
            self.version = meta[3] if len(meta) > 3 else ""

        # Short alias: "Color Plasma" -> "color_plasma"
        self.alias = self.display_name.replace(" ", "_").lower()

        # Convert D-Bus dict to HasTraits for introspection
        self._traits = dict_as_class_traits(traits_dict) if traits_dict else None

    @property
    def traits(self):
        """Get HasTraits instance for trait introspection."""
        return self._traits


def _get_trait_type(trait_dict: dict) -> str:
    """Extract type name from serialized trait dict."""
    cls_info = trait_dict.get("__class__", ("", "unknown"))
    cls_name = cls_info[1] if isinstance(cls_info, (list, tuple)) else "unknown"
    # Normalize type names - handle various casing
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
    # Skip non-config traits
    metadata = trait_dict.get("metadata", {})
    if not metadata.get("config", False):
        return

    arg_name = f"--{name.replace('_', '-')}"
    trait_type = _get_trait_type(trait_dict)

    # Build help text from constraints
    help_parts = []
    if "min" in trait_dict:
        help_parts.append(f"min: {trait_dict['min']}")
    if "max" in trait_dict:
        help_parts.append(f"max: {trait_dict['max']}")
    if "default_value" in trait_dict and trait_dict["default_value"] is not None:
        help_parts.append(f"default: {trait_dict['default_value']}")

    help_text = f"[{', '.join(help_parts)}]" if help_parts else None

    if trait_type == "bool":
        # Boolean gets --flag / --no-flag
        parser.add_argument(
            arg_name,
            action=BooleanOptionalAction,
            default=trait_dict.get("default_value"),
            help=help_text,
        )
    elif trait_type == "choice":
        # Enum with choices - preserve case for server validation
        values = trait_dict.get("values", [])
        # Create case-insensitive lookup, bound at definition time
        lower_to_original = {v.lower(): v for v in values}

        def make_choice_type(lookup: dict[str, str]):
            """Factory to bind lookup at definition time."""

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
        # Colors as strings
        parser.add_argument(
            arg_name,
            type=str,
            default=trait_dict.get("default_value"),
            metavar="COLOR",
            help=help_text,
        )
    else:
        # Generic string
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

        # Check if arg was provided (not None and different from default)
        arg_name = name.replace("-", "_")
        if hasattr(args, arg_name):
            value = getattr(args, arg_name)
            default = trait_dict.get("default_value")
            if value is not None and value != default:
                changed[name] = value

    return changed


class AnimCommand(Command):
    """Animation layer management."""

    name = "anim"
    help = "Manage custom animation layers"
    aliases: ClassVar[list[str]] = ["animation", "layer"]

    def __init__(self, cli: "UChromaCLI"):
        super().__init__(cli)
        self._renderer_cache: dict[str, RendererInfo] | None = None
        self._alias_map: dict[str, str] = {}  # alias -> full_name

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("-l", "--list", action="store_true", help="list available renderers")

        sub = parser.add_subparsers(dest="anim_cmd", metavar="COMMAND")

        # list - show available renderers
        list_p = sub.add_parser("list", help="list available renderers", aliases=["ls"])
        list_p.add_argument("-a", "--all", action="store_true", help="show all details")

        # show - show current layers
        show_p = sub.add_parser("show", help="show active layers", aliases=["status"])
        show_p.add_argument("-v", "--verbose", action="store_true", help="show layer properties")

        # add - add a renderer (subparsers added dynamically)
        add_p = sub.add_parser("add", help="add a renderer layer", add_help=False)
        add_p.add_argument(
            "-z", "--zindex", type=int, default=-1, metavar="N", help="layer index (default: auto)"
        )

        # rm - remove a layer
        rm_p = sub.add_parser("rm", help="remove a layer", aliases=["del", "remove"])
        rm_p.add_argument("zindex", type=int, metavar="N", help="layer index to remove")

        # set - modify a layer (subparsers added dynamically)
        sub.add_parser("set", help="modify layer properties", aliases=["mod"], add_help=False)

        # pause - toggle pause
        sub.add_parser("pause", help="toggle animation pause")

        # stop - stop all animations
        sub.add_parser("stop", help="stop and clear all layers", aliases=["clear"])

    def run(self, args: Namespace) -> int:
        # Handle --list shortcut
        if getattr(args, "list", False):
            return self._list(args, show_all=False)

        cmd = getattr(args, "anim_cmd", None)

        if cmd is None:
            return self._show(args)

        if cmd in ("list", "ls"):
            return self._list(args, show_all=getattr(args, "all", False))

        if cmd in ("show", "status"):
            return self._show(args)

        if cmd == "add":
            return self._add(args)

        if cmd in ("rm", "del", "remove"):
            return self._rm(args)

        if cmd in ("set", "mod"):
            return self._set(args)

        if cmd == "pause":
            return self._pause(args)

        if cmd in ("stop", "clear"):
            return self._stop(args)

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Renderer Info (from D-Bus)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_renderers(self, args: Namespace) -> dict[str, RendererInfo] | None:
        """Get available renderers from D-Bus, cached per command run."""
        if self._renderer_cache is not None:
            return self._renderer_cache

        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return None

        avail = service.get_available_renderers(device)
        if not avail:
            return None

        # Sort by display name
        def get_display_name(item):
            meta = item[1].get("meta", {})
            if isinstance(meta, dict):
                return meta.get("display_name", item[0])
            return meta[0] if meta else item[0]

        sorted_avail = OrderedDict(sorted(avail.items(), key=get_display_name))

        self._renderer_cache = {}
        for full_name, data in sorted_avail.items():
            meta = data.get("meta", {})
            traits = data.get("traits", {})
            info = RendererInfo(full_name, meta, traits)
            self._renderer_cache[full_name] = info
            self._alias_map[info.alias] = full_name
            # Also map short class name
            short_name = full_name.split(".")[-1].lower()
            if short_name not in self._alias_map:
                self._alias_map[short_name] = full_name

        return self._renderer_cache

    def _resolve_renderer(self, name: str) -> str | None:
        """Resolve a renderer name/alias to full name."""
        if self._renderer_cache and name in self._renderer_cache:
            return name
        return self._alias_map.get(name.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # Subcommands
    # ─────────────────────────────────────────────────────────────────────────

    def _calc_key_width(self, renderers: dict[str, RendererInfo]) -> int:
        """Calculate max key width for table alignment."""
        keys = []
        for info in renderers.values():
            keys.append(info.alias)
            for name in info.traits_dict:
                keys.append(name)
            # Add metadata keys
            keys.extend(["author", "version", "description", "name"])
        return max(len(k) for k in keys) + 1 if keys else 15

    def _list(self, args: Namespace, show_all: bool = False) -> int:
        """List available renderers."""
        renderers = self._get_renderers(args)
        if renderers is None:
            self.print(self.out.muted("No renderers available"))
            return 0

        self.print()
        self.print(self.out.header(" Available renderers and arguments:"))
        self.print()

        key_width = self._calc_key_width(renderers)

        for info in renderers.values():
            # Header row: alias | description (both bold)
            self.print(
                self.out.table_header(key_width, info.alias, info.description or info.display_name)
            )

            # Metadata section (author, version)
            has_meta = info.author or info.version
            if has_meta:
                self.print(self.out.table_sep(key_width))
                if info.author:
                    self.print(self.out.table_row(key_width, self.out.key("author"), info.author))
                if info.version:
                    self.print(self.out.table_row(key_width, self.out.key("version"), info.version))

            # Traits section
            self._show_traits_table(info.traits_dict, key_width, has_separator=not has_meta)

            self.print()
            self.print()

        return 0

    def _show_traits_table(
        self,
        traits_dict: dict,
        key_width: int,
        values: dict | None = None,
        has_separator: bool = True,
    ) -> None:
        """Display traits in table format with SilkCircuit colors."""
        count = 0
        for name, trait_dict in sorted(traits_dict.items()):
            metadata = trait_dict.get("metadata", {})
            if not metadata.get("config", False):
                continue

            trait_type = _get_trait_type(trait_dict)

            # Extract constraint values
            min_val = trait_dict.get("min")
            max_val = trait_dict.get("max")
            default_val = trait_dict.get("default_value")
            choices = trait_dict.get("values")

            # Special formatting for color types
            if trait_type == "color":
                value_str = self.out.format_color_trait(default_val)
            elif trait_type == "colors":
                # Colorscheme - default_val might be a list of colors
                colors_list = default_val if isinstance(default_val, list) else None
                value_str = self.out.format_colorscheme_trait(colors_list)
            else:
                # Use the colorful constraint formatter for other types
                value_str = self.out.format_constraints(
                    trait_type,
                    min_val=min_val,
                    max_val=max_val,
                    default=default_val,
                    choices=choices,
                )

            # First trait gets separator (if we need one)
            if count == 0 and has_separator:
                self.print(self.out.table_sep(key_width))

            # If showing current values
            if values is not None and name in values:
                val = values[name]
                # Color the current value based on type
                if trait_type == "color" and isinstance(val, str):
                    val_str = self.out.color_value(val)
                elif trait_type == "colors" and isinstance(val, list):
                    val_str = self.out.color_swatch(val)
                elif isinstance(val, (int, float)):
                    val_str = self.out.number(val)
                elif isinstance(val, str) and val.startswith("#"):
                    val_str = self.out.color_value(val)
                else:
                    val_str = self.out.value(str(val))
                self.print(self.out.table_row(key_width, self.out.key(name), val_str))
                self.print(
                    self.out.table_row(key_width, self.out.type_hint(f"({trait_type})"), value_str)
                )
                self.print(self.out.table_sep(key_width))
            else:
                self.print(self.out.table_row(key_width, name, value_str))

            count += 1

    def _show_traits(self, traits_dict: dict, indent: int = 2) -> None:
        """Display trait info from D-Bus dict (simple format)."""
        prefix = " " * indent
        for name, trait_dict in sorted(traits_dict.items()):
            metadata = trait_dict.get("metadata", {})
            if not metadata.get("config", False):
                continue

            trait_type = _get_trait_type(trait_dict)

            # Constraints
            constraints = []
            if "min" in trait_dict:
                constraints.append(f"min: {trait_dict['min']}")
            if "max" in trait_dict:
                constraints.append(f"max: {trait_dict['max']}")
            if "values" in trait_dict:
                constraints.append(f"choices: {', '.join(trait_dict['values'])}")
            if "default_value" in trait_dict and trait_dict["default_value"] is not None:
                constraints.append(f"default: {trait_dict['default_value']}")

            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            self.print(f"{prefix}{self.out.key(name)} ({trait_type}){constraint_str}")

    def _show(self, args: Namespace) -> int:
        """Show current animation layers."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        current = service.get_current_renderers(device)
        if not current:
            self.print(self.out.muted("No active animation layers"))
            return 0

        # Load renderer info for display names
        self._get_renderers(args)

        self.print()
        self.print(self.out.header("Active Layers"))
        self.print()

        verbose = getattr(args, "verbose", False)

        for renderer_type, path in current:
            # Extract zindex from path
            zindex = int(path.split("/")[-1])

            # Get display name
            info = self._renderer_cache.get(renderer_type) if self._renderer_cache else None
            display_name = info.display_name if info else renderer_type.split(".")[-1]

            self.print(f"  {self.out.value(str(zindex))}  {self.out.device(display_name)}")

            # Show properties if verbose
            if verbose:
                try:
                    props = service.get_layer_info(device, zindex)
                    if props:
                        for k, v in sorted(props.items()):
                            if k.startswith("_") or k in ("Key", "ZIndex"):
                                continue
                            val = v.value if hasattr(v, "value") else v
                            self.print(f"       {self.out.kv(k, str(val))}")
                except Exception:
                    pass

        self.print()
        return 0

    def _add(self, args: Namespace) -> int:
        """Add a renderer layer with dynamic trait args."""
        renderers = self._get_renderers(args)
        if renderers is None:
            self.print(self.out.error("No renderers available"))
            return 1

        unparsed = getattr(args, "unparsed", [])

        # Build dynamic parser for renderer selection
        parser = ArgumentParser(prog="uchroma anim add", add_help=True)
        parser.add_argument(
            "-z", "--zindex", type=int, default=-1, metavar="N", help="layer index (default: auto)"
        )

        sub = parser.add_subparsers(dest="renderer", metavar="RENDERER")

        for info in renderers.values():
            rparser = sub.add_parser(info.alias, help=info.description or info.display_name)

            # Add trait args from D-Bus dict
            for trait_name, trait_dict in info.traits_dict.items():
                _add_trait_to_parser(rparser, trait_name, trait_dict)

        try:
            add_args = parser.parse_args(unparsed)
        except SystemExit:
            return 1

        if not add_args.renderer:
            parser.print_help()
            return 1

        # Resolve renderer name
        full_name = self._resolve_renderer(add_args.renderer)
        if not full_name:
            self.print(self.out.error(f"Unknown renderer: {add_args.renderer}"))
            return 1

        info = renderers[full_name]

        # Extract changed traits
        changed = _extract_changed_traits(add_args, info.traits_dict)

        # Add the renderer
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        result = service.add_renderer(device, full_name, add_args.zindex, changed)
        if result is None:
            self.print(self.out.error("Failed to create layer"))
            return 1

        layer_idx = result.split("/")[-1]
        self.print(self.out.success(f"Created layer {layer_idx}: {info.display_name}"))
        return 0

    def _rm(self, args: Namespace) -> int:
        """Remove a layer."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        zindex = args.zindex

        if not service.remove_renderer(device, zindex):
            self.print(self.out.error(f"Failed to remove layer {zindex}"))
            return 1

        self.print(self.out.success(f"Removed layer {zindex}"))
        return 0

    def _set(self, args: Namespace) -> int:
        """Modify layer properties."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        current = service.get_current_renderers(device)
        if not current:
            self.print(self.out.error("No active animation layers"))
            return 1

        renderers = self._get_renderers(args)
        if renderers is None:
            return 1

        unparsed = getattr(args, "unparsed", [])

        # Build parser for layer selection
        parser = ArgumentParser(prog="uchroma anim set", add_help=True)
        sub = parser.add_subparsers(dest="layer", metavar="LAYER")

        for renderer_type, path in current:
            zindex = int(path.split("/")[-1])
            info = renderers.get(renderer_type)
            if info is None:
                continue

            lparser = sub.add_parser(str(zindex), help=f"Layer {zindex}: {info.display_name}")

            # Add trait args from D-Bus dict
            for trait_name, trait_dict in info.traits_dict.items():
                _add_trait_to_parser(lparser, trait_name, trait_dict)

        try:
            set_args = parser.parse_args(unparsed)
        except SystemExit:
            return 1

        if not set_args.layer:
            parser.print_help()
            return 1

        zindex = int(set_args.layer)

        # Find the renderer for this layer
        renderer_type = None
        for rt, path in current:
            if int(path.split("/")[-1]) == zindex:
                renderer_type = rt
                break

        if renderer_type is None:
            self.print(self.out.error(f"Layer {zindex} not found"))
            return 1

        info = renderers.get(renderer_type)
        if info is None or not info.traits_dict:
            self.print(self.out.error("Layer has no configurable properties"))
            return 1

        # Extract changed traits
        changed = _extract_changed_traits(set_args, info.traits_dict)

        if not changed:
            self.print(self.out.warning("No changes specified"))
            return 1

        # Apply changes via D-Bus
        if not service.set_layer_traits(device, zindex, changed):
            self.print(self.out.error(f"Failed to update layer {zindex}"))
            return 1

        self.print(self.out.success(f"Updated layer {zindex}"))
        return 0

    def _pause(self, args: Namespace) -> int:
        """Toggle animation pause."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        paused = service.pause_animation(device)
        state = "paused" if paused else "running"
        self.print(f"Animation {self.out.value(state)}")
        return 0

    def _stop(self, args: Namespace) -> int:
        """Stop all animations."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not service.stop_animation(device):
            self.print(self.out.error("Failed to stop animation"))
            return 1

        self.print(self.out.success("Animation stopped"))
        return 0
