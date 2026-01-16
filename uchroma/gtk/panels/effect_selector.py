#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Effect Selector Panel

Horizontal flow of effect cards for hardware FX selection.
"""

from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk  # noqa: E402

from ..widgets.effect_card import EffectCard  # noqa: E402


class EffectSelector(Gtk.Box):
    """Horizontal effect card selector."""

    __gtype_name__ = "UChromaEffectSelector"

    __gsignals__: ClassVar[dict] = {
        "effect-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self._selected_effect = None
        self._cards = {}
        self._effects = []

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

        self._flow.set_valign(Gtk.Align.START)

        scroll.set_child(self._flow)
        self.append(scroll)

    def _on_card_activated(self, card, effect_id):
        """Handle card click."""
        self.select_effect(effect_id)
        self.emit("effect-selected", effect_id)

    def set_effects(self, effects: list[dict]):
        """Update effect list."""
        self._effects = effects
        self._cards.clear()

        child = self._flow.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._flow.remove(child)
            child = next_child

        for effect in effects:
            effect_id: str = effect["id"]  # type: ignore[assignment]
            effect_name: str = effect["name"]  # type: ignore[assignment]
            effect_icon: str = effect.get("icon", "starred-symbolic")  # type: ignore[assignment]
            preview_class: str = effect.get("preview", "default")  # type: ignore[assignment]
            card = EffectCard(
                effect_id=effect_id,
                name=effect_name,
                icon=effect_icon,
                preview_class=preview_class,
            )
            card.connect("effect-activated", self._on_card_activated)

            self._flow.append(card)
            self._cards[effect_id] = card

        if self._selected_effect:
            self.select_effect(self._selected_effect)

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
