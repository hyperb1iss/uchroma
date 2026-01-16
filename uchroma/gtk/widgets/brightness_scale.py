#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Brightness Scale Widget

Compact horizontal brightness control with icon and percentage label.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk  # noqa: E402


class BrightnessScale(Gtk.Box):
    """Compact brightness control with icon and label."""

    __gtype_name__ = "UChromaBrightnessScale"

    __gsignals__: ClassVar[dict] = {
        "value-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.add_css_class("brightness-control")

        # Sun icon
        icon = Gtk.Image.new_from_icon_name("display-brightness-symbolic")
        icon.add_css_class("brightness-icon")
        self.append(icon)

        # Scale
        self._scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self._scale.set_draw_value(False)
        self._scale.set_size_request(100, -1)
        self._scale.set_value(100)
        self._scale.add_css_class("brightness-scale")
        self._scale.connect("value-changed", self._on_value_changed)
        self.append(self._scale)

        # Percentage label
        self._label = Gtk.Label(label="100%")
        self._label.add_css_class("brightness-label")
        self._label.set_width_chars(4)
        self._label.set_xalign(1)
        self.append(self._label)

    def _on_value_changed(self, scale):
        value = scale.get_value()
        self._label.set_label(f"{int(value)}%")
        self.emit("value-changed", value / 100.0)

    @property
    def value(self) -> float:
        """Get brightness as 0.0-1.0."""
        return self._scale.get_value() / 100.0

    @value.setter
    def value(self, value: float):
        """Set brightness as 0.0-1.0."""
        self._scale.set_value(value * 100)

    def set_sensitive(self, sensitive: bool):
        """Enable/disable the control."""
        self._scale.set_sensitive(sensitive)
