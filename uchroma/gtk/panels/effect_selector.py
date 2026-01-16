"""
Effect Selector Panel

Horizontal flow of effect cards for hardware FX selection.
"""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk

from ..widgets.effect_card import EFFECTS, EffectCard


class EffectSelector(Gtk.Box):
    """Horizontal effect card selector."""

    __gtype_name__ = "UChromaEffectSelector"

    __gsignals__ = {
        "effect-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self._selected_effect = None
        self._cards = {}

        self.add_css_class("effect-selector")
        self.set_margin_start(16)
        self.set_margin_end(16)

        self._build_ui()

    def _build_ui(self):
        """Build the effect selector UI."""
        # Scrolled container for horizontal flow
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scroll.set_vexpand(False)
        scroll.set_min_content_height(100)

        # Flow box for cards
        self._flow = Gtk.FlowBox()
        self._flow.set_homogeneous(True)
        self._flow.set_min_children_per_line(4)
        self._flow.set_max_children_per_line(10)
        self._flow.set_column_spacing(8)
        self._flow.set_row_spacing(8)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_valign(Gtk.Align.START)

        # Add effect cards
        for effect in EFFECTS:
            card = EffectCard(
                effect_id=effect["id"],
                name=effect["name"],
                icon=effect["icon"],
                preview_class=effect.get("preview", "default"),
            )
            card.connect("effect-activated", self._on_card_activated)

            self._flow.append(card)
            self._cards[effect["id"]] = card

        scroll.set_child(self._flow)
        self.append(scroll)

    def _on_card_activated(self, card, effect_id):
        """Handle card click."""
        self.select_effect(effect_id)
        self.emit("effect-selected", effect_id)

    def select_effect(self, effect_id: str):
        """Select an effect (update visual state)."""
        # Deselect previous
        if self._selected_effect and self._selected_effect in self._cards:
            self._cards[self._selected_effect].active = False

        # Select new
        self._selected_effect = effect_id
        if effect_id in self._cards:
            self._cards[effect_id].active = True

    @property
    def selected_effect(self) -> str | None:
        return self._selected_effect
