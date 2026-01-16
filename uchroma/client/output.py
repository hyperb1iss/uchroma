"""
CLI output styling with SilkCircuit color palette.

Respects NO_COLOR env var and TTY detection.
"""

import os
import re
import sys

# SilkCircuit Neon palette
COLORS: dict[str, tuple[int, int, int]] = {
    "electric_purple": (225, 53, 255),
    "neon_cyan": (128, 255, 234),
    "coral": (255, 106, 193),
    "electric_yellow": (241, 250, 140),
    "success_green": (80, 250, 123),
    "error_red": (255, 99, 99),
    "dim": (128, 128, 128),
}

# Unicode symbols (pre-computed for Python 3.10 compatibility)
CHECKMARK = "\u2713"  # ✓
CROSS = "\u2717"  # ✗
SEPARATOR = "\u2500"  # ─
PIPE = "\u2502"  # │

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_PATTERN.sub("", str(text))


class Output:
    """CLI output with SilkCircuit styling."""

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

    def _rgb(self, r: int, g: int, b: int, text: str) -> str:
        """Apply RGB color to text."""
        if not self._color_enabled:
            return text
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"

    def _style(self, text: str, bold: bool = False) -> str:
        """Apply text styles."""
        if not self._color_enabled or not bold:
            return text
        return f"\x1b[1m{text}\x1b[0m"

    # Color shortcuts using SilkCircuit palette
    def cyan(self, text: str) -> str:
        """Neon cyan - paths, interactions."""
        return self._rgb(*COLORS["neon_cyan"], text)

    def purple(self, text: str) -> str:
        """Electric purple - keywords, markers."""
        return self._rgb(*COLORS["electric_purple"], text)

    def coral(self, text: str) -> str:
        """Coral - hashes, numbers."""
        return self._rgb(*COLORS["coral"], text)

    def yellow(self, text: str) -> str:
        """Electric yellow - warnings, timestamps."""
        return self._rgb(*COLORS["electric_yellow"], text)

    def green(self, text: str) -> str:
        """Success green."""
        return self._rgb(*COLORS["success_green"], text)

    def red(self, text: str) -> str:
        """Error red."""
        return self._rgb(*COLORS["error_red"], text)

    def dim(self, text: str) -> str:
        """Dimmed text."""
        return self._rgb(*COLORS["dim"], text)

    def bold(self, text: str) -> str:
        """Bold text."""
        return self._style(text, bold=True)

    # Semantic output methods
    def success(self, message: str) -> str:
        """Format success message."""
        return f"{self.green(CHECKMARK)} {message}"

    def error(self, message: str) -> str:
        """Format error message."""
        return f"{self.red(CROSS)} {message}"

    def warning(self, message: str) -> str:
        """Format warning message."""
        return f"{self.yellow('!')} {message}"

    def device_line(self, name: str, device_type: str, key: str) -> str:
        """Format a device listing line."""
        return f"{self.bold(self.cyan(name))} {self.dim(device_type)} {self.dim(key)}"

    def columns(self, items: list[tuple[str, str]], key_width: int = 0) -> list[str]:
        """Format key-value pairs as aligned columns."""
        if not key_width:
            key_width = max(len(k) for k, _ in items) if items else 0

        lines = []
        for key, value in items:
            padded_key = key.rjust(key_width)
            lines.append(f"  {self.bold(padded_key)} {PIPE} {value}")
        return lines

    def trait_line(
        self, name: str, trait_type: str, value: str | None = None, constraints: str = ""
    ) -> str:
        """Format a trait/parameter line."""
        parts = [f"  {self.bold(self.cyan(name))}"]
        parts.append(f" {self.dim(f'({trait_type})')}")
        if value is not None:
            parts.append(f" = {self.purple(str(value))}")
        if constraints:
            parts.append(f" {self.dim(constraints)}")
        return "".join(parts)

    def header(self, text: str) -> str:
        """Format a section header."""
        return self.bold(text)

    def separator(self, width: int = 40) -> str:
        """Format a horizontal separator."""
        return self.dim(SEPARATOR * width)
