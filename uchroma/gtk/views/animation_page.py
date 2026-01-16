"""
Animation Page

Layer composer for custom animation effects with drag-reorder support.
"""

import asyncio
from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk  # noqa: E402

# Available renderers with metadata
RENDERERS = [
    {
        "id": "uchroma.fxlib.plasma.Plasma",
        "name": "Plasma",
        "description": "Colorful moving blobs of plasma",
        "icon": "weather-fog-symbolic",
    },
    {
        "id": "uchroma.fxlib.rainbow.Rainbow",
        "name": "Rainflow",
        "description": "Simple flowing colors",
        "icon": "weather-clear-symbolic",
    },
    {
        "id": "uchroma.fxlib.ripple.Ripple",
        "name": "Ripples",
        "description": "Ripples of color when keys are pressed",
        "icon": "emblem-synchronizing-symbolic",
    },
    {
        "id": "uchroma.fxlib.reaction.Reaction",
        "name": "Reaction",
        "description": "Keys change color when pressed",
        "icon": "input-keyboard-symbolic",
    },
]

BLEND_MODES = [
    "screen",
    "multiply",
    "addition",
    "subtract",
    "lighten_only",
    "darken_only",
    "soft_light",
    "hard_light",
    "dodge",
    "difference",
    "grain_extract",
    "grain_merge",
    "divide",
]


class LayerRow(Gtk.Box):
    """A single layer in the animation stack."""

    __gtype_name__ = "UChromaAnimationLayerRow"

    __gsignals__: ClassVar[dict] = {
        "delete-requested": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "selected": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "blend-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "opacity-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
    }

    def __init__(self, renderer_name: str, zindex: int):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.renderer_name = renderer_name
        self.zindex = zindex
        self._selected = False

        self.add_css_class("layer-row")
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._build_ui()

    def _build_ui(self):
        """Build the layer row UI."""
        # Drag handle
        handle = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        handle.add_css_class("layer-handle")
        self.append(handle)

        # Z-index badge
        zindex_label = Gtk.Label(label=str(self.zindex))
        zindex_label.add_css_class("layer-zindex")
        self.append(zindex_label)
        self._zindex_label = zindex_label

        # Layer name
        name_label = Gtk.Label(label=self.renderer_name)
        name_label.add_css_class("layer-name")
        name_label.set_hexpand(True)
        name_label.set_xalign(0)
        self.append(name_label)
        self._name_label = name_label

        # Blend mode dropdown
        blend_dropdown = Gtk.DropDown.new_from_strings(BLEND_MODES)
        blend_dropdown.add_css_class("layer-blend-dropdown")
        blend_dropdown.set_valign(Gtk.Align.CENTER)
        blend_dropdown.connect("notify::selected", self._on_blend_changed)
        self.append(blend_dropdown)
        self._blend_dropdown = blend_dropdown

        # Opacity slider
        opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        opacity_scale.add_css_class("layer-opacity-scale")
        opacity_scale.set_value(1.0)
        opacity_scale.set_draw_value(False)
        opacity_scale.set_valign(Gtk.Align.CENTER)
        opacity_scale.set_size_request(80, -1)
        opacity_scale.connect("value-changed", self._on_opacity_changed)
        self.append(opacity_scale)
        self._opacity_scale = opacity_scale

        # Delete button
        delete_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        delete_btn.add_css_class("layer-delete-button")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("circular")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.connect("clicked", lambda *_: self.emit("delete-requested"))
        self.append(delete_btn)

        # Click gesture for selection
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_clicked)
        self.add_controller(click)

    def _on_clicked(self, gesture, n_press, x, y):
        """Handle click for selection."""
        self.emit("selected")

    def _on_blend_changed(self, dropdown, pspec):
        """Handle blend mode change."""
        idx = dropdown.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            self.emit("blend-changed", BLEND_MODES[idx])

    def _on_opacity_changed(self, scale):
        """Handle opacity change."""
        self.emit("opacity-changed", scale.get_value())

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        if value:
            self.add_css_class("selected")
        else:
            self.remove_css_class("selected")

    def set_blend_mode(self, mode: str):
        """Set the blend mode dropdown."""
        try:
            idx = BLEND_MODES.index(mode)
            self._blend_dropdown.set_selected(idx)
        except ValueError:
            pass

    def set_opacity(self, opacity: float):
        """Set the opacity slider."""
        self._opacity_scale.set_value(opacity)


