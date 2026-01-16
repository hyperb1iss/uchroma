#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
FX command — hardware lighting effects.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command

# Available hardware effects
EFFECTS = {
    "off": "Disable all effects",
    "static": "Static color",
    "spectrum": "Cycle through all colors",
    "wave": "Wave animation",
    "breathe": "Breathing effect",
    "reactive": "React to keypresses",
    "starlight": "Sparkling stars",
}


class FxCommand(Command):
    """Apply hardware lighting effects."""

    name = "fx"
    help = "Set hardware lighting effect"
    aliases: ClassVar[list[str]] = ["effect"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "effect",
            nargs="?",
            choices=list(EFFECTS.keys()),
            metavar="EFFECT",
            help="effect name (off, static, spectrum, wave, breathe, reactive, starlight)",
        )
        parser.add_argument(
            "-c",
            "--color",
            type=str,
            metavar="COLOR",
            help="color for effect (name, hex, or rgb)",
        )
        parser.add_argument(
            "--color2",
            type=str,
            metavar="COLOR",
            help="secondary color (for breathe, starlight)",
        )
        parser.add_argument(
            "--speed",
            type=int,
            choices=[1, 2, 3],
            default=2,
            help="effect speed (1=slow, 2=medium, 3=fast)",
        )
        parser.add_argument(
            "--direction",
            type=str,
            choices=["left", "right"],
            default="right",
            help="wave direction",
        )
        parser.add_argument(
            "-l",
            "--list",
            action="store_true",
            help="list available effects",
        )

    def run(self, args: Namespace) -> int:
        if args.list or args.effect is None:
            return self._list_effects()

        return self._set_effect(args)

    def _list_effects(self) -> int:
        """List available effects."""
        self.print(self.out.header("Hardware Effects"))
        self.print()

        for name, description in EFFECTS.items():
            self.print(f"  {self.out.key(name):12} {self.out.muted(description)}")

        self.print()
        self.print(self.out.muted("Use: uchroma fx <effect> [--color COLOR]"))
        return 0

    def _set_effect(self, args: Namespace) -> int:
        """Apply the selected effect."""
        # Lazy import to avoid circular dependency at module load time
        from uchroma.client.device_service import get_device_service  # noqa: PLC0415

        service = get_device_service()

        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            return self.error(str(e))

        effect = args.effect

        # Build effect description for output
        parts = [effect]
        if args.color:
            parts.append(f"color={args.color}")
        if args.color2:
            parts.append(f"color2={args.color2}")
        if effect == "wave":
            parts.append(f"direction={args.direction}")
        if effect in ("reactive", "starlight"):
            parts.append(f"speed={args.speed}")

        effect_desc = " ".join(parts)

        try:
            service.set_effect(
                device,
                effect,
                color=args.color,
                color2=args.color2,
                speed=args.speed,
                direction=args.direction,
            )
            return self.success(f"{device.Name}: {effect_desc}")
        except ValueError as e:
            return self.error(str(e))
