#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Dashboard Page

Quick overview and controls for the selected device.
"""

import asyncio

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk  # noqa: E402


class DashboardPage(Adw.PreferencesPage):
    """Dashboard with device overview and quick controls."""

    __gtype_name__ = "UChromaDashboardPage"

    def __init__(self):
        super().__init__()

        self._device = None
        self._pending_tasks: set[asyncio.Task] = set()

        self.set_title("Dashboard")
        self.set_icon_name("go-home-symbolic")

        self._build_ui()

    def _build_ui(self):
        """Build the dashboard UI."""
        # === DEVICE INFO GROUP ===
        self.info_group = Adw.PreferencesGroup()
        self.info_group.set_title("DEVICE")
        self.add(self.info_group)

        # Device name row (display only)
        self.name_row = Adw.ActionRow()
        self.name_row.set_title("Name")
        self.name_row.set_subtitle("No device selected")
        self.name_row.add_css_class("property")
        self.info_group.add(self.name_row)

        # Device type row
        self.type_row = Adw.ActionRow()
        self.type_row.set_title("Type")
        self.type_row.set_subtitle("—")
        self.info_group.add(self.type_row)

        # Product ID row
        self.product_row = Adw.ActionRow()
        self.product_row.set_title("Product ID")
        self.product_row.set_subtitle("—")

        product_label = Gtk.Label()
        product_label.add_css_class("mono")
        product_label.add_css_class("dim")
        self.product_row.add_suffix(product_label)
        self._product_label = product_label
        self.info_group.add(self.product_row)

        # Matrix size (if applicable)
        self.matrix_row = Adw.ActionRow()
        self.matrix_row.set_title("LED Matrix")
        self.matrix_row.set_subtitle("—")
        self.info_group.add(self.matrix_row)

        # === BRIGHTNESS GROUP ===
        self.brightness_group = Adw.PreferencesGroup()
        self.brightness_group.set_title("BRIGHTNESS")
        self.add(self.brightness_group)

        # Brightness slider
        self.brightness_row = Adw.ActionRow()
        self.brightness_row.set_title("Brightness")

        self.brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.brightness_scale.set_hexpand(True)
        self.brightness_scale.set_valign(Gtk.Align.CENTER)
        self.brightness_scale.set_size_request(200, -1)
        self.brightness_scale.set_draw_value(False)
        self.brightness_scale.connect("value-changed", self._on_brightness_changed)
        self.brightness_row.add_suffix(self.brightness_scale)

        # Brightness percentage label
        self.brightness_label = Gtk.Label(label="100%")
        self.brightness_label.add_css_class("mono")
        self.brightness_label.set_width_chars(4)
        self.brightness_row.add_suffix(self.brightness_label)

        self.brightness_group.add(self.brightness_row)

        # Suspend toggle
        self.suspend_row = Adw.SwitchRow()
        self.suspend_row.set_title("Suspend Lighting")
        self.suspend_row.set_subtitle("Turn off all LEDs")
        self.suspend_row.connect("notify::active", self._on_suspend_changed)
        self.brightness_group.add(self.suspend_row)

        # === CURRENT EFFECT GROUP ===
        self.effect_group = Adw.PreferencesGroup()
        self.effect_group.set_title("CURRENT EFFECT")
        self.add(self.effect_group)

        # Current effect row
        self.effect_row = Adw.ActionRow()
        self.effect_row.set_title("Active Effect")
        self.effect_row.set_subtitle("None")

        effect_badge = Gtk.Label(label="—")
        effect_badge.add_css_class("accent")
        self.effect_row.add_suffix(effect_badge)
        self._effect_badge = effect_badge
        self.effect_group.add(self.effect_row)

        # Animation status
        self.anim_row = Adw.ActionRow()
        self.anim_row.set_title("Animation")

        self.anim_indicator = Gtk.Label(label="Stopped")
        self.anim_indicator.add_css_class("dim")
        self.anim_row.add_suffix(self.anim_indicator)
        self.effect_group.add(self.anim_row)

        # === QUICK ACTIONS GROUP ===
        self.actions_group = Adw.PreferencesGroup()
        self.actions_group.set_title("QUICK ACTIONS")
        self.add(self.actions_group)

        # Quick effect buttons in a flow box
        self.quick_effects_row = Adw.ActionRow()
        self.quick_effects_row.set_title("Quick Effects")
        self.quick_effects_row.set_subtitle("Apply a preset effect")
        self.actions_group.add(self.quick_effects_row)

        effects_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        effects_box.set_valign(Gtk.Align.CENTER)

        effects = [
            ("Static", "static", "#e135ff"),
            ("Wave", "wave", "#80ffea"),
            ("Spectrum", "spectrum", "#ff6ac1"),
            ("Breathe", "breathe", "#f1fa8c"),
        ]

        for label, effect_id, _color in effects:
            btn = Gtk.Button(label=label)
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_quick_effect, effect_id)
            effects_box.append(btn)

        self.quick_effects_row.add_suffix(effects_box)

    def set_device(self, device):
        """Set the current device."""
        self._device = device

        if not device:
            self.name_row.set_subtitle("No device selected")
            self.type_row.set_subtitle("—")
            self._product_label.set_label("—")
            self.matrix_row.set_subtitle("—")
            self.brightness_scale.set_value(100)
            self._effect_badge.set_label("—")
            return

        # Update info
        self.name_row.set_subtitle(device.name)
        self.type_row.set_subtitle(device.device_type)
        self._product_label.set_label(device.product_id_hex)

        if device.has_matrix:
            self.matrix_row.set_subtitle(f"{device.width} x {device.height}")
        else:
            self.matrix_row.set_subtitle("Not available")

        # Bind brightness
        self.brightness_scale.set_value(device.brightness)
        device.bind_property(
            "brightness",
            self.brightness_scale.get_adjustment(),
            "value",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        # Bind suspend
        device.bind_property(
            "suspended",
            self.suspend_row,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        # Update effect display
        self._update_effect_display()

        # Connect to changes
        device.connect("notify::current-fx", lambda *_: self._update_effect_display())
        device.connect("notify::is-animating", lambda *_: self._update_anim_display())

    def _update_effect_display(self):
        """Update the current effect display."""
        if not self._device:
            return

        fx = self._device.current_fx or "None"
        self.effect_row.set_subtitle(fx.title())
        self._effect_badge.set_label(fx.upper())

    def _update_anim_display(self):
        """Update animation status display."""
        if not self._device:
            return

        if self._device.is_animating:
            self.anim_indicator.set_label("Running")
            self.anim_indicator.remove_css_class("dim")
            self.anim_indicator.add_css_class("cyan")
            self.anim_indicator.add_css_class("glow-active")
        else:
            self.anim_indicator.set_label("Stopped")
            self.anim_indicator.add_css_class("dim")
            self.anim_indicator.remove_css_class("cyan")
            self.anim_indicator.remove_css_class("glow-active")

    def _on_brightness_changed(self, scale):
        """Handle brightness slider change."""
        value = int(scale.get_value())
        self.brightness_label.set_label(f"{value}%")

    def _on_suspend_changed(self, row, pspec):
        """Handle suspend toggle."""
        # Handled by binding

    def _on_quick_effect(self, button, effect_id):
        """Apply a quick effect."""
        if not self._device:
            return

        # Get app and set effect via D-Bus
        app = self.get_root().get_application()
        if app:
            self._schedule_task(app.dbus.set_effect(self._device.path, effect_id))

    def _schedule_task(self, coro):
        """Schedule an async task and track it to prevent GC."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
