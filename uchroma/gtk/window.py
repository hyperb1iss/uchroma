"""
UChroma Main Window

Single-screen layout with matrix preview, mode toggle, and contextual panels.
"""

import asyncio

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .panels import EffectSelector, LayerPanel, ModeToggle, ParamInspector  # noqa: E402
from .param_utils import build_param_defs, extract_description, humanize_label, is_hidden_effect  # noqa: E402
from .services.preview_renderer import PreviewRenderer  # noqa: E402
from .widgets import BrightnessScale, MatrixPreview  # noqa: E402
from .widgets.effect_card import icon_for_effect, preview_for_effect  # noqa: E402


class UChromaWindow(Adw.ApplicationWindow):
    """Main application window."""

    __gtype_name__ = "UChromaWindow"

    MODE_HARDWARE = "hardware"
    MODE_CUSTOM = "custom"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("UChroma")
        self.set_default_size(900, 700)
        self.set_size_request(700, 550)

        self._device = None
        self._mode = self.MODE_HARDWARE
        self._selected_effect = None
        self._effect_params = {}
        self._effects = []
        self._effect_defs = {}
        self._renderers = []
        self._renderer_defs = {}
        self._anim_state = ""
        self._syncing_layers = False
        self._pending_tasks: set[asyncio.Task] = set()

        # Preview renderer
        self._preview_renderer = PreviewRenderer(rows=6, cols=22)
        self._preview_renderer.set_callback(self._on_preview_frame)

        self._build_ui()
        self._connect_signals()

        # Start preview
        self._preview_renderer.set_effect("spectrum", {})
        self._preview_renderer.start(30)

    def _build_ui(self):
        """Build the window UI."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.add_css_class("main-container")

        # === HEADER BAR ===
        header = self._build_header()
        main_box.append(header)

        # === CONTENT AREA ===
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.add_css_class("content-area")
        content.set_vexpand(True)

        # Matrix Preview
        preview_frame = Gtk.Box()
        preview_frame.add_css_class("preview-frame")
        preview_frame.set_halign(Gtk.Align.CENTER)
        preview_frame.set_margin_top(16)
        preview_frame.set_margin_bottom(16)

        self._matrix_preview = MatrixPreview(rows=6, cols=22)
        preview_frame.append(self._matrix_preview)
        content.append(preview_frame)

        # Mode Toggle
        self._mode_toggle = ModeToggle()
        content.append(self._mode_toggle)

        # Mode-specific content (Stack)
        self._mode_stack = Gtk.Stack()
        self._mode_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._mode_stack.set_transition_duration(150)
        self._mode_stack.set_vexpand(True)

        # Hardware FX mode
        hw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._effect_selector = EffectSelector()
        hw_box.append(self._effect_selector)
        self._mode_stack.add_named(hw_box, "hardware")

        # Custom Animation mode
        custom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._layer_panel = LayerPanel()
        custom_box.append(self._layer_panel)
        self._mode_stack.add_named(custom_box, "custom")

        content.append(self._mode_stack)

        # Parameter Inspector
        self._param_inspector = ParamInspector()
        content.append(self._param_inspector)

        main_box.append(content)
        self.set_content(main_box)

    def _build_header(self) -> Adw.HeaderBar:
        """Build the header bar."""
        header = Adw.HeaderBar()
        header.add_css_class("flat")

        # Left side: Device selector
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self._device_dropdown = Gtk.DropDown()
        self._device_dropdown.add_css_class("device-dropdown")
        self._device_dropdown.set_size_request(180, -1)

        # Placeholder model
        self._device_model = Gtk.StringList.new(["No device"])
        self._device_dropdown.set_model(self._device_model)
        self._device_dropdown.connect("notify::selected", self._on_device_selected)

        device_box.append(self._device_dropdown)
        header.pack_start(device_box)

        # Center: Title
        title = Adw.WindowTitle(title="UChroma", subtitle="")
        header.set_title_widget(title)
        self._window_title = title

        # Right side: Brightness + Power + Settings
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Brightness
        self._brightness = BrightnessScale()
        self._brightness.connect("value-changed", self._on_brightness_changed)
        controls_box.append(self._brightness)

        # Power toggle
        self._power_btn = Gtk.ToggleButton()
        self._power_btn.set_icon_name("system-shutdown-symbolic")
        self._power_btn.add_css_class("power-toggle")
        self._power_btn.add_css_class("circular")
        self._power_btn.set_tooltip_text("Suspend lighting")
        self._power_btn.connect("toggled", self._on_power_toggled)
        controls_box.append(self._power_btn)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        controls_box.append(sep)

        # Settings button
        settings_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.set_action_name("app.settings")
        controls_box.append(settings_btn)

        header.pack_end(controls_box)

        return header

    def _connect_signals(self):
        """Connect widget signals."""
        # Mode toggle
        self._mode_toggle.connect("mode-changed", self._on_mode_changed)

        # Effect selector
        self._effect_selector.connect("effect-selected", self._on_effect_selected)

        # Layer panel
        self._layer_panel.connect("layer-added", self._on_layer_added)
        self._layer_panel.connect("layer-removed", self._on_layer_removed)
        self._layer_panel.connect("layer-selected", self._on_layer_selected)
        self._layer_panel.connect("layer-changed", self._on_layer_changed)
        self._layer_panel.connect("play-clicked", self._on_play_clicked)
        self._layer_panel.connect("stop-clicked", self._on_stop_clicked)

        # Parameter inspector
        self._param_inspector.connect("param-changed", self._on_param_changed)

    # === DEVICE MANAGEMENT ===

    def set_device(self, device):
        """Set the current device."""
        self._device = device

        if device:
            self._window_title.set_subtitle(device.name)

            # Update preview size from device
            if getattr(device, "has_matrix", False):
                rows = getattr(device, "height", 0)
                cols = getattr(device, "width", 0)
                if rows and cols:
                    self._matrix_preview.set_matrix_size(rows, cols)
                    self._preview_renderer.set_size(rows, cols)

            # Update brightness
            if hasattr(device, "brightness"):
                self._brightness.value = device.brightness

            self._schedule_task(self._load_device_state())
        else:
            self._window_title.set_subtitle("")

    def update_device_list(self, devices: list):
        """Update the device dropdown."""
        if not devices:
            self._device_model = Gtk.StringList.new(["No device"])
        else:
            names = [d.name for d in devices]
            self._device_model = Gtk.StringList.new(names)

        self._device_dropdown.set_model(self._device_model)

    def _on_device_selected(self, dropdown, pspec):
        """Handle device selection from dropdown."""
        idx = dropdown.get_selected()
        app = self.get_application()
        if app and hasattr(app, "device_store") and idx < len(app.device_store):  # type: ignore[arg-type]
            device = app.device_store.get_item(idx)
            self.set_device(device)

    async def _load_device_state(self):
        """Fetch effects, renderers, and current animation state."""
        if not self._device:
            return

        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        path = self._device.path
        available_fx = await app.dbus.get_available_fx(path)
        available_renderers = await app.dbus.get_available_renderers(path)
        current_fx = await app.dbus.get_current_fx(path)
        current_renderers = await app.dbus.get_current_renderers(path)
        anim_state = await app.dbus.get_animation_state(path)

        layer_infos = []
        for renderer_id, layer_path in current_renderers:
            zindex = self._layer_zindex_from_path(layer_path)
            info = await app.dbus.get_layer_info(path, zindex)
            layer_infos.append((renderer_id, zindex, info))

        GLib.idle_add(
            self._apply_device_state,
            available_fx,
            available_renderers,
            current_fx,
            layer_infos,
            anim_state,
        )

    def _apply_device_state(
        self,
        available_fx: dict,
        available_renderers: dict,
        current_fx,
        layer_infos: list[tuple[str, int, dict]],
        anim_state: str,
    ) -> bool:
        self._effects = self._build_effect_defs(available_fx)
        self._effect_defs = {e["id"]: e for e in self._effects}
        self._effect_selector.set_effects(self._effects)

        self._renderers = self._build_renderer_defs(available_renderers)
        self._renderer_defs = {r["id"]: r for r in self._renderers}
        self._layer_panel.set_renderers(self._renderers)

        self._apply_current_effect(current_fx)
        self._apply_current_layers(layer_infos)

        self._anim_state = anim_state or ""
        self._update_mode_status()
        return False

    def _build_effect_defs(self, available_fx: dict) -> list[dict]:
        effects = []
        for fx_name, traits in available_fx.items():
            if is_hidden_effect(traits):
                continue
            effects.append(
                {
                    "id": fx_name,
                    "name": humanize_label(fx_name),
                    "description": extract_description(traits) or "",
                    "icon": icon_for_effect(fx_name),
                    "preview": preview_for_effect(fx_name),
                    "params": build_param_defs(traits),
                }
            )
        effects.sort(key=lambda e: (0 if e["id"] == "disable" else 1, e["name"].lower()))
        return effects

    def _renderer_icon_for(self, renderer_id: str) -> str:
        renderer_id = renderer_id.lower()
        if "plasma" in renderer_id:
            return "weather-fog-symbolic"
        if "rainbow" in renderer_id or "rainflow" in renderer_id:
            return "weather-clear-symbolic"
        if "ripple" in renderer_id:
            return "emblem-synchronizing-symbolic"
        if "reaction" in renderer_id or "typewriter" in renderer_id:
            return "input-keyboard-symbolic"
        if "vortex" in renderer_id:
            return "media-playlist-repeat-symbolic"
        if "nebula" in renderer_id or "aurora" in renderer_id:
            return "weather-showers-symbolic"
        return "applications-graphics-symbolic"

    def _build_renderer_defs(self, available_renderers: dict) -> list[dict]:
        renderers = []
        for renderer_id, payload in available_renderers.items():
            meta = payload.get("meta", {})
            traits = payload.get("traits", {})
            renderers.append(
                {
                    "id": renderer_id,
                    "name": meta.get("display_name") or humanize_label(renderer_id.split(".")[-1]),
                    "description": meta.get("description", ""),
                    "icon": self._renderer_icon_for(renderer_id),
                    "params": build_param_defs(
                        traits,
                        exclude={"blend_mode", "opacity", "width", "height", "zindex", "running"},
                    ),
                }
            )
        renderers.sort(key=lambda r: r["name"].lower())
        return renderers

    def _layer_zindex_from_path(self, path: str) -> int:
        try:
            return int(str(path).rstrip("/").split("/")[-1])
        except (ValueError, AttributeError):
            return -1

    def _apply_current_effect(self, current_fx):
        fx_name = ""
        fx_params = {}
        if isinstance(current_fx, (list, tuple)) and len(current_fx) >= 2:
            fx_name = current_fx[0] or ""
            fx_params = current_fx[1] or {}

        self._selected_effect = fx_name or None
        self._effect_params = fx_params or {}

        if self._selected_effect and self._selected_effect in self._effect_defs:
            effect_data = self._effect_defs[self._selected_effect]
            self._effect_selector.select_effect(self._selected_effect)
            if self._mode == self.MODE_HARDWARE:
                self._param_inspector.set_params(
                    effect_data.get("params", []),
                    f"{effect_data['name'].upper()} SETTINGS",
                    self._effect_params,
                )
                self._preview_renderer.set_effect(self._selected_effect, self._effect_params)
        elif self._mode == self.MODE_HARDWARE:
            self._param_inspector.clear()
            self._preview_renderer.set_effect("disable", {})

    def _apply_current_layers(self, layer_infos: list[tuple[str, int, dict]]):
        self._syncing_layers = True
        try:
            self._layer_panel.clear()
            for renderer_id, zindex, info in sorted(layer_infos, key=lambda x: x[1]):
                renderer_data = self._renderer_defs.get(renderer_id)
                renderer_name = (
                    renderer_data.get("name")
                    if renderer_data
                    else humanize_label(renderer_id.split(".")[-1])
                )
                row = self._layer_panel.add_layer(renderer_id, renderer_name)
                if info.get("blend_mode"):
                    row.blend_mode = str(info.get("blend_mode"))
                if info.get("opacity") is not None:
                    row.opacity = float(info.get("opacity"))
        finally:
            self._syncing_layers = False

    def _update_mode_status(self):
        if self._mode == self.MODE_HARDWARE:
            if self._selected_effect and self._selected_effect in self._effect_defs:
                effect_data = self._effect_defs[self._selected_effect]
                self._mode_toggle.set_status(
                    effect_data["name"], self._selected_effect != "disable"
                )
            else:
                self._mode_toggle.set_status("No effect", False)
            return

        if not self._layer_panel.layers:
            self._mode_toggle.set_status("No layers", False)
            return

        if self._anim_state == "paused":
            self._mode_toggle.set_status("Paused", False)
        else:
            self._mode_toggle.set_status("Running", True)

    # === MODE SWITCHING ===

    def _on_mode_changed(self, toggle, mode):
        """Handle mode change."""
        self._mode = mode
        self._mode_stack.set_visible_child_name(mode)

        if mode == self.MODE_HARDWARE:
            # Show effect params if effect selected
            if self._selected_effect:
                effect_data = self._effect_defs.get(self._selected_effect)
                if effect_data:
                    self._param_inspector.set_params(
                        effect_data.get("params", []),
                        f"{effect_data['name'].upper()} SETTINGS",
                        self._effect_params,
                    )
                self._preview_renderer.set_effect(self._selected_effect, self._effect_params)
            else:
                self._param_inspector.clear()
                self._preview_renderer.set_effect("disable", {})
            self._update_mode_status()

        else:
            # Custom mode - show layer params or empty
            if self._layer_panel.selected_layer:
                self._show_layer_params(self._layer_panel.selected_layer)
            else:
                self._param_inspector.clear()
            if self._layer_panel.layers:
                self._preview_renderer.set_effect("plasma", {})
            else:
                self._preview_renderer.set_effect("disable", {})
            self._update_mode_status()

    # === HARDWARE FX ===

    def _on_effect_selected(self, selector, effect_id):
        """Handle effect card selection."""
        self._selected_effect = effect_id
        effect_data = self._effect_defs.get(effect_id)

        if effect_data:
            # Update preview
            self._preview_renderer.set_effect(effect_id, self._effect_params)

            # Show params
            self._param_inspector.set_params(
                effect_data.get("params", []),
                f"{effect_data['name'].upper()} SETTINGS",
                self._effect_params,
            )
            self._effect_params = self._param_inspector.get_values()

            # Update status
            self._mode_toggle.set_status(effect_data["name"], effect_id != "disable")

            # Apply to device
            self._apply_effect_to_device(effect_id)

    def _apply_effect_to_device(self, effect_id: str):
        """Apply effect to device via D-Bus."""
        if not self._device:
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            params = self._param_inspector.get_values()
            self._schedule_task(app.dbus.set_effect(self._device.path, effect_id, params))

    # === CUSTOM ANIMATION ===

    def _on_layer_added(self, panel, renderer_id):
        """Handle layer added."""
        renderer_data = self._renderer_defs.get(renderer_id)
        renderer_name = (
            renderer_data.get("name")
            if renderer_data
            else humanize_label(renderer_id.split(".")[-1])
        )
        row = panel.add_layer(renderer_id, renderer_name)

        # Apply to device
        if self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                zindex = len(panel.layers) - 1
                self._schedule_task(app.dbus.add_renderer(self._device.path, renderer_id, zindex))

        # Update preview for custom animation
        self._preview_renderer.set_effect("plasma", {})

        # Update status
        self._anim_state = "running"
        self._update_mode_status()
        self._show_layer_params(row)

    def _on_layer_removed(self, panel, zindex):
        """Handle layer removed."""
        if self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                self._schedule_task(app.dbus.remove_renderer(self._device.path, zindex))

        if not panel.layers:
            self._anim_state = "stopped"
            self._update_mode_status()
            self._preview_renderer.set_effect("disable", {})

    def _on_layer_selected(self, panel, row):
        """Handle layer selection."""
        if row:
            self._show_layer_params(row)
        else:
            self._param_inspector.clear()

    def _show_layer_params(self, row):
        """Show parameters for selected layer."""
        renderer_data = self._renderer_defs.get(row.renderer_id)
        if renderer_data:
            params = renderer_data.get("params", [])
            title = f"{renderer_data['name'].upper()} SETTINGS"
            self._param_inspector.set_params(params, title)

            if self._device:
                self._schedule_task(self._load_layer_params(row, params, title))

    async def _load_layer_params(self, row, params, title):
        """Load current trait values for a layer."""
        if not self._device:
            return

        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        info = await app.dbus.get_layer_info(self._device.path, row.zindex)
        values = {param["name"]: info.get(param["name"]) for param in params if param["name"] in info}
        GLib.idle_add(self._param_inspector.set_params, params, title, values)

    def _on_layer_changed(self, panel, zindex, prop, value):
        """Handle layer property change."""
        if self._syncing_layers:
            return
        if not self._device:
            return

        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        if prop == "visible":
            if zindex < 0 or zindex >= len(panel.layers):
                return
            opacity = 0.0 if not value else panel.layers[zindex].opacity
            self._schedule_task(
                app.dbus.set_layer_traits(self._device.path, zindex, {"opacity": opacity})
            )
            return

        if prop in {"blend_mode", "opacity"}:
            self._schedule_task(
                app.dbus.set_layer_traits(self._device.path, zindex, {prop: value})
            )

    def _on_play_clicked(self, panel):
        """Handle play button."""
        if self._device and self._anim_state == "paused":
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                self._schedule_task(app.dbus.pause_animation(self._device.path))
        self._anim_state = "running"
        self._update_mode_status()

    def _on_stop_clicked(self, panel):
        """Handle stop button."""
        panel.clear()
        self._param_inspector.clear()
        self._anim_state = "stopped"
        self._update_mode_status()
        self._preview_renderer.set_effect("disable", {})

        # Stop on device
        if self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                self._schedule_task(app.dbus.stop_animation(self._device.path))

    # === PARAMETERS ===

    def _on_param_changed(self, inspector, name, value):
        """Handle parameter value change."""
        if self._mode == self.MODE_HARDWARE and self._selected_effect:
            self._effect_params[name] = value
            self._preview_renderer.set_effect(self._selected_effect, self._effect_params)
            self._apply_effect_to_device(self._selected_effect)
            return

        if self._mode == self.MODE_CUSTOM and self._layer_panel.selected_layer and self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                zindex = self._layer_panel.selected_layer.zindex
                self._schedule_task(
                    app.dbus.set_layer_traits(self._device.path, zindex, {name: value})
                )

    # === HEADER CONTROLS ===

    def _on_brightness_changed(self, scale, value):
        """Handle brightness change."""
        if not self._device:
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            self._schedule_task(app.dbus.set_brightness(self._device.path, value))

    def _on_power_toggled(self, btn):
        """Handle power toggle."""
        suspended = btn.get_active()

        if suspended:
            btn.add_css_class("suspended")
        else:
            btn.remove_css_class("suspended")

        if not self._device:
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            self._schedule_task(app.dbus.set_suspended(self._device.path, suspended))

    # === PREVIEW ===

    def _on_preview_frame(self, frame):
        """Handle preview frame update."""
        self._matrix_preview.update_frame(frame)

    # === LIFECYCLE ===

    def on_devices_ready(self):
        """Called when devices are loaded from D-Bus."""
        app = self.get_application()
        if app and hasattr(app, "device_store") and len(app.device_store) > 0:  # type: ignore[arg-type]
            # Update device list
            devices = [app.device_store.get_item(i) for i in range(len(app.device_store))]  # type: ignore[arg-type]
            self.update_device_list(devices)

            # Select first device
            first_device = app.device_store.get_item(0)
            self.set_device(first_device)

    def _schedule_task(self, coro):
        """Schedule an async task and track it to prevent GC."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def do_close_request(self):
        """Handle window close."""
        self._preview_renderer.stop()
        return False
