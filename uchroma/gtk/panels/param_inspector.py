#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Parameter Inspector Panel

Contextual parameter controls for selected effect or layer.
"""

from typing import ClassVar, cast

import gi

gi.require_version("Gtk", "4.0")

import cairo  # noqa: E402
from gi.repository import Gdk, GLib, GObject, Gtk  # noqa: E402

from uchroma.color import ColorScheme  # noqa: E402
from uchroma.log import Log  # noqa: E402

_logger = Log.get("uchroma.gtk")


def _get_sorted_schemes() -> list[tuple[str, tuple[str, ...]]]:
    """Get ColorScheme names and values sorted alphabetically."""
    return sorted([(s.name, s.value) for s in ColorScheme], key=lambda x: x[0].lower())


class ParamInspector(Gtk.Box):
    """Contextual parameter inspector with horizontal layout."""

    __gtype_name__ = "UChromaParamInspector"

    __gsignals__: ClassVar[dict] = {
        "param-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),  # name, value
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self._params = []
        self._param_map = {}
        self._widgets = {}
        self._debounce_sources = {}
        self._recent_colors = []

        self.add_css_class("param-inspector")
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(8)
        self.set_margin_bottom(16)

        self._build_ui()

    def _build_ui(self):
        """Build the inspector UI."""
        # Title
        self._title = Gtk.Label(label="SETTINGS")
        self._title.add_css_class("panel-title")
        self._title.set_xalign(0)
        self._title.set_margin_bottom(4)
        self.append(self._title)

        # Parameters container (horizontal flow)
        self._params_box = Gtk.FlowBox()
        self._params_box.set_homogeneous(False)
        self._params_box.set_min_children_per_line(1)
        self._params_box.set_max_children_per_line(6)
        self._params_box.set_column_spacing(16)
        self._params_box.set_row_spacing(8)
        self._params_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.append(self._params_box)

        # Empty state
        self._empty = Gtk.Label(label="Select an effect or layer")
        self._empty.add_css_class("dim")
        self._empty.set_margin_top(8)
        self.append(self._empty)

    @staticmethod
    def _rgba_to_hex(rgba: Gdk.RGBA) -> str:
        return f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"

    @staticmethod
    def _parse_color_text(text: str) -> tuple[Gdk.RGBA, str] | None:
        raw = text.strip()
        if not raw:
            return None
        if not raw.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in raw):
            if len(raw) in (3, 6):
                raw = f"#{raw}"
        rgba = Gdk.RGBA()
        if rgba.parse(raw):
            hex_color = ParamInspector._rgba_to_hex(rgba)
            return rgba, hex_color
        return None

    def _get_button_rgba(self, button: Gtk.Widget) -> Gdk.RGBA:
        rgba = getattr(button, "_rgba", None)
        if isinstance(rgba, Gdk.RGBA):
            return rgba
        return Gdk.RGBA()

    def _set_color_button_rgba(
        self,
        button: Gtk.MenuButton,
        rgba: Gdk.RGBA,
        *,
        emit: bool = True,
        update_entry: bool = True,
    ):
        button._rgba = rgba
        hex_color = self._rgba_to_hex(rgba)

        swatch = getattr(button, "_swatch_area", None)
        if swatch is not None:
            swatch._rgba = rgba
            swatch.queue_draw()

        label = getattr(button, "_label", None)
        if label is not None:
            label.set_label(hex_color)

        entry = getattr(button, "_entry", None)
        if update_entry and entry is not None and entry.get_text() != hex_color:
            entry.set_text(hex_color)

        if emit:
            on_change = getattr(button, "_on_change", None)
            if on_change:
                on_change(hex_color)

    def _add_recent_color(self, hex_color: str):
        hex_color = hex_color.lower()
        if hex_color in self._recent_colors:
            self._recent_colors.remove(hex_color)
        self._recent_colors.insert(0, hex_color)
        self._recent_colors = self._recent_colors[:8]

    def _populate_swatch_row(
        self, container: Gtk.Box, colors: list[str], on_select, *, empty_label: str | None = None
    ):
        child = container.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            container.remove(child)
            child = next_child

        if not colors:
            if empty_label:
                label = Gtk.Label(label=empty_label)
                label.add_css_class("color-section-empty")
                label.set_xalign(0)
                container.append(label)
            return

        for color_str in colors:
            btn = self._create_swatch_button(color_str, on_select)
            container.append(btn)

    def _create_swatch_button(self, color_str: str, on_select):
        rgba = Gdk.RGBA()
        if not rgba.parse(str(color_str)):
            rgba.parse("#888888")

        swatch = Gtk.DrawingArea()
        swatch.set_size_request(18, 18)
        swatch.add_css_class("color-swatch")
        swatch._rgba = rgba

        def draw(area, cr, width, height):
            r = area._rgba
            radius = 4
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()
            cr.set_source_rgba(r.red, r.green, r.blue, 1.0)
            cr.fill()

        swatch.set_draw_func(draw)

        btn = Gtk.Button()
        btn.add_css_class("color-swatch-btn")
        btn.set_child(swatch)

        def on_click(_btn, rgba=rgba):
            on_select(rgba)

        btn.connect("clicked", on_click)
        return btn

    def _create_color_button(
        self,
        color_str: str,
        *,
        on_change,
        show_label: bool = False,
        default_color: str | None = None,
    ) -> Gtk.MenuButton:
        rgba = Gdk.RGBA()
        if not rgba.parse(str(color_str)):
            rgba.parse("#888888")

        btn = Gtk.MenuButton()
        btn.add_css_class("param-color")
        if show_label:
            btn.add_css_class("param-color-wide")

        swatch = Gtk.DrawingArea()
        swatch.set_size_request(18, 18)
        swatch.add_css_class("color-swatch")
        swatch._rgba = rgba

        def draw(area, cr, width, height):
            r = area._rgba
            radius = 4
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()
            cr.set_source_rgba(r.red, r.green, r.blue, 1.0)
            cr.fill()

        swatch.set_draw_func(draw)

        hex_color = self._rgba_to_hex(rgba)
        btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_content.set_margin_start(6)
        btn_content.set_margin_end(6)
        btn_content.set_margin_top(4)
        btn_content.set_margin_bottom(4)
        btn_content.append(swatch)

        label = None
        if show_label:
            label = Gtk.Label(label=hex_color)
            label.add_css_class("color-hex-label")
            label.set_xalign(0)
            btn_content.append(label)

        btn.set_child(btn_content)

        btn._rgba = rgba
        btn._swatch_area = swatch
        btn._label = label
        btn._on_change = on_change

        popover = Gtk.Popover()
        popover.add_css_class("color-popover")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_start(8)
        content.set_margin_end(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        entry_label = Gtk.Label(label="Hex")
        entry_label.add_css_class("color-section-label")
        entry_label.set_xalign(0)
        entry_row.append(entry_label)

        entry = Gtk.Entry()
        entry.add_css_class("color-hex-entry")
        entry.set_width_chars(9)
        entry.set_text(hex_color)
        entry_row.append(entry)

        def apply_rgba(new_rgba: Gdk.RGBA, *, update_entry: bool = True):
            self._set_color_button_rgba(btn, new_rgba, emit=True, update_entry=update_entry)
            self._add_recent_color(self._rgba_to_hex(new_rgba))
            self._populate_swatch_row(
                recent_row,
                self._recent_colors,
                lambda r: apply_rgba(r, update_entry=True),
                empty_label="No recent colors",
            )

        def on_entry_changed(entry_widget):
            result = self._parse_color_text(entry_widget.get_text())
            if result is None:
                entry_widget.add_css_class("invalid")
                return
            entry_widget.remove_css_class("invalid")
            new_rgba, _hex = result
            self._set_color_button_rgba(btn, new_rgba, emit=True, update_entry=False)

        entry.connect("changed", on_entry_changed)

        def on_entry_activate(entry_widget):
            result = self._parse_color_text(entry_widget.get_text())
            if result is None:
                entry_widget.add_css_class("invalid")
                return
            entry_widget.remove_css_class("invalid")
            new_rgba, _hex = result
            apply_rgba(new_rgba, update_entry=True)

        entry.connect("activate", on_entry_activate)

        content.append(entry_row)

        recent_title = Gtk.Label(label="Recent")
        recent_title.add_css_class("color-section-label")
        recent_title.set_xalign(0)
        content.append(recent_title)

        recent_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        recent_row.add_css_class("color-swatch-row")
        self._populate_swatch_row(
            recent_row,
            self._recent_colors,
            lambda r: apply_rgba(r, update_entry=True),
            empty_label="No recent colors",
        )
        content.append(recent_row)

        palette_title = Gtk.Label(label="Palette")
        palette_title.add_css_class("color-section-label")
        palette_title.set_xalign(0)
        content.append(palette_title)

        palette_row = Gtk.FlowBox()
        palette_row.add_css_class("color-swatch-grid")
        palette_row.set_selection_mode(Gtk.SelectionMode.NONE)
        palette_row.set_max_children_per_line(8)
        palette_row.set_row_spacing(6)
        palette_row.set_column_spacing(6)

        palette = [
            "#ffffff",
            "#e6e6e6",
            "#b3b3b3",
            "#666666",
            "#111111",
            "#ff3b30",
            "#ff9500",
            "#ffcc00",
            "#34c759",
            "#00ffea",
            "#00ffff",
            "#32ade6",
            "#007aff",
            "#5856d6",
            "#af52de",
            "#ff2d55",
            "#ff6ac1",
            "#f1fa8c",
            "#50fa7b",
            "#80ffea",
        ]

        def on_palette_select(new_rgba):
            apply_rgba(new_rgba, update_entry=True)

        for color in palette:
            swatch_btn = self._create_swatch_button(color, on_palette_select)
            palette_row.append(swatch_btn)

        content.append(palette_row)

        if default_color:
            reset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            reset_btn = Gtk.Button(label="Reset to default")
            reset_btn.add_css_class("color-reset-btn")
            reset_row.append(reset_btn)

            def on_reset_click(_btn, color=default_color):
                default_rgba = Gdk.RGBA()
                if default_rgba.parse(str(color)):
                    apply_rgba(default_rgba, update_entry=True)

            reset_btn.connect("clicked", on_reset_click)
            content.append(reset_row)

        popover.set_child(content)
        btn.set_popover(popover)
        btn._entry = entry

        return btn

    def set_params(self, params: list, title: str = "SETTINGS", values: dict | None = None):
        """Set parameters to display.

        Args:
            params: List of param definitions
            title: Section title
            values: Optional dict of current values
        """
        self._clear_params()
        self._params = params
        self._param_map = {param["name"]: param for param in params}
        self._title.set_label(title)

        values = values or {}

        if not params:
            self._empty.set_visible(True)
            self._params_box.set_visible(False)
            return

        self._empty.set_visible(False)
        self._params_box.set_visible(True)

        for param in params:
            widget = self._create_param_widget(param, values.get(param["name"]))
            if widget:
                self._params_box.append(widget)

    def _clear_params(self):
        """Clear all parameter widgets."""
        # Cancel any pending debounces
        for source_id in self._debounce_sources.values():
            GLib.source_remove(source_id)
        self._debounce_sources.clear()

        # Remove widgets
        child = self._params_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._params_box.remove(child)
            child = next_child

        self._widgets.clear()
        self._params = []
        self._param_map.clear()

    def _create_param_widget(self, param: dict, current_value=None) -> Gtk.Widget | None:
        """Create a widget for a parameter."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("param-group")

        # Label
        label = Gtk.Label(label=param.get("label", param["name"]))
        label.add_css_class("param-label")
        label.set_xalign(0)
        box.append(label)

        # Widget based on type
        param_type = param["type"]
        name = param["name"]

        if param_type == "color":
            widget = self._create_color_widget(param, current_value)
        elif param_type == "color_list":
            widget = self._create_color_list_widget(param, current_value)
        elif param_type == "color_preset":
            widget = self._create_color_preset_widget(param, current_value)
        elif param_type == "range":
            widget = self._create_range_widget(param, current_value)
        elif param_type == "choice":
            widget = self._create_choice_widget(param, current_value)
        elif param_type == "toggle":
            widget = self._create_toggle_widget(param, current_value)
        else:
            return None

        if widget:
            box.append(widget)
            if name not in self._widgets:
                self._widgets[name] = widget

        # Wrap in FlowBoxChild
        child = Gtk.FlowBoxChild()
        child.set_child(box)

        return child

    def _create_color_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a color picker button."""
        color_str = current_value or param.get("default", "#ffffff") or "#ffffff"
        return self._create_color_button(
            color_str,
            on_change=lambda _hex, name=param["name"]: self._emit_debounced(name, _hex),
            show_label=True,
            default_color=param.get("default"),
        )

    def _create_color_preset_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a color preset selector with gradient swatches (for ColorPresetTrait)."""
        options = param.get("options", [])
        current = current_value or param.get("default")

        # Get schemes that match the options
        all_schemes = dict(_get_sorted_schemes())

        # MenuButton with gradient preview
        preset_btn = Gtk.MenuButton()
        preset_btn.add_css_class("param-preset-btn")

        # Create button content with gradient + label
        btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Gradient swatch for current selection
        gradient = Gtk.DrawingArea()
        gradient.set_size_request(60, 18)
        gradient.add_css_class("preset-btn-gradient")

        current_colors = all_schemes.get(current, ()) if current else ()
        self._setup_gradient_draw(gradient, current_colors)
        btn_content.append(gradient)

        # Label
        label = Gtk.Label(label=current if current else "Select...")
        label.add_css_class("preset-btn-label")
        btn_content.append(label)

        # Dropdown arrow
        arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic")
        arrow.add_css_class("preset-btn-arrow")
        btn_content.append(arrow)

        preset_btn.set_child(btn_content)

        # Store references for updating
        preset_btn._gradient = gradient
        preset_btn._label = label
        preset_btn._schemes = all_schemes

        # Popover with scrollable list
        popover = Gtk.Popover()
        popover.add_css_class("param-preset-popover")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("preset-list")

        # Sort options alphabetically and add rows with gradients
        sorted_options = sorted(options, key=str.lower)
        for name in sorted_options:
            colors = all_schemes.get(name, ())
            row = self._create_preset_option_row(name, colors, preset_btn, popover, param["name"])
            listbox.append(row)

        scroll.set_child(listbox)
        popover.set_child(scroll)
        preset_btn.set_popover(popover)

        return preset_btn

    def _setup_gradient_draw(self, gradient: Gtk.DrawingArea, colors: tuple):
        """Set up gradient drawing function with given colors."""
        rgba_colors = []
        for color_str in colors:
            rgba = Gdk.RGBA()
            if rgba.parse(str(color_str)):
                rgba_colors.append(rgba)

        def draw_gradient(area, cr, width, height, cols=rgba_colors):
            if not cols:
                cr.set_source_rgb(0.3, 0.3, 0.3)
                cr.rectangle(0, 0, width, height)
                cr.fill()
                return

            radius = 4
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()

            pat = cairo.LinearGradient(0, 0, width, 0)
            for i, c in enumerate(cols):
                stop = i / max(len(cols) - 1, 1)
                pat.add_color_stop_rgb(stop, c.red, c.green, c.blue)

            cr.set_source(pat)
            cr.fill()

        gradient.set_draw_func(draw_gradient)

    def _create_preset_option_row(
        self,
        name: str,
        colors: tuple,
        preset_btn: Gtk.MenuButton,
        popover: Gtk.Popover,
        param_name: str,
    ) -> Gtk.Widget:
        """Create a preset option row with gradient and name."""
        row = Gtk.ListBoxRow()
        row.add_css_class("preset-row")

        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("preset-item-btn")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        # Gradient swatch
        gradient = Gtk.DrawingArea()
        gradient.set_size_request(80, 20)
        gradient.add_css_class("preset-gradient")

        # Parse colors
        rgba_colors = []
        for color_str in colors:
            rgba = Gdk.RGBA()
            if rgba.parse(str(color_str)):
                rgba_colors.append(rgba)

        def draw_gradient(area, cr, width, height, cols=rgba_colors):
            if not cols:
                cr.set_source_rgb(0.3, 0.3, 0.3)
                cr.rectangle(0, 0, width, height)
                cr.fill()
                return

            radius = 4
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()

            pat = cairo.LinearGradient(0, 0, width, 0)
            for i, c in enumerate(cols):
                stop = i / max(len(cols) - 1, 1)
                pat.add_color_stop_rgb(stop, c.red, c.green, c.blue)

            cr.set_source(pat)
            cr.fill()

        gradient.set_draw_func(draw_gradient)
        box.append(gradient)

        # Name label
        label = Gtk.Label(label=name)
        label.set_xalign(0)
        label.set_hexpand(True)
        label.add_css_class("preset-name")
        box.append(label)

        btn.set_child(box)

        def on_click(b, n=name, c=colors, pb=preset_btn, po=popover, pn=param_name):
            # Update button label and gradient
            if hasattr(pb, "_label"):
                pb._label.set_label(n)
            if hasattr(pb, "_gradient") and hasattr(pb, "_schemes"):
                gradient = cast(Gtk.DrawingArea, pb._gradient)
                self._setup_gradient_draw(gradient, c)
                gradient.queue_draw()
            po.popdown()
            self.emit("param-changed", pn, n)

        btn.connect("clicked", on_click)

        row.set_child(btn)
        return row

    def _create_color_list_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a multi-color picker row with preset selector."""
        _logger.debug(f"color_list widget: param={param}, current_value={current_value}")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.add_css_class("param-color-list-outer")

        # Preset dropdown row
        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preset_row.add_css_class("param-preset-row")

        preset_label = Gtk.Label(label="Preset")
        preset_label.add_css_class("param-preset-label")
        preset_row.append(preset_label)

        # Create preset selector with MenuButton + Popover (more reliable than DropDown)
        schemes = _get_sorted_schemes()
        scheme_values = {s[0]: s[1] for s in schemes}

        # MenuButton shows current selection
        preset_btn = Gtk.MenuButton()
        preset_btn.add_css_class("param-preset-btn")
        preset_btn.set_label("Select preset...")

        # Popover with scrollable list
        popover = Gtk.Popover()
        popover.add_css_class("param-preset-popover")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("preset-list")

        # Add preset rows with gradients
        for name, colors in schemes:
            row = self._create_preset_row(name, colors, preset_btn, popover, param["name"])
            listbox.append(row)

        scroll.set_child(listbox)
        popover.set_child(scroll)
        preset_btn.set_popover(popover)

        preset_row.append(preset_btn)
        outer.append(preset_row)

        # Color buttons row
        wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        wrapper.add_css_class("param-color-list")

        defaults = param.get("defaults", [])
        if not isinstance(defaults, (list, tuple)):
            defaults = [defaults]
        values = current_value if isinstance(current_value, (list, tuple)) else []

        min_len = int(param.get("min", 0) or 0)
        max_len = param.get("max")
        count = max(len(values), len(defaults), min_len)
        if isinstance(max_len, int):
            count = min(count, max_len)
        count = min(count, 6) if count else min(min_len or 2, 6)

        allow_empty = min_len == 0
        auto_toggle = None
        if allow_empty:
            auto_toggle = Gtk.ToggleButton(label="Auto")
            auto_toggle.add_css_class("param-toggle")
            auto_toggle.set_active(len(values) == 0)
            auto_toggle.connect("toggled", self._on_color_list_toggle, param["name"])
            wrapper.append(auto_toggle)

        # Resolve defaults - might be ColorScheme names or actual colors
        resolved_defaults = []
        for d in defaults:
            if isinstance(d, str) and not d.startswith("#"):
                # Might be a ColorScheme name
                try:
                    scheme = ColorScheme[d]
                    resolved_defaults.extend(scheme.value)
                except (KeyError, AttributeError):
                    # Not a scheme name, use as-is
                    resolved_defaults.append(d)
            else:
                resolved_defaults.append(d)

        buttons = []
        for idx in range(count):
            color_str = None
            if idx < len(values):
                color_str = values[idx]
            elif idx < len(resolved_defaults):
                color_str = resolved_defaults[idx]
            if not color_str:
                color_str = "#888888"  # Gray fallback instead of white

            btn = self._create_color_button(
                color_str,
                on_change=lambda _hex, name=param["name"]: self._emit_color_list(name),
                show_label=False,
                default_color=resolved_defaults[idx] if idx < len(resolved_defaults) else None,
            )
            btn.set_sensitive(not (auto_toggle and auto_toggle.get_active()))
            wrapper.append(btn)
            buttons.append(btn)

        outer.append(wrapper)

        # Store widget references
        self._widgets[param["name"]] = {
            "buttons": buttons,
            "toggle": auto_toggle,
            "preset_btn": preset_btn,
            "scheme_values": scheme_values,
        }

        return outer

    def _create_preset_row(
        self,
        name: str,
        colors: tuple,
        preset_btn: Gtk.MenuButton,
        popover: Gtk.Popover,
        param_name: str,
    ) -> Gtk.Widget:
        """Create a preset row with gradient and name."""
        row = Gtk.ListBoxRow()
        row.add_css_class("preset-row")

        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("preset-item-btn")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        # Gradient swatch
        gradient = Gtk.DrawingArea()
        gradient.set_size_request(80, 20)
        gradient.add_css_class("preset-gradient")

        # Parse colors
        rgba_colors = []
        for color_str in colors:
            rgba = Gdk.RGBA()
            if rgba.parse(str(color_str)):
                rgba_colors.append(rgba)

        def draw_gradient(area, cr, width, height, cols=rgba_colors):
            if not cols:
                cr.set_source_rgb(0.3, 0.3, 0.3)
                cr.rectangle(0, 0, width, height)
                cr.fill()
                return

            # Draw rounded rectangle with gradient
            radius = 4
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()

            pat = cairo.LinearGradient(0, 0, width, 0)
            for i, c in enumerate(cols):
                stop = i / max(len(cols) - 1, 1)
                pat.add_color_stop_rgb(stop, c.red, c.green, c.blue)

            cr.set_source(pat)
            cr.fill()

        gradient.set_draw_func(draw_gradient)
        box.append(gradient)

        # Name label
        label = Gtk.Label(label=name)
        label.set_xalign(0)
        label.set_hexpand(True)
        label.add_css_class("preset-name")
        box.append(label)

        btn.set_child(box)

        # Connect click to apply preset
        def on_preset_click(b, n=name, c=colors, pb=preset_btn, po=popover, pn=param_name):
            self._apply_preset(n, c, pb, po, pn)

        btn.connect("clicked", on_preset_click)

        row.set_child(btn)
        return row

    def _apply_preset(
        self,
        name: str,
        colors: tuple,
        preset_btn: Gtk.MenuButton,
        popover: Gtk.Popover,
        param_name: str,
    ):
        """Apply a preset to the color buttons."""
        # Update button label
        preset_btn.set_label(name)

        # Close popover
        popover.popdown()

        # Get widget info
        widget_info = self._widgets.get(param_name)
        if not isinstance(widget_info, dict):
            return

        buttons = widget_info.get("buttons", [])

        # Disable auto toggle if active
        toggle = widget_info.get("toggle")
        if toggle and toggle.get_active():
            toggle.set_active(False)

        # Update button colors
        for idx, btn in enumerate(buttons):
            if idx < len(colors):
                rgba = Gdk.RGBA()
                if rgba.parse(str(colors[idx])):
                    self._set_color_button_rgba(btn, rgba, emit=False, update_entry=True)

        # Emit change
        self._emit_color_list(param_name)

    def _create_range_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a slider with value label."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        min_val = param.get("min", 0)
        max_val = param.get("max", 100)
        step = param.get("step", 1)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, step)
        scale.set_draw_value(False)
        scale.set_size_request(100, -1)
        scale.add_css_class("param-scale")

        value = current_value if current_value is not None else param.get("default", min_val)
        scale.set_value(value)

        label = Gtk.Label()
        label.add_css_class("param-value")
        label.set_width_chars(4)

        def update_label(*_):
            val = scale.get_value()
            if step >= 1:
                label.set_label(str(int(val)))
            else:
                label.set_label(f"{val:.1f}")

        update_label()
        scale.connect("value-changed", update_label)
        scale.connect("value-changed", self._on_range_changed, param["name"])

        box.append(scale)
        box.append(label)

        return box

    def _create_choice_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a dropdown selector."""
        options = param.get("options", [])
        string_list = Gtk.StringList.new(options)

        dropdown = Gtk.DropDown(model=string_list)
        dropdown.add_css_class("param-dropdown")
        dropdown.set_size_request(100, -1)

        # Set current value
        value = current_value or param.get("default", options[0] if options else "")
        if value in options:
            dropdown.set_selected(options.index(value))

        dropdown.connect("notify::selected", self._on_choice_changed, param["name"], options)
        return dropdown

    def _create_toggle_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a toggle switch."""
        switch = Gtk.Switch()
        switch.add_css_class("param-switch")

        value = current_value if current_value is not None else param.get("default", False)
        switch.set_active(value)

        switch.connect("notify::active", self._on_toggle_changed, param["name"])
        return switch

    def _on_color_changed(self, btn, pspec, name):
        """Handle color change."""
        rgba = btn.get_rgba()
        hex_color = (
            f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        )
        self._emit_debounced(name, hex_color)

    def _on_color_list_toggle(self, btn, name):
        """Handle auto toggle for multi-color lists."""
        widget_info = self._widgets.get(name)
        if not isinstance(widget_info, dict):
            return
        for button in widget_info.get("buttons", []):
            button.set_sensitive(not btn.get_active())
        self._emit_color_list(name)

    def _on_color_list_changed(self, btn, pspec, name):
        """Handle multi-color list changes."""
        self._emit_color_list(name)

    def _emit_color_list(self, name: str):
        widget_info = self._widgets.get(name)
        if not isinstance(widget_info, dict):
            return
        toggle = widget_info.get("toggle")
        if toggle and toggle.get_active():
            self._emit_debounced(name, [])
            return

        values = []
        for button in widget_info.get("buttons", []):
            rgba = self._get_button_rgba(button)
            values.append(
                f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
            )
        self._emit_debounced(name, values)

    def _on_range_changed(self, scale, name):
        """Handle range change."""
        param = self._param_map.get(name, {})
        value = scale.get_value()
        if param.get("value_type") == "int":
            value = round(value)
        self._emit_debounced(name, value)

    def _on_choice_changed(self, dropdown, pspec, name, options):
        """Handle choice change."""
        idx = dropdown.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION and idx < len(options):
            self.emit("param-changed", name, options[idx])

    def _on_toggle_changed(self, switch, pspec, name):
        """Handle toggle change."""
        self.emit("param-changed", name, switch.get_active())

    def _emit_debounced(self, name: str, value, delay_ms: int = 100):
        """Emit param-changed with debounce for continuous controls."""
        # Cancel existing timer for this param
        if name in self._debounce_sources:
            GLib.source_remove(self._debounce_sources[name])

        # Set new timer
        self._debounce_sources[name] = GLib.timeout_add(
            delay_ms, self._emit_param_changed, name, value
        )

    def _emit_param_changed(self, name: str, value) -> bool:
        """Actually emit the signal (called after debounce)."""
        if name in self._debounce_sources:
            del self._debounce_sources[name]
        self.emit("param-changed", name, value)
        return False  # Don't repeat

    def get_values(self) -> dict:
        """Get all current parameter values."""
        values = {}
        for param in self._params:
            name = param["name"]
            widget = self._widgets.get(name)
            if not widget:
                continue

            if param["type"] == "color":
                rgba = self._get_button_rgba(widget)
                values[name] = (
                    f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
                )
            elif param["type"] == "color_list":
                if isinstance(widget, dict):
                    toggle = widget.get("toggle")
                    if toggle and toggle.get_active():
                        values[name] = []
                    else:
                        colors = []
                        for btn in widget.get("buttons", []):
                            rgba = self._get_button_rgba(btn)
                            colors.append(
                                f"#{int(rgba.red * 255):02x}"
                                f"{int(rgba.green * 255):02x}"
                                f"{int(rgba.blue * 255):02x}"
                            )
                        values[name] = colors
            elif param["type"] == "range":
                # Widget is a box with scale as first child
                scale = widget.get_first_child()
                value = scale.get_value()
                if param.get("value_type") == "int":
                    value = round(value)
                values[name] = value
            elif param["type"] == "color_preset":
                # Widget is a MenuButton, get label for current preset name
                label = widget.get_label()
                if label and label != "Select preset...":
                    values[name] = label
            elif param["type"] == "choice":
                idx = widget.get_selected()
                options = param.get("options", [])
                if idx != Gtk.INVALID_LIST_POSITION and idx < len(options):
                    values[name] = options[idx]
            elif param["type"] == "toggle":
                values[name] = widget.get_active()

        return values

    def clear(self):
        """Clear the inspector."""
        self._clear_params()
        self._empty.set_visible(True)
        self._params_box.set_visible(False)
        self._title.set_label("SETTINGS")
