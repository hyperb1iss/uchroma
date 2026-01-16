#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Effect Card Widget

Visual card for hardware effect selection with animated preview strip.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk, Pango  # noqa: E402


class EffectCard(Gtk.Button):
    """Visual card for effect selection."""

    __gtype_name__ = "UChromaEffectCard"

    __gsignals__: ClassVar[dict] = {
        "effect-activated": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, effect_id: str, name: str, icon: str, preview_class: str = "default"):
        super().__init__()

        self.effect_id = effect_id
        self._active = False

        self.set_can_focus(True)
        self.add_css_class("effect-card")
        self.set_size_request(80, 80)

        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        # Icon
        icon_widget = Gtk.Image.new_from_icon_name(icon)
        icon_widget.set_pixel_size(24)
        icon_widget.add_css_class("effect-icon")
        box.append(icon_widget)

        # Name
        label = Gtk.Label(label=name)
        label.add_css_class("effect-name")
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(10)
        box.append(label)

        # Preview strip
        preview = Gtk.Box()
        preview.add_css_class("effect-preview")
        preview.add_css_class(f"preview-{preview_class}")
        preview.set_size_request(-1, 12)
        preview.set_hexpand(True)
        box.append(preview)

        self.set_child(box)

        # Connect click
        self.connect("clicked", self._on_clicked)

    def _on_clicked(self, button):
        self.emit("effect-activated", self.effect_id)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        if value:
            self.add_css_class("active")
        else:
            self.remove_css_class("active")


EFFECT_ICON_MAP = {
    "disable": "system-shutdown-symbolic",
    "static": "color-select-symbolic",
    "wave": "weather-windy-symbolic",
    "spectrum": "weather-clear-symbolic",
    "reactive": "input-keyboard-symbolic",
    "breathe": "weather-fog-symbolic",
    "starlight": "starred-symbolic",
    "ripple": "emblem-synchronizing-symbolic",
    "rainbow": "weather-clear-symbolic",
    "fire": "weather-clear-symbolic",
}

EFFECT_PREVIEW_MAP = {
    "disable": "off",
    "static": "static",
    "wave": "wave",
    "spectrum": "spectrum",
    "reactive": "reactive",
    "breathe": "breathe",
    "starlight": "starlight",
    "ripple": "ripple",
    "rainbow": "rainbow",
    "fire": "fire",
}


def icon_for_effect(effect_id: str) -> str:
    """Get a symbolic icon name for an effect."""
    return EFFECT_ICON_MAP.get(effect_id, "starred-symbolic")


def preview_for_effect(effect_id: str) -> str:
    """Get preview style class for an effect."""
    return EFFECT_PREVIEW_MAP.get(effect_id, "default")
