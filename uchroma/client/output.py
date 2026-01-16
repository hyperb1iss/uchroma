#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
CLI output styling with semantic design tokens.

Exposes only semantic methods (device, key, value, etc.) — not colors.
Color mapping is internal via the SilkCircuit theme.

Respects NO_COLOR env var and TTY detection.
"""

import os
import re
import sys
from enum import Enum, auto

# ─────────────────────────────────────────────────────────────────────────────
# Design Tokens (internal)
# ─────────────────────────────────────────────────────────────────────────────


class _Token(Enum):
    """Semantic design tokens — maps UI concepts to colors."""

    # Content types
    DEVICE = auto()  # Device names
    KEY = auto()  # Property names, labels
    VALUE = auto()  # Property values, data
    PATH = auto()  # File paths, URLs
    HEADER = auto()  # Section titles (bold only)

    # States
    SUCCESS = auto()  # Confirmations, completed
    ERROR = auto()  # Failures, problems
    WARNING = auto()  # Cautions, attention
    MUTED = auto()  # Metadata, less important
    ACTIVE = auto()  # Current/selected marker


# SilkCircuit Neon theme — maps tokens to RGB values
_THEME: dict[_Token, tuple[int, int, int] | None] = {
    # Content types
    _Token.DEVICE: (128, 255, 234),  # Neon Cyan
    _Token.KEY: (128, 255, 234),  # Neon Cyan
    _Token.VALUE: (225, 53, 255),  # Electric Purple
    _Token.PATH: (128, 255, 234),  # Neon Cyan
    _Token.HEADER: None,  # Bold only, no color
    # States
    _Token.SUCCESS: (80, 250, 123),  # Green
    _Token.ERROR: (255, 99, 99),  # Red
    _Token.WARNING: (241, 250, 140),  # Electric Yellow
    _Token.MUTED: (128, 128, 128),  # Gray
    _Token.ACTIVE: (80, 250, 123),  # Green
}


# ─────────────────────────────────────────────────────────────────────────────
# Symbols
# ─────────────────────────────────────────────────────────────────────────────

CHECKMARK = "\u2713"  # ✓
CROSS = "\u2717"  # ✗
SEPARATOR = "\u2500"  # ─
PIPE = "\u2502"  # │
CROSS_CHAR = "\u253c"  # ┼
BULLET = "\u2022"  # •

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_PATTERN.sub("", str(text))


# ─────────────────────────────────────────────────────────────────────────────
# Output Class
# ─────────────────────────────────────────────────────────────────────────────


class Output:
    """
    CLI output with semantic styling.

    All public methods use UI concepts (device, key, value), not colors.
    The theme mapping is internal and swappable.
    """

    def __init__(self, force_color: bool | None = None):
        self._color_enabled = self._detect_color(force_color)

    def _detect_color(self, force: bool | None) -> bool:
        """Detect if color output should be enabled."""
        if force is not None:
            return force
        # NO_COLOR standard: https://no-color.org/
        if os.environ.get("NO_COLOR"):
            return False
        # Check if stdout is a TTY
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return False
        # Check for dumb terminal
        return os.environ.get("TERM") != "dumb"

    # ─────────────────────────────────────────────────────────────────────────
    # Internal styling
    # ─────────────────────────────────────────────────────────────────────────

    def _rgb(self, r: int, g: int, b: int, text: str) -> str:
        """Apply RGB color to text."""
        if not self._color_enabled:
            return text
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"

    def _bold(self, text: str) -> str:
        """Apply bold style."""
        if not self._color_enabled:
            return text
        return f"\x1b[1m{text}\x1b[0m"

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

    def path(self, text: str) -> str:
        """Format a file path or URL."""
        return self._apply(_Token.PATH, text)

    def header(self, text: str) -> str:
        """Format a section header."""
        return self._apply(_Token.HEADER, text, bold=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Semantic methods — states
    # ─────────────────────────────────────────────────────────────────────────

    def success(self, message: str) -> str:
        """Format a success message with checkmark."""
        mark = self._apply(_Token.SUCCESS, CHECKMARK)
        return f"{mark} {message}"

    def error(self, message: str) -> str:
        """Format an error message with cross."""
        mark = self._apply(_Token.ERROR, CROSS)
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
        return f"{self.key(k)} = {self.value(v)}"

    def columns(self, items: list[tuple[str, str]], key_width: int = 0) -> list[str]:
        """Format key-value pairs as aligned columns."""
        if not key_width:
            key_width = max(len(k) for k, _ in items) if items else 0

        lines = []
        for k, v in items:
            padded_key = k.rjust(key_width)
            lines.append(f"  {self._bold(padded_key)} {PIPE} {v}")
        return lines

    def trait_line(
        self, name: str, trait_type: str, current_value: str | None = None, constraints: str = ""
    ) -> str:
        """Format a trait/parameter line."""
        parts = [f"  {self.key(name)}"]
        parts.append(f" {self.muted(f'({trait_type})')}")
        if current_value is not None:
            parts.append(f" = {self.value(str(current_value))}")
        if constraints:
            parts.append(f" {self.muted(constraints)}")
        return "".join(parts)

    def separator(self, width: int = 40) -> str:
        """Format a horizontal separator."""
        return self.muted(SEPARATOR * width)

    # ─────────────────────────────────────────────────────────────────────────
    # Table formatters (matching old client.py style)
    # ─────────────────────────────────────────────────────────────────────────

    def table_row(self, key_width: int, key: str, value: str, width: int = 80) -> str:
        """Format a table row with right-justified key and vertical separator."""
        # Get visible length of key (without ANSI codes) for proper padding
        key_visible_len = len(strip_ansi(key))
        # Calculate padding needed
        padding = key_width - key_visible_len
        padded_key = " " * padding + key

        # Ellipsize long values
        visible_len = len(strip_ansi(value))
        max_val_len = width - key_width - 5
        if visible_len > max_val_len and max_val_len > 10:
            # Find a good truncation point
            value = strip_ansi(value)[: max_val_len - 5] + "(...)"

        return f" {padded_key} {PIPE} {value}"

    def table_sep(self, key_width: int, width: int = 80) -> str:
        """Format a table separator line with cross character."""
        left = SEPARATOR * (key_width + 1)
        right = SEPARATOR * (width - key_width - 3)
        return f" {left}{CROSS_CHAR}{right}"

    def table_header(self, key_width: int, key: str, value: str) -> str:
        """Format a table header row (bold key and value)."""
        return self.table_row(key_width, self._bold(key), self._bold(value))
