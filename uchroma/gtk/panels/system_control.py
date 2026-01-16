#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
System Control Panel

Fan control and power mode controls for supported laptops.
"""

from __future__ import annotations

import time
from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk, GLib  # noqa: E402

from ..param_utils import humanize_label  # noqa: E402


class SystemControlPanel(Gtk.Box):
    """Laptop system control panel (fan, power, boost)."""

    __gtype_name__ = "UChromaSystemControlPanel"

    __gsignals__: ClassVar[dict] = {
        "power-mode-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "fan-mode-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, int, int)),
        "fan-rpm-changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "cpu-boost-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "gpu-boost-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self._syncing = False
        self._power_modes: list[str] = []
        self._boost_modes: list[str] = []
        self._fan_mode = "auto"
        self._fan_limits = {
            "min_manual_rpm": 3500,
            "max_rpm": 5000,
            "supports_dual_fan": False,
        }
        self._fan_rpm_source: int | None = None
        self._last_user_change = {"fan1": 0.0, "fan2": 0.0}

        self.add_css_class("system-control")
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(8)
        self.set_margin_bottom(16)

        self._build_ui()

    def _build_ui(self):
        """Build the system control UI."""
        title = Gtk.Label(label="SYSTEM CONTROL")
        title.add_css_class("panel-title")
        title.set_xalign(0)
        self.append(title)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(150)
        self.append(self._stack)

        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._content.add_css_class("system-content")
        self._stack.add_named(self._content, "content")

        self._empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._empty.set_halign(Gtk.Align.CENTER)
        self._empty.set_margin_top(12)
        self._empty.set_margin_bottom(8)
        self._stack.add_named(self._empty, "empty")

        empty_icon = Gtk.Image.new_from_icon_name("computer-symbolic")
        empty_icon.set_pixel_size(28)
        empty_icon.set_opacity(0.4)
        self._empty.append(empty_icon)

        self._empty_label = Gtk.Label(label="System control is unavailable")
        self._empty_label.add_css_class("dim")
        self._empty.append(self._empty_label)

        self._build_power_controls()
        self._build_boost_controls()
        self._build_fan_controls()

        self._stack.set_visible_child_name("empty")

    def _build_power_controls(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("system-row")

        label = Gtk.Label(label="Power Mode")
        label.add_css_class("system-label")
        label.set_xalign(0)
        label.set_size_request(120, -1)
        row.append(label)

        self._power_dropdown = Gtk.DropDown()
        self._power_dropdown.add_css_class("system-dropdown")
        self._power_dropdown.set_hexpand(True)
        self._power_dropdown.connect("notify::selected", self._on_power_selected)
        row.append(self._power_dropdown)

        self._content.append(row)

    def _build_boost_controls(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("system-row")

        label = Gtk.Label(label="Boost")
        label.add_css_class("system-label")
        label.set_xalign(0)
        label.set_size_request(120, -1)
        row.append(label)

        boost_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        boost_box.set_hexpand(True)

        cpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cpu_label = Gtk.Label(label="CPU")
        cpu_label.add_css_class("system-subtitle")
        cpu_label.set_xalign(0)
        cpu_box.append(cpu_label)

        self._cpu_dropdown = Gtk.DropDown()
        self._cpu_dropdown.add_css_class("system-dropdown")
        self._cpu_dropdown.connect("notify::selected", self._on_cpu_boost_selected)
        cpu_box.append(self._cpu_dropdown)

        gpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        gpu_label = Gtk.Label(label="GPU")
        gpu_label.add_css_class("system-subtitle")
        gpu_label.set_xalign(0)
        gpu_box.append(gpu_label)

        self._gpu_dropdown = Gtk.DropDown()
        self._gpu_dropdown.add_css_class("system-dropdown")
        self._gpu_dropdown.connect("notify::selected", self._on_gpu_boost_selected)
        gpu_box.append(self._gpu_dropdown)

        boost_box.append(cpu_box)
        boost_box.append(gpu_box)

        row.append(boost_box)
        self._content.append(row)

    def _build_fan_controls(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("system-row")

        label = Gtk.Label(label="Fan Mode")
        label.add_css_class("system-label")
        label.set_xalign(0)
        label.set_size_request(120, -1)
        row.append(label)

        control = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._fan_auto_switch = Gtk.Switch()
        self._fan_auto_switch.connect("notify::active", self._on_fan_mode_toggled)
        control.append(self._fan_auto_switch)

        self._fan_mode_label = Gtk.Label(label="Auto")
        self._fan_mode_label.add_css_class("system-value")
        control.append(self._fan_mode_label)

        row.append(control)
        self._content.append(row)

        self._fan1_row, self._fan1 = self._build_fan_row("Fan 1", "fan1")
        self._content.append(self._fan1_row)

        self._fan2_row, self._fan2 = self._build_fan_row("Fan 2", "fan2")
        self._content.append(self._fan2_row)
        self._fan2_row.set_visible(False)

    def _build_fan_row(self, label: str, key: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("system-row")

        name = Gtk.Label(label=label)
        name.add_css_class("system-label")
        name.set_xalign(0)
        name.set_size_request(120, -1)
        row.append(name)

        slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 5000, 100)
        slider.set_draw_value(False)
        slider.set_hexpand(True)
        slider.add_css_class("system-slider")
        slider.connect("value-changed", self._on_fan_slider_changed, key)
        row.append(slider)

        values = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        target = Gtk.Label(label="Target: --")
        target.add_css_class("system-value")
        target.set_xalign(1)
        values.append(target)

        current = Gtk.Label(label="Current: --")
        current.add_css_class("system-value")
        current.add_css_class("dim")
        current.set_xalign(1)
        values.append(current)

        row.append(values)

        return row, {"slider": slider, "target": target, "current": current}

    def set_available(self, available: bool, message: str | None = None):
        """Show or hide the controls based on availability."""
        self._stack.set_visible_child_name("content" if available else "empty")
        if message:
            self._empty_label.set_label(message)

    def set_power_modes(self, modes: list[str], current: str | None = None):
        """Set available power modes and selection."""
        self._power_modes = [mode.lower() for mode in modes]
        labels = [humanize_label(mode) for mode in self._power_modes] or ["Unknown"]
        model = Gtk.StringList.new(labels)
        prev_sync = self._syncing
        self._syncing = True
        try:
            self._power_dropdown.set_model(model)
            self._power_dropdown.set_sensitive(bool(self._power_modes))

            idx = 0
            if current:
                current = current.lower()
                if current in self._power_modes:
                    idx = self._power_modes.index(current)
            self._power_dropdown.set_selected(idx)
        finally:
            self._syncing = prev_sync

    def set_power_mode(self, mode: str):
        """Update current power mode selection."""
        if not self._power_modes:
            return
        mode = mode.lower()
        if mode not in self._power_modes:
            return

        prev_sync = self._syncing
        self._syncing = True
        try:
            self._power_dropdown.set_selected(self._power_modes.index(mode))
        finally:
            self._syncing = prev_sync

    def set_boost_modes(self, modes: list[str], cpu: str | None = None, gpu: str | None = None):
        """Set available boost modes and selections."""
        self._boost_modes = [mode.lower() for mode in modes]
        labels = [humanize_label(mode) for mode in self._boost_modes] or ["Unknown"]
        model = Gtk.StringList.new(labels)
        prev_sync = self._syncing
        self._syncing = True
        try:
            self._cpu_dropdown.set_model(model)
            self._gpu_dropdown.set_model(model)
            self._cpu_dropdown.set_sensitive(bool(self._boost_modes))
            self._gpu_dropdown.set_sensitive(bool(self._boost_modes))

            if cpu:
                cpu = cpu.lower()
            if gpu:
                gpu = gpu.lower()
            if cpu and cpu in self._boost_modes:
                self._cpu_dropdown.set_selected(self._boost_modes.index(cpu))
            else:
                self._cpu_dropdown.set_selected(0)
            if gpu and gpu in self._boost_modes:
                self._gpu_dropdown.set_selected(self._boost_modes.index(gpu))
            else:
                self._gpu_dropdown.set_selected(0)
        finally:
            self._syncing = prev_sync

    def set_cpu_boost(self, mode: str):
        """Update current CPU boost selection."""
        self._set_boost_dropdown(self._cpu_dropdown, mode)

    def set_gpu_boost(self, mode: str):
        """Update current GPU boost selection."""
        self._set_boost_dropdown(self._gpu_dropdown, mode)

    def _set_boost_dropdown(self, dropdown: Gtk.DropDown, mode: str):
        if not self._boost_modes:
            return
        mode = mode.lower()
        if mode not in self._boost_modes:
            return

        prev_sync = self._syncing
        self._syncing = True
        try:
            dropdown.set_selected(self._boost_modes.index(mode))
        finally:
            self._syncing = prev_sync

    def set_boost_enabled(self, enabled: bool):
        """Enable or disable boost controls."""
        self._cpu_dropdown.set_sensitive(enabled)
        self._gpu_dropdown.set_sensitive(enabled)

    def set_fan_limits(self, limits: dict):
        """Set fan limits and dual-fan capability."""
        self._fan_limits.update({k: v for k, v in limits.items() if v is not None})
        min_manual = int(self._fan_limits.get("min_manual_rpm", 3500))
        max_rpm = int(self._fan_limits.get("max_rpm", 5000))

        prev_sync = self._syncing
        self._syncing = True
        try:
            for fan in (self._fan1, self._fan2):
                adjustment = fan["slider"].get_adjustment()
                adjustment.set_lower(min_manual)
                adjustment.set_upper(max_rpm)
                adjustment.set_step_increment(100)
                adjustment.set_page_increment(500)
                value = int(fan["slider"].get_value())
                if value < min_manual:
                    fan["slider"].set_value(min_manual)
                    fan["target"].set_label(f"Target: {min_manual} RPM")
        finally:
            self._syncing = prev_sync

        supports_dual = bool(self._fan_limits.get("supports_dual_fan"))
        self._fan2_row.set_visible(supports_dual)

    def set_fan_state(self, rpm: list[int], mode: str):
        """Update fan mode and RPM display."""
        mode = mode.lower() if mode else "auto"
        self._fan_mode = mode
        prev_sync = self._syncing
        self._syncing = True
        try:
            self._fan_auto_switch.set_active(mode == "auto")
            self._fan_mode_label.set_label("Auto" if mode == "auto" else "Manual")
        finally:
            self._syncing = prev_sync

        self._set_fan_enabled(mode != "auto")
        self._update_fan_rpm("fan1", rpm[0] if rpm else 0)
        if self._fan2_row.get_visible():
            fan2_rpm = rpm[1] if len(rpm) > 1 else 0
            self._update_fan_rpm("fan2", fan2_rpm)

    def _set_fan_enabled(self, enabled: bool):
        self._fan1["slider"].set_sensitive(enabled)
        self._fan2["slider"].set_sensitive(enabled)

    def _update_fan_rpm(self, key: str, rpm: int):
        fan = self._fan1 if key == "fan1" else self._fan2
        fan["current"].set_label(f"Current: {int(rpm)} RPM")

        if self._fan_mode == "auto":
            return

        now = time.monotonic()
        if now - self._last_user_change.get(key, 0.0) < 1.2:
            return

        self._syncing = True
        try:
            fan["slider"].set_value(int(rpm))
            fan["target"].set_label(f"Target: {int(rpm)} RPM")
        finally:
            self._syncing = False

    def _on_power_selected(self, dropdown, pspec):
        if self._syncing or not self._power_modes:
            return
        idx = dropdown.get_selected()
        if 0 <= idx < len(self._power_modes):
            self.emit("power-mode-changed", self._power_modes[idx])

    def _on_cpu_boost_selected(self, dropdown, pspec):
        if self._syncing or not self._boost_modes:
            return
        idx = dropdown.get_selected()
        if 0 <= idx < len(self._boost_modes):
            self.emit("cpu-boost-changed", self._boost_modes[idx])

    def _on_gpu_boost_selected(self, dropdown, pspec):
        if self._syncing or not self._boost_modes:
            return
        idx = dropdown.get_selected()
        if 0 <= idx < len(self._boost_modes):
            self.emit("gpu-boost-changed", self._boost_modes[idx])

    def _on_fan_mode_toggled(self, switch, pspec):
        if self._syncing:
            return
        mode = "auto" if switch.get_active() else "manual"
        self._fan_mode = mode
        self._fan_mode_label.set_label("Auto" if mode == "auto" else "Manual")
        self._set_fan_enabled(mode != "auto")
        if mode == "manual":
            min_manual = int(self._fan_limits.get("min_manual_rpm", 0))
            if min_manual > 0:
                prev_sync = self._syncing
                self._syncing = True
                try:
                    for fan in (self._fan1, self._fan2):
                        if fan is self._fan2 and not self._fan2_row.get_visible():
                            continue
                        value = int(fan["slider"].get_value())
                        if value < min_manual:
                            value = min_manual
                            fan["slider"].set_value(value)
                        fan["target"].set_label(f"Target: {value} RPM")
                finally:
                    self._syncing = prev_sync
        fan1 = int(self._fan1["slider"].get_value())
        fan2 = int(self._fan2["slider"].get_value()) if self._fan2_row.get_visible() else -1
        self.emit("fan-mode-changed", mode, fan1, fan2)

    def _on_fan_slider_changed(self, slider, key: str):
        if self._syncing:
            return
        value = int(slider.get_value())
        fan = self._fan1 if key == "fan1" else self._fan2
        fan["target"].set_label(f"Target: {value} RPM")
        self._last_user_change[key] = time.monotonic()

        if self._fan_rpm_source is not None:
            GLib.source_remove(self._fan_rpm_source)
            self._fan_rpm_source = None

        self._fan_rpm_source = GLib.timeout_add(150, self._emit_fan_rpm_changed)

    def _emit_fan_rpm_changed(self, *args):
        if self._syncing:
            return False
        fan1 = int(self._fan1["slider"].get_value())
        fan2 = int(self._fan2["slider"].get_value()) if self._fan2_row.get_visible() else -1
        self.emit("fan-rpm-changed", fan1, fan2)
        self._fan_rpm_source = None
        return False
