"""
Parameter Inspector Panel

Contextual parameter controls for selected effect or layer.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GLib, GObject, Gtk  # noqa: E402


class ParamInspector(Gtk.Box):
    """Contextual parameter inspector with horizontal layout."""

    __gtype_name__ = "UChromaParamInspector"

    __gsignals__: ClassVar[dict] = {
        "param-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),  # name, value
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self._params = []
        self._widgets = {}
        self._debounce_sources = {}

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

    def set_params(self, params: list, title: str = "SETTINGS", values: dict | None = None):
        """Set parameters to display.

        Args:
            params: List of param definitions
            title: Section title
            values: Optional dict of current values
        """
        self._clear_params()
        self._params = params
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

    def _create_param_widget(self, param: dict, current_value=None) -> Gtk.Widget:
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
            self._widgets[name] = widget

        # Wrap in FlowBoxChild
        child = Gtk.FlowBoxChild()
        child.set_child(box)

        return child

    def _create_color_widget(self, param: dict, current_value) -> Gtk.Widget:
        """Create a color picker button."""
        btn = Gtk.ColorDialogButton()
        btn.add_css_class("param-color")

        # Set color
        color_str = current_value or param.get("default", "#ffffff")
        rgba = Gdk.RGBA()
        rgba.parse(color_str)
        btn.set_rgba(rgba)

        btn.connect("notify::rgba", self._on_color_changed, param["name"])
        return btn

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

    def _on_range_changed(self, scale, name):
        """Handle range change."""
        self._emit_debounced(name, scale.get_value())

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
                rgba = widget.get_rgba()
                values[name] = (
                    f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
                )
            elif param["type"] == "range":
                # Widget is a box with scale as first child
                scale = widget.get_first_child()
                values[name] = scale.get_value()
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
