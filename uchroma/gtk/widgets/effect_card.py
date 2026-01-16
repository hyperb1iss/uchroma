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


# Effect definitions
EFFECTS = [
    {
        "id": "disable",
        "name": "Off",
        "icon": "system-shutdown-symbolic",
        "preview": "off",
        "params": [],
    },
    {
        "id": "static",
        "name": "Static",
        "icon": "color-select-symbolic",
        "preview": "static",
        "params": [
            {"name": "color", "type": "color", "label": "Color", "default": "#e135ff"},
        ],
    },
    {
        "id": "wave",
        "name": "Wave",
        "icon": "weather-windy-symbolic",
        "preview": "wave",
        "params": [
            {
                "name": "direction",
                "type": "choice",
                "label": "Direction",
                "options": ["LEFT", "RIGHT"],
                "default": "RIGHT",
            },
            {
                "name": "speed",
                "type": "range",
                "label": "Speed",
                "min": 1,
                "max": 4,
                "step": 1,
                "default": 2,
            },
        ],
    },
    {
        "id": "spectrum",
        "name": "Spectrum",
        "icon": "weather-clear-symbolic",
        "preview": "spectrum",
        "params": [],
    },
    {
        "id": "reactive",
        "name": "Reactive",
        "icon": "input-keyboard-symbolic",
        "preview": "reactive",
        "params": [
            {"name": "color", "type": "color", "label": "Color", "default": "#80ffea"},
            {
                "name": "speed",
                "type": "range",
                "label": "Speed",
                "min": 1,
                "max": 4,
                "step": 1,
                "default": 2,
            },
        ],
    },
    {
        "id": "breathe",
        "name": "Breathe",
        "icon": "weather-fog-symbolic",
        "preview": "breathe",
        "params": [
            {"name": "color1", "type": "color", "label": "Color 1", "default": "#e135ff"},
            {"name": "color2", "type": "color", "label": "Color 2", "default": "#80ffea"},
            {
                "name": "speed",
                "type": "range",
                "label": "Speed",
                "min": 1,
                "max": 4,
                "step": 1,
                "default": 2,
            },
        ],
    },
    {
        "id": "starlight",
        "name": "Starlight",
        "icon": "starred-symbolic",
        "preview": "starlight",
        "params": [
            {"name": "color1", "type": "color", "label": "Color 1", "default": "#e135ff"},
            {"name": "color2", "type": "color", "label": "Color 2", "default": "#80ffea"},
            {
                "name": "speed",
                "type": "range",
                "label": "Speed",
                "min": 1,
                "max": 4,
                "step": 1,
                "default": 2,
            },
        ],
    },
]


def get_effect_by_id(effect_id: str) -> dict | None:
    """Get effect definition by ID."""
    return next((e for e in EFFECTS if e["id"] == effect_id), None)
