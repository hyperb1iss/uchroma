# pylint: disable=unused-argument, no-member, no-self-use, protected-access, not-an-iterable, invalid-name
import asyncio
import importlib
import logging
import types

from collections import OrderedDict
from concurrent import futures
from typing import List, NamedTuple

from traitlets import Bool, Dict, HasTraits, List
import numpy as np

from uchroma.frame import Frame
from uchroma.renderer import MAX_FPS, NUM_BUFFERS, Renderer, RendererMeta
from uchroma.traits import get_args_dict
from uchroma.util import Ticker


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
            self._renderers[r_idx]._flush()

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

        self._running = True

        self._create_buffers()

        self._anim_task = asyncio.ensure_future(self._animate())
        self._anim_task.add_done_callback(self._renderer_done)

        return True


    @asyncio.coroutine
    def _stop(self):
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


    def stop(self):
        if not self._running:
            return False

        asyncio.ensure_future(self._stop())

        return True


RendererInfo = NamedTuple('RendererInfo', [('module', types.ModuleType),
                                           ('clazz', type),
                                           ('key', str),
                                           ('meta', RendererMeta)])

class AnimationManager(HasTraits):
    """
    Configures and manages animations of one or more renderers
    """

    renderers = List()
    renderer_info = Dict()
    running = Bool(False)

    def __init__(self, driver):
        super(AnimationManager, self).__init__()

        self._driver = driver

        self._loop = None

        self._logger = logging.getLogger('uchroma.animmgr')

        with self.hold_trait_notifications():
            # TODO: Get a proper plugin system going
            self.renderer_info = OrderedDict()

            self._fxlib = importlib.import_module('uchroma.fxlib')
            self._discover_renderers()

            self.renderers = []


    def _discover_renderers(self):
        for item in self._fxlib.__dir__():
            obj = getattr(self._fxlib, item)
            if isinstance(obj, type) and issubclass(obj, Renderer):
                if obj.meta.display_name == '_unknown_':
                    self._logger.error("Renderer %s did not set metadata, skipping",
                                       obj.__name__)
                    continue

                key = '%s.%s' % (obj.__module__, obj.__name__)
                info = RendererInfo(obj.__module__, obj, key, obj.meta)
                self.renderer_info[key] = info


    def _get_renderer(self, name, **traits) -> Renderer:
        """
        Instantiate a renderer

        :param name: Name of the discovered renderer

        :return: The renderer object
        """
        if name not in self.renderer_info:
            self._logger.error("Unknown renderer: %s", name)
            return None

        info = self.renderer_info[name]

        try:
            zorder = len(self.renderers)
            return info.clazz(self._driver, zorder, **traits)

        except ImportError as err:
            self._logger.exception('Invalid renderer: %s', name, exc_info=err)

        return None


    def add_renderer(self, name, **traits) -> int:
        """
        Adds a renderer which will produce a layer of this animation.
        Any number of renderers may be added and the output will be
        composited together. The z-order of the layers corresponds to
        the order renderers were added, with the first producing the
        base layer and hte last producing the topmost layer.

        Renderers may be loaded from any valid Python package, the
        default is "uchroma.fxlib".

        The loop must not be running when this is called.

        :param renderer: Key name of a discovered renderer

        :return: Z-position of the new renderer or -1 on error
        """
        renderer = self._get_renderer(name, **traits)
        if renderer is None:
            self._logger.error('Renderer %s failed to load', renderer)
            return -1

        if not renderer.init(self._driver.frame_control):
            self._logger.error('Renderer %s failed to initialize', renderer.name)
            return -1

        self.renderers = [*self.renderers, renderer]

        return renderer.zorder


    def start(self, blend_mode: str=None) -> bool:
        """
        Start the renderers added via add_renderer

        Initializes the animation loop and starts the action.

        :return: True if the animation was started successfully
        """
        if self.running:
            return False

        if self.renderers is None or len(self.renderers) == 0:
            self._logger.error('No renderers were configured')
            return False

        self._loop = AnimationLoop(self._driver.frame_control,
                                   *self.renderers,
                                   default_blend_mode=blend_mode)

        self._driver.reset()

        if self._loop.start():
            self.running = True

            layers = OrderedDict()
            for renderer in self.renderers:
                key = '%s.%s' % (renderer.__class__.__module__, renderer.__class__.__name__)
                layers[key] = get_args_dict(renderer)
            self._driver.preferences.layers = layers

            return True

        return False


    def stop(self) -> bool:
        """
        Stop the currently running animation

        Cleans up the renderers and stops the animation loop.
        """
        if not self.running:
            return False

        if self._loop.stop():
            self.running = False
            self._driver.reset()

            self._driver.preferences.layers = {}
            return True

        return False


    def clear_renderers(self) -> bool:
        """
        Clear the list of renderers
        """
        if self.running:
            return False

        self.renderers = []
        return True


    def reset(self):
        """
        Stop animations and clear the renderer list
        """
        self.stop()
        self.clear_renderers()


    def restore_prefs(self, prefs):
        if prefs.layers is not None and len(prefs.layers) > 0:
            try:
                for name, args in prefs.layers.items():
                    self.add_renderer(name, **args)
                self.start()

            except Exception as err:
                self._logger.exception('Failed to add renderers, clearing! [%s]',
                                       prefs.layers, exc_info=err)
                self.clear_renderers()
                prefs.layers = {}


    def __del__(self):
        if self.running:
            self.stop()
