"""
UChroma Main Window

Single-screen layout with matrix preview, mode toggle, and contextual panels.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .panels import EffectSelector, LayerPanel, ModeToggle, ParamInspector
from .services.preview_renderer import PreviewRenderer
from .widgets import BrightnessScale, MatrixPreview
from .widgets.effect_card import get_effect_by_id
from .widgets.layer_row import get_renderer_by_id


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
            if hasattr(device, "matrix_rows") and hasattr(device, "matrix_cols"):
                self._matrix_preview.set_matrix_size(device.matrix_rows, device.matrix_cols)
                self._preview_renderer.set_size(device.matrix_rows, device.matrix_cols)

            # Update brightness
            if hasattr(device, "brightness"):
                self._brightness.value = device.brightness

            # Update current effect
            if hasattr(device, "current_fx") and device.current_fx:
                self._effect_selector.select_effect(device.current_fx)
                self._selected_effect = device.current_fx
                effect_data = get_effect_by_id(device.current_fx)
                if effect_data:
                    self._param_inspector.set_params(
                        effect_data.get("params", []), f"{effect_data['name'].upper()} SETTINGS"
                    )
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
        if app and hasattr(app, "device_store") and idx < len(app.device_store):
            device = app.device_store.get_item(idx)
            self.set_device(device)

    # === MODE SWITCHING ===

    def _on_mode_changed(self, toggle, mode):
        """Handle mode change."""
        self._mode = mode
        self._mode_stack.set_visible_child_name(mode)

        if mode == self.MODE_HARDWARE:
            # Show effect params if effect selected
            if self._selected_effect:
                effect_data = get_effect_by_id(self._selected_effect)
                if effect_data:
                    self._param_inspector.set_params(
                        effect_data.get("params", []),
                        f"{effect_data['name'].upper()} SETTINGS",
                        self._effect_params,
                    )
            else:
                self._param_inspector.clear()

            # Update status
            if self._selected_effect:
                self._mode_toggle.set_status(self._selected_effect.title(), True)
            else:
                self._mode_toggle.set_status("No effect", False)

        else:
            # Custom mode - show layer params or empty
            if self._layer_panel.selected_layer:
                self._show_layer_params(self._layer_panel.selected_layer)
            else:
                self._param_inspector.clear()

            # Update status based on layers
            if self._layer_panel.layers:
                self._mode_toggle.set_status("Running", True)
            else:
                self._mode_toggle.set_status("No layers", False)

    # === HARDWARE FX ===

    def _on_effect_selected(self, selector, effect_id):
        """Handle effect card selection."""
        self._selected_effect = effect_id
        effect_data = get_effect_by_id(effect_id)

        if effect_data:
            # Update preview
            self._preview_renderer.set_effect(effect_id, self._effect_params)

            # Show params
            self._param_inspector.set_params(
                effect_data.get("params", []), f"{effect_data['name'].upper()} SETTINGS"
            )

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
            import asyncio

            params = self._param_inspector.get_values()
            asyncio.create_task(app.dbus.set_effect(self._device.path, effect_id, params))

    # === CUSTOM ANIMATION ===

    def _on_layer_added(self, panel, renderer_id):
        """Handle layer added."""
        renderer_data = get_renderer_by_id(renderer_id)
        if renderer_data:
            row = panel.add_layer(renderer_id, renderer_data["name"])

            # Apply to device
            if self._device:
                app = self.get_application()
                if app and hasattr(app, "dbus"):
                    import asyncio

                    zindex = len(panel.layers) - 1
                    asyncio.create_task(
                        app.dbus.add_renderer(self._device.path, renderer_id, zindex)
                    )

            # Update preview for custom animation
            self._preview_renderer.set_effect("plasma", {})

            # Update status
            self._mode_toggle.set_status("Running", True)

    def _on_layer_removed(self, panel, zindex):
        """Handle layer removed."""
        if self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                import asyncio

                asyncio.create_task(app.dbus.remove_renderer(self._device.path, zindex))

        if not panel.layers:
            self._mode_toggle.set_status("No layers", False)
            self._preview_renderer.set_effect("disable", {})

    def _on_layer_selected(self, panel, row):
        """Handle layer selection."""
        if row:
            self._show_layer_params(row)
        else:
            self._param_inspector.clear()

    def _show_layer_params(self, row):
        """Show parameters for selected layer."""
        renderer_data = get_renderer_by_id(row.renderer_id)
        if renderer_data:
            self._param_inspector.set_params(
                renderer_data.get("params", []), f"{renderer_data['name'].upper()} SETTINGS"
            )

    def _on_layer_changed(self, panel, zindex, prop, value):
        """Handle layer property change."""
        # TODO: Update via D-Bus when API supports it

    def _on_play_clicked(self, panel):
        """Handle play button."""
        self._mode_toggle.set_status("Running", True)

    def _on_stop_clicked(self, panel):
        """Handle stop button."""
        panel.clear()
        self._param_inspector.clear()
        self._mode_toggle.set_status("Stopped", False)
        self._preview_renderer.set_effect("disable", {})

        # Stop on device
        if self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                import asyncio

                asyncio.create_task(app.dbus.stop_animation(self._device.path))

    # === PARAMETERS ===

    def _on_param_changed(self, inspector, name, value):
        """Handle parameter value change."""
        self._effect_params[name] = value

        # Update preview
        if self._mode == self.MODE_HARDWARE and self._selected_effect:
            self._preview_renderer.set_effect(self._selected_effect, self._effect_params)
            self._apply_effect_to_device(self._selected_effect)

        # TODO: Update layer params via D-Bus

    # === HEADER CONTROLS ===

    def _on_brightness_changed(self, scale, value):
        """Handle brightness change."""
        if not self._device:
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            import asyncio

            asyncio.create_task(app.dbus.set_brightness(self._device.path, value))

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
            import asyncio

            asyncio.create_task(app.dbus.set_suspended(self._device.path, suspended))

    # === PREVIEW ===

    def _on_preview_frame(self, frame):
        """Handle preview frame update."""
        self._matrix_preview.update_frame(frame)

    # === LIFECYCLE ===

    def on_devices_ready(self):
        """Called when devices are loaded from D-Bus."""
        app = self.get_application()
        if app and hasattr(app, "device_store") and len(app.device_store) > 0:
            # Update device list
            devices = [app.device_store.get_item(i) for i in range(len(app.device_store))]
            self.update_device_list(devices)

            # Select first device
            first_device = app.device_store.get_item(0)
            self.set_device(first_device)

    def do_close_request(self):
        """Handle window close."""
        self._preview_renderer.stop()
        return False
