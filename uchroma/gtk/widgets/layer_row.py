"""
Layer Row Widget

Compact layer row for animation stack with inline controls.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk, Pango  # noqa: E402

from uchroma.blending import BlendOp  # noqa: E402

BLEND_MODES = BlendOp.get_modes()


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

        # Drag handle
        handle = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        handle.add_css_class("layer-handle")
        handle.set_opacity(0.5)
        box.append(handle)

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

        # Blend mode dropdown
        blend_list = Gtk.StringList.new(BLEND_MODES)
        self._blend_dropdown = Gtk.DropDown(model=blend_list)
        self._blend_dropdown.add_css_class("layer-blend")
        self._blend_dropdown.set_size_request(90, -1)
        self._blend_dropdown.connect("notify::selected", self._on_blend_changed)
        box.append(self._blend_dropdown)
        self.blend_mode = self._blend_mode

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

    def _on_blend_changed(self, dropdown, pspec):
        idx = dropdown.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION and idx < len(BLEND_MODES):
            self._blend_mode = BLEND_MODES[idx]
            self.emit("blend-changed", self._blend_mode)

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
        self._blend_dropdown.set_selected(BLEND_MODES.index(value))

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
