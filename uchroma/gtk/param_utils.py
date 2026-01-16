#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Parameter helpers for trait-driven UI controls.
"""

from __future__ import annotations

from typing import Any

from uchroma.color import ColorScheme
from uchroma.log import Log

_logger = Log.get("uchroma.gtk.params")

MAX_COLOR_SLOTS = 6

# Cache ColorScheme names for fast lookup
_COLOR_SCHEME_NAMES = frozenset(s.name for s in ColorScheme)

LABEL_OVERRIDES = {
    "fps": "FPS",
    "fx": "FX",
}


def humanize_label(name: str) -> str:
    """Convert snake_case to a title label with small overrides."""
    if name in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[name]
    return name.replace("_", " ").title()


def _class_name(trait_def: dict) -> str:
    cls = trait_def.get("__class__", "")
    if isinstance(cls, (list, tuple)) and len(cls) == 2:
        return str(cls[1])
    return str(cls)


def _is_configurable(trait_def: dict) -> bool:
    metadata = trait_def.get("metadata", {}) or {}
    if metadata.get("config") is True:
        return True
    if metadata.get("config") is False:
        return False
    return not trait_def.get("read_only")


def _is_hidden_trait(name: str, trait_def: dict) -> bool:
    if name in {"hidden"}:
        return True
    if trait_def.get("read_only"):
        return True
    metadata = trait_def.get("metadata", {}) or {}
    return bool(metadata.get("hidden"))


def extract_description(traits: dict[str, dict]) -> str | None:
    """Extract a description value from trait metadata if present."""
    desc = traits.get("description")
    if not desc:
        return None
    return desc.get("default_value") or desc.get("__value__")


def is_hidden_effect(traits: dict[str, dict]) -> bool:
    hidden = traits.get("hidden")
    if not hidden:
        return False
    return bool(hidden.get("default_value") or hidden.get("__value__"))


def trait_to_param(name: str, trait_def: dict) -> dict | None:
    """Convert a trait definition to a parameter schema."""
    if not _is_configurable(trait_def) or _is_hidden_trait(name, trait_def):
        return None

    cls_name = _class_name(trait_def)
    label = trait_def.get("label") or humanize_label(name)

    if "ColorSchemeTrait" in cls_name:
        defaults = trait_def.get("default_value") or []
        if not isinstance(defaults, (list, tuple)):
            defaults = [defaults]
        return {
            "name": name,
            "type": "color_list",
            "label": label,
            "defaults": list(defaults),
            "min": int(trait_def.get("minlen", 0) or 0),
            "max": trait_def.get("maxlen"),
        }

    if "ColorTrait" in cls_name:
        return {
            "name": name,
            "type": "color",
            "label": label,
            "default": trait_def.get("default_value"),
        }

    if "Bool" in cls_name:
        return {
            "name": name,
            "type": "toggle",
            "label": label,
            "default": trait_def.get("default_value", False),
        }

    # ColorPresetTrait - a color scheme preset selector with gradient swatches
    if trait_def.get("info_text") == "a predefined color scheme" and "values" in trait_def:
        values = list(trait_def.get("values") or [])
        default = trait_def.get("default_value")
        return {
            "name": name,
            "type": "color_preset",
            "label": label,
            "options": values,
            "default": default if default in values else None,
        }

    if "values" in trait_def:
        values = list(trait_def.get("values") or [])
        default = trait_def.get("default_value")
        return {
            "name": name,
            "type": "choice",
            "label": label,
            "options": values,
            "default": default if default in values else (values[0] if values else None),
        }

    if cls_name in {"Int", "Float"}:
        min_val = trait_def.get("min", 0)
        max_val = trait_def.get("max")
        default = trait_def.get("default_value")
        value_type = "int" if cls_name == "Int" else "float"

        if max_val is None:
            if isinstance(default, (int, float)) and default > 0:
                max_val = default * 2
            else:
                max_val = min_val + 100

        step = trait_def.get("step")
        if step is None:
            if cls_name == "Float":
                span = float(max_val) - float(min_val)
                step = 0.1 if span <= 10 else 0.5
            else:
                step = 1

        return {
            "name": name,
            "type": "range",
            "label": label,
            "min": min_val,
            "max": max_val,
            "step": step,
            "default": default if default is not None else min_val,
            "value_type": value_type,
        }

    return None


def build_param_defs(traits: dict[str, dict], *, exclude: set[str] | None = None) -> list[dict]:
    """Build parameter definitions from trait metadata."""
    exclude = exclude or set()
    params: list[dict[str, Any]] = []
    for name in sorted(traits.keys()):
        if name in exclude:
            continue
        param = trait_to_param(name, traits[name])
        if param:
            params.append(param)
    return params
