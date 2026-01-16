#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Layer Panel

Layer list with playback controls for custom animation mode.
"""

import os
from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk  # noqa: E402

from ..widgets.layer_row import LayerRow  # noqa: E402


class LayerPanel(Gtk.Box):
    """Layer management panel with playback controls."""

    __gtype_name__ = "UChromaLayerPanel"

    __gsignals__: ClassVar[dict] = {
        "layer-added": (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # renderer_id
        "layer-removed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # zindex
        "layer-selected": (GObject.SignalFlags.RUN_FIRST, None, (object,)),  # LayerRow or None
        "layer-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (int, str, object),
        ),  # zindex, property, value
        "play-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "stop-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._layers = []
        self._selected_layer = None
        self._renderers = []
        self._add_btn = None

        self.add_css_class("layer-panel")
        self.set_margin_start(16)
        self.set_margin_end(16)

        self._build_ui()

    def _build_ui(self):
        """Build the layer panel UI."""
        # Header with title and controls
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("layer-header")
        header.set_margin_bottom(8)

        title = Gtk.Label(label="LAYERS")
        title.add_css_class("panel-title")
        title.set_xalign(0)
        title.set_hexpand(True)
        header.append(title)

        # Add layer button
        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.add_css_class("circular")
        add_btn.set_tooltip_text("Add layer")
        add_btn.connect("clicked", self._on_add_clicked)
        header.append(add_btn)
        self._add_btn = add_btn

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(4)
        sep.set_margin_end(4)
        header.append(sep)

        # Play button
        self._play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self._play_btn.add_css_class("flat")
        self._play_btn.add_css_class("play-btn")
        self._play_btn.set_tooltip_text("Start animation")
        self._play_btn.connect("clicked", lambda *_: self.emit("play-clicked"))
        header.append(self._play_btn)

        # Stop button
        self._stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
        self._stop_btn.add_css_class("flat")
        self._stop_btn.add_css_class("stop-btn")
        self._stop_btn.set_tooltip_text("Stop animation")
        self._stop_btn.connect("clicked", lambda *_: self.emit("stop-clicked"))
        header.append(self._stop_btn)

        self.append(header)

        # Layer list container
        list_frame = Gtk.Frame()
        list_frame.add_css_class("layer-list-frame")

        # Layer list
        self._list = Gtk.ListBox()
        self._list.add_css_class("layer-list")
        self._list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._list.connect("row-selected", self._on_row_selected)
        self._list.set_placeholder(self._create_placeholder())

        list_frame.set_child(self._list)
        self.append(list_frame)

    def _create_placeholder(self) -> Gtk.Widget:
        """Create empty state placeholder."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        icon.set_pixel_size(32)
        icon.set_opacity(0.3)
        box.append(icon)

        self._placeholder_label = Gtk.Label(label="Add a layer to begin")
        self._placeholder_label.set_opacity(0.5)
        box.append(self._placeholder_label)

        return box

    def _on_add_clicked(self, btn):
        """Show renderer picker."""
        if os.getenv("UCHROMA_GTK_DEBUG"):
            renderer_ids = [renderer.get("id", "") for renderer in self._renderers]
            print(f"GTK: add layer clicked renderers={renderer_ids}")

        if not self._renderers:
            dialog = Adw.MessageDialog.new(
                self.get_root(),  # type: ignore[arg-type]
                "No Renderers",
                "No renderers are available for this selection.",
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present()
            return

        dialog = Adw.MessageDialog.new(
            self.get_root(),  # type: ignore[arg-type]
            "Add Animation Layer",
            "Choose a renderer to add:",
        )

        for renderer in self._renderers:
            dialog.add_response(renderer["id"], renderer["name"])

        dialog.add_response("cancel", "Cancel")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_renderer_dialog_response)
        dialog.present()

    def _on_renderer_dialog_response(self, dialog, response):
        """Handle renderer selection from dialog."""
        if response == "cancel":
            return
        self.emit("layer-added", response)

    def _on_row_selected(self, listbox, row):
        """Handle layer row selection."""
        self._selected_layer = row
        self.emit("layer-selected", row)

    def add_layer(self, renderer_id: str, renderer_name: str) -> LayerRow:
        """Add a new layer to the list."""
        zindex = len(self._layers)

        renderer_data = next((r for r in self._renderers if r["id"] == renderer_id), None)
        row = LayerRow(renderer_id, renderer_name, zindex, renderer_data=renderer_data)
        row.connect("layer-deleted", self._on_layer_deleted)
        row.connect("blend-changed", self._on_layer_blend_changed)
        row.connect("opacity-changed", self._on_layer_opacity_changed)
        row.connect("visibility-changed", self._on_layer_visibility_changed)

        self._list.prepend(row)  # Newest at top (highest z-index)
        self._layers.append(row)

        # Update z-index display (reverse order)
        self._update_zindices()

        return row

    def _on_layer_deleted(self, row):
        """Handle layer deletion."""
        idx = self._layers.index(row) if row in self._layers else -1
        if idx >= 0:
            self._list.remove(row)
            self._layers.remove(row)
            self._update_zindices()
            self.emit("layer-removed", idx)

            if self._selected_layer is row:
                self._selected_layer = None
                self.emit("layer-selected", None)

    def _on_layer_blend_changed(self, row, blend_mode):
        idx = self._layers.index(row) if row in self._layers else -1
        if idx >= 0:
            self.emit("layer-changed", idx, "blend_mode", blend_mode)

    def _on_layer_opacity_changed(self, row, opacity):
        idx = self._layers.index(row) if row in self._layers else -1
        if idx >= 0:
            self.emit("layer-changed", idx, "opacity", opacity)

    def _on_layer_visibility_changed(self, row, visible):
        idx = self._layers.index(row) if row in self._layers else -1
        if idx >= 0:
            self.emit("layer-changed", idx, "visible", visible)

    def _update_zindices(self):
        """Update z-index display on all rows."""
        for i, row in enumerate(self._layers):
            row.update_zindex(i)

    def clear(self):
        """Remove all layers."""
        for row in self._layers[:]:
            self._list.remove(row)
        self._layers.clear()
        self._selected_layer = None
        self.emit("layer-selected", None)

    def set_placeholder_text(self, text: str):
        """Update placeholder text."""
        if hasattr(self, "_placeholder_label"):
            self._placeholder_label.set_label(text)

    def set_renderers(self, renderers: list[dict]):
        """Set available renderer metadata."""
        self._renderers = renderers
        if hasattr(self, "_add_btn"):
            tooltip = "Add layer" if renderers else "No renderers available for this selection"
            self._add_btn.set_tooltip_text(tooltip)

    @property
    def layers(self) -> list:
        return self._layers

    @property
    def selected_layer(self) -> LayerRow | None:
        return self._selected_layer
