"""
Effects Page

Effect selection with visual cards and dynamic parameter controls.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gdk, GLib, GObject, Gtk


# Effect definitions with metadata
EFFECTS = [
    {
        'id': 'disable',
        'name': 'Off',
        'description': 'Turn off all lighting',
        'icon': 'system-shutdown-symbolic',
        'preview_class': 'off',
        'params': [],
    },
    {
        'id': 'static',
        'name': 'Static',
        'description': 'Solid color across all keys',
        'icon': 'color-select-symbolic',
        'preview_class': 'static',
        'params': [
            {'name': 'color', 'type': 'color', 'default': '#e135ff'},
        ],
    },
    {
        'id': 'wave',
        'name': 'Wave',
        'description': 'Flowing wave of colors',
        'icon': 'weather-windy-symbolic',
        'preview_class': 'wave',
        'params': [
            {'name': 'direction', 'type': 'choice', 'options': ['LEFT', 'RIGHT'], 'default': 'RIGHT'},
        ],
    },
    {
        'id': 'spectrum',
        'name': 'Spectrum',
        'description': 'Cycle through all colors',
        'icon': 'weather-clear-symbolic',
        'preview_class': 'spectrum',
        'params': [],
    },
    {
        'id': 'reactive',
        'name': 'Reactive',
        'description': 'Keys light up when pressed',
        'icon': 'input-keyboard-symbolic',
        'preview_class': 'reactive',
        'params': [
            {'name': 'color', 'type': 'color', 'default': '#80ffea'},
            {'name': 'speed', 'type': 'range', 'min': 1, 'max': 4, 'default': 2},
        ],
    },
    {
        'id': 'breathe',
        'name': 'Breathe',
        'description': 'Pulsing color effect',
        'icon': 'weather-fog-symbolic',
        'preview_class': 'breathe',
        'params': [
            {'name': 'color1', 'type': 'color', 'default': '#e135ff'},
            {'name': 'color2', 'type': 'color', 'default': '#80ffea'},
        ],
    },
    {
        'id': 'starlight',
        'name': 'Starlight',
        'description': 'Twinkling stars effect',
        'icon': 'starred-symbolic',
        'preview_class': 'starlight',
        'params': [
            {'name': 'color1', 'type': 'color', 'default': '#e135ff'},
            {'name': 'color2', 'type': 'color', 'default': '#80ffea'},
            {'name': 'speed', 'type': 'range', 'min': 1, 'max': 4, 'default': 2},
        ],
    },
    {
        'id': 'ripple',
        'name': 'Ripple',
        'description': 'Ripples emanate from key presses',
        'icon': 'emblem-synchronizing-symbolic',
        'preview_class': 'ripple',
        'params': [
            {'name': 'color', 'type': 'color', 'default': '#ff6ac1'},
        ],
    },
]


class EffectCard(Gtk.FlowBoxChild):
    """Visual card for effect selection."""

    __gtype_name__ = 'UChromaEffectCard'

    def __init__(self, effect_data):
        super().__init__()

        self.effect_data = effect_data
        self.effect_id = effect_data['id']

        self._build_ui()

    def _build_ui(self):
        """Build the card UI."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class('effect-card')
        box.set_size_request(140, 100)

        # Icon
        icon = Gtk.Image.new_from_icon_name(self.effect_data['icon'])
        icon.add_css_class('effect-icon')
        icon.set_pixel_size(32)
        box.append(icon)

        # Name
        name = Gtk.Label(label=self.effect_data['name'])
        name.add_css_class('effect-name')
        box.append(name)

        # Preview bar
        preview = Gtk.Box()
        preview.add_css_class('effect-preview')
        preview.add_css_class(self.effect_data['preview_class'])
        box.append(preview)

        self.set_child(box)

    def set_active(self, active: bool):
        """Set whether this card is active."""
        if active:
            self.get_child().add_css_class('active')
        else:
            self.get_child().remove_css_class('active')


