# pylint: disable=invalid-name, too-many-instance-attributes, too-many-function-args
import asyncio
import logging

from abc import abstractmethod
from typing import NamedTuple

from traitlets import HasTraits, Float, Instance, observe, Unicode

from uchroma.input import InputQueue
from uchroma.frame import Frame
from uchroma.layer import Layer
from uchroma.traits import ColorTrait, WriteOnceInt
from uchroma.util import Ticker


MAX_FPS = 30
DEFAULT_FPS = 15
NUM_BUFFERS = 2


_RendererMeta = NamedTuple('_RendererMeta', [('display_name', str), ('description', str),
                                             ('author', str), ('version', str)])


class RendererMeta(_RendererMeta, Instance):

    read_only = True
    allow_none = False

    def __init__(self, display_name, description, author, version, *args, **kwargs):
        super(RendererMeta, self).__init__(klass=_RendererMeta, \
            args=(display_name, description, author, version), *args, **kwargs)


class Renderer(HasTraits):
    """
    Base class for custom effects renderers.
    """

    # traits
    meta = RendererMeta('_unknown_', 'Unimplemented', 'Unknown', '0')

    fps = Float(min=0.0, max=MAX_FPS, default_value=DEFAULT_FPS)
    blend_mode = Unicode()
    opacity = Float(min=0.0, max=1.0, default_value=1.0)
    background_color = ColorTrait()

    height = WriteOnceInt()
    width = WriteOnceInt()
    zorder = WriteOnceInt()

    def __init__(self, driver, zorder: int=0, *args, **kwargs):
        self._avail_q = asyncio.Queue(maxsize=NUM_BUFFERS)
        self._active_q = asyncio.Queue(maxsize=NUM_BUFFERS)

        self._running = False

        self.zorder = zorder
        self.width = driver.width
        self.height = driver.height

        self._tick = Ticker(1 / DEFAULT_FPS)

        self._input_queue = None
        if hasattr(driver, 'input_manager') and driver.input_manager is not None:
            self._input_queue = InputQueue(driver)

        self._logger = logging.getLogger('uchroma.%s.%d' % (self.__class__.__name__, zorder))
        self._logger.info('call super')
        super(Renderer, self).__init__(*args, **kwargs)


    def init(self, frame: Frame) -> bool:
        """
        Invoked by AnimationLoop when the effect is activated. At this
        point, the traits will have been set. An implementation
        should perform any final setup here.

        :param frame: The frame instance being configured

        :return: True if the renderer was configured
        """
        return False


    def finish(self, frame: Frame):
        """
        Invoked by AnimationLoop when the effect is deactivated.
        An implementation should perform cleanup tasks here.

        :param frame: The frame instance being shut down
        """
        pass


    @abstractmethod
    @asyncio.coroutine
    def draw(self, layer: Layer, timestamp: float) -> bool:
        """
        Coroutine called by AnimationLoop when a new frame needs
        to be drawn. If nothing should be drawn (such as if keyboard
        input is needed), then the implementation should yield until
        ready.

        :param frame: The current empty frame to be drawn
        :param timestamp: The timestamp of this frame

        :return: True if the frame has been drawn
        """
        return False


    @property
    def has_key_input(self) -> bool:
        """
        True if the device is capable of producing key events
        """
        return self._input_queue is not None


    @property
    def key_expire_time(self) -> float:
        """
        Gets the duration (in seconds) that key events will remain
        available.
        """
        return self._input_queue.expire_time


    @key_expire_time.setter
    def key_expire_time(self, expire_time: float):
        """
        Set the duration (in seconds) that key events should remain
        in the queue for. This allows the renderer to act on groups
        of key events over time. If zero, events are not kept after
        being dequeued.
        """
        self._input_queue.expire_time = expire_time


    @asyncio.coroutine
    def get_input_events(self):
        """
        Gets input events, yielding until at least one event is
        available. If expiration is not enabled, this returns
        a single item. Otherwise a list of all unexpired events
        is returned.
        """
        if not self.has_key_input:
            raise ValueError('Input events are not supported for this device')

        self._input_queue.attach()

        events = yield from self._input_queue.get_events()
        return events


    @observe('fps')
    def _fps_changed(self, change):
        self._tick.interval = 1 / self.fps


    @property
    def logger(self):
        """
        The logger for this instance
        """
        return self._logger


    def _free_layer(self, layer):
        """
        Clear the layer and return it to the queue

        Called by AnimationLoop after a layer is replaced on the
        active list. Implementations should not call this directly.
        """
        layer.lock(False)
        layer.clear()
        self._avail_q.put_nowait(layer)


    @asyncio.coroutine
    def _run(self):
        """
        Coroutine which dequeues buffers for drawing and queues them
        to the AnimationLoop when drawing is done.
        """
        if self._running:
            return

        self._running = True

        while self._running:
            with self._tick:
                # get a buffer, blocking if necessary
                layer = yield from self._avail_q.get()

                try:
                    # draw the layer
                    status = yield from self.draw(layer, asyncio.get_event_loop().time())
                except Exception as err:
                    self.logger.exception("Exception in renderer, exiting now!", exc_info=err)
                    self.logger.error('Renderer traits: %s', self._trait_values)
                    break

                if not self._running:
                    break

                # submit for composition
                if status:
                    layer.lock(True)
                    yield from self._active_q.put(layer)

            # FIXME: Use "async with" on Python 3.6+
            yield from self._tick.tick()

        self._stop()


    def _flush(self):
        if self._running:
            return
        for qlen in range(0, self._avail_q.qsize()):
            self._avail_q.get_nowait()
        for qlen in range(0, self._active_q.qsize()):
            self._active_q.get_nowait()


    def _stop(self):
        if not self._running:
            return

        self.logger.info("Stopping renderer")

        self._running = False

        self._flush()

        if self.has_key_input:
            self._input_queue.detach()
