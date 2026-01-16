#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
CLI output styling with SilkCircuit design language.

Electric meets elegant — neon aesthetics for terminal output.
Respects NO_COLOR env var and TTY detection.
"""

import os
import re
import sys
from enum import Enum, auto

# ─────────────────────────────────────────────────────────────────────────────
# SilkCircuit Color Palette
# ─────────────────────────────────────────────────────────────────────────────

# Core palette - RGB tuples
ELECTRIC_PURPLE = (225, 53, 255)  # Keywords, markers, importance
NEON_CYAN = (128, 255, 234)  # Functions, paths, interactions
CORAL = (255, 106, 193)  # Hashes, numbers, constants
ELECTRIC_YELLOW = (241, 250, 140)  # Warnings, timestamps, attention
SUCCESS_GREEN = (80, 250, 123)  # Success states, confirmations
ERROR_RED = (255, 99, 99)  # Errors, danger, removals
SOFT_WHITE = (248, 248, 242)  # Primary text
DIM_GRAY = (98, 114, 164)  # Muted, metadata
DARK_GRAY = (68, 71, 90)  # Borders, separators


class _Token(Enum):
    """Semantic design tokens — maps UI concepts to colors."""

    # Content types
    DEVICE = auto()  # Device names — bold cyan
    KEY = auto()  # Property names — cyan
    VALUE = auto()  # Property values — purple
    NUMBER = auto()  # Numeric values — coral
    PATH = auto()  # File paths — cyan
    HEADER = auto()  # Section titles — bold white
    TYPE = auto()  # Type annotations — dim

    # States
    SUCCESS = auto()  # Confirmations — green
    ERROR = auto()  # Failures — red
    WARNING = auto()  # Cautions — yellow
    MUTED = auto()  # Metadata — dim gray
    ACTIVE = auto()  # Current/selected — green
    ACCENT = auto()  # Highlights — purple


# Token → RGB mapping
_THEME: dict[_Token, tuple[int, int, int] | None] = {
    _Token.DEVICE: NEON_CYAN,
    _Token.KEY: NEON_CYAN,
    _Token.VALUE: ELECTRIC_PURPLE,
    _Token.NUMBER: CORAL,
    _Token.PATH: NEON_CYAN,
    _Token.HEADER: SOFT_WHITE,
    _Token.TYPE: DIM_GRAY,
    _Token.SUCCESS: SUCCESS_GREEN,
    _Token.ERROR: ERROR_RED,
    _Token.WARNING: ELECTRIC_YELLOW,
    _Token.MUTED: DIM_GRAY,
    _Token.ACTIVE: SUCCESS_GREEN,
    _Token.ACCENT: ELECTRIC_PURPLE,
}


# ─────────────────────────────────────────────────────────────────────────────
# Box Drawing Characters
# ─────────────────────────────────────────────────────────────────────────────

# Standard box drawing
BOX_H = "─"  # Horizontal
BOX_V = "│"  # Vertical
BOX_TL = "┌"  # Top-left corner
BOX_TR = "┐"  # Top-right corner
BOX_BL = "└"  # Bottom-left corner
BOX_BR = "┘"  # Bottom-right corner
BOX_VR = "├"  # Vertical + right
BOX_VL = "┤"  # Vertical + left
BOX_HD = "┬"  # Horizontal + down
BOX_HU = "┴"  # Horizontal + up
BOX_X = "┼"  # Cross

# Rounded corners (modern feel)
BOX_TL_R = "╭"
BOX_TR_R = "╮"
BOX_BL_R = "╰"
BOX_BR_R = "╯"

# Heavy variants
BOX_H_HEAVY = "━"
BOX_V_HEAVY = "┃"

# Symbols
SYM_CHECK = "✓"
SYM_CROSS = "✗"
SYM_BULLET = "•"
SYM_ARROW = "→"
SYM_DIAMOND = "◆"
SYM_CIRCLE = "●"
SYM_CIRCLE_EMPTY = "○"
SYM_STAR = "★"
SYM_BOLT = "⚡"
SYM_GAUGE = "▰"
SYM_GAUGE_EMPTY = "▱"

# Block characters for bars
BLOCK_FULL = "█"
BLOCK_7_8 = "▉"
BLOCK_3_4 = "▊"
BLOCK_5_8 = "▋"
BLOCK_1_2 = "▌"
BLOCK_3_8 = "▍"
BLOCK_1_4 = "▎"
BLOCK_1_8 = "▏"
BLOCK_EMPTY = "░"

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_PATTERN.sub("", str(text))


# ─────────────────────────────────────────────────────────────────────────────
# Output Class
# ─────────────────────────────────────────────────────────────────────────────


class Output:
    """
    CLI output with SilkCircuit styling.

    Electric meets elegant — semantic methods for terminal output.
    """

    def __init__(self, force_color: bool | None = None):
        self._color_enabled = self._detect_color(force_color)

    def _detect_color(self, force: bool | None) -> bool:
        """Detect if color output should be enabled."""
        if force is not None:
            return force
        if os.environ.get("NO_COLOR"):
            return False
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return False
        return os.environ.get("TERM") != "dumb"

    # ─────────────────────────────────────────────────────────────────────────
    # Internal styling
    # ─────────────────────────────────────────────────────────────────────────

    def _rgb(self, r: int, g: int, b: int, text: str) -> str:
        """Apply RGB color to text."""
        if not self._color_enabled:
            return text
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"

    def _bg_rgb(self, r: int, g: int, b: int, text: str) -> str:
        """Apply RGB background color to text."""
        if not self._color_enabled:
            return text
        return f"\x1b[48;2;{r};{g};{b}m{text}\x1b[0m"

    def _bold(self, text: str) -> str:
        """Apply bold style."""
        if not self._color_enabled:
            return text
        return f"\x1b[1m{text}\x1b[0m"

    def _dim(self, text: str) -> str:
        """Apply dim style."""
        if not self._color_enabled:
            return text
        return f"\x1b[2m{text}\x1b[0m"

    def _italic(self, text: str) -> str:
        """Apply italic style."""
        if not self._color_enabled:
            return text
        return f"\x1b[3m{text}\x1b[0m"

    def _apply(self, token: _Token, text: str, bold: bool = False) -> str:
        """Apply a design token to text."""
        rgb = _THEME.get(token)
        result = text
        if rgb is not None:
            result = self._rgb(*rgb, result)
        if bold:
            result = self._bold(result)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Semantic methods — content types
    # ─────────────────────────────────────────────────────────────────────────

    def device(self, text: str) -> str:
        """Format a device name."""
        return self._apply(_Token.DEVICE, text, bold=True)

    def key(self, text: str) -> str:
        """Format a property name or label."""
        return self._apply(_Token.KEY, text)

    def value(self, text: str) -> str:
        """Format a property value."""
        return self._apply(_Token.VALUE, text)

    def number(self, text: str | int | float) -> str:
        """Format a numeric value."""
        return self._apply(_Token.NUMBER, str(text))

    def path(self, text: str) -> str:
        """Format a file path or URL."""
        return self._apply(_Token.PATH, text)

    def header(self, text: str) -> str:
        """Format a section header."""
        return self._apply(_Token.HEADER, text, bold=True)

    def type_hint(self, text: str) -> str:
        """Format a type annotation."""
        return self._apply(_Token.TYPE, text)

    def accent(self, text: str) -> str:
        """Format with accent color."""
        return self._apply(_Token.ACCENT, text)

    def constraint_label(self, text: str) -> str:
        """Format a constraint label (min:, max:, default:)."""
        return self._apply(_Token.MUTED, text)

    def choice(self, text: str) -> str:
        """Format a choice/enum value."""
        return self._rgb(*NEON_CYAN, text)

    # ─────────────────────────────────────────────────────────────────────────
    # Trait constraint formatters
    # ─────────────────────────────────────────────────────────────────────────

    def format_constraint(self, label: str, value: str | int | float) -> str:
        """Format a single constraint like 'min: 0.5'."""
        return f"{self.constraint_label(label)} {self.number(value)}"

    def format_constraints(
        self,
        trait_type: str,
        min_val: float | int | None = None,
        max_val: float | int | None = None,
        default: str | int | float | None = None,
        choices: list[str] | None = None,
    ) -> str:
        """Format trait constraints with full color."""
        parts = []

        if min_val is not None:
            parts.append(self.format_constraint("min:", min_val))
        if max_val is not None:
            parts.append(self.format_constraint("max:", max_val))
        if choices:
            # Show all choices with accent color
            choice_str = ", ".join(self.choice(c.lower()) for c in choices)
            parts.append(f"{self.constraint_label('one of:')} {choice_str}")
        if default is not None:
            # Color default value based on type
            if isinstance(default, (int, float)):
                default_str = self.number(default)
            elif isinstance(default, str) and default.startswith("#"):
                default_str = self.accent(default)
            else:
                default_str = self.value(str(default))
            parts.append(f"{self.constraint_label('default:')} {default_str}")

        if parts:
            return f"{self.type_hint(trait_type + ':')} {', '.join(parts)}"
        return self.type_hint(trait_type)

    def _parse_color_rgb(self, color_str: str) -> tuple[int, int, int] | None:
        """Parse a color string to RGB tuple. Returns None on failure."""
        try:
            from uchroma.colorlib import Color  # noqa: PLC0415

            c = Color.NewFromHtml(color_str)
            return c.intTuple[:3]
        except Exception:
            return None

    def color_text(self, text: str, color_str: str) -> str:
        """Render text in the specified color (by name or hex)."""
        rgb = self._parse_color_rgb(color_str)
        if rgb:
            return self._rgb(*rgb, text)
        return text

    def color_value(self, color_str: str) -> str:
        """Format a color value, displayed in its own color with a swatch."""
        rgb = self._parse_color_rgb(color_str)
        if rgb:
            swatch = self._rgb(*rgb, "█")
            return f"{swatch} {self._rgb(*rgb, color_str)}"
        return self.value(color_str)

    def color_swatch(self, colors: list[str]) -> str:
        """Render an inline color swatch from a list of color strings."""
        swatches = []
        for color_str in colors:
            rgb = self._parse_color_rgb(color_str)
            if rgb:
                swatches.append(self._rgb(*rgb, "●"))
            else:
                swatches.append(self.muted("○"))
        return " ".join(swatches)

    def format_color_trait(self, default: str | None = None) -> str:
        """Format a color trait type with optional default swatch."""
        if default:
            return f"{self.type_hint('color:')} {self.constraint_label('default:')} {self.color_value(default)}"
        return self.type_hint("color")

    def format_colorscheme_trait(self, default: list[str] | None = None) -> str:
        """Format a colorscheme trait type with optional swatch."""
        if default:
            swatch = self.color_swatch(default)
            return f"{self.type_hint('colors:')} {self.constraint_label('default:')} {swatch}"
        return self.type_hint("colors")

    # ─────────────────────────────────────────────────────────────────────────
    # Semantic methods — states
    # ─────────────────────────────────────────────────────────────────────────

    def success(self, message: str) -> str:
        """Format a success message with checkmark."""
        mark = self._apply(_Token.SUCCESS, SYM_CHECK)
        return f"{mark} {message}"

    def error(self, message: str) -> str:
        """Format an error message with cross."""
        mark = self._apply(_Token.ERROR, SYM_CROSS)
        return f"{mark} {message}"

    def warning(self, message: str) -> str:
        """Format a warning message."""
        mark = self._apply(_Token.WARNING, "!")
        return f"{mark} {message}"

    def muted(self, text: str) -> str:
        """Format muted/secondary text."""
        return self._apply(_Token.MUTED, text)

    def active(self, text: str) -> str:
        """Format active/selected indicator."""
        return self._apply(_Token.ACTIVE, text)

    # ─────────────────────────────────────────────────────────────────────────
    # Compound formatters
    # ─────────────────────────────────────────────────────────────────────────

    def device_line(self, name: str, device_type: str, device_key: str) -> str:
        """Format a device listing line."""
        return f"{self.device(name)} {self.muted(device_type)} {self.muted(device_key)}"

    def kv(self, k: str, v: str) -> str:
        """Format a key-value pair inline."""
        return f"{self.key(k)}{self.muted(':')} {self.value(v)}"

    def columns(self, items: list[tuple[str, str]], key_width: int = 0) -> list[str]:
        """Format key-value pairs as aligned columns."""
        if not key_width:
            key_width = max(len(k) for k, _ in items) if items else 0

        lines = []
        for k, v in items:
            padded_key = k.rjust(key_width)
            lines.append(f"  {self.key(padded_key)} {self.muted(BOX_V)} {v}")
        return lines

    def trait_line(
        self, name: str, trait_type: str, current_value: str | None = None, constraints: str = ""
    ) -> str:
        """Format a trait/parameter line."""
        parts = [f"  {self.key(name)}"]
        parts.append(f" {self.type_hint(f'({trait_type})')}")
        if current_value is not None:
            parts.append(f" {self.muted('=')} {self.value(str(current_value))}")
        if constraints:
            parts.append(f" {self.muted(constraints)}")
        return "".join(parts)

    def separator(self, width: int = 40) -> str:
        """Format a horizontal separator."""
        return self.muted(BOX_H * width)

    # ─────────────────────────────────────────────────────────────────────────
    # Modern Table Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def table_row(self, key_width: int, key: str, value: str, width: int = 80) -> str:
        """Format a table row with right-justified key and vertical separator."""
        key_visible_len = len(strip_ansi(key))
        padding = key_width - key_visible_len
        padded_key = " " * padding + key
        return f" {padded_key} {self.muted(BOX_V)} {value}"

    def table_sep(self, key_width: int, width: int = 80) -> str:
        """Format a table separator line with cross character."""
        left = BOX_H * (key_width + 1)
        right = BOX_H * (width - key_width - 3)
        return self.muted(f" {left}{BOX_X}{right}")

    def table_header(self, key_width: int, key: str, value: str) -> str:
        """Format a table header row (bold key and value)."""
        return self.table_row(key_width, self._bold(key), self._bold(value))

    # ─────────────────────────────────────────────────────────────────────────
    # Panel / Box Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def panel_top(self, title: str = "", width: int = 60) -> str:
        """Format a panel top border with optional title."""
        if title:
            title_str = f" {title} "
            padding = width - len(title_str) - 2
            left_pad = padding // 2
            right_pad = padding - left_pad
            line = (
                f"{BOX_TL_R}{BOX_H * left_pad}{self.header(title_str)}{BOX_H * right_pad}{BOX_TR_R}"
            )
        else:
            line = f"{BOX_TL_R}{BOX_H * (width - 2)}{BOX_TR_R}"
        return self.muted(line) if not title else line

    def panel_row(self, content: str, width: int = 60) -> str:
        """Format a panel content row."""
        visible_len = len(strip_ansi(content))
        padding = width - visible_len - 4
        return f"{self.muted(BOX_V)} {content}{' ' * max(0, padding)} {self.muted(BOX_V)}"

    def panel_bottom(self, width: int = 60) -> str:
        """Format a panel bottom border."""
        return self.muted(f"{BOX_BL_R}{BOX_H * (width - 2)}{BOX_BR_R}")

    def panel_divider(self, width: int = 60) -> str:
        """Format a panel internal divider."""
        return self.muted(f"{BOX_VR}{BOX_H * (width - 2)}{BOX_VL}")

    # ─────────────────────────────────────────────────────────────────────────
    # Progress Bars & Gauges
    # ─────────────────────────────────────────────────────────────────────────

    def progress_bar(
        self,
        value: float,
        max_value: float = 100,
        width: int = 20,
        show_percent: bool = True,
    ) -> str:
        """Format a progress bar with optional percentage."""
        pct = min(1.0, max(0.0, value / max_value)) if max_value > 0 else 0
        filled = int(pct * width)
        empty = width - filled

        # Color based on level
        if pct <= 0.2:
            fill_color = ERROR_RED
        elif pct <= 0.5:
            fill_color = ELECTRIC_YELLOW
        else:
            fill_color = SUCCESS_GREEN

        filled_str = self._rgb(*fill_color, BLOCK_FULL * filled)
        empty_str = self.muted(BLOCK_EMPTY * empty)
        bar = f"{filled_str}{empty_str}"

        if show_percent:
            pct_str = self.number(f"{int(pct * 100)}%")
            return f"{bar} {pct_str}"
        return bar

    def gauge(self, value: float, max_value: float = 100, segments: int = 5) -> str:
        """Format a compact gauge indicator."""
        pct = min(1.0, max(0.0, value / max_value)) if max_value > 0 else 0
        filled = int(pct * segments)

        parts = []
        for i in range(segments):
            if i < filled:
                parts.append(self._rgb(*SUCCESS_GREEN, SYM_GAUGE))
            else:
                parts.append(self.muted(SYM_GAUGE_EMPTY))
        return "".join(parts)

    def battery_bar(self, level: int, charging: bool = False, width: int = 10) -> str:
        """Format a battery indicator."""
        pct = min(100, max(0, level)) / 100
        filled = int(pct * width)
        empty = width - filled

        # Color based on level
        if level <= 20:
            fill_color = ERROR_RED
        elif level <= 50:
            fill_color = ELECTRIC_YELLOW
        else:
            fill_color = SUCCESS_GREEN

        filled_str = self._rgb(*fill_color, BLOCK_FULL * filled)
        empty_str = self.muted(BLOCK_EMPTY * empty)

        icon = self._rgb(*ELECTRIC_YELLOW, SYM_BOLT) if charging else ""
        return f"[{filled_str}{empty_str}] {icon}"

    def rpm_gauge(self, rpm: int, max_rpm: int = 5000) -> str:
        """Format an RPM gauge for fan speed."""
        pct = min(1.0, max(0.0, rpm / max_rpm)) if max_rpm > 0 else 0

        # Color based on speed
        if pct <= 0.3:
            color = SUCCESS_GREEN
        elif pct <= 0.7:
            color = ELECTRIC_YELLOW
        else:
            color = ERROR_RED

        segments = 8
        filled = int(pct * segments)
        bar = self._rgb(*color, SYM_GAUGE * filled) + self.muted(
            SYM_GAUGE_EMPTY * (segments - filled)
        )
        return f"{bar} {self.number(rpm)} RPM"

    # ─────────────────────────────────────────────────────────────────────────
    # Status Indicators
    # ─────────────────────────────────────────────────────────────────────────

    def status_dot(self, active: bool = True) -> str:
        """Format a status indicator dot."""
        if active:
            return self._rgb(*SUCCESS_GREEN, SYM_CIRCLE)
        return self.muted(SYM_CIRCLE_EMPTY)

    def status_badge(self, text: str, variant: str = "default") -> str:
        """Format a status badge."""
        colors: dict[str, tuple[int, int, int]] = {
            "success": SUCCESS_GREEN,
            "error": ERROR_RED,
            "warning": ELECTRIC_YELLOW,
            "info": NEON_CYAN,
            "default": DIM_GRAY,
        }
        r, g, b = colors.get(variant, DIM_GRAY)
        return self._rgb(r, g, b, f"[{text}]")

    def label(self, text: str, value: str) -> str:
        """Format a labeled value."""
        return f"{self.muted(text + ':')} {self.value(value)}"

    # ─────────────────────────────────────────────────────────────────────────
    # Special Formatters
    # ─────────────────────────────────────────────────────────────────────────

    def color_block(self, color_str: str) -> str:
        """Format a color block preview with background color."""
        # Try to parse common color formats
        try:
            if color_str.startswith("#"):
                r = int(color_str[1:3], 16)
                g = int(color_str[3:5], 16)
                b = int(color_str[5:7], 16)
                return self._bg_rgb(r, g, b, "  ") + f" {self.muted(color_str)}"
        except (ValueError, IndexError):
            pass
        return self.value(color_str)

    def sparkline(self, values: list[float], width: int = 10) -> str:
        """Format a mini sparkline chart."""
        if not values:
            return self.muted("─" * width)

        chars = "▁▂▃▄▅▆▇█"
        min_v = min(values)
        max_v = max(values)
        range_v = max_v - min_v if max_v != min_v else 1

        # Sample values to fit width
        step = max(1, len(values) // width)
        sampled = values[::step][:width]

        result = []
        for v in sampled:
            idx = int((v - min_v) / range_v * (len(chars) - 1))
            result.append(chars[idx])

        return self._rgb(*NEON_CYAN, "".join(result))

    def timestamp(self, text: str) -> str:
        """Format a timestamp."""
        return self._rgb(*ELECTRIC_YELLOW, text)

    def command(self, text: str) -> str:
        """Format a command or code snippet."""
        return self._rgb(*CORAL, text)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy exports for compatibility
# ─────────────────────────────────────────────────────────────────────────────

CHECKMARK = SYM_CHECK
CROSS = SYM_CROSS
SEPARATOR = BOX_H
PIPE = BOX_V
CROSS_CHAR = BOX_X
BULLET = SYM_BULLET
