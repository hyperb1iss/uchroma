#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# ANSI color utilities for CLI output.
#

import re

# ANSI escape code pattern
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def strip_codes(text: str) -> str:
    """Remove ANSI escape codes from a string."""
    return ANSI_PATTERN.sub("", str(text))


def color(text: str, style: str = None, fore: tuple = None, back: tuple = None) -> str:
    """Apply color/style to text."""
    codes = []

    if style == "bright":
        codes.append("1")  # Bold

    if fore and len(fore) >= 3:
        codes.append(f"38;2;{fore[0]};{fore[1]};{fore[2]}")

    if back and len(back) >= 3:
        codes.append(f"48;2;{back[0]};{back[1]};{back[2]}")

    if not codes:
        return str(text)

    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


class Colr(str):
    """Simple colored string class with alignment support."""

    def __new__(cls, text=""):
        return super().__new__(cls, str(text))

    def rjust(self, width, fillchar=" "):
        """Right-justify, accounting for ANSI codes."""
        visible_len = len(strip_codes(self))
        padding = max(0, width - visible_len)
        return Colr(fillchar * padding + self)

    def ljust(self, width, fillchar=" "):
        """Left-justify, accounting for ANSI codes."""
        visible_len = len(strip_codes(self))
        padding = max(0, width - visible_len)
        return Colr(self + fillchar * padding)

    def center(self, width, text=None, fore=None, back=None):
        """Center text with optional colors."""
        display_text = text if text is not None else str(self)
        visible_len = len(strip_codes(display_text))
        total_pad = max(0, width - visible_len)
        left_pad = total_pad // 2
        right_pad = total_pad - left_pad

        padded = " " * left_pad + display_text + " " * right_pad

        codes = []
        if fore and len(fore) >= 3:
            codes.append(f"38;2;{fore[0]};{fore[1]};{fore[2]}")
        if back and len(back) >= 3:
            codes.append(f"48;2;{back[0]};{back[1]};{back[2]}")

        if codes:
            return Colr(f"\x1b[{';'.join(codes)}m{padded}\x1b[0m")
        return Colr(padded)
