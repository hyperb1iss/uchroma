#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Matrix command — direct LED matrix control.

View matrix info, set colors, and control individual pixels.
"""

from argparse import ArgumentParser, Namespace
from typing import ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service


class MatrixCommand(Command):
    """Direct LED matrix control."""

    name = "matrix"
    help = "LED matrix information and control"
    aliases: ClassVar[list[str]] = ["pixels", "frame"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="matrix_cmd", metavar="COMMAND")

        # info - show matrix dimensions and capabilities
        sub.add_parser("info", help="show matrix dimensions and capabilities")

        # fill - fill entire matrix with a color
        fill_p = sub.add_parser("fill", aliases=["solid"], help="fill matrix with solid color")
        fill_p.add_argument("color", metavar="COLOR", help="color to fill (name, hex, or rgb)")

        # off - turn off all LEDs
        sub.add_parser("off", aliases=["clear"], help="turn off all matrix LEDs")

        # preview - show current frame state
        sub.add_parser("preview", aliases=["show"], help="show ASCII preview of matrix state")

    def run(self, args: Namespace) -> int:
        cmd = getattr(args, "matrix_cmd", None)

        if cmd is None or cmd == "info":
            return self._info(args)
        elif cmd in ("fill", "solid"):
            return self._fill(args)
        elif cmd in ("off", "clear"):
            return self._off(args)
        elif cmd in ("preview", "show"):
            return self._preview(args)

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Info
    # ─────────────────────────────────────────────────────────────────────────

    def _info(self, args: Namespace) -> int:
        """Show matrix dimensions and capabilities."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        self.print()
        self.print(self.out.header(f" Matrix Info: {device.Name}"))
        self.print()

        key_width = 15

        has_matrix = device.HasMatrix
        self.print(
            self.out.table_row(
                key_width,
                self.out.key("has_matrix"),
                self.out.value("yes") if has_matrix else self.out.muted("no"),
            )
        )

        if has_matrix:
            width = device.Width
            height = device.Height
            total = width * height

            self.print(
                self.out.table_row(
                    key_width,
                    self.out.key("dimensions"),
                    f"{self.out.number(width)} x {self.out.number(height)}",
                )
            )
            self.print(
                self.out.table_row(
                    key_width,
                    self.out.key("total_leds"),
                    self.out.number(str(total)),
                )
            )
            self.print(
                self.out.table_row(
                    key_width,
                    self.out.key("layout"),
                    f"{height} rows, {width} columns",
                )
            )

            # Show visual grid
            self.print()
            self.print(self.out.muted(f"  Grid layout ({width}x{height}):"))
            self.print()
            self._draw_grid(width, height)

        self.print()
        return 0

    def _draw_grid(self, width: int, height: int) -> None:
        """Draw an ASCII representation of the matrix grid."""
        # Limit display size for large matrices
        max_width = min(width, 30)
        max_height = min(height, 10)

        # Top border
        self.print(f"    ╭{'─' * (max_width * 2 + 1)}╮")

        # Rows
        for row in range(max_height):
            row_label = f"{row:2d}"
            cells = "·" * max_width
            if width > max_width:
                cells = cells[:-1] + "…"
            self.print(f"  {row_label}│ {' '.join(cells)} │")

        if height > max_height:
            self.print(f"    │ {'…' * max_width} │")

        # Bottom border
        self.print(f"    ╰{'─' * (max_width * 2 + 1)}╯")

        # Column labels
        col_labels = " ".join(f"{i % 10}" for i in range(min(max_width, 10)))
        self.print(f"      {col_labels}")

    # ─────────────────────────────────────────────────────────────────────────
    # Fill
    # ─────────────────────────────────────────────────────────────────────────

    def _fill(self, args: Namespace) -> int:
        """Fill entire matrix with a solid color."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not device.HasMatrix:
            self.print(self.out.error("Device does not have an LED matrix"))
            return 1

        color = args.color

        # Use hardware 'static' effect if available
        available_fx = device.AvailableFX or {}
        if "static" in available_fx:
            if service.set_effect(device, "static", color=color):
                self.print(self.out.success(f"Matrix filled: {color}"))
                return 0
            else:
                self.print(self.out.error("Failed to set static color"))
                return 1
        else:
            self.print(self.out.error("Device does not support static fill"))
            self.print(self.out.muted("  Try using a renderer: uchroma anim add ..."))
            return 1

    # ─────────────────────────────────────────────────────────────────────────
    # Off/Clear
    # ─────────────────────────────────────────────────────────────────────────

    def _off(self, args: Namespace) -> int:
        """Turn off all matrix LEDs."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not device.HasMatrix:
            self.print(self.out.error("Device does not have an LED matrix"))
            return 1

        # Try to disable using hardware effect
        available_fx = device.AvailableFX or {}
        if "disable" in available_fx and service.set_effect(device, "disable"):
            self.print(self.out.success("Matrix LEDs disabled"))
            return 0

        # Fallback: try static with black
        if "static" in available_fx and service.set_effect(device, "static", color="#000000"):
            self.print(self.out.success("Matrix LEDs cleared"))
            return 0

        # Last resort: stop any animations
        if service.stop_animation(device):
            self.print(self.out.success("Matrix animations stopped"))
            return 0

        self.print(self.out.error("Could not disable matrix LEDs"))
        return 1

    # ─────────────────────────────────────────────────────────────────────────
    # Preview
    # ─────────────────────────────────────────────────────────────────────────

    def _preview(self, args: Namespace) -> int:
        """Show ASCII preview of current matrix state."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        if not device.HasMatrix:
            self.print(self.out.error("Device does not have an LED matrix"))
            return 1

        self.print()
        self.print(self.out.header(f" Matrix Preview: {device.Name}"))
        self.print()

        width = device.Width
        height = device.Height

        # Get current FX state
        current_fx = device.CurrentFX
        if current_fx and isinstance(current_fx, tuple) and len(current_fx) >= 1:
            fx_name = current_fx[0]
            self.print(self.out.muted(f"  Current effect: {fx_name}"))
            self.print()

        # Get current renderers
        current_renderers = service.get_current_renderers(device)
        if current_renderers:
            self.print(self.out.muted(f"  Active layers: {len(current_renderers)}"))
            for i, renderer in enumerate(current_renderers):
                short_name = renderer.split(".")[-1]
                self.print(self.out.muted(f"    [{i}] {short_name}"))
            self.print()

        # Display a placeholder grid (actual pixel data would require
        # server-side frame buffer access which isn't exposed via D-Bus)
        self.print(self.out.muted(f"  Matrix grid ({width}x{height}):"))
        self.print()
        self._draw_preview_grid(width, height)

        self.print()
        self.print(self.out.muted("  Note: Real-time pixel preview requires GTK frontend"))
        self.print()

        return 0

    def _draw_preview_grid(self, width: int, height: int) -> None:
        """Draw a preview grid with unicode blocks."""
        max_width = min(width, 40)
        max_height = min(height, 12)

        # Simple gradient pattern for visual interest
        for row in range(max_height):
            row_label = f"{row:2d}"
            cells = []
            for col in range(max_width):
                # Create a simple visual pattern
                brightness = (row + col) % 4
                if brightness == 0:
                    cells.append("░")
                elif brightness == 1:
                    cells.append("▒")
                elif brightness == 2:
                    cells.append("▓")
                else:
                    cells.append("█")

            if width > max_width:
                cells[-1] = "…"

            self.print(f"  {row_label} {''.join(cells)}")

        if height > max_height:
            self.print(f"     {'…' * max_width}")
