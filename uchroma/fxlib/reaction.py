#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name

from traitlets import Int, observe

from uchroma.color import ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait

DEFAULT_SPEED = 6
MAX_SPEED = 9
EXPIRE_TIME_FACTOR = 0.25

REACT_COLOR_KEY = "reaction_color"


class Reaction(Renderer):
    """
    Reaction creates a two tone animation effect based on the 'react' fx
    Config Options:
     - background_color: the static color when no keys are active
     - color: the color the key will change to when pressed
     - speed: (1 - 9) how fast the keys will change back. 9 is the fastest.
    """

    meta = RendererMeta("Reaction", "Keys change color when pressed", "Ryan Burns", "1.0")

    # Configuration options
    speed = Int(default_value=DEFAULT_SPEED, min=1, max=MAX_SPEED).tag(config=True)
    background_color = ColorTrait().tag(config=True)
    color = ColorTrait().tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fps = 30

        # It seems like observers can be called before __init__
        # How is this possible?
        if not hasattr(self, "init_speed"):
            self._set_speed(DEFAULT_SPEED)

        if not hasattr(self, "init_colors"):
            self._set_colors("#000000", "#FFFFFF")

    @observe("speed")
    def _change_speed(self, change):
        """
        responds to speed changes made by the user
        """
        self.init_speed = True
        self._set_speed(change.new)

    def _set_speed(self, value):
        expire = MAX_SPEED + 1 - value
        self.key_expire_time = expire * EXPIRE_TIME_FACTOR

    def _set_colors(self, bg_color, color):
        self._gradient = ColorUtils.color_scheme(color=color, base_color=bg_color, steps=100)
        self._gradient_count = len(self._gradient)

    def _process_events(self, layer, events):
        """
        process events and assign a color to each one
        """
        if self._gradient is None:
            return None

        for event in events:
            if REACT_COLOR_KEY not in event.data:
                # percent_complete appears to go from 1 to 0.
                # perhaps it should be renamed percent_remaining?
                idx = int(self._gradient_count - (event.percent_complete * self._gradient_count))
                if event.percent_complete <= 0.15:
                    # TODO: Is there a better way to know if this will be
                    # the last event for this key press?
                    event.data[REACT_COLOR_KEY] = self.background_color
                else:
                    idx = max(0, min(self._gradient_count - 1, idx))
                    event.data[REACT_COLOR_KEY] = self._gradient[idx]

            self._react_keys(layer, event)

    def _react_keys(self, layer, event):
        """
        updates all the coordinates for an event with the appropriate color
        """
        if event.coords is None or len(event.coords) == 0:
            self.logger.error("No coordinates available: %s", event)
            return

        react_color = event.data[REACT_COLOR_KEY]
        for coord in event.coords:
            layer.put(coord.y, coord.x, react_color)

    async def draw(self, layer, timestamp):
        """
        Draw the next layer
        """
        if not self.has_key_input or not self._input_queue.attach():
            return False

        events = self._input_queue.get_events_nowait()
        if events:
            self._process_events(layer, events)

        return True

    @observe("background_color", "color")
    def _update_colors(self, change=None):
        """
        responds to color changes made by the user
        """
        with self.hold_trait_notifications():
            if change.new is None:
                return

            self.init_colors = True
            bg_color = self.background_color
            if bg_color == (0, 0, 0, 1):
                bg_color = None
            self._set_colors(bg_color, self.color)

    def init(self, frame) -> bool:
        return self.has_key_input