class AnimationPage(Adw.PreferencesPage):
    """Animation layer composer page."""

    __gtype_name__ = "UChromaAnimationPage"

    def __init__(self):
        super().__init__()

        self._device = None
        self._layers = []
        self._selected_layer = None
        self._pending_tasks: set[asyncio.Task] = set()

        self.set_title("Animation")
        self.set_icon_name("media-playlist-repeat-symbolic")

        self._build_ui()

    def _build_ui(self):
        """Build the animation page UI."""
        # === LAYERS GROUP ===
        self.layers_group = Adw.PreferencesGroup()
        self.layers_group.set_title("ANIMATION LAYERS")
        self.layers_group.set_description("Stack renderers to create complex effects")
        self.add(self.layers_group)

        # Layers list
        self.layers_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.layers_box.add_css_class("layer-list")

        # Empty state
        self.empty_state = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.empty_state.set_margin_top(24)
        self.empty_state.set_margin_bottom(24)
        self.empty_state.set_halign(Gtk.Align.CENTER)

        empty_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        empty_icon.set_pixel_size(48)
        empty_icon.add_css_class("dim")
        self.empty_state.append(empty_icon)

        empty_label = Gtk.Label(label="No animation layers")
        empty_label.add_css_class("dim")
        self.empty_state.append(empty_label)

        self.layers_box.append(self.empty_state)

        # Wrapper with padding
        layers_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        layers_wrapper.set_margin_start(4)
        layers_wrapper.set_margin_end(4)
        layers_wrapper.set_margin_top(8)
        layers_wrapper.set_margin_bottom(8)
        layers_wrapper.append(self.layers_box)
        self.layers_group.add(layers_wrapper)

        # Add layer button
        add_btn_row = Adw.ActionRow()
        add_btn_row.set_title("Add Layer")
        add_btn_row.set_subtitle("Add a new animation renderer")

        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("circular")
        add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add_layer_clicked)
        add_btn_row.add_suffix(add_btn)

        self.layers_group.add(add_btn_row)

        # === LAYER SETTINGS GROUP ===
        self.settings_group = Adw.PreferencesGroup()
        self.settings_group.set_title("LAYER SETTINGS")
        self.settings_group.set_visible(False)
        self.add(self.settings_group)

        # Placeholder for layer-specific settings
        self.settings_placeholder = Adw.ActionRow()
        self.settings_placeholder.set_title("Select a layer to edit its settings")
        self.settings_placeholder.add_css_class("dim")
        self.settings_group.add(self.settings_placeholder)

        # === PLAYBACK CONTROLS GROUP ===
        self.playback_group = Adw.PreferencesGroup()
        self.playback_group.set_title("PLAYBACK")
        self.add(self.playback_group)

        playback_row = Adw.ActionRow()
        playback_row.set_title("Animation Control")

        # Control buttons box
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_box.add_css_class("playback-controls")
        controls_box.set_valign(Gtk.Align.CENTER)

        # Play button
        self.play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self.play_btn.add_css_class("playback-button")
        self.play_btn.add_css_class("play")
        self.play_btn.set_tooltip_text("Start animation")
        self.play_btn.connect("clicked", self._on_play_clicked)
        controls_box.append(self.play_btn)

        # Pause button
        self.pause_btn = Gtk.Button.new_from_icon_name("media-playback-pause-symbolic")
        self.pause_btn.add_css_class("playback-button")
        self.pause_btn.add_css_class("pause")
        self.pause_btn.set_tooltip_text("Pause animation")
        self.pause_btn.connect("clicked", self._on_pause_clicked)
        controls_box.append(self.pause_btn)

        # Stop button
        self.stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
        self.stop_btn.add_css_class("playback-button")
        self.stop_btn.add_css_class("stop")
        self.stop_btn.set_tooltip_text("Stop and clear all layers")
        self.stop_btn.connect("clicked", self._on_stop_clicked)
        controls_box.append(self.stop_btn)

        playback_row.add_suffix(controls_box)

        # FPS indicator
        self.fps_label = Gtk.Label(label="15 FPS")
        self.fps_label.add_css_class("fps-indicator")
        self.fps_label.set_margin_start(16)
        playback_row.add_suffix(self.fps_label)

        self.playback_group.add(playback_row)

        # Animation state row
        state_row = Adw.ActionRow()
        state_row.set_title("Status")

        self.state_label = Gtk.Label(label="Stopped")
        self.state_label.add_css_class("dim")
        state_row.add_suffix(self.state_label)

        self.playback_group.add(state_row)

    def set_device(self, device):
        """Set the current device."""
        self._device = device
        self._refresh_layers()

        if device:
            device.connect("notify::is-animating", self._on_animation_state_changed)
            self._update_state_display()

    def _refresh_layers(self):
        """Refresh the layer list from device state."""
        # Clear existing layers
        for layer in self._layers:
            self.layers_box.remove(layer)
        self._layers.clear()

        # TODO: Load current layers from device
        # For now, show empty state
        self.empty_state.set_visible(len(self._layers) == 0)
        self.settings_group.set_visible(False)

    def _on_add_layer_clicked(self, button):
        """Show renderer picker dialog."""
        dialog = Adw.MessageDialog.new(
            self.get_root(), "Add Animation Layer", "Choose a renderer to add:"
        )

        # Add renderer options
        for renderer in RENDERERS:
            dialog.add_response(renderer["id"], renderer["name"])

        dialog.add_response("cancel", "Cancel")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        dialog.connect("response", self._on_renderer_chosen)
        dialog.present()

    def _on_renderer_chosen(self, dialog, response):
        """Handle renderer selection."""
        if response == "cancel":
            return

        renderer_id = response
        renderer_data = next((r for r in RENDERERS if r["id"] == renderer_id), None)
        if not renderer_data:
            return

        # Add layer to UI
        zindex = len(self._layers)
        layer_row = LayerRow(renderer_data["name"], zindex)
        layer_row.connect("delete-requested", self._on_layer_delete, layer_row)
        layer_row.connect("selected", self._on_layer_selected, layer_row)

        self.layers_box.append(layer_row)
        self._layers.append(layer_row)

        self.empty_state.set_visible(False)

        # Add to device
        if self._device:
            app = self.get_root().get_application()
            if app:
                self._schedule_task(app.dbus.add_renderer(self._device.path, renderer_id, zindex))

    def _schedule_task(self, coro):
        """Schedule an async task and track it to prevent GC."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def _on_layer_delete(self, layer_row, row):
        """Handle layer deletion."""
        zindex = self._layers.index(row)
        self.layers_box.remove(row)
        self._layers.remove(row)

        # Update zindex for remaining layers
        for i, layer in enumerate(self._layers):
            layer.zindex = i
            layer._zindex_label.set_label(str(i))

        self.empty_state.set_visible(len(self._layers) == 0)

        if self._selected_layer is row:
            self._selected_layer = None
            self.settings_group.set_visible(False)

        # Remove from device
        if self._device:
            app = self.get_root().get_application()
            if app:
                self._schedule_task(app.dbus.remove_renderer(self._device.path, zindex))

    def _on_layer_selected(self, layer_row, row):
        """Handle layer selection."""
        # Deselect previous
        if self._selected_layer:
            self._selected_layer.selected = False

        self._selected_layer = row
        row.selected = True

        # Show settings (placeholder for now)
        self.settings_group.set_visible(True)
        # TODO: Build layer-specific settings

    def _on_play_clicked(self, button):
        """Start animation."""
        # Animation starts automatically when layers are added

    def _on_pause_clicked(self, button):
        """Toggle pause."""
        # TODO: Implement via D-Bus

    def _on_stop_clicked(self, button):
        """Stop and clear all layers."""
        if self._device:
            app = self.get_root().get_application()
            if app:
                self._schedule_task(app.dbus.stop_animation(self._device.path))

        # Clear UI
        for layer in self._layers[:]:
            self.layers_box.remove(layer)
        self._layers.clear()
        self.empty_state.set_visible(True)
        self._selected_layer = None
        self.settings_group.set_visible(False)

    def _on_animation_state_changed(self, device, pspec):
        """Handle animation state change."""
        self._update_state_display()

    def _update_state_display(self):
        """Update the state label."""
        if not self._device:
            self.state_label.set_label("Stopped")
            self.state_label.add_css_class("dim")
            self.state_label.remove_css_class("cyan")
            return

        if self._device.is_animating:
            self.state_label.set_label("Running")
            self.state_label.remove_css_class("dim")
            self.state_label.add_css_class("cyan")
        else:
            self.state_label.set_label("Stopped")
            self.state_label.add_css_class("dim")
            self.state_label.remove_css_class("cyan")
