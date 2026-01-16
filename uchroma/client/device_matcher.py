#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Device selection and fuzzy matching."""

import re
from typing import Literal

MatchType = Literal["name", "index", "key", "path", "fuzzy"]


def parse_device_spec(spec: str) -> tuple[MatchType, str | int]:
    """
    Parse a device specification string.

    Formats:
        @blackwidow     -> ("name", "blackwidow")
        0               -> ("index", 0)
        1532:0226       -> ("key", "1532:0226")
        1532:0226.01    -> ("key", "1532:0226.01")
        /io/uchroma/... -> ("path", "/io/uchroma/...")
        black           -> ("fuzzy", "black")
    """
    spec = spec.strip()

    # @ prefix = explicit name match
    if spec.startswith("@"):
        return ("name", spec[1:].lower())

    # D-Bus path
    if spec.startswith(("/io/uchroma", "/org/")):
        return ("path", spec)

    # Key format: XXXX:XXXX or XXXX:XXXX.NN
    if re.match(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}(\.\d{2})?$", spec):
        return ("key", spec.lower())

    # Pure numeric = index
    if re.match(r"^\d+$", spec):
        return ("index", int(spec))

    # Fallback: fuzzy name match
    return ("fuzzy", spec.lower())


class DeviceMatcher:
    """Match devices by various criteria with fuzzy support."""

    def __init__(self, devices: list[dict]):
        """
        Initialize with device list.

        Each device dict should have: name, key, type
        """
        self._devices = devices

    def match(self, match_type: MatchType, value: str | int) -> dict:
        """
        Find a device matching the given criteria.

        Raises ValueError if not found or ambiguous.
        """
        if match_type == "path":
            # Direct path lookup - caller handles this
            raise ValueError("Path lookup should be handled by D-Bus client")

        if match_type == "index":
            if not isinstance(value, int):
                value = int(value)
            if 0 <= value < len(self._devices):
                return self._devices[value]
            raise ValueError(f"Device index {value} not found (have {len(self._devices)} devices)")

        if match_type == "key":
            value = str(value).lower()
            for dev in self._devices:
                key = dev["key"].lower()
                # Exact or prefix match (1532:0226 matches 1532:0226.00)
                if key == value or key.startswith(value + "."):
                    return dev
            raise ValueError(f"Device with key '{value}' not found")

        if match_type == "name":
            value = str(value).lower()
            for dev in self._devices:
                if dev["name"].lower() == value:
                    return dev
            raise ValueError(f"Device '{value}' not found")

        if match_type == "fuzzy":
            value = str(value).lower()
            matches = []
            for dev in self._devices:
                name = dev["name"].lower()
                # Check if value is substring of name
                if value in name:
                    matches.append(dev)

            if len(matches) == 0:
                raise ValueError(f"Device matching '{value}' not found")
            if len(matches) > 1:
                names = ", ".join(d["name"] for d in matches)
                raise ValueError(f"Device '{value}' is ambiguous: matches {names}")
            return matches[0]

        raise ValueError(f"Unknown match type: {match_type}")

    def auto_select(self) -> dict:
        """
        Auto-select device if only one exists.

        Raises ValueError if multiple devices present.
        """
        if len(self._devices) == 0:
            raise ValueError("No devices found")
        if len(self._devices) == 1:
            return self._devices[0]
        raise ValueError(
            f"Multiple devices found ({len(self._devices)}). Specify with @name, index, or key."
        )
