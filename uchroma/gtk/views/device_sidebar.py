"""
Device Sidebar

List of connected UChroma devices with selection.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import GObject, Gtk  # noqa: E402


class DeviceRow(Gtk.Box):
    """Row widget for a device in the sidebar."""

    __gtype_name__ = "UChromaDeviceRow"

    def __init__(self, device):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.device = device

        self.add_css_class("device-row")

        # Device icon
        self.icon = Gtk.Image.new_from_icon_name(device.icon_name)
        self.icon.add_css_class("device-icon")
        self.append(self.icon)

        # Text box
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)

        # Device name
        self.name_label = Gtk.Label(label=device.name)
        self.name_label.add_css_class("device-name")
        self.name_label.set_xalign(0)
        self.name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        text_box.append(self.name_label)

        # Subtitle (product ID)
        self.subtitle_label = Gtk.Label(label=device.product_id_hex)
        self.subtitle_label.add_css_class("device-subtitle")
        self.subtitle_label.set_xalign(0)
        text_box.append(self.subtitle_label)

        self.append(text_box)

        # Brightness indicator (small bar)
        self.brightness_bar = Gtk.LevelBar()
        self.brightness_bar.set_min_value(0)
        self.brightness_bar.set_max_value(100)
        self.brightness_bar.set_value(device.brightness)
        self.brightness_bar.set_valign(Gtk.Align.CENTER)
        self.brightness_bar.set_size_request(40, 4)
        self.append(self.brightness_bar)

        # Bind brightness
        device.bind_property(
            "brightness", self.brightness_bar, "value", GObject.BindingFlags.SYNC_CREATE
        )

        # Bind name
        device.bind_property("name", self.name_label, "label", GObject.BindingFlags.SYNC_CREATE)


class DeviceSidebar(Gtk.ListBox):
    """Sidebar showing connected devices."""

    __gtype_name__ = "UChromaDeviceSidebar"

    __gsignals__: ClassVar[dict] = {
        "device-selected": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, device_store=None):
        super().__init__()

        self.device_store = device_store
        self._rows = {}

        self.add_css_class("device-sidebar")
        self.add_css_class("navigation-sidebar")
        self.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Connect selection signal
        self.connect("row-selected", self._on_row_selected)

        # Populate from store
        if device_store:
            self._bind_store(device_store)

    def _bind_store(self, store):
        """Bind to device store for dynamic updates."""
        # Initial population
        for i in range(store.get_n_items()):
            device = store.get_item(i)
            self._add_device_row(device)

        # Subscribe to changes
        store.connect("items-changed", self._on_items_changed)

    def _on_items_changed(self, store, position, removed, added):
        """Handle store changes."""
        # Remove rows
        for _ in range(removed):
            row = self.get_row_at_index(position)
            if row:
                device = row.get_child().device
                self._rows.pop(device.path, None)
                self.remove(row)

        # Add new rows
        for i in range(added):
            device = store.get_item(position + i)
            self._add_device_row(device, position + i)

    def _add_device_row(self, device, position=-1):
        """Add a row for a device."""
        if device.path in self._rows:
            return

        row_widget = DeviceRow(device)
        row = Gtk.ListBoxRow()
        row.set_child(row_widget)
        row.add_css_class("animate-in")

        if position >= 0:
            self.insert(row, position)
        else:
            self.append(row)

        self._rows[device.path] = row

    def _on_row_selected(self, listbox, row):
        """Handle row selection."""
        if row:
            device = row.get_child().device
            self.emit("device-selected", device)
        else:
            self.emit("device-selected", None)

    def select_device(self, device):
        """Programmatically select a device."""
        if device and device.path in self._rows:
            row = self._rows[device.path]
            self.select_row(row)
