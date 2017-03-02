# pylint: disable=invalid-name
import asyncio
import time

from traitlets import observe, Int

from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait

from ._plasma import draw_plasma


class Plasma(Renderer):
    """
    Draws a old-school plasma effect
    """

    # meta
    meta = RendererMeta('Plasma', 'Colorful moving blobs of plasma',
                        'Steve Kondik', 'v1.0')

    # configurable traits
    color_scheme = ColorSchemeTrait(minlen=2, \
            default_value=[*ColorScheme.Qap.value]).tag(config=True)
    preset = ColorPresetTrait(ColorScheme, \
            default_value=ColorScheme.Qap).tag(config=True)
    gradient_length = Int(default_value=360, min=0).tag(config=True)


    def __init__(self, *args, **kwargs):
        super(Plasma, self).__init__(*args, **kwargs)

        self._gradient = None
        self._start_time = 0
        self.fps = 15


    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(self.gradient_length, *self.color_scheme)


    @observe('color_scheme', 'gradient_length', 'preset')
    def _scheme_changed(self, changed):
        with self.hold_trait_notifications():
            self.logger.debug("Parameters changed: %s", changed)
            if changed.name == 'preset':
                self.color_scheme.clear()
                self.color_scheme = list(changed.new.value)
            self._gen_gradient()


    def init(self, frame):
        self._start_time = time.time()
        self._gen_gradient()
        return True


    @asyncio.coroutine
    def draw(self, layer, timestamp):
        duration = timestamp - self._start_time

        draw_plasma(layer.width, layer.height, layer.matrix, duration, self._gradient)

        return True
