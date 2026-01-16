"""
Mode Toggle Panel

Switch between Hardware FX and Custom Animation modes.
"""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk


class ModeToggle(Gtk.Box):
    """Mode toggle with status indicator."""

    __gtype_name__ = "UChromaModeToggle"

    MODE_HARDWARE = "hardware"
    MODE_CUSTOM = "custom"

    __gsignals__ = {
        "mode-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self._mode = self.MODE_HARDWARE

        self.add_css_class("mode-toggle-bar")
        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        self._build_ui()

    def _build_ui(self):
        """Build the toggle UI."""
        # Left spacer for centering
        left_spacer = Gtk.Box()
        left_spacer.set_hexpand(True)
        self.append(left_spacer)

        # Toggle button group
        toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        toggle_box.add_css_class("linked")
        toggle_box.add_css_class("mode-toggle")

        self._hw_btn = Gtk.ToggleButton(label="Hardware FX")
        self._hw_btn.add_css_class("mode-btn")
        self._hw_btn.set_active(True)
        self._hw_btn.connect("toggled", self._on_hw_toggled)
        toggle_box.append(self._hw_btn)

        self._custom_btn = Gtk.ToggleButton(label="Custom Animation")
        self._custom_btn.add_css_class("mode-btn")
        self._custom_btn.set_group(self._hw_btn)
        self._custom_btn.connect("toggled", self._on_custom_toggled)
        toggle_box.append(self._custom_btn)

        self.append(toggle_box)

        # Right side: status indicator
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_box.set_hexpand(True)
        right_box.set_halign(Gtk.Align.END)

        self._status_icon = Gtk.Image.new_from_icon_name("media-playback-stop-symbolic")
        self._status_icon.add_css_class("status-icon")
        right_box.append(self._status_icon)

        self._status_label = Gtk.Label(label="Stopped")
        self._status_label.add_css_class("status-label")
        self._status_label.add_css_class("dim")
        right_box.append(self._status_label)

        self.append(right_box)

    def _on_hw_toggled(self, btn):
        if btn.get_active() and self._mode != self.MODE_HARDWARE:
            self._mode = self.MODE_HARDWARE
            self.emit("mode-changed", self._mode)

    def _on_custom_toggled(self, btn):
        if btn.get_active() and self._mode != self.MODE_CUSTOM:
            self._mode = self.MODE_CUSTOM
            self.emit("mode-changed", self._mode)

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value == self.MODE_HARDWARE:
            self._hw_btn.set_active(True)
        elif value == self.MODE_CUSTOM:
            self._custom_btn.set_active(True)
        self._mode = value

    def set_status(self, status: str, running: bool = False):
        """Update status indicator."""
        self._status_label.set_label(status)

        if running:
            self._status_icon.set_from_icon_name("media-playback-start-symbolic")
            self._status_label.remove_css_class("dim")
            self._status_label.add_css_class("running")
        else:
            self._status_icon.set_from_icon_name("media-playback-stop-symbolic")
            self._status_label.add_css_class("dim")
            self._status_label.remove_css_class("running")
