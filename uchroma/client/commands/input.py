#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Input command — keyboard reactive effects.

Configure lighting effects that respond to key presses.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service

# Reactive renderer module names
REACTIVE_RENDERERS = {
    "reaction": "uchroma.fxlib.reaction.Reaction",
    "ripple": "uchroma.fxlib.ripple.Ripple",
    "typewriter": "uchroma.fxlib.typewriter.Typewriter",
}


class InputCommand(Command):
    """Keyboard reactive lighting effects."""

    name = "input"
    help = "Configure reactive key effects"
    aliases: ClassVar[list[str]] = ["react", "reactive"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="input_cmd", metavar="COMMAND")

        # status - show current reactive effects
        sub.add_parser("status", help="show current reactive effect status")

        # list - show available reactive effects
        sub.add_parser("list", aliases=["ls"], help="list available reactive effects")

        # set - activate a reactive effect
        set_p = sub.add_parser("set", aliases=["enable"], help="enable a reactive effect")
        set_p.add_argument(
            "effect",
            metavar="EFFECT",
            help="reactive effect (reaction, ripple, typewriter)",
        )
        set_p.add_argument(
            "--color",
            metavar="COLOR",
            help="primary color for effect",
        )
        set_p.add_argument(
            "--bg-color",
            metavar="COLOR",
            dest="bg_color",
            help="background color (for reaction)",
        )
        set_p.add_argument(
            "--speed",
            type=int,
            metavar="N",
            help="effect speed (1-9)",
        )

        # off - disable reactive effects
        sub.add_parser("off", aliases=["disable"], help="disable reactive effects")

    def run(self, args: Namespace) -> int:
        cmd = getattr(args, "input_cmd", None)

        if cmd is None or cmd == "status":
            return self._status(args)
        elif cmd in ("list", "ls"):
            return self._list(args)
        elif cmd in ("set", "enable"):
            return self._set(args)
        elif cmd in ("off", "disable"):
            return self._off(args)

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────────

    def _status(self, args: Namespace) -> int:
        """Show current reactive effect status."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        self.print()
        self.print(self.out.header(" Reactive Input Status:"))
        self.print()

        key_width = 15

        # Check for active reactive renderers
        current = service.get_current_renderers(device) or []
        active_reactive = []

        for renderer in current:
            for name, full_name in REACTIVE_RENDERERS.items():
                if full_name == renderer or renderer.endswith(f".{name.title()}"):
                    active_reactive.append(name)

        if active_reactive:
            self.print(
                self.out.table_row(
                    key_width,
                    self.out.key("status"),
                    self.out.active("● ") + self.out.value("active"),
                )
            )
            self.print(
                self.out.table_row(
                    key_width,
                    self.out.key("effects"),
                    ", ".join(active_reactive),
                )
            )

            # Show layer info for each reactive renderer
            for i, renderer in enumerate(current):
                for name in REACTIVE_RENDERERS:
                    if renderer.endswith(f".{name.title()}"):
                        layer_info = service.get_layer_info(device, i)
                        if layer_info:
                            traits = layer_info.get("traits", {})
                            if traits:
                                self.print()
                                self.print(
                                    self.out.table_row(
                                        key_width,
                                        self.out.device(name),
                                        self.out.muted("(layer traits)"),
                                    )
                                )
                                for k, v in traits.items():
                                    if not k.startswith("_"):
                                        self.print(self.out.table_row(key_width, f"  {k}", str(v)))
        else:
            self.print(
                self.out.table_row(
                    key_width,
                    self.out.key("status"),
                    self.out.muted("inactive"),
                )
            )
            self.print()
            self.print(
                self.out.muted(f"  Enable with: {self.out.command('uchroma input set <effect>')}")
            )

        self.print()
        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # List effects
    # ─────────────────────────────────────────────────────────────────────────

    def _list(self, args: Namespace) -> int:
        """List available reactive effects."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        self.print()
        self.print(self.out.header(" Available Reactive Effects:"))
        self.print()

        key_width = 15

        # Get available renderers from device
        available = service.get_available_renderers(device) or {}

        # Check which reactive renderers are available
        for name, full_name in REACTIVE_RENDERERS.items():
            if full_name in available:
                info = available[full_name]
                description = ""
                if isinstance(info, dict) and "meta" in info:
                    meta = info["meta"]
                    if isinstance(meta, dict):
                        description = meta.get("description", "")

                self.print(
                    self.out.table_row(
                        key_width,
                        self.out.device(name),
                        description or f"Reactive {name} effect",
                    )
                )
            else:
                self.print(
                    self.out.table_row(
                        key_width,
                        self.out.muted(name),
                        self.out.muted("not available"),
                    )
                )

        self.print()

        # Show trait info for each available effect
        for name, full_name in REACTIVE_RENDERERS.items():
            if full_name in available:
                info = available[full_name]
                if isinstance(info, dict):
                    traits = {k: v for k, v in info.items() if k not in ("meta", "__class__")}
                    if traits:
                        self.print(self.out.header(f"  {name} options:"))
                        for trait_name, trait_info in traits.items():
                            if isinstance(trait_info, dict):
                                trait_type = self._get_trait_type(trait_info)
                                default = trait_info.get("default_value", "")
                                self.print(
                                    self.out.table_row(
                                        key_width,
                                        f"  --{trait_name.replace('_', '-')}",
                                        f"{trait_type} (default: {default})"
                                        if default
                                        else trait_type,
                                    )
                                )
                        self.print()

        return 0

    def _get_trait_type(self, trait_dict: dict) -> str:
        """Extract type name from serialized trait dict."""
        cls_info = trait_dict.get("__class__", ("", "unknown"))
        cls_name = cls_info[1] if isinstance(cls_info, (list, tuple)) else "unknown"
        cls_lower = cls_name.lower()
        type_map = {
            "float": "float",
            "int": "int",
            "unicode": "str",
            "bool": "bool",
            "colortrait": "color",
            "colorschemetrait": "colors",
        }
        return type_map.get(cls_lower, "str")

    # ─────────────────────────────────────────────────────────────────────────
    # Set effect
    # ─────────────────────────────────────────────────────────────────────────

    def _set(self, args: Namespace) -> int:
        """Enable a reactive effect."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        effect = args.effect.lower()
        if effect not in REACTIVE_RENDERERS:
            self.print(self.out.error(f"Unknown reactive effect: {effect}"))
            self.print(self.out.muted(f"  Available: {', '.join(REACTIVE_RENDERERS.keys())}"))
            return 1

        full_name = REACTIVE_RENDERERS[effect]

        # Check if available
        available = service.get_available_renderers(device) or {}
        if full_name not in available:
            self.print(self.out.error(f"Effect '{effect}' not available on this device"))
            return 1

        # Build traits from args
        traits: dict = {}
        if args.color:
            traits["color"] = args.color
        if args.bg_color:
            traits["background_color"] = args.bg_color
        if args.speed:
            traits["speed"] = args.speed

        # First stop any existing reactive effects
        current = service.get_current_renderers(device) or []
        for i, renderer in enumerate(current):
            for name in REACTIVE_RENDERERS:
                if renderer.endswith(f".{name.title()}"):
                    service.remove_renderer(device, i)

        # Add the new effect
        result = service.add_renderer(device, full_name, traits=traits)
        if result:
            self.print(self.out.success(f"Enabled: {effect}"))
            if traits:
                for k, v in traits.items():
                    self.print(self.out.muted(f"  {k}: {v}"))
        else:
            self.print(self.out.error(f"Failed to enable {effect}"))
            return 1

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Disable
    # ─────────────────────────────────────────────────────────────────────────

    def _off(self, args: Namespace) -> int:
        """Disable reactive effects."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        # Find and remove reactive renderers
        current = service.get_current_renderers(device) or []
        removed = []

        # Remove in reverse order to avoid index shifting
        for i in range(len(current) - 1, -1, -1):
            renderer = current[i]
            for name in REACTIVE_RENDERERS:
                if renderer.endswith(f".{name.title()}"):
                    if service.remove_renderer(device, i):
                        removed.append(name)
                    break

        if removed:
            self.print(self.out.success(f"Disabled: {', '.join(removed)}"))
        else:
            self.print(self.out.muted("No reactive effects were active"))

        return 0
