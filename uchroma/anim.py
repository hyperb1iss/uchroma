# pylint: disable=unused-argument, no-member, no-self-use, protected-access, not-an-iterable, invalid-name
import asyncio
import importlib
import logging
import types

from abc import abstractmethod
from collections import OrderedDict
from concurrent import futures
from typing import NamedTuple

import numpy as np

from uchroma.input import InputQueue
from uchroma.frame import Frame
from uchroma.layer import Layer
from uchroma.util import examine, Ticker


MAX_FPS = 30
DEFAULT_FPS = 15
NUM_BUFFERS = 2


class Renderer(object):
    """
    Base class for custom effects renderers.
    """

    def __init__(self, driver, name: str, zorder: int=0, *args, **kwargs):
        self._avail_q = asyncio.Queue(maxsize=NUM_BUFFERS)
        self._active_q = asyncio.Queue(maxsize=NUM_BUFFERS)

        self._running = False
        self._name = name
        self._zorder = zorder
        self._tick = Ticker(1 / DEFAULT_FPS)

        self._input_queue = None
        if driver.input_manager is not None:
            self._input_queue = InputQueue(driver)

        self._logger = logging.getLogger("uchroma.%s" % (name))

        super(Renderer, self).__init__(*args, **kwargs)


    def init(self, frame: Frame, **kwargs) -> bool:
        """
        Invoked by AnimationLoop when the effect is activated. An
        arbitrary set of arguments may be passed, and an implementation
        should performa any necessary setup here.

        :param frame: The frame instance being configured
        :param args: Arbitrary arguments

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
    def name(self) -> str:
        """
        The identifier of this renderer
        """
        return self._name


    @property
    def zorder(self) -> int:
        """
        The z-order of this layer, if stacked
        """
        return self._zorder


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


    @property
    def fps(self) -> float:
        return 1 / self._tick.interval


    @fps.setter
    def fps(self, value: float):
        if value > MAX_FPS:
            raise ValueError("Maximum FPS is %d" % MAX_FPS)

        self._tick.interval = 1 / value


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


    def _stop(self):
        if not self._running:
            return

        self.logger.info("Stopping renderer")

        self._running = False
        if self.has_key_input:
            self._input_queue.detach()


class AnimationLoop(object):
    """
    Collects the output of one or more Renderers and displays the
    composited image.

    The loop is a fully asynchronous design, and renderers may independently
    block or yield buffers at different rates. Each renderer has a pair of
    asyncio.Queue objects and will put buffers onto the "active" queue when
    their draw cycle is completed. The loop yields on these queues until
    at least one buffer is available. All new buffers are placed on the
    "active" list and the previous buffers are returned to the respective
    renderer on the "avail" queue. If a renderer doesn't produce any output
    during the round, the current buffer is kept. The active list is finally
    composed and sent to the hardware.

    The design of this loop intends to be as CPU-efficient as possible and
    does not wake up spuriously or otherwise consume cycles while inactive.
    """
    def __init__(self, frame: Frame, *renderers: Renderer, default_blend_mode: str=None):
        self._frame = frame
        self._renderers = list(renderers)
        self._default_blend_mode = default_blend_mode

        self._running = False
        self._anim_task = None
        self._error = False

        self._waiters = []
        self._tasks = []

        self._bufs = None
        self._active_bufs = None

        self.logger = logging.getLogger('uchroma.animloop')


    @asyncio.coroutine
    def _dequeue(self, r_idx: int):
        """
        Gather completed layers from the renderers. If nothing
        is available, keep the last layer (in case the renderers
        are producing output at different rates). Yields until
        at least one layer is ready.
        """
        if not self._running or r_idx >= len(self._renderers):
            return

        renderer = self._renderers[r_idx]

        # wait for a buffer
        buf = yield from renderer._active_q.get()

        # return the old buffer to the renderer
        if self._active_bufs[r_idx] is not None:
            renderer._free_layer(self._active_bufs[r_idx])

        # put it on the active list
        self._active_bufs[r_idx] = buf


    def _dequeue_nowait(self, r_idx) -> bool:
        """
        Variation of _dequeue which does not yield.

        :return: True if any layers became active
        """
        if not self._running or r_idx >= len(self._renderers):
            return False

        renderer = self._renderers[r_idx]

        # check if a buffer is ready
        if not renderer._active_q.empty():
            buf = renderer._active_q.get_nowait()
            if buf is not None:

                # return the last buffer
                if self._active_bufs[r_idx] is not None:
                    renderer._free_layer(self._active_bufs[r_idx])

                # put it on the composition list
                self._active_bufs[r_idx] = buf
                return True

        return False


    @asyncio.coroutine
    def _get_layers(self):
        """
        Wait for renderers to produce new layers, yields until at least one
        layer is active.
        """
        # schedule tasks to wait on each renderer queue
        for r_idx in range(0, len(self._renderers)):
            if self._waiters[r_idx] is None or self._waiters[r_idx].done():
                self._waiters[r_idx] = asyncio.ensure_future(self._dequeue(r_idx))

        # async wait for at least one completion
        yield from asyncio.wait(self._waiters, return_when=futures.FIRST_COMPLETED)

        # check the rest without waiting
        for r_idx in range(0, len(self._renderers)):
            if self._waiters[r_idx] is not None and not self._waiters[r_idx].done():
                self._dequeue_nowait(r_idx)


    def _commit_layers(self):
        """
        Merge layers from all renderers and commit to the hardware
        """
        self._frame.commit(self._active_bufs)


    @asyncio.coroutine
    def _animate(self):
        """
        Main loop

        Starts the renderers, waits for new layers to be drawn,
        composites the layers, sends them to the hardware, and
        finally syncs to achieve consistent frame rate. If no
        layers are ready, the loop yields to prevent spurious
        wakeups.
        """
        self.logger.info("AnimationLoop is starting..")

        # start the renderers
        for renderer in self._renderers:
            self._tasks.append(asyncio.ensure_future(renderer._run()))

        tick = Ticker(1 / MAX_FPS)

        # loop forever, waiting for layers
        while self._running:
            with tick:
                yield from self._get_layers()

                if not self._running or self._error:
                    break

                # compose and display the frame
                self._commit_layers()

            # FIXME: Use "async with" on Python 3.6+
            yield from tick.tick()

        self.logger.info("AnimationLoop is exiting..")

        if self._error:
            self.logger.error("Shutting down event loop due to error")

        yield from asyncio.gather(*self._tasks)


    def _renderer_done(self, future):
        """
        Invoked when the renderer exits
        """
        self.logger.info("AnimationLoop is cleaning up")
        for renderer in self._renderers:
            renderer.finish(self._frame)

        self._renderers.clear()

        self._anim_task = None
        self._error = False
        self._frame.reset()


    def _create_buffers(self):
        """
        Creates a pair of buffers for each renderer and sets up
        the bookkeeping.
        """
        self._waiters = list((None,) * len(self._renderers))

        # active buffer list
        self._active_bufs = np.array((None,) * len(self._renderers))

        # load up the renderers with layers to draw on
        for r_idx in range(0, len(self._renderers)):
            for buf in range(0, NUM_BUFFERS):
                layer = self._frame.create_layer()
                layer.blend_mode = self._default_blend_mode
                self._renderers[r_idx]._free_layer(layer)


    def start(self) -> bool:
        """
        Start the AnimationLoop

        Initializes the renderers, zeros the buffers, and starts the loop.

        Requires an active asyncio event loop.

        :return: True if the loop was started
        """
        if self._running:
            self.logger.error("Animation loop already running")
            return False

        if len(self._renderers) == 0:
            self.logger.error("No renderers were configured")
            return False

        self._frame.reset()

        self._running = True

        self._create_buffers()

        self._anim_task = asyncio.ensure_future(self._animate())
        self._anim_task.add_done_callback(self._renderer_done)

        return True


    @asyncio.coroutine
    def stop(self):
        """
        Stop this AnimationLoop

        Shuts down the loop and triggers cleanup tasks.
        """
        if not self._running:
            return False

        self._running = False

        for renderer in self._renderers:
            renderer._stop()

        for task in self._tasks:
            if not task.done():
                task.cancel()

        for waiter in self._waiters:
            if not waiter.done():
                waiter.cancel()

        if self._anim_task is not None and not self._anim_task.done():
            self._anim_task.cancel()

        yield from asyncio.wait([*self._tasks, *self._waiters, self._anim_task],
                                return_when=asyncio.ALL_COMPLETED)

        self.logger.info("AnimationLoop stopped")


RendererMeta = NamedTuple('RendererMetadata', [('module', types.ModuleType),
                                               ('clazz', type),
                                               ('name', str),
                                               ('description', str),
                                               ('args', OrderedDict)])

class AnimationManager(object):
    """
    Configures and manages animations of one or more renderers
    """

    def __init__(self, driver):
        self._driver = driver
        self._renderers = OrderedDict()
        self._loop = None
        self._running = False

        self._logger = logging.getLogger('uchroma.animmgr')

        # TODO: Get a proper plugin system going
        self._metadata = OrderedDict()
        self._fxlib = importlib.import_module('uchroma.fxlib')
        self._discover_renderers()


    def _discover_renderers(self):
        for item in self._fxlib.__dir__():
            obj = getattr(self._fxlib, item)
            if isinstance(obj, type) and issubclass(obj, Renderer):
                meta = RendererMeta(self._fxlib, obj, obj.__name__, None,
                                    examine(getattr(obj, 'init')))
                self._metadata[obj.__name__.lower()] = meta


    def _get_renderer(self, name) -> Renderer:
        """
        Instantiate a renderer

        :param name: Name of the discovered renderer

        :return: The renderer object
        """
        if name.lower() not in self._metadata:
            self._logger.error("Unknown renderer: %s", name)
            return None

        meta = self._metadata[name.lower()]

        try:
            zorder = len(self._renderers)
            name = 'anim-%s-%s.%d' % (self._driver.serial_number, meta.name, zorder)
            return meta.clazz(self._driver, name, zorder)

        except ImportError as err:
            self._logger.exception('Invalid renderer: %s', name, exc_info=err)

        return None


    def add_renderer(self, name, **kwargs) -> str:
        """
        Adds a renderer which will produce a layer of this animation.
        Any number of renderers may be added and the output will be
        composited together. The z-order of the layers corresponds to
        the order renderers were added, with the first producing the
        base layer and hte last producing the topmost layer.

        Renderers may be loaded from any valid Python package, the
        default is "uchroma.fxlib".

        The loop must not be running when this is called.

        :param renderer: Class of the renderer (string or type object)
        :param module: Module where the renderer lives
        :param *: Renderer-specific configuration arguments

        :return: A cookie which can be used to reconfigure the renderer (TODO)
        """
        renderer = self._get_renderer(name)
        if renderer is None:
            self._logger.error('Renderer %s failed to load', renderer)
            return None

        if not renderer.init(self._driver.frame_control, **kwargs):
            self._logger.error('Renderer %s failed to initialize', renderer.name)
            return None

        self._renderers[renderer.name] = renderer

        return renderer.name


    def start(self, blend_mode: str=None) -> bool:
        """
        Start the renderers added via add_renderer

        Initializes the animation loop and starts the action.

        :return: True if the animation was started successfully
        """
        if self._renderers is None or len(self._renderers) == 0:
            self._logger.error('No renderers were configured')
            return False

        self._loop = AnimationLoop(self._driver.frame_control,
                                   *self._renderers.values(),
                                   default_blend_mode=blend_mode)

        if self._loop.start():
            self._running = True
            return True

        return False


    @asyncio.coroutine
    def stop(self) -> bool:
        """
        Stop the currently running animation

        Cleans up the renderers and stops the animation loop.
        """
        if not self._running:
            return False

        result = yield from self._loop.stop()
        self._renderers.clear()
        self._running = False

        return result


    @property
    def is_running(self) -> bool:
        """
        True if an animation is currently running
        """
        return self._running


    @property
    def available_renderers(self) -> OrderedDict:
        """
        The map of discovered renderers
        """
        return self._metadata


    def __del__(self):
        if self.is_running:
            self.stop()
