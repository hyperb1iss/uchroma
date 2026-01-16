#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Layer Row Widget

Compact layer row for animation stack with inline controls.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GObject, Gtk, Pango  # noqa: E402

from uchroma.blending import BlendOp  # noqa: E402

BLEND_MODES = BlendOp.get_modes()

# Blend mode metadata: (display_name, description, category)
BLEND_INFO = {
    "screen": ("Screen", "Brightens by inverting, multiplying, inverting", "lighten"),
    "addition": ("Add", "Adds colors together, very bright", "lighten"),
    "dodge": ("Dodge", "Brightens based on layer, high contrast", "lighten"),
    "lighten_only": ("Lighten", "Keeps brighter pixels from each layer", "lighten"),
    "multiply": ("Multiply", "Darkens by multiplying colors", "darken"),
    "darken_only": ("Darken", "Keeps darker pixels from each layer", "darken"),
    "soft_light": ("Soft Light", "Gentle contrast like diffused light", "contrast"),
    "hard_light": ("Hard Light", "Strong contrast, multiply or screen", "contrast"),
    "difference": ("Difference", "Subtracts colors, inverts similar areas", "compare"),
    "subtract": ("Subtract", "Subtracts layer from base", "compare"),
    "divide": ("Divide", "Divides base by layer, brightens", "compare"),
    "grain_extract": ("Grain Extract", "Extracts texture details", "texture"),
    "grain_merge": ("Grain Merge", "Merges texture details", "texture"),
}

CATEGORY_ORDER = ["lighten", "darken", "contrast", "compare", "texture"]
CATEGORY_LABELS = {
    "lighten": "Lighten",
    "darken": "Darken",
    "contrast": "Contrast",
    "compare": "Compare",
    "texture": "Texture",
}


