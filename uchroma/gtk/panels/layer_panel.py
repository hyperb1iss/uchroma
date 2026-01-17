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

import cairo  # noqa: E402
from gi.repository import Adw, Gdk, GLib, GObject, Gtk  # noqa: E402

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
        "layer-reordered": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (int, int),
        ),  # from_index, to_index
        "play-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "stop-clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._layers = []
        self._selected_layer = None
        self._renderers = []
        self._add_btn = None
        self._drop_target_row = None

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

        # Setup drop target for layer reordering
        self._setup_drop_target()

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

    def _setup_drop_target(self):
        """Setup drop target for layer reordering."""
        drop_target = Gtk.DropTarget.new(GObject.TYPE_INT, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_drop)
        drop_target.connect("motion", self._on_drag_motion)
        drop_target.connect("leave", self._on_drag_leave)
        self._list.add_controller(drop_target)

    def _on_drag_motion(self, target, x, y):
        """Handle drag motion - highlight drop position."""
        row = self._list.get_row_at_y(int(y))

        # Clear previous highlight
        if self._drop_target_row and self._drop_target_row != row:
            self._drop_target_row.remove_css_class("layer-drop-above")
            self._drop_target_row.remove_css_class("layer-drop-below")

        if row:
            row_alloc = row.get_allocation()
            row_mid = row_alloc.height / 2
            relative_y = y - row_alloc.y

            row.remove_css_class("layer-drop-above")
            row.remove_css_class("layer-drop-below")

            if relative_y < row_mid:
                row.add_css_class("layer-drop-above")
            else:
                row.add_css_class("layer-drop-below")

            self._drop_target_row = row

        return Gdk.DragAction.MOVE

    def _on_drag_leave(self, target):
        """Clear drop highlighting when drag leaves."""
        if self._drop_target_row:
            self._drop_target_row.remove_css_class("layer-drop-above")
            self._drop_target_row.remove_css_class("layer-drop-below")
            self._drop_target_row = None

    def _on_drop(self, target, value, x, y):
        """Handle drop - reorder layers."""
        if value is None:
            self._on_drag_leave(target)
            return False

        if isinstance(value, GLib.Variant):
            from_index = value.get_int32()
        else:
            from_index = int(value)

        drop_row = self._list.get_row_at_y(int(y))
        if not drop_row or not isinstance(drop_row, LayerRow):
            self._on_drag_leave(target)
            return False

        row_alloc = drop_row.get_allocation()
        row_mid = row_alloc.height / 2
        relative_y = y - row_alloc.y

        # The list is displayed in reverse order (highest z-index at top)
        visual_drop_pos = drop_row.get_index()
        if relative_y >= row_mid:
            visual_drop_pos += 1

        num_layers = len(self._layers)

        if from_index < 0 or from_index >= num_layers:
            self._on_drag_leave(target)
            return False

        source_row = self._layers[from_index]
        source_visual_pos = num_layers - 1 - from_index

        # Account for shift when moving down
        if visual_drop_pos > source_visual_pos:
            visual_drop_pos -= 1

        to_index = num_layers - 1 - visual_drop_pos
        to_index = max(0, min(num_layers - 1, to_index))

        if from_index != to_index:
            # Reorder in our list
            self._layers.remove(source_row)
            self._layers.insert(to_index, source_row)

            # Reorder in the ListBox
            self._list.remove(source_row)
            new_visual_pos = num_layers - 1 - to_index
            self._list.insert(source_row, new_visual_pos)

            # Update z-indices
            self._update_zindices()

            # Emit signal for parent
            self.emit("layer-reordered", from_index, to_index)

        # Clear drop styling
        self._on_drag_leave(target)
        source_row.remove_css_class("layer-dragging")

        return True

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

        # Create custom dialog with rich renderer list
        dialog = Adw.Window()
        dialog.set_title("Add Animation Layer")
        dialog.set_modal(True)
        dialog.set_transient_for(self.get_root())  # type: ignore[arg-type]
        dialog.set_default_size(380, 500)
        dialog.add_css_class("renderer-dialog")

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: dialog.close())
        header.pack_start(cancel_btn)

        title = Gtk.Label(label="Add Animation Layer")
        title.add_css_class("title")
        header.set_title_widget(title)

        main_box.append(header)

        # Scrolled list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_margin_start(12)
        scroll.set_margin_end(12)
        scroll.set_margin_top(8)
        scroll.set_margin_bottom(12)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("renderer-list")
        listbox.add_css_class("boxed-list")

        # Sort renderers alphabetically by name
        sorted_renderers = sorted(self._renderers, key=lambda r: r.get("name", "").lower())

        for renderer in sorted_renderers:
            row = self._create_renderer_row(renderer, dialog)
            listbox.append(row)

        scroll.set_child(listbox)
        main_box.append(scroll)

        dialog.set_content(main_box)
        dialog.present()

    def _create_renderer_row(self, renderer: dict, dialog) -> Gtk.Widget:
        """Create a rich renderer row with name, description, and preview."""
        row = Gtk.ListBoxRow()
        row.add_css_class("renderer-row")

        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("renderer-btn")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Color gradient preview (from default colorscheme if available)
        gradient = Gtk.DrawingArea()
        gradient.set_size_request(48, 48)
        gradient.add_css_class("renderer-gradient")

        # Get colors from renderer's default colorscheme trait
        colors = []
        traits = renderer.get("traits", {})
        for trait_def in traits.values():
            cls_name = ""
            cls_info = trait_def.get("__class__", "")
            if isinstance(cls_info, (list, tuple)) and len(cls_info) == 2:
                cls_name = str(cls_info[1])
            if "ColorSchemeTrait" in cls_name:
                default_colors = trait_def.get("default_value", [])
                if isinstance(default_colors, (list, tuple)):
                    colors = list(default_colors)
                break

        # Parse colors
        rgba_colors = []
        for color_str in colors[:6]:
            rgba = Gdk.RGBA()
            if rgba.parse(str(color_str)):
                rgba_colors.append(rgba)

        def draw_gradient(area, cr, width, height, cols=rgba_colors):
            radius = 8
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()

            if cols:
                pat = cairo.LinearGradient(0, 0, width, height)
                for i, c in enumerate(cols):
                    stop = i / max(len(cols) - 1, 1)
                    pat.add_color_stop_rgb(stop, c.red, c.green, c.blue)
                cr.set_source(pat)
            else:
                # Fallback gradient
                pat = cairo.LinearGradient(0, 0, width, height)
                pat.add_color_stop_rgb(0, 0.3, 0.2, 0.5)
                pat.add_color_stop_rgb(1, 0.5, 0.3, 0.7)
                cr.set_source(pat)

            cr.fill()

        gradient.set_draw_func(draw_gradient)
        box.append(gradient)

        # Text content
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)

        name_label = Gtk.Label(label=renderer.get("name", "Unknown"))
        name_label.add_css_class("renderer-name")
        name_label.set_xalign(0)
        text_box.append(name_label)

        # Description
        desc = renderer.get("description", "")
        if desc:
            desc_label = Gtk.Label(label=desc)
            desc_label.add_css_class("renderer-desc")
            desc_label.set_xalign(0)
            desc_label.set_wrap(True)
            desc_label.set_max_width_chars(35)
            text_box.append(desc_label)

        # Author if available
        author = renderer.get("author", "")
        if author:
            author_label = Gtk.Label(label=f"by {author}")
            author_label.add_css_class("renderer-author")
            author_label.set_xalign(0)
            text_box.append(author_label)

        box.append(text_box)

        # Arrow
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        arrow.add_css_class("renderer-arrow")
        box.append(arrow)

        btn.set_child(box)

        renderer_id = renderer.get("id", "")
        btn.connect(
            "clicked", lambda b, rid=renderer_id, d=dialog: self._on_renderer_selected(rid, d)
        )

        row.set_child(btn)
        return row

    def _on_renderer_selected(self, renderer_id: str, dialog):
        """Handle renderer selection from custom dialog."""
        dialog.close()
        self.emit("layer-added", renderer_id)

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

    def select_layer(self, row: LayerRow | None):
        """Programmatically select a layer row."""
        self._list.select_row(row)

    @property
    def layers(self) -> list:
        return self._layers

    @property
    def selected_layer(self) -> LayerRow | None:
        return self._selected_layer
