# pylint: disable=invalid-name
import asyncio
import math
import operator

from uchroma.anim import Renderer
from uchroma.color import ColorUtils, Splotch
from uchroma.util import clamp


DEFAULT_SPEED = 5
DEFAULT_WIDTH = 3

EXPIRE_TIME_FACTOR = 0.15

COLOR_KEY = 'ripple_color'
SCHEME_KEY = 'color_scheme'


class Ripple(Renderer):

    def __init__(self, *args, **kwargs):

        super(Ripple, self).__init__(*args, **kwargs)

        self._generator = None
        self._max_distance = None

        self._ripple_width = DEFAULT_WIDTH
        self._set_speed(DEFAULT_SPEED)


    def _set_speed(self, speed=DEFAULT_SPEED):
        self.key_expire_time = speed * EXPIRE_TIME_FACTOR


    def _set_ripple_width(self, width):
        self._ripple_width = width


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


    def _draw_circles(self, layer, radius, event):
        width = self._ripple_width
        if COLOR_KEY not in event.data:
            return

        if SCHEME_KEY in event.data:
            colors = event.data[SCHEME_KEY]
        else:
            color = event.data[COLOR_KEY]
            if width > 1:
                colors = ColorUtils.color_scheme(color=color, base_color=color, steps=width)
            else:
                colors = [color]
            event.data[SCHEME_KEY] = colors

        for circle_num in range(width - 1, -1, -1):
            if radius - circle_num < 0:
                continue

            rad = radius - circle_num
            a = Ripple._ease(1.0 - (rad / self._max_distance))
            cc = (*colors[circle_num].rgb, colors[circle_num].alpha * a)

            for coord in event.coords:
                layer.ellipse(coord.y, coord.x, rad / 1.33, rad, color=cc)


    @asyncio.coroutine
    def draw(self, layer, timestamp):
        """
        Draw the next layer
        """

        # Yield until the queue becomes active
        events = yield from self.get_input_events()

        if len(events) > 0:
            self._process_events(events)

            # paint circles in descending timestamp order (oldest first)
            events = sorted(events, key=operator.itemgetter(0), reverse=True)

            for event in events:
                distance = 1.0 - event.percent_complete
                if distance < 1.0:
                    radius = self._max_distance * distance

                    self._draw_circles(layer, radius, event)

            return True

        return False


    def init(self, frame, color=None, bg_color=None, preset_name=None,
             speed=DEFAULT_SPEED, ripple_width=DEFAULT_WIDTH, *args, **kwargs) -> bool:

        if not self.has_key_input:
            return False

        self._max_distance = math.hypot(frame.width, frame.height)
        self._ripple_width = ripple_width
        self._set_speed(speed)

        if preset_name is not None:
            splotch = Splotch.get(preset_name)
            if splotch is not None:
                bg_color = splotch.first()
                color = splotch.second()

        if bg_color is None or bg_color[0] is None:
            bg_color = None

        if color is None or color[0] is None:
            color = None

        if color is None and bg_color is None:
            self._generator = ColorUtils.rainbow_generator()
        else:
            self._generator = ColorUtils.scheme_generator(
                color=color, base_color=bg_color)

        frame.background_color = bg_color

        return True
