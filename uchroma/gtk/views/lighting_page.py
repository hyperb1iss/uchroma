"""
Lighting Page

Unified lighting control with mode switcher for Hardware Effects vs Custom Animation.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GObject, Gtk

# Hardware effects with metadata
HARDWARE_EFFECTS = [
    {
        "id": "disable",
        "name": "Off",
        "description": "Turn off all lighting",
        "icon": "system-shutdown-symbolic",
        "preview_class": "off",
        "params": [],
    },
    {
        "id": "static",
        "name": "Static",
        "description": "Solid color across all keys",
        "icon": "color-select-symbolic",
        "preview_class": "static",
        "params": [
            {"name": "color", "type": "color", "label": "Color", "default": "#e135ff"},
        ],
    },
    {
        "id": "wave",
        "name": "Wave",
        "description": "Flowing wave of colors",
        "icon": "weather-windy-symbolic",
        "preview_class": "wave",
        "params": [
            {
                "name": "direction",
                "type": "choice",
                "label": "Direction",
                "options": ["LEFT", "RIGHT"],
                "default": "RIGHT",
            },
            {"name": "speed", "type": "range", "label": "Speed", "min": 1, "max": 4, "default": 2},
        ],
    },
    {
        "id": "spectrum",
        "name": "Spectrum",
        "description": "Cycle through all colors",
        "icon": "weather-clear-symbolic",
        "preview_class": "spectrum",
        "params": [],
    },
    {
        "id": "reactive",
        "name": "Reactive",
        "description": "Keys light up when pressed",
        "icon": "input-keyboard-symbolic",
        "preview_class": "reactive",
        "params": [
            {"name": "color", "type": "color", "label": "Color", "default": "#80ffea"},
            {"name": "speed", "type": "range", "label": "Speed", "min": 1, "max": 4, "default": 2},
        ],
    },
    {
        "id": "breathe",
        "name": "Breathe",
        "description": "Pulsing color effect",
        "icon": "weather-fog-symbolic",
        "preview_class": "breathe",
        "params": [
            {"name": "color1", "type": "color", "label": "Color 1", "default": "#e135ff"},
            {"name": "color2", "type": "color", "label": "Color 2", "default": "#80ffea"},
            {"name": "speed", "type": "range", "label": "Speed", "min": 1, "max": 4, "default": 2},
        ],
    },
    {
        "id": "starlight",
        "name": "Starlight",
        "description": "Twinkling stars effect",
        "icon": "starred-symbolic",
        "preview_class": "starlight",
        "params": [
            {"name": "color1", "type": "color", "label": "Color 1", "default": "#e135ff"},
            {"name": "color2", "type": "color", "label": "Color 2", "default": "#80ffea"},
            {"name": "speed", "type": "range", "label": "Speed", "min": 1, "max": 4, "default": 2},
        ],
    },
]

# Custom animation renderers with metadata
RENDERERS = [
    {
        "id": "uchroma.fxlib.plasma.Plasma",
        "name": "Plasma",
        "description": "Colorful moving blobs of plasma",
        "icon": "weather-fog-symbolic",
        "params": [
            {"name": "background", "type": "color", "label": "Background", "default": "#000000"},
            {"name": "color1", "type": "color", "label": "Color 1", "default": "#e135ff"},
            {"name": "color2", "type": "color", "label": "Color 2", "default": "#80ffea"},
            {"name": "color3", "type": "color", "label": "Color 3", "default": "#ff6ac1"},
            {"name": "color4", "type": "color", "label": "Color 4", "default": "#f1fa8c"},
        ],
    },
    {
        "id": "uchroma.fxlib.rainbow.Rainbow",
        "name": "Rainflow",
        "description": "Simple flowing colors",
        "icon": "weather-clear-symbolic",
        "params": [
            {
                "name": "speed",
                "type": "range",
                "label": "Speed",
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "default": 1.0,
            },
            {
                "name": "saturation",
                "type": "range",
                "label": "Saturation",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 1.0,
            },
        ],
    },
    {
        "id": "uchroma.fxlib.ripple.Ripple",
        "name": "Ripples",
        "description": "Ripples of color when keys are pressed",
        "icon": "emblem-synchronizing-symbolic",
        "params": [
            {"name": "color", "type": "color", "label": "Ripple Color", "default": "#ff6ac1"},
            {
                "name": "speed",
                "type": "range",
                "label": "Speed",
                "min": 0.5,
                "max": 3.0,
                "step": 0.1,
                "default": 1.5,
            },
        ],
    },
    {
        "id": "uchroma.fxlib.reaction.Reaction",
        "name": "Reaction",
        "description": "Keys change color when pressed",
        "icon": "input-keyboard-symbolic",
        "params": [
            {"name": "color", "type": "color", "label": "Press Color", "default": "#80ffea"},
            {
                "name": "fade_time",
                "type": "range",
                "label": "Fade Time",
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "default": 0.5,
            },
        ],
    },
]

BLEND_MODES = [
    "normal",
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


class EffectCard(Gtk.FlowBoxChild):
    """Visual card for effect selection."""

    __gtype_name__ = "UChromaEffectCard"

    def __init__(self, effect_data):
        super().__init__()
        self.effect_data = effect_data
        self.effect_id = effect_data["id"]
        self._build_ui()

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("effect-card")
        box.set_size_request(140, 100)

        icon = Gtk.Image.new_from_icon_name(self.effect_data["icon"])
        icon.add_css_class("effect-icon")
        icon.set_pixel_size(32)
        box.append(icon)

        name = Gtk.Label(label=self.effect_data["name"])
        name.add_css_class("effect-name")
        box.append(name)

        preview = Gtk.Box()
        preview.add_css_class("effect-preview")
        preview.add_css_class(self.effect_data.get("preview_class", "default"))
        box.append(preview)

        self.set_child(box)

    def set_active(self, active: bool):
        if active:
            self.get_child().add_css_class("active")
        else:
            self.get_child().remove_css_class("active")


class LayerRow(Gtk.Box):
    """A single layer in the animation stack."""

    __gtype_name__ = "UChromaLayerRow"

    __gsignals__ = {
        "delete-requested": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "selected": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "blend-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "opacity-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
    }

    def __init__(self, renderer_data: dict, zindex: int):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.renderer_data = renderer_data
        self.renderer_id = renderer_data["id"]
        self.renderer_name = renderer_data["name"]
        self.zindex = zindex
        self._selected = False
        self._blend_mode = "normal"
        self._opacity = 1.0

        self.add_css_class("layer-row")
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._build_ui()

    def _build_ui(self):
        handle = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        handle.add_css_class("layer-handle")
        self.append(handle)

        zindex_label = Gtk.Label(label=str(self.zindex))
        zindex_label.add_css_class("layer-zindex")
        self.append(zindex_label)
        self._zindex_label = zindex_label

        name_label = Gtk.Label(label=self.renderer_name)
        name_label.add_css_class("layer-name")
        name_label.set_hexpand(True)
        name_label.set_xalign(0)
        self.append(name_label)

        blend_dropdown = Gtk.DropDown.new_from_strings(BLEND_MODES)
        blend_dropdown.add_css_class("layer-blend-dropdown")
        blend_dropdown.set_valign(Gtk.Align.CENTER)
        blend_dropdown.connect("notify::selected", self._on_blend_changed)
        self.append(blend_dropdown)
        self._blend_dropdown = blend_dropdown

        opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        opacity_scale.add_css_class("layer-opacity-scale")
        opacity_scale.set_value(1.0)
        opacity_scale.set_draw_value(False)
        opacity_scale.set_valign(Gtk.Align.CENTER)
        opacity_scale.set_size_request(80, -1)
        opacity_scale.connect("value-changed", self._on_opacity_changed)
        self.append(opacity_scale)
        self._opacity_scale = opacity_scale

        delete_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        delete_btn.add_css_class("layer-delete-button")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("circular")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.connect("clicked", lambda *_: self.emit("delete-requested"))
        self.append(delete_btn)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_clicked)
        self.add_controller(click)

    def _on_clicked(self, gesture, n_press, x, y):
        self.emit("selected")

    def _on_blend_changed(self, dropdown, pspec):
        idx = dropdown.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            self._blend_mode = BLEND_MODES[idx]
            self.emit("blend-changed", self._blend_mode)

    def _on_opacity_changed(self, scale):
        self._opacity = scale.get_value()
        self.emit("opacity-changed", self._opacity)

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

    def update_zindex(self, zindex: int):
        self.zindex = zindex
        self._zindex_label.set_label(str(zindex))


class LightingPage(Adw.PreferencesPage):
    """Unified lighting control page."""

    __gtype_name__ = "UChromaLightingPage"

    MODE_HARDWARE = "hardware"
    MODE_CUSTOM = "custom"

    def __init__(self):
        super().__init__()

        self._device = None
        self._current_mode = self.MODE_HARDWARE
        self._current_effect = None
        self._effect_cards = {}
        self._param_widgets = {}
        self._layers = []
        self._selected_layer = None

        self.set_title("Lighting")
        self.set_icon_name("starred-symbolic")

        self._build_ui()

    def _build_ui(self):
        # === MODE SWITCHER ===
        self.mode_group = Adw.PreferencesGroup()
        self.add(self.mode_group)

        mode_row = Adw.ActionRow()
        mode_row.set_title("Lighting Mode")
        mode_row.set_subtitle(
            "Hardware effects run on device, custom animation is software-rendered"
        )

        # Segmented button for mode switching
        self.mode_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.mode_button.add_css_class("linked")
        self.mode_button.set_valign(Gtk.Align.CENTER)

        self.hw_btn = Gtk.ToggleButton(label="Hardware FX")
        self.hw_btn.set_active(True)
        self.hw_btn.add_css_class("mode-toggle")
        self.hw_btn.connect("toggled", self._on_mode_toggled, self.MODE_HARDWARE)
        self.mode_button.append(self.hw_btn)

        self.custom_btn = Gtk.ToggleButton(label="Custom Animation")
        self.custom_btn.set_group(self.hw_btn)
        self.custom_btn.add_css_class("mode-toggle")
        self.custom_btn.connect("toggled", self._on_mode_toggled, self.MODE_CUSTOM)
        self.mode_button.append(self.custom_btn)

        mode_row.add_suffix(self.mode_button)
        self.mode_group.add(mode_row)

        # === HARDWARE EFFECTS SECTION ===
        self._build_hardware_ui()

        # === CUSTOM ANIMATION SECTION ===
        self._build_animation_ui()

        # Show initial mode
        self._update_mode_visibility()

    def _build_hardware_ui(self):
        """Build hardware effects UI."""
        # Effects grid
        self.effects_group = Adw.PreferencesGroup()
        self.effects_group.set_title("EFFECTS")
        self.effects_group.set_description("Built-in hardware lighting effects")
        self.add(self.effects_group)

        self.effects_flow = Gtk.FlowBox()
        self.effects_flow.set_homogeneous(True)
        self.effects_flow.set_min_children_per_line(2)
        self.effects_flow.set_max_children_per_line(4)
        self.effects_flow.set_column_spacing(12)
        self.effects_flow.set_row_spacing(12)
        self.effects_flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.effects_flow.connect("child-activated", self._on_effect_selected)

        for effect in HARDWARE_EFFECTS:
            card = EffectCard(effect)
            self.effects_flow.append(card)
            self._effect_cards[effect["id"]] = card

        flow_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        flow_wrapper.set_margin_start(12)
        flow_wrapper.set_margin_end(12)
        flow_wrapper.set_margin_top(12)
        flow_wrapper.set_margin_bottom(12)
        flow_wrapper.append(self.effects_flow)
        self.effects_group.add(flow_wrapper)

        # Effect parameters
        self.effect_params_group = Adw.PreferencesGroup()
        self.effect_params_group.set_title("EFFECT SETTINGS")
        self.effect_params_group.set_visible(False)
        self.add(self.effect_params_group)

    def _build_animation_ui(self):
        """Build custom animation UI."""
        # Layers list
        self.layers_group = Adw.PreferencesGroup()
        self.layers_group.set_title("ANIMATION LAYERS")
        self.layers_group.set_description("Stack renderers with blend modes and opacity")
        self.add(self.layers_group)

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

        layers_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        layers_wrapper.set_margin_start(4)
        layers_wrapper.set_margin_end(4)
        layers_wrapper.set_margin_top(8)
        layers_wrapper.set_margin_bottom(8)
        layers_wrapper.append(self.layers_box)
        self.layers_group.add(layers_wrapper)

        # Add layer button
        add_row = Adw.ActionRow()
        add_row.set_title("Add Layer")
        add_row.set_subtitle("Choose a renderer to add to the stack")
        add_row.set_activatable(True)
        add_row.connect("activated", self._on_add_layer_clicked)

        add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        add_row.add_suffix(add_icon)
        self.layers_group.add(add_row)

        # Layer settings
        self.layer_settings_group = Adw.PreferencesGroup()
        self.layer_settings_group.set_title("LAYER SETTINGS")
        self.layer_settings_group.set_visible(False)
        self.add(self.layer_settings_group)

        # Playback controls
        self.playback_group = Adw.PreferencesGroup()
        self.playback_group.set_title("PLAYBACK")
        self.add(self.playback_group)

        playback_row = Adw.ActionRow()
        playback_row.set_title("Animation Control")

        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_box.add_css_class("playback-controls")
        controls_box.set_valign(Gtk.Align.CENTER)

        self.play_btn = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self.play_btn.add_css_class("playback-button")
        self.play_btn.add_css_class("suggested-action")
        self.play_btn.set_tooltip_text("Start animation")
        self.play_btn.connect("clicked", self._on_play_clicked)
        controls_box.append(self.play_btn)

        self.stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
        self.stop_btn.add_css_class("playback-button")
        self.stop_btn.add_css_class("destructive-action")
        self.stop_btn.set_tooltip_text("Stop and clear all layers")
        self.stop_btn.connect("clicked", self._on_stop_clicked)
        controls_box.append(self.stop_btn)

        playback_row.add_suffix(controls_box)

        self.state_label = Gtk.Label(label="Stopped")
        self.state_label.add_css_class("dim")
        self.state_label.set_margin_start(16)
        playback_row.add_suffix(self.state_label)

        self.playback_group.add(playback_row)

        # FPS control
        fps_row = Adw.SpinRow.new_with_range(1, 60, 1)
        fps_row.set_title("Frame Rate")
        fps_row.set_subtitle("Frames per second")
        fps_row.set_value(30)
        self.fps_row = fps_row
        self.playback_group.add(fps_row)

    def _on_mode_toggled(self, button, mode):
        """Handle mode toggle."""
        if not button.get_active():
            return

        self._current_mode = mode
        self._update_mode_visibility()

        # Stop animation when switching to hardware mode
        if mode == self.MODE_HARDWARE and self._device:
            self._stop_animation()

    def _update_mode_visibility(self):
        """Show/hide sections based on current mode."""
        is_hardware = self._current_mode == self.MODE_HARDWARE

        # Hardware sections
        self.effects_group.set_visible(is_hardware)
        self.effect_params_group.set_visible(is_hardware and self._current_effect is not None)

        # Animation sections
        self.layers_group.set_visible(not is_hardware)
        self.layer_settings_group.set_visible(not is_hardware and self._selected_layer is not None)
        self.playback_group.set_visible(not is_hardware)

    def set_device(self, device):
        """Set the current device."""
        self._device = device

        if device:
            if device.current_fx and device.current_fx in self._effect_cards:
                self._select_effect(device.current_fx)

            device.connect("notify::is-animating", self._on_animation_state_changed)
            self._update_state_display()

    # === HARDWARE EFFECTS ===

    def _on_effect_selected(self, flow_box, child):
        if not child:
            return
        effect_id = child.effect_id
        self._select_effect(effect_id)
        if self._device:
            self._apply_effect(effect_id)

    def _select_effect(self, effect_id: str):
        for eid, card in self._effect_cards.items():
            card.set_active(eid == effect_id)
        self._current_effect = effect_id
        self._build_effect_params(effect_id)

    def _build_effect_params(self, effect_id: str):
        """Build parameter controls for selected effect."""
        # Clear existing
        child = self.effect_params_group.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.effect_params_group.remove(child)
            child = next_child

        self._param_widgets.clear()

        effect_data = next((e for e in HARDWARE_EFFECTS if e["id"] == effect_id), None)
        if not effect_data or not effect_data["params"]:
            self.effect_params_group.set_visible(False)
            return

        self.effect_params_group.set_visible(True)

        for param in effect_data["params"]:
            row = self._create_param_row(param, self._on_effect_param_changed)
            if row:
                self.effect_params_group.add(row)

    def _on_effect_param_changed(self, widget, pspec, param_name):
        """Handle effect parameter change."""
        if not self._device or not self._current_effect:
            return
        params = self._collect_effect_params()
        self._apply_effect(self._current_effect, params)

    def _collect_effect_params(self) -> dict:
        """Collect current effect parameter values."""
        params = {}
        for name, widget in self._param_widgets.items():
            if isinstance(widget, Gtk.ColorDialogButton):
                rgba = widget.get_rgba()
                params[name] = rgba.to_string()
            elif isinstance(widget, Adw.SpinRow):
                params[name] = widget.get_value()
            elif isinstance(widget, Adw.ComboRow):
                idx = widget.get_selected()
                if idx != Gtk.INVALID_LIST_POSITION:
                    params[name] = widget.get_model().get_string(idx)
        return params

    def _apply_effect(self, effect_id: str, params: dict = None):
        """Apply effect to device."""
        if not self._device:
            return
        app = self.get_root().get_application()
        if app:
            import asyncio

            asyncio.create_task(app.dbus.set_effect(self._device.path, effect_id, params))

    # === CUSTOM ANIMATION ===

    def _on_add_layer_clicked(self, row):
        """Show renderer picker."""
        dialog = Adw.MessageDialog.new(self.get_root(), "Add Animation Layer", "Choose a renderer:")

        for renderer in RENDERERS:
            dialog.add_response(renderer["id"], renderer["name"])

        dialog.add_response("cancel", "Cancel")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_renderer_chosen)
        dialog.present()

    def _on_renderer_chosen(self, dialog, response):
        if response == "cancel":
            return

        renderer_data = next((r for r in RENDERERS if r["id"] == response), None)
        if not renderer_data:
            return

        zindex = len(self._layers)
        layer_row = LayerRow(renderer_data, zindex)
        layer_row.connect("delete-requested", self._on_layer_delete, layer_row)
        layer_row.connect("selected", self._on_layer_selected, layer_row)
        layer_row.connect("blend-changed", self._on_layer_blend_changed, layer_row)
        layer_row.connect("opacity-changed", self._on_layer_opacity_changed, layer_row)

        self.layers_box.append(layer_row)
        self._layers.append(layer_row)
        self.empty_state.set_visible(False)

        if self._device:
            app = self.get_root().get_application()
            if app:
                import asyncio

                asyncio.create_task(app.dbus.add_renderer(self._device.path, response, zindex))

    def _on_layer_delete(self, layer_row, row):
        zindex = self._layers.index(row)
        self.layers_box.remove(row)
        self._layers.remove(row)

        for i, layer in enumerate(self._layers):
            layer.update_zindex(i)

        self.empty_state.set_visible(len(self._layers) == 0)

        if self._selected_layer is row:
            self._selected_layer = None
            self.layer_settings_group.set_visible(False)

        if self._device:
            app = self.get_root().get_application()
            if app:
                import asyncio

                asyncio.create_task(app.dbus.remove_renderer(self._device.path, zindex))

    def _on_layer_selected(self, layer_row, row):
        if self._selected_layer:
            self._selected_layer.selected = False

        self._selected_layer = row
        row.selected = True

        self._build_layer_settings(row)
        self.layer_settings_group.set_visible(True)

    def _on_layer_blend_changed(self, layer_row, blend_mode, row):
        # TODO: Update via D-Bus when API supports it
        pass

    def _on_layer_opacity_changed(self, layer_row, opacity, row):
        # TODO: Update via D-Bus when API supports it
        pass

    def _build_layer_settings(self, layer_row: LayerRow):
        """Build settings for selected layer."""
        # Clear existing
        child = self.layer_settings_group.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.layer_settings_group.remove(child)
            child = next_child

        renderer_data = layer_row.renderer_data

        # Layer info header
        info_row = Adw.ActionRow()
        info_row.set_title(renderer_data["name"])
        info_row.set_subtitle(renderer_data.get("description", ""))

        icon = Gtk.Image.new_from_icon_name(
            renderer_data.get("icon", "applications-graphics-symbolic")
        )
        info_row.add_prefix(icon)
        self.layer_settings_group.add(info_row)

        # Renderer parameters
        for param in renderer_data.get("params", []):
            row = self._create_param_row(param, self._on_layer_param_changed)
            if row:
                self.layer_settings_group.add(row)

    def _on_layer_param_changed(self, widget, pspec, param_name):
        """Handle layer parameter change."""
        # TODO: Update renderer params via D-Bus

    def _on_play_clicked(self, button):
        # Animation starts when layers are added
        self._update_state_display()

    def _on_stop_clicked(self, button):
        self._stop_animation()

    def _stop_animation(self):
        """Stop animation and clear layers."""
        if self._device:
            app = self.get_root().get_application()
            if app:
                import asyncio

                asyncio.create_task(app.dbus.stop_animation(self._device.path))

        for layer in self._layers[:]:
            self.layers_box.remove(layer)
        self._layers.clear()
        self.empty_state.set_visible(True)
        self._selected_layer = None
        self.layer_settings_group.set_visible(False)
        self._update_state_display()

    def _on_animation_state_changed(self, device, pspec):
        self._update_state_display()

    def _update_state_display(self):
        if not self._device:
            self.state_label.set_label("Stopped")
            self.state_label.add_css_class("dim")
            return

        if self._device.is_animating:
            self.state_label.set_label("Running")
            self.state_label.remove_css_class("dim")
            self.state_label.add_css_class("success")
        else:
            self.state_label.set_label("Stopped")
            self.state_label.add_css_class("dim")
            self.state_label.remove_css_class("success")

    # === SHARED UTILITIES ===

    def _create_param_row(self, param, callback) -> Gtk.Widget:
        """Create a row widget for a parameter."""
        label = param.get("label", param["name"].replace("_", " ").title())

        if param["type"] == "color":
            row = Adw.ActionRow()
            row.set_title(label)

            color_btn = Gtk.ColorDialogButton()
            color_btn.set_valign(Gtk.Align.CENTER)

            rgba = Gdk.RGBA()
            rgba.parse(param.get("default", "#ffffff"))
            color_btn.set_rgba(rgba)

            color_btn.connect("notify::rgba", callback, param["name"])
            row.add_suffix(color_btn)

            self._param_widgets[param["name"]] = color_btn
            return row

        elif param["type"] == "range":
            step = param.get("step", 1)
            row = Adw.SpinRow.new_with_range(param["min"], param["max"], step)
            row.set_title(label)
            row.set_value(param.get("default", param["min"]))
            row.connect("notify::value", callback, param["name"])

            self._param_widgets[param["name"]] = row
            return row

        elif param["type"] == "choice":
            row = Adw.ComboRow()
            row.set_title(label)

            model = Gtk.StringList.new(param["options"])
            row.set_model(model)

            default_idx = param["options"].index(param.get("default", param["options"][0]))
            row.set_selected(default_idx)

            row.connect("notify::selected", callback, param["name"])

            self._param_widgets[param["name"]] = row
            return row

        return None
