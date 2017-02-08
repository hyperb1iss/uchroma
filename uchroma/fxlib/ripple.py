# pylint: disable=invalid-name
import asyncio
import math
import operator

from traitlets import Int, observe

from uchroma.anim import Renderer, RendererMeta
from uchroma.color import ColorUtils
from uchroma.traits import ColorTrait
from uchroma.util import clamp


DEFAULT_SPEED = 5
DEFAULT_WIDTH = 3

EXPIRE_TIME_FACTOR = 0.15

COLOR_KEY = 'ripple_color'
SCHEME_KEY = 'color_scheme'


class Ripple(Renderer):

    # meta
    meta = RendererMeta('Ripples', 'Ripples of color when keys are pressed',
                        'Steve Kondik', '1.0')

    # configurable traits
    ripple_width = Int(default_value=DEFAULT_WIDTH, min=1, max=5)
    speed = Int(default_value=DEFAULT_SPEED, min=1, max=9)
    color = ColorTrait()
    base_color = ColorTrait()

    def __init__(self, *args, **kwargs):

        super(Ripple, self).__init__(*args, **kwargs)

        self._generator = None
        self._max_distance = None

        self.key_expire_time = DEFAULT_SPEED * EXPIRE_TIME_FACTOR

        self.fps = 30


    @observe('speed')
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


    def _draw_circles(self, layer, radius, event):
        width = self.ripple_width
        if COLOR_KEY not in event.data:
            return

        if event.coords is None or len(event.coords) == 0:
            self.logger.error('No coordinates available: %s', event)
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


    @observe('color', 'base_color')
    def _update_colors(self, change=None):
        if self.color is None and self.base_color is None:
            self._generator = ColorUtils.rainbow_generator()
        else:
            self._generator = ColorUtils.scheme_generator(
                color=self.color, base_color=self.base_color)


    def init(self, frame) -> bool:

        if not self.has_key_input:
            return False

        self._max_distance = math.hypot(frame.width, frame.height)

        self._update_colors()

        return True
