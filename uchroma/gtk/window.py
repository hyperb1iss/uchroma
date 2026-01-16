#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
UChroma Main Window

Single-screen layout with matrix preview, mode toggle, and contextual panels.
"""

import asyncio
import os

import gi
import numpy as np

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .panels import (  # noqa: E402
    EffectSelector,
    LayerPanel,
    ModeToggle,
    ParamInspector,
    SystemControlPanel,
)
from .param_utils import (  # noqa: E402
    build_param_defs,
    extract_description,
    humanize_label,
    is_hidden_effect,
)
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
        self._device_list = []
        self._selected_devices = []
        self._mode = self.MODE_HARDWARE
        self._selected_effect = None
        self._effect_params = {}
        self._effects = []
        self._effect_defs = {}
        self._renderers = []
        self._renderer_defs = {}
        self._anim_state = ""
        self._fx_mixed = False
        self._layers_mixed = False
        self._device_layouts = {}
        self._syncing_layers = False
        self._pending_tasks: set[asyncio.Task] = set()

        self._preview_renderer = PreviewRenderer(rows=6, cols=22)
        self._preview_renderer.set_callback(self._on_preview_frame)

        self._device_preview_renderers = {}
        self._device_previews = {}
        self._live_preview_source = None
        self._live_preview_inflight = False
        self._live_preview_seq = None
        self._live_preview_interval_ms = self._read_live_preview_interval()

        self._system_panel = None
        self._system_device_path = None
        self._system_refresh_id = None
        self._system_refresh_inflight = False
        self._system_refresh_interval_ms = 1000
        self._system_power_modes: list[str] = []
        self._system_boost_modes: list[str] = []

        self._build_ui()
        self._connect_signals()

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

        self._preview_stack = Gtk.Stack()
        self._preview_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._preview_stack.set_transition_duration(150)

        self._matrix_preview = MatrixPreview(rows=6, cols=22)
        self._preview_stack.add_named(self._matrix_preview, "single")

        self._multi_preview = Gtk.FlowBox()
        self._multi_preview.set_homogeneous(False)
        self._multi_preview.set_selection_mode(Gtk.SelectionMode.NONE)
        self._multi_preview.set_min_children_per_line(1)
        self._multi_preview.set_max_children_per_line(2)
        self._multi_preview.set_column_spacing(16)
        self._multi_preview.set_row_spacing(16)
        self._multi_preview.set_valign(Gtk.Align.START)

        multi_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        multi_wrapper.append(self._multi_preview)
        self._preview_stack.add_named(multi_wrapper, "multi")

        preview_frame.append(self._preview_stack)
        content.append(preview_frame)

        # Section tabs
        self._section_stack = Adw.ViewStack()
        self._section_stack.set_vexpand(True)

        self._section_switcher = Adw.ViewSwitcher()
        self._section_switcher.set_stack(self._section_stack)
        self._section_switcher.add_css_class("section-switcher")
        self._section_switcher.set_halign(Gtk.Align.CENTER)
        self._section_switcher.set_margin_top(4)
        self._section_switcher.set_margin_bottom(8)

        content.append(self._section_switcher)
        content.append(self._section_stack)

        # === EFFECTS PAGE ===
        effects_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Mode Toggle
        self._mode_toggle = ModeToggle()
        effects_box.append(self._mode_toggle)

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

        effects_box.append(self._mode_stack)

        # Parameter Inspector
        self._param_inspector = ParamInspector()
        effects_box.append(self._param_inspector)

        self._section_stack.add_titled(effects_box, "effects", "Effects")

        # === SYSTEM PAGE ===
        system_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._system_panel = SystemControlPanel()
        system_box.append(self._system_panel)

        self._section_stack.add_titled(system_box, "system", "System")
        self._section_stack.set_visible_child_name("effects")

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

        # System control
        if self._system_panel:
            self._system_panel.connect("power-mode-changed", self._on_power_mode_changed)
            self._system_panel.connect("fan-mode-changed", self._on_fan_mode_changed)
            self._system_panel.connect("fan-rpm-changed", self._on_fan_rpm_changed)
            self._system_panel.connect("cpu-boost-changed", self._on_cpu_boost_changed)
            self._system_panel.connect("gpu-boost-changed", self._on_gpu_boost_changed)

    def _debug_log(self, message: str):
        if os.getenv("UCHROMA_GTK_DEBUG"):
            print(message)

    def _read_live_preview_interval(self) -> int:
        fps = os.getenv("UCHROMA_LIVE_PREVIEW_FPS")
        if fps:
            try:
                fps_val = max(1, int(fps))
                return max(40, int(1000 / fps_val))
            except ValueError:
                pass
        interval = os.getenv("UCHROMA_LIVE_PREVIEW_INTERVAL_MS")
        if interval:
            try:
                return max(40, int(interval))
            except ValueError:
                pass
        return 250

    # === DEVICE MANAGEMENT ===

    def set_devices(self, devices: list):
        """Set active devices (single or multiple)."""
        self._selected_devices = devices
        self._device = devices[0] if devices else None

        if self._device:
            if self._device_list:
                if len(devices) == len(self._device_list):
                    if self._device_dropdown.get_selected() != 0:
                        self._device_dropdown.set_selected(0)
                elif len(devices) == 1 and devices[0] in self._device_list:
                    idx = self._device_list.index(devices[0]) + 1
                    if self._device_dropdown.get_selected() != idx:
                        self._device_dropdown.set_selected(idx)

            subtitle = self._device.name
            if len(devices) > 1:
                subtitle = f"{self._device.name} +{len(devices) - 1}"
            self._window_title.set_subtitle(subtitle)

            if hasattr(self._device, "brightness"):
                self._brightness.value = self._device.brightness

            self._update_preview_visibility()
            self._schedule_task(self._load_device_state())
            self._schedule_task(self._load_system_state())
        else:
            self._window_title.set_subtitle("")
            self._update_preview_visibility()
            self._stop_system_refresh()
            if self._system_panel:
                self._system_panel.set_available(False, "Select a laptop to manage system control")

    def update_device_list(self, devices: list):
        """Update the device dropdown."""
        self._device_list = devices
        names = ["All devices"] if devices else ["No device"]
        names.extend([d.name for d in devices])
        self._device_model = Gtk.StringList.new(names)
        self._device_dropdown.set_model(self._device_model)

    def _on_device_selected(self, dropdown, pspec):
        """Handle device selection from dropdown."""
        idx = dropdown.get_selected()
        if not self._device_list:
            return

        if idx == 0:
            self.set_devices(self._device_list)
        else:
            device_idx = idx - 1
            if device_idx < len(self._device_list):
                self.set_devices([self._device_list[device_idx]])

    async def _load_device_state(self):
        """Fetch effects, renderers, and current animation state."""
        devices = self._selected_devices or ([self._device] if self._device else [])
        if not devices:
            return

        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        device_states = []
        for device in devices:
            path = device.path
            available_fx = await app.dbus.get_available_fx(path)
            available_renderers = await app.dbus.get_available_renderers(path)
            current_fx = await app.dbus.get_current_fx(path)
            current_renderers = await app.dbus.get_current_renderers(path)
            if current_renderers is None:
                current_renderers = []
            anim_state = await app.dbus.get_animation_state(path)
            key_mapping = await app.dbus.get_key_mapping(path)

            self._debug_log(
                f"GTK: device={device.name} path={path} renderers={list(available_renderers)}"
            )

            layer_infos = []
            for renderer_id, layer_path in current_renderers:
                zindex = self._layer_zindex_from_path(layer_path)
                info = await app.dbus.get_layer_info(path, zindex)
                layer_infos.append((renderer_id, zindex, info))

            device_states.append(
                {
                    "device": device,
                    "available_fx": available_fx,
                    "available_renderers": available_renderers,
                    "current_fx": current_fx,
                    "current_renderers": current_renderers,
                    "layer_infos": layer_infos,
                    "anim_state": anim_state,
                    "key_mapping": key_mapping,
                }
            )

        fx_sets = [set(state["available_fx"].keys()) for state in device_states]
        renderer_sets = [set(state["available_renderers"].keys()) for state in device_states]
        common_fx = set.intersection(*fx_sets) if fx_sets else set()
        common_renderers = set.intersection(*renderer_sets) if renderer_sets else set()

        fx_base = device_states[0]["available_fx"]
        renderer_base = device_states[0]["available_renderers"]
        available_fx = {k: fx_base[k] for k in common_fx if k in fx_base}
        available_renderers = {k: renderer_base[k] for k in common_renderers if k in renderer_base}
        self._debug_log(
            f"GTK: common renderers={list(available_renderers)} devices={len(device_states)}"
        )

        fx_names = [
            state["current_fx"][0] if state["current_fx"] else "" for state in device_states
        ]
        fx_params = [
            state["current_fx"][1] if state["current_fx"] else {} for state in device_states
        ]
        same_fx = len(set(fx_names)) == 1
        same_params = all(params == fx_params[0] for params in fx_params) if fx_params else True
        fx_mixed = not (same_fx and same_params)
        current_fx = device_states[0]["current_fx"] if same_fx else ("", {})

        renderer_stacks = [
            [renderer_id for renderer_id, _path in state["current_renderers"]]
            for state in device_states
        ]
        same_layers = len({tuple(stack) for stack in renderer_stacks}) <= 1
        layers_mixed = not same_layers
        layer_infos = device_states[0]["layer_infos"] if same_layers else []

        anim_states = [state["anim_state"] for state in device_states]
        anim_state = anim_states[0] if len(set(anim_states)) == 1 else "mixed"

        device_layouts = {}
        for state in device_states:
            mapping = state.get("key_mapping") or {}
            device_layouts[state["device"].path] = (
                self._compute_active_cells(mapping) if mapping else None
            )

        GLib.idle_add(
            self._apply_device_state,
            available_fx,
            available_renderers,
            current_fx,
            layer_infos,
            anim_state,
            device_layouts,
            fx_mixed,
            layers_mixed,
        )

    def _apply_device_state(
        self,
        available_fx: dict,
        available_renderers: dict,
        current_fx,
        layer_infos: list[tuple[str, int, dict]],
        anim_state: str,
        device_layouts: dict,
        fx_mixed: bool,
        layers_mixed: bool,
    ) -> bool:
        self._device_layouts = device_layouts
        self._fx_mixed = fx_mixed
        self._layers_mixed = layers_mixed

        self._effects = self._build_effect_defs(available_fx)
        self._effect_defs = {e["id"]: e for e in self._effects}
        self._effect_selector.set_effects(self._effects)

        self._renderers = self._build_renderer_defs(available_renderers)
        self._renderer_defs = {r["id"]: r for r in self._renderers}
        self._layer_panel.set_renderers(self._renderers)

        self._apply_current_effect(current_fx)
        if layers_mixed:
            self._layer_panel.clear()
            self._layer_panel.set_placeholder_text("Layers differ across devices")
            self._param_inspector.clear()
        else:
            placeholder = "Add a layer to begin"
            if not self._renderers:
                placeholder = "No renderers available for this selection"
            self._layer_panel.set_placeholder_text(placeholder)
            self._apply_current_layers(layer_infos)

        self._anim_state = anim_state or ""
        self._auto_select_mode(self._anim_state, layer_infos)

        if self._mode == self.MODE_CUSTOM:
            if not layers_mixed and layer_infos:
                self._apply_preview_effect("plasma", {})
            else:
                self._apply_preview_effect("disable", {})

        self._update_preview_visibility()
        self._update_mode_status()
        return False

    # === SYSTEM CONTROL ===

    async def _load_system_state(self):
        """Load system control state for the selected device."""
        if not self._system_panel:
            return

        self._stop_system_refresh()
        self._system_device_path = None
        self._system_power_modes = []
        self._system_boost_modes = []

        devices = self._selected_devices or ([self._device] if self._device else [])
        if len(devices) != 1:
            self._system_panel.set_available(
                False, "Select a single laptop device for system control"
            )
            return

        device = devices[0]
        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        system_proxy = await app.dbus.get_system_proxy(device.path)
        if not system_proxy:
            self._system_panel.set_available(
                False, "System control is only available on supported laptops"
            )
            return

        fan_limits = await app.dbus.get_fan_limits(device.path)
        power_modes = await app.dbus.get_available_power_modes(device.path)
        boost_modes = await app.dbus.get_available_boost_modes(device.path)
        fan_rpm = await app.dbus.get_fan_rpm(device.path)
        fan_mode = await app.dbus.get_fan_mode(device.path)
        power_mode = await app.dbus.get_power_mode(device.path)
        cpu_boost = await app.dbus.get_cpu_boost(device.path)
        gpu_boost = await app.dbus.get_gpu_boost(device.path)

        GLib.idle_add(
            self._apply_system_state,
            device.path,
            fan_limits,
            power_modes,
            boost_modes,
            fan_rpm,
            fan_mode,
            power_mode,
            cpu_boost,
            gpu_boost,
        )

    def _apply_system_state(
        self,
        path: str,
        fan_limits: dict,
        power_modes: list[str],
        boost_modes: list[str],
        fan_rpm: list[int],
        fan_mode: str,
        power_mode: str,
        cpu_boost: str,
        gpu_boost: str,
    ) -> bool:
        if not self._system_panel:
            return False

        self._system_device_path = path
        self._system_power_modes = power_modes or []
        self._system_boost_modes = boost_modes or []

        self._system_panel.set_available(True)
        self._system_panel.set_fan_limits(fan_limits or {"supports_dual_fan": False})
        self._system_panel.set_power_modes(power_modes, power_mode)
        self._system_panel.set_boost_modes(boost_modes, cpu_boost, gpu_boost)
        self._system_panel.set_boost_enabled(
            power_mode == "custom" and bool(self._system_boost_modes)
        )
        self._system_panel.set_fan_state(fan_rpm or [], fan_mode)

        self._start_system_refresh()
        return False

    def _start_system_refresh(self):
        if not self._system_device_path:
            return
        if self._system_refresh_id is not None:
            return
        self._system_refresh_id = GLib.timeout_add(
            self._system_refresh_interval_ms, self._on_system_refresh_tick
        )

    def _stop_system_refresh(self):
        if self._system_refresh_id is None:
            return
        GLib.source_remove(self._system_refresh_id)
        self._system_refresh_id = None
        self._system_refresh_inflight = False

    def _on_system_refresh_tick(self):
        if not self._system_device_path:
            return False
        if self._system_refresh_inflight:
            return True
        self._system_refresh_inflight = True
        self._schedule_task(self._refresh_system_state(self._system_device_path))
        return True

    async def _refresh_system_state(self, path: str):
        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            self._system_refresh_inflight = False
            return
        if path != self._system_device_path:
            self._system_refresh_inflight = False
            return

        try:
            fan_rpm = await app.dbus.get_fan_rpm(path)
            fan_mode = await app.dbus.get_fan_mode(path)
            power_mode = await app.dbus.get_power_mode(path)
            cpu_boost = await app.dbus.get_cpu_boost(path)
            gpu_boost = await app.dbus.get_gpu_boost(path)
        finally:
            self._system_refresh_inflight = False

        GLib.idle_add(
            self._apply_system_refresh,
            path,
            fan_rpm,
            fan_mode,
            power_mode,
            cpu_boost,
            gpu_boost,
        )

    def _apply_system_refresh(
        self,
        path: str,
        fan_rpm: list[int],
        fan_mode: str,
        power_mode: str,
        cpu_boost: str,
        gpu_boost: str,
    ) -> bool:
        if not self._system_panel or path != self._system_device_path:
            return False

        self._system_panel.set_power_mode(power_mode)
        self._system_panel.set_boost_enabled(
            power_mode == "custom" and bool(self._system_boost_modes)
        )
        self._system_panel.set_cpu_boost(cpu_boost)
        self._system_panel.set_gpu_boost(gpu_boost)
        self._system_panel.set_fan_state(fan_rpm or [], fan_mode)
        return False

    def _on_power_mode_changed(self, panel, mode: str):
        if not self._system_device_path:
            return
        if self._system_panel:
            self._system_panel.set_boost_enabled(
                mode == "custom" and bool(self._system_boost_modes)
            )
        app = self.get_application()
        if app and hasattr(app, "dbus"):
            self._schedule_task(app.dbus.set_power_mode(self._system_device_path, mode))

    def _on_fan_mode_changed(self, panel, mode: str, fan1: int, fan2: int):
        if not self._system_device_path:
            return
        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        if mode == "auto":
            self._schedule_task(app.dbus.set_fan_auto(self._system_device_path))
            return

        self._schedule_task(self._set_manual_fan(self._system_device_path, fan1, fan2))

    async def _set_manual_fan(self, path: str, fan1: int, fan2: int):
        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return
        if "custom" in self._system_power_modes:
            await app.dbus.set_power_mode(path, "custom")
        await app.dbus.set_fan_rpm(path, fan1, fan2)

    def _on_fan_rpm_changed(self, panel, fan1: int, fan2: int):
        if not self._system_device_path:
            return
        app = self.get_application()
        if app and hasattr(app, "dbus"):
            self._schedule_task(app.dbus.set_fan_rpm(self._system_device_path, fan1, fan2))

    def _on_cpu_boost_changed(self, panel, mode: str):
        if not self._system_device_path:
            return
        app = self.get_application()
        if app and hasattr(app, "dbus"):
            self._schedule_task(app.dbus.set_cpu_boost(self._system_device_path, mode))

    def _on_gpu_boost_changed(self, panel, mode: str):
        if not self._system_device_path:
            return
        app = self.get_application()
        if app and hasattr(app, "dbus"):
            self._schedule_task(app.dbus.set_gpu_boost(self._system_device_path, mode))

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

    def _compute_active_cells(self, key_mapping: dict) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for points in key_mapping.values():
            if points is None:
                continue
            if (
                isinstance(points, (list, tuple))
                and points
                and isinstance(points[0], (list, tuple))
            ):
                for point in points:
                    if len(point) >= 2:
                        cells.add((int(point[0]), int(point[1])))
            elif isinstance(points, (list, tuple)) and len(points) >= 2:
                cells.add((int(points[0]), int(points[1])))
        return cells

    def _layout_bounds(self, cells: set[tuple[int, int]] | None) -> tuple[int, int]:
        if not cells:
            return (0, 0)
        max_row = max(point[0] for point in cells)
        max_col = max(point[1] for point in cells)
        return (max_row + 1, max_col + 1)

    def _ensure_device_preview(self, device):
        path = device.path
        if path in self._device_previews:
            return self._device_previews[path]

        rows = getattr(device, "height", 0) or 6
        cols = getattr(device, "width", 0) or 22

        preview = MatrixPreview(rows=rows, cols=cols)
        renderer = PreviewRenderer(rows=rows, cols=cols)
        renderer.set_callback(preview.update_frame)

        self._device_previews[path] = preview
        self._device_preview_renderers[path] = renderer
        return preview

    def _build_multi_preview(self):
        child = self._multi_preview.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._multi_preview.remove(child)
            child = next_child

        active_paths = set()
        for device in self._selected_devices:
            active_paths.add(device.path)
            preview = self._ensure_device_preview(device)
            layout = self._device_layouts.get(device.path)
            preview.set_active_cells(layout)

            rows = getattr(device, "height", 0) or 0
            cols = getattr(device, "width", 0) or 0
            if (rows == 0 or cols == 0) and layout:
                rows, cols = self._layout_bounds(layout)
            if rows == 0:
                rows = preview.rows
            if cols == 0:
                cols = preview.cols
            preview.set_matrix_size(rows, cols)

            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("preview-card")

            label = Gtk.Label(label=device.name)
            label.add_css_class("preview-label")
            label.set_xalign(0)
            card.append(label)
            card.append(preview)

            self._multi_preview.append(card)

        for path, renderer in list(self._device_preview_renderers.items()):
            if path in active_paths:
                renderer.start(30)
            else:
                renderer.stop()

    def _update_preview_visibility(self):
        if not self._selected_devices:
            self._preview_stack.set_visible_child_name("single")
            self._preview_renderer.stop()
            for renderer in self._device_preview_renderers.values():
                renderer.stop()
            self._stop_live_preview()
            return

        if len(self._selected_devices) > 1:
            self._preview_stack.set_visible_child_name("multi")
            self._preview_renderer.stop()
            self._build_multi_preview()
            self._stop_live_preview()
            return

        self._preview_stack.set_visible_child_name("single")
        if not self._device:
            self._preview_renderer.stop()
            self._stop_live_preview()
            return

        rows = getattr(self._device, "height", 0) or 0
        cols = getattr(self._device, "width", 0) or 0
        layout = self._device_layouts.get(self._device.path)
        self._matrix_preview.set_active_cells(layout)
        if (rows == 0 or cols == 0) and layout:
            rows, cols = self._layout_bounds(layout)
        rows = rows or 6
        cols = cols or 22
        self._matrix_preview.set_matrix_size(rows, cols)

        if self._should_live_preview():
            self._start_live_preview()
            return

        self._stop_live_preview()
        self._preview_renderer.set_size(rows, cols)
        self._preview_renderer.start(30)

    def _apply_preview_effect(self, effect_id: str, params: dict | None = None):
        if self._live_preview_source is not None:
            return
        params = params or {}
        if len(self._selected_devices) > 1:
            for device in self._selected_devices:
                self._ensure_device_preview(device)
                renderer = self._device_preview_renderers.get(device.path)
                if renderer:
                    renderer.set_effect(effect_id, params)
            return

        self._preview_renderer.set_effect(effect_id, params)

    def _should_live_preview(self, layer_infos: list[tuple[str, int, dict]] | None = None) -> bool:
        if not self._device:
            return False
        if len(self._selected_devices) != 1:
            return False
        if self._mode != self.MODE_CUSTOM:
            return False
        if self._layers_mixed:
            return False
        has_layers = (
            bool(layer_infos) if layer_infos is not None else bool(self._layer_panel.layers)
        )
        if not has_layers:
            return False
        return self._anim_state in {"running", "paused", ""}

    def _start_live_preview(self):
        if self._live_preview_source is not None or not self._device:
            return
        self._preview_renderer.stop()
        self._live_preview_seq = None
        self._live_preview_source = GLib.timeout_add(
            self._live_preview_interval_ms,
            self._live_preview_tick,
        )

    def _stop_live_preview(self):
        if self._live_preview_source is None:
            return
        GLib.source_remove(self._live_preview_source)
        self._live_preview_source = None
        self._live_preview_seq = None

    def _live_preview_tick(self) -> bool:
        if self._live_preview_inflight:
            return True
        if not self._device:
            return False
        self._live_preview_inflight = True
        self._schedule_task(self._fetch_live_frame(self._device))
        return True

    async def _fetch_live_frame(self, device):
        try:
            app = self.get_application()
            if not app or not hasattr(app, "dbus"):
                return
            if self._live_preview_source is None:
                return

            frame = await app.dbus.get_current_frame(device.path)
            if not frame:
                return

            data = frame.get("data")
            width = int(frame.get("width") or 0)
            height = int(frame.get("height") or 0)
            seq = frame.get("seq")
            if not data or width <= 0 or height <= 0:
                return
            if seq is not None and seq == self._live_preview_seq:
                return

            buffer = np.frombuffer(data, dtype=np.uint8)
            expected = width * height * 3
            if buffer.size < expected:
                return

            matrix = buffer[:expected].reshape((height, width, 3))
            if self._matrix_preview.rows != height or self._matrix_preview.cols != width:
                GLib.idle_add(self._matrix_preview.set_matrix_size, height, width)
            GLib.idle_add(self._matrix_preview.update_frame, matrix)
            self._live_preview_seq = seq
        finally:
            self._live_preview_inflight = False

    def _iter_target_devices(self) -> list:
        if self._selected_devices:
            return self._selected_devices
        if self._device:
            return [self._device]
        return []

    def _apply_current_effect(self, current_fx):
        fx_name = ""
        fx_params = {}
        if isinstance(current_fx, (list, tuple)) and len(current_fx) >= 2:
            fx_name = current_fx[0] or ""
            fx_params = current_fx[1] or {}

        self._selected_effect = fx_name or None if not self._fx_mixed else None
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
        elif self._mode == self.MODE_HARDWARE:
            self._param_inspector.clear()
            self._effect_selector.select_effect("")

        if self._mode == self.MODE_HARDWARE:
            if self._selected_effect:
                self._apply_preview_effect(self._selected_effect, self._effect_params)
            else:
                self._apply_preview_effect("disable", {})

    def _apply_current_layers(self, layer_infos: list[tuple[str, int, dict]]):
        self._syncing_layers = True
        try:
            self._layer_panel.clear()
            for renderer_id, _zindex, info in sorted(layer_infos, key=lambda x: x[1]):
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
            if self._fx_mixed:
                self._mode_toggle.set_status("Mixed", False)
                return
            if self._selected_effect and self._selected_effect in self._effect_defs:
                effect_data = self._effect_defs[self._selected_effect]
                self._mode_toggle.set_status(
                    effect_data["name"], self._selected_effect != "disable"
                )
            else:
                self._mode_toggle.set_status("No effect", False)
            return

        if self._layers_mixed or self._anim_state == "mixed":
            self._mode_toggle.set_status("Mixed", False)
            return

        if not self._layer_panel.layers:
            self._mode_toggle.set_status("No layers", False)
            return

        if self._anim_state == "paused":
            self._mode_toggle.set_status("Paused", False)
        else:
            self._mode_toggle.set_status("Running", True)

    def _auto_select_mode(self, anim_state: str, layer_infos: list[tuple[str, int, dict]]):
        if anim_state == "mixed" or self._layers_mixed:
            return

        active = anim_state in {"running", "paused"}
        if not active and not anim_state and layer_infos:
            active = True

        target_mode = self.MODE_CUSTOM if active else self.MODE_HARDWARE
        if self._mode != target_mode:
            self._mode_toggle.mode = target_mode

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
                self._apply_preview_effect(self._selected_effect, self._effect_params)
            else:
                self._param_inspector.clear()
                self._apply_preview_effect("disable", {})
            self._update_mode_status()

        else:
            # Custom mode - show layer params or empty
            if self._layer_panel.selected_layer:
                self._show_layer_params(self._layer_panel.selected_layer)
            else:
                self._param_inspector.clear()
            if self._layer_panel.layers:
                self._apply_preview_effect("plasma", {})
            else:
                self._apply_preview_effect("disable", {})
            self._update_mode_status()
        self._update_preview_visibility()

    # === HARDWARE FX ===

    def _on_effect_selected(self, selector, effect_id):
        """Handle effect card selection."""
        self._fx_mixed = False
        self._selected_effect = effect_id
        effect_data = self._effect_defs.get(effect_id)

        if effect_data:
            # Update preview
            self._apply_preview_effect(effect_id, self._effect_params)

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
        if not self._iter_target_devices():
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            params = self._param_inspector.get_values()
            for device in self._iter_target_devices():
                self._schedule_task(app.dbus.set_effect(device.path, effect_id, params))

    # === CUSTOM ANIMATION ===

    def _on_layer_added(self, panel, renderer_id):
        """Handle layer added."""
        self._layers_mixed = False
        self._layer_panel.set_placeholder_text("Add a layer to begin")
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
                for device in self._iter_target_devices():
                    self._schedule_task(app.dbus.add_renderer(device.path, renderer_id, zindex))

        # Update preview for custom animation
        self._apply_preview_effect("plasma", {})

        # Update status
        self._anim_state = "running"
        self._update_mode_status()
        self._show_layer_params(row)
        self._update_preview_visibility()

    def _on_layer_removed(self, panel, zindex):
        """Handle layer removed."""
        if self._device:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                for device in self._iter_target_devices():
                    self._schedule_task(app.dbus.remove_renderer(device.path, zindex))

        if not panel.layers:
            self._anim_state = "stopped"
            self._update_mode_status()
            self._apply_preview_effect("disable", {})
        self._update_preview_visibility()

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
        if not self._device or self._layers_mixed:
            return

        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        info = await app.dbus.get_layer_info(self._device.path, row.zindex)
        values = {
            param["name"]: info.get(param["name"]) for param in params if param["name"] in info
        }
        GLib.idle_add(self._param_inspector.set_params, params, title, values)

    def _on_layer_changed(self, panel, zindex, prop, value):
        """Handle layer property change."""
        if self._syncing_layers:
            return
        if self._layers_mixed:
            return
        targets = self._iter_target_devices()
        if not targets:
            return

        app = self.get_application()
        if not app or not hasattr(app, "dbus"):
            return

        if prop == "visible":
            if zindex < 0 or zindex >= len(panel.layers):
                return
            opacity = 0.0 if not value else panel.layers[zindex].opacity
            for device in targets:
                self._schedule_task(
                    app.dbus.set_layer_traits(device.path, zindex, {"opacity": opacity})
                )
            return

        if prop in {"blend_mode", "opacity"}:
            for device in targets:
                self._schedule_task(app.dbus.set_layer_traits(device.path, zindex, {prop: value}))

    def _on_play_clicked(self, panel):
        """Handle play button."""
        targets = self._iter_target_devices()
        if targets and self._anim_state == "paused":
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                for device in targets:
                    self._schedule_task(app.dbus.pause_animation(device.path))
        self._anim_state = "running"
        self._update_mode_status()
        self._update_preview_visibility()

    def _on_stop_clicked(self, panel):
        """Handle stop button."""
        panel.clear()
        self._param_inspector.clear()
        self._anim_state = "stopped"
        self._update_mode_status()
        self._apply_preview_effect("disable", {})
        self._update_preview_visibility()

        # Stop on device
        if self._iter_target_devices():
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                for device in self._iter_target_devices():
                    self._schedule_task(app.dbus.stop_animation(device.path))

    # === PARAMETERS ===

    def _on_param_changed(self, inspector, name, value):
        """Handle parameter value change."""
        if self._mode == self.MODE_HARDWARE and self._selected_effect:
            self._effect_params[name] = value
            self._apply_preview_effect(self._selected_effect, self._effect_params)
            self._apply_effect_to_device(self._selected_effect)
            return

        if self._mode == self.MODE_CUSTOM and self._layer_panel.selected_layer:
            app = self.get_application()
            if app and hasattr(app, "dbus"):
                zindex = self._layer_panel.selected_layer.zindex
                for device in self._iter_target_devices():
                    self._schedule_task(
                        app.dbus.set_layer_traits(device.path, zindex, {name: value})
                    )

    # === HEADER CONTROLS ===

    def _on_brightness_changed(self, scale, value):
        """Handle brightness change."""
        if not self._iter_target_devices():
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            for device in self._iter_target_devices():
                self._schedule_task(app.dbus.set_brightness(device.path, value))

    def _on_power_toggled(self, btn):
        """Handle power toggle."""
        suspended = btn.get_active()

        if suspended:
            btn.add_css_class("suspended")
        else:
            btn.remove_css_class("suspended")

        if not self._iter_target_devices():
            return

        app = self.get_application()
        if app and hasattr(app, "dbus"):
            for device in self._iter_target_devices():
                self._schedule_task(app.dbus.set_suspended(device.path, suspended))

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
            self.set_devices([devices[0]])

    def _schedule_task(self, coro):
        """Schedule an async task and track it to prevent GC."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def do_close_request(self):
        """Handle window close."""
        self._preview_renderer.stop()
        for renderer in self._device_preview_renderers.values():
            renderer.stop()
        self._stop_live_preview()
        self._stop_system_refresh()
        return False