class EffectsPage(Adw.PreferencesPage):
    """Effects selection and configuration page."""

    __gtype_name__ = 'UChromaEffectsPage'

    def __init__(self):
        super().__init__()

        self._device = None
        self._current_effect = None
        self._cards = {}
        self._param_widgets = {}

        self.set_title('Effects')
        self.set_icon_name('starred-symbolic')

        self._build_ui()

    def _build_ui(self):
        """Build the effects page UI."""
        # === EFFECTS SELECTION GROUP ===
        self.effects_group = Adw.PreferencesGroup()
        self.effects_group.set_title('EFFECTS')
        self.effects_group.set_description('Select a lighting effect')
        self.add(self.effects_group)

        # Flow box for effect cards
        self.effects_flow = Gtk.FlowBox()
        self.effects_flow.set_homogeneous(True)
        self.effects_flow.set_min_children_per_line(2)
        self.effects_flow.set_max_children_per_line(4)
        self.effects_flow.set_column_spacing(12)
        self.effects_flow.set_row_spacing(12)
        self.effects_flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.effects_flow.connect('child-activated', self._on_effect_selected)

        # Add effect cards
        for effect in EFFECTS:
            card = EffectCard(effect)
            self.effects_flow.append(card)
            self._cards[effect['id']] = card

        # Wrap in a row-like container
        flow_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        flow_box.set_margin_start(12)
        flow_box.set_margin_end(12)
        flow_box.set_margin_top(12)
        flow_box.set_margin_bottom(12)
        flow_box.append(self.effects_flow)
        self.effects_group.add(flow_box)

        # === EFFECT PARAMETERS GROUP ===
        self.params_group = Adw.PreferencesGroup()
        self.params_group.set_title('EFFECT SETTINGS')
        self.params_group.set_visible(False)
        self.add(self.params_group)

    def set_device(self, device):
        """Set the current device."""
        self._device = device

        if device:
            # Select current effect card
            if device.current_fx and device.current_fx in self._cards:
                self._select_effect(device.current_fx)

    def _on_effect_selected(self, flow_box, child):
        """Handle effect card selection."""
        if not child:
            return

        effect_id = child.effect_id
        self._select_effect(effect_id)

        # Apply effect to device
        if self._device:
            self._apply_effect(effect_id)

    def _select_effect(self, effect_id: str):
        """Select an effect and update UI."""
        # Update card states
        for eid, card in self._cards.items():
            card.set_active(eid == effect_id)

        self._current_effect = effect_id

        # Build parameter UI
        self._build_params_ui(effect_id)

    def _build_params_ui(self, effect_id: str):
        """Build parameter controls for the selected effect."""
        # Clear existing params
        while True:
            child = self.params_group.get_first_child()
            if child is None:
                break
            if hasattr(child, '__gtype_name__') and 'Preferences' not in child.__gtype_name__:
                break
            self.params_group.remove(child)

        self._param_widgets.clear()

        # Find effect data
        effect_data = next((e for e in EFFECTS if e['id'] == effect_id), None)
        if not effect_data or not effect_data['params']:
            self.params_group.set_visible(False)
            return

        self.params_group.set_visible(True)

        # Create parameter widgets
        for param in effect_data['params']:
            row = self._create_param_row(param)
            if row:
                self.params_group.add(row)

    def _create_param_row(self, param) -> Gtk.Widget:
        """Create a row widget for a parameter."""
        name = param['name'].replace('_', ' ').title()

        if param['type'] == 'color':
            row = Adw.ActionRow()
            row.set_title(name)

            color_btn = Gtk.ColorDialogButton()
            color_btn.set_valign(Gtk.Align.CENTER)

            # Set default color
            rgba = Gdk.RGBA()
            rgba.parse(param.get('default', '#ffffff'))
            color_btn.set_rgba(rgba)

            color_btn.connect('notify::rgba', self._on_param_changed, param['name'])
            row.add_suffix(color_btn)

            self._param_widgets[param['name']] = color_btn
            return row

        elif param['type'] == 'range':
            row = Adw.SpinRow.new_with_range(
                param['min'],
                param['max'],
                1
            )
            row.set_title(name)
            row.set_value(param.get('default', param['min']))
            row.connect('notify::value', self._on_param_changed, param['name'])

            self._param_widgets[param['name']] = row
            return row

        elif param['type'] == 'choice':
            row = Adw.ComboRow()
            row.set_title(name)

            model = Gtk.StringList.new(param['options'])
            row.set_model(model)

            default_idx = param['options'].index(param.get('default', param['options'][0]))
            row.set_selected(default_idx)

            row.connect('notify::selected', self._on_param_changed, param['name'])

            self._param_widgets[param['name']] = row
            return row

        return None

    def _on_param_changed(self, widget, pspec, param_name):
        """Handle parameter value change."""
        if not self._device or not self._current_effect:
            return

        # Collect all params and reapply effect
        params = self._collect_params()
        self._apply_effect(self._current_effect, params)

    def _collect_params(self) -> dict:
        """Collect current parameter values."""
        params = {}

        for name, widget in self._param_widgets.items():
            if isinstance(widget, Gtk.ColorDialogButton):
                rgba = widget.get_rgba()
                params[name] = rgba.to_string()
            elif isinstance(widget, Adw.SpinRow):
                params[name] = int(widget.get_value())
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
            asyncio.create_task(
                app.dbus.set_effect(self._device.path, effect_id, params)
            )
