"""
LED Zones Page

Control individual LED zones on the device.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk

# LED zone definitions with icons
ZONE_ICONS = {
    "backlight": "input-keyboard-symbolic",
    "logo": "emblem-system-symbolic",
    "scroll_wheel": "input-mouse-symbolic",
    "battery": "battery-symbolic",
    "macro": "view-grid-symbolic",
    "game": "input-gaming-symbolic",
    "misc": "preferences-other-symbolic",
    "profile_red": "emblem-important-symbolic",
    "profile_green": "emblem-ok-symbolic",
    "profile_blue": "emblem-default-symbolic",
}

LED_MODES = ["STATIC", "BLINK", "PULSE", "SPECTRUM"]


class ZoneCard(Gtk.Box):
    """Card widget for a single LED zone."""

    __gtype_name__ = "UChromaZoneCard"

    def __init__(self, zone_name: str, zone_data: dict = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.zone_name = zone_name
        self._zone_data = zone_data or {}

        self.add_css_class("zone-card")
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        self._build_ui()

    def _build_ui(self):
        """Build the zone card UI."""
        # Header with icon and name
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        icon_name = ZONE_ICONS.get(self.zone_name, "preferences-other-symbolic")
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.add_css_class("zone-icon")
        icon.set_pixel_size(24)
        header.append(icon)
        self._icon = icon

        display_name = self.zone_name.replace("_", " ").title()
        name_label = Gtk.Label(label=display_name)
        name_label.add_css_class("zone-name")
        name_label.set_hexpand(True)
        name_label.set_xalign(0)
        header.append(name_label)

        # Enable switch
        self.enable_switch = Gtk.Switch()
        self.enable_switch.set_valign(Gtk.Align.CENTER)
        self.enable_switch.set_active(True)
        self.enable_switch.connect("notify::active", self._on_enabled_changed)
        header.append(self.enable_switch)

        self.append(header)

        # Settings box (collapsible based on enabled state)
        self.settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Brightness row
        bright_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        bright_label = Gtk.Label(label="Brightness")
        bright_label.set_xalign(0)
        bright_label.set_hexpand(True)
        bright_label.add_css_class("dim")
        bright_box.append(bright_label)

        self.brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.brightness_scale.set_value(100)
        self.brightness_scale.set_draw_value(False)
        self.brightness_scale.set_size_request(120, -1)
        bright_box.append(self.brightness_scale)

        self.brightness_label = Gtk.Label(label="100%")
        self.brightness_label.add_css_class("mono")
        self.brightness_label.set_width_chars(4)
        self.brightness_scale.connect("value-changed", self._on_brightness_changed)
        bright_box.append(self.brightness_label)

        self.settings_box.append(bright_box)

        # Color row
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        color_label = Gtk.Label(label="Color")
        color_label.set_xalign(0)
        color_label.set_hexpand(True)
        color_label.add_css_class("dim")
        color_box.append(color_label)

        self.color_button = Gtk.ColorDialogButton()
        self.color_button.set_valign(Gtk.Align.CENTER)

        # Default color
        rgba = Gdk.RGBA()
        rgba.parse("#e135ff")
        self.color_button.set_rgba(rgba)

        color_box.append(self.color_button)

        self.settings_box.append(color_box)

        # Mode row
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        mode_label = Gtk.Label(label="Mode")
        mode_label.set_xalign(0)
        mode_label.set_hexpand(True)
        mode_label.add_css_class("dim")
        mode_box.append(mode_label)

        self.mode_dropdown = Gtk.DropDown.new_from_strings(LED_MODES)
        self.mode_dropdown.set_valign(Gtk.Align.CENTER)
        mode_box.append(self.mode_dropdown)

        self.settings_box.append(mode_box)

        self.append(self.settings_box)

    def _on_enabled_changed(self, switch, pspec):
        """Handle enabled toggle."""
        enabled = switch.get_active()
        self.settings_box.set_sensitive(enabled)

        if enabled:
            self.remove_css_class("disabled")
            self._icon.remove_css_class("dim")
        else:
            self.add_css_class("disabled")
            self._icon.add_css_class("dim")

    def _on_brightness_changed(self, scale):
        """Handle brightness change."""
        value = int(scale.get_value())
        self.brightness_label.set_label(f"{value}%")


class ZonesPage(Adw.PreferencesPage):
    """LED zones control page."""

    __gtype_name__ = "UChromaZonesPage"

    def __init__(self):
        super().__init__()

        self._device = None
        self._zone_cards = {}

        self.set_title("LED Zones")
        self.set_icon_name("preferences-color-symbolic")

        self._build_ui()

    def _build_ui(self):
        """Build the zones page UI."""
        # === ZONES GROUP ===
        self.zones_group = Adw.PreferencesGroup()
        self.zones_group.set_title("LED ZONES")
        self.zones_group.set_description("Control individual lighting zones")
        self.add(self.zones_group)

        # Placeholder message
        self.placeholder = Adw.ActionRow()
        self.placeholder.set_title("No LED zones available")
        self.placeholder.set_subtitle("This device may not support zone control")
        self.placeholder.add_css_class("dim")
        self.zones_group.add(self.placeholder)

        # Container for zone cards
        self.zones_flow = Gtk.FlowBox()
        self.zones_flow.set_homogeneous(True)
        self.zones_flow.set_min_children_per_line(1)
        self.zones_flow.set_max_children_per_line(2)
        self.zones_flow.set_column_spacing(8)
        self.zones_flow.set_row_spacing(8)
        self.zones_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.zones_flow.set_visible(False)

        # Wrapper
        flow_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        flow_wrapper.set_margin_start(4)
        flow_wrapper.set_margin_end(4)
        flow_wrapper.set_margin_top(8)
        flow_wrapper.set_margin_bottom(8)
        flow_wrapper.append(self.zones_flow)
        self.zones_group.add(flow_wrapper)

        # === ALL ZONES GROUP ===
        self.all_zones_group = Adw.PreferencesGroup()
        self.all_zones_group.set_title("ALL ZONES")
        self.add(self.all_zones_group)

        # Master brightness
        bright_row = Adw.ActionRow()
        bright_row.set_title("Master Brightness")
        bright_row.set_subtitle("Adjust all zones at once")

        self.master_brightness = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.master_brightness.set_value(100)
        self.master_brightness.set_draw_value(False)
        self.master_brightness.set_size_request(150, -1)
        self.master_brightness.set_valign(Gtk.Align.CENTER)
        bright_row.add_suffix(self.master_brightness)

        self.all_zones_group.add(bright_row)

        # All off button
        off_row = Adw.ActionRow()
        off_row.set_title("Turn Off All")
        off_row.set_subtitle("Disable all LED zones")

        off_btn = Gtk.Button(label="Turn Off")
        off_btn.add_css_class("destructive-action")
        off_btn.set_valign(Gtk.Align.CENTER)
        off_row.add_suffix(off_btn)

        self.all_zones_group.add(off_row)

    def set_device(self, device):
        """Set the current device."""
        self._device = device
        self._refresh_zones()

    def _refresh_zones(self):
        """Refresh zone list from device."""
        # Clear existing zones
        for zone_id in list(self._zone_cards.keys()):
            card = self._zone_cards.pop(zone_id)
            self.zones_flow.remove(card.get_parent())

        if not self._device:
            self.placeholder.set_visible(True)
            self.zones_flow.set_visible(False)
            return

        # TODO: Get available zones from device
        # For now, show common zones as example
        example_zones = ["backlight", "logo"]

        if not example_zones:
            self.placeholder.set_visible(True)
            self.zones_flow.set_visible(False)
            return

        self.placeholder.set_visible(False)
        self.zones_flow.set_visible(True)

        for zone_name in example_zones:
            card = ZoneCard(zone_name)
            child = Gtk.FlowBoxChild()
            child.set_child(card)
            self.zones_flow.append(child)
            self._zone_cards[zone_name] = card