class LayerRow(Gtk.ListBoxRow):
    """Compact layer row with inline blend mode and opacity."""

    __gtype_name__ = "UChromaLayerRow"

    __gsignals__: ClassVar[dict] = {
        "layer-selected": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "layer-deleted": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "blend-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "opacity-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        "visibility-changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self, renderer_id: str, renderer_name: str, zindex: int, renderer_data=None):
        super().__init__()

        self.renderer_id = renderer_id
        self.renderer_name = renderer_name
        self.renderer_data = renderer_data
        self.zindex = zindex
        self._blend_mode = "screen"
        self._opacity = 1.0
        self._visible = True

        self.add_css_class("layer-row")
        self.set_selectable(True)
        self.set_activatable(True)

        self._build_ui()

    def _build_ui(self):
        """Build the row UI."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(8)
        box.set_margin_end(8)

        # Drag handle - use a Box container for better event handling
        self._handle = Gtk.Box()
        self._handle.add_css_class("layer-handle")
        self._handle.set_cursor(Gdk.Cursor.new_from_name("grab"))
        handle_icon = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        self._handle.append(handle_icon)
        box.append(self._handle)

        # Z-index badge
        self._zindex_label = Gtk.Label(label=str(self.zindex))
        self._zindex_label.add_css_class("layer-zindex")
        self._zindex_label.set_width_chars(2)
        box.append(self._zindex_label)

        # Renderer name
        name_label = Gtk.Label(label=self.renderer_name)
        name_label.add_css_class("layer-name")
        name_label.set_hexpand(True)
        name_label.set_xalign(0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(name_label)

        # Blend mode picker (MenuButton + Popover)
        self._blend_btn = Gtk.MenuButton()
        self._blend_btn.add_css_class("layer-blend")
        self._blend_btn.set_size_request(90, -1)

        # Button label shows current mode
        self._blend_label = Gtk.Label(
            label=BLEND_INFO.get(self._blend_mode, (self._blend_mode,))[0]
        )
        self._blend_btn.set_child(self._blend_label)

        # Build popover with categorized blend modes
        popover = self._build_blend_popover()
        self._blend_btn.set_popover(popover)
        box.append(self._blend_btn)

        # Opacity slider
        self._opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        self._opacity_scale.add_css_class("layer-opacity")
        self._opacity_scale.set_value(1.0)
        self._opacity_scale.set_draw_value(False)
        self._opacity_scale.set_size_request(70, -1)
        self._opacity_scale.connect("value-changed", self._on_opacity_changed)
        box.append(self._opacity_scale)

        # Visibility toggle
        self._vis_btn = Gtk.ToggleButton()
        self._vis_btn.set_icon_name("view-reveal-symbolic")
        self._vis_btn.add_css_class("flat")
        self._vis_btn.add_css_class("layer-visibility")
        self._vis_btn.set_active(True)
        self._vis_btn.connect("toggled", self._on_visibility_toggled)
        box.append(self._vis_btn)

        # Delete button
        delete_btn = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("layer-delete")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", lambda *_: self.emit("layer-deleted"))
        box.append(delete_btn)

        self.set_child(box)

        # Setup drag source for reordering
        self._setup_drag_source()

    def _setup_drag_source(self):
        """Setup drag source for layer reordering on the handle."""
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect("prepare", self._on_drag_prepare)
        drag_source.connect("drag-begin", self._on_drag_begin)
        drag_source.connect("drag-end", self._on_drag_end)
        # Attach to the handle widget, not the whole row
        self._handle.add_controller(drag_source)

    def _on_drag_prepare(self, source, x, y):
        """Prepare drag data - return content provider with row index."""
        # Store the row's current index in the value
        return Gdk.ContentProvider.new_for_value(self.zindex)

    def _on_drag_begin(self, source, drag):
        """Handle drag start - create visual feedback."""
        # Use WidgetPaintable for the drag icon
        paintable = Gtk.WidgetPaintable.new(self)
        Gtk.DragSource.set_icon(source, paintable, 0, 0)
        self.add_css_class("layer-dragging")
        self._handle.set_cursor(Gdk.Cursor.new_from_name("grabbing"))

    def _on_drag_end(self, source, drag, delete_data):
        """Handle drag end - clean up styling."""
        self.remove_css_class("layer-dragging")
        self._handle.set_cursor(Gdk.Cursor.new_from_name("grab"))

    def _build_blend_popover(self) -> Gtk.Popover:
        """Build popover with categorized blend modes."""
        popover = Gtk.Popover()
        popover.add_css_class("blend-popover")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(280)
        scroll.set_propagate_natural_height(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(4)

        # Group modes by category
        categories: dict[str, list[str]] = {cat: [] for cat in CATEGORY_ORDER}
        for mode in BLEND_MODES:
            info = BLEND_INFO.get(mode)
            if info:
                categories[info[2]].append(mode)

        for cat in CATEGORY_ORDER:
            modes = categories.get(cat, [])
            if not modes:
                continue

            # Category header
            header = Gtk.Label(label=CATEGORY_LABELS.get(cat, cat))
            header.add_css_class("blend-category")
            header.set_xalign(0)
            vbox.append(header)

            # Mode buttons
            for mode in modes:
                info = BLEND_INFO.get(mode, (mode, "", cat))
                btn = Gtk.Button()
                btn.add_css_class("flat")
                btn.add_css_class("blend-option")

                btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
                btn_box.set_margin_start(4)
                btn_box.set_margin_end(4)

                name = Gtk.Label(label=info[0])
                name.add_css_class("blend-name")
                name.set_xalign(0)
                btn_box.append(name)

                desc = Gtk.Label(label=info[1])
                desc.add_css_class("blend-desc")
                desc.set_xalign(0)
                btn_box.append(desc)

                btn.set_child(btn_box)
                btn.connect("clicked", self._on_blend_selected, mode, popover)
                vbox.append(btn)

        scroll.set_child(vbox)
        popover.set_child(scroll)
        return popover

    def _on_blend_selected(self, btn, mode: str, popover: Gtk.Popover):
        """Handle blend mode selection."""
        self._blend_mode = mode
        info = BLEND_INFO.get(mode, (mode,))
        self._blend_label.set_label(info[0])
        popover.popdown()
        self.emit("blend-changed", mode)

    def _on_opacity_changed(self, scale):
        self._opacity = scale.get_value()
        self.emit("opacity-changed", self._opacity)

    def _on_visibility_toggled(self, btn):
        self._visible = btn.get_active()
        btn.set_icon_name("view-reveal-symbolic" if self._visible else "view-conceal-symbolic")
        self.emit("visibility-changed", self._visible)

    def update_zindex(self, zindex: int):
        """Update the z-index display."""
        self.zindex = zindex
        self._zindex_label.set_label(str(zindex))

    @property
    def blend_mode(self) -> str:
        return self._blend_mode

    @blend_mode.setter
    def blend_mode(self, value: str):
        if value in BLEND_MODES:
            self._blend_mode = value
            info = BLEND_INFO.get(value, (value,))
            self._blend_label.set_label(info[0])

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        self._opacity = max(0.0, min(1.0, value))
        self._opacity_scale.set_value(self._opacity)

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = value
        self._vis_btn.set_active(value)
