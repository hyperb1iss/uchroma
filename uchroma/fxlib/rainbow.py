import asyncio

from traitlets import Int, observe
from grapefruit import Color

from uchroma.renderer import Renderer, RendererMeta


DEFAULT_SPEED = 8


class Rainbow(Renderer):

    # meta
    meta = RendererMeta('Rainflow', 'Simple flowing colors', 'Steve Kondik', '1.0')

    # configurable traits
    speed = Int(default_value=DEFAULT_SPEED, min=0, max=20).tag(config=True)
    stagger = Int(default_value=4, min=0, max=100).tag(config=True)


    def __init__(self, *args, **kwargs):
        super(Rainbow, self).__init__(*args, **kwargs)

        self._gradient = None
        self._offset = 0

        self.fps = 5


    @staticmethod
    def _hue_gradient(start, length):
        step = 360 / length
        return [Color.NewFromHsv((start + (step * x)) % 360, 1, 1) for x in range(0, length)]


    @observe('speed', 'stagger')
    def _create_gradient(self, change=None):
        self._offset = 0
        self._gradient = Rainbow._hue_gradient( \
            0, self.speed * self.width + (self.height * self.stagger))


    def init(self, frame):
        self._create_gradient()
        return True


    async def draw(self, layer, timestamp):
        data = []
        for row in range(0, layer.height):
            data.append( \
                [self._gradient[ \
                (self._offset + (row * self.stagger) + col) % len(self._gradient)] \
                for col in range(0, layer.width)])

        layer.put_all(data)
        self._offset = (self._offset + 1) % len(self._gradient)

        return True
