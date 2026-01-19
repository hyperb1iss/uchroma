#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name

import math
import time
from dataclasses import dataclass

from traitlets import Bool, Int, observe

from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorTrait
from uchroma.util import clamp

DEFAULT_SPEED = 5
DEFAULT_WIDTH = 3

EXPIRE_TIME_FACTOR = 0.15

COLOR_KEY = "ripple_color"


@dataclass
class RippleInstance:
    coords: list
    colors: list
    start_time: float
    duration: float


class Ripple(Renderer):
    # meta
    meta = RendererMeta("Ripples", "Ripples of color when keys are pressed", "Stefanie Jane", "1.0")

    # configurable traits
    ripple_width = Int(default_value=DEFAULT_WIDTH, min=1, max=5).tag(config=True)
    speed = Int(default_value=DEFAULT_SPEED, min=1, max=9).tag(config=True)
    preset = ColorPresetTrait(ColorScheme, default_value=None).tag(config=True)
    random = Bool(False).tag(config=True, label="Auto Colors")
    color = ColorTrait().tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._generator = ColorUtils.rainbow_generator()
        self._max_distance: float | None = None
        self._ripples: list[RippleInstance] = []
        self._last_event_ts = {}
        self.key_expire_time = DEFAULT_SPEED * EXPIRE_TIME_FACTOR

        self.fps = 30

    @observe("speed")
    def _set_speed(self, change):
        self.key_expire_time = change.new * EXPIRE_TIME_FACTOR

    def _process_events(self, events):
        if self._generator is None:
            return None

        for event in events:
            if COLOR_KEY not in event.data:
                event.data[COLOR_KEY] = next(self._generator)

    @staticmethod
    def _ease(n):
        n = clamp(n, 0.0, 1.0)
        n = 2 * n
        if n < 1:
            return 0.5 * n**5

        n = n - 2
        return 0.5 * (n**5 + 2)

    def _draw_circles(self, layer, radius, ripple: RippleInstance):
        width = self.ripple_width
        if not ripple.coords:
            return
        colors = ripple.colors

        for circle_num in range(width - 1, -1, -1):
            if radius - circle_num < 0:
                continue

            rad = radius - circle_num
            a = Ripple._ease(1.0 - (rad / self._max_distance))
            cc = (*colors[circle_num].rgb, colors[circle_num].alpha() * a)

            for coord in ripple.coords:
                layer.ellipse(coord.y, coord.x, rad / 1.33, rad, color=cc)

    async def draw(self, layer, timestamp):
        """
        Draw the next layer
        """
        if not self.has_key_input or not self._input_queue.attach():
            return False

        events = self._input_queue.get_events_nowait()
        if events:
            self._process_events(events)
            for event in events:
                if not event.coords:
                    continue
                last_ts = self._last_event_ts.get(event.keycode)
                if last_ts is not None and event.timestamp <= last_ts:
                    continue
                self._last_event_ts[event.keycode] = event.timestamp

                color = event.data.get(COLOR_KEY)
                if color is None:
                    continue
                if self.ripple_width > 1:
                    colors = ColorUtils.color_scheme(
                        color=color, base_color=color, steps=self.ripple_width
                    )
                else:
                    colors = [color]

                duration = max(0.01, event.expire_time - event.timestamp)
                self._ripples.append(
                    RippleInstance(
                        coords=event.coords,
                        colors=colors,
                        start_time=event.timestamp,
                        duration=duration,
                    )
                )

        now = time.time()
        active = []
        if self._max_distance is None:
            return False
        for ripple in self._ripples:
            elapsed = now - ripple.start_time
            if elapsed < 0:
                continue
            progress = elapsed / ripple.duration
            if progress >= 1.0:
                continue
            radius = self._max_distance * progress
            self._draw_circles(layer, radius, ripple)
            active.append(ripple)

        self._ripples = active
        return True

    @observe("preset", "color", "background_color", "random")
    def _update_colors(self, change=None):
        with self.hold_trait_notifications():
            if change.new is None:
                return

            if change.name == "preset":
                self.color = "black"
                self.random = False
                self._generator = ColorUtils.color_generator(list(change.new.value))
            elif change.name == "random" and change.new:
                self.preset = None
                self.color = "black"
                self._generator = ColorUtils.rainbow_generator()
            else:
                self.preset = None
                self.random = False
                base_color = self.background_color
                if base_color == (0, 0, 0, 1):
                    base_color = None
                if self.color is None and base_color is None:
                    self._generator = ColorUtils.rainbow_generator()
                else:
                    self._generator = ColorUtils.scheme_generator(
                        color=self.color, base_color=base_color
                    )

    def init(self, frame) -> bool:
        if not self.has_key_input:
            return False

        self._max_distance = math.hypot(frame.width, frame.height)
        self._ripples = []
        self._last_event_ts = {}

        return True
