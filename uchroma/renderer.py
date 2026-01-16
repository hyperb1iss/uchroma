#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name, too-many-instance-attributes, too-many-function-args

import asyncio
from abc import abstractmethod
from typing import NamedTuple

from traitlets import Bool, Float, HasTraits, Int, observe

from uchroma.blending import BlendOp
from uchroma.input_queue import InputQueue
from uchroma.layer import Layer
from uchroma.log import Log
from uchroma.traits import ColorTrait, DefaultCaselessStrEnum, WriteOnceInt
from uchroma.util import Ticker

MAX_FPS = 30
DEFAULT_FPS = 15
NUM_BUFFERS = 2


class RendererMeta(NamedTuple):
    display_name: str
    description: str
    author: str
    version: str


class Renderer(HasTraits):
    """
    Base class for custom effects renderers.
    """

    # traits
    meta = RendererMeta("_unknown_", "Unimplemented", "Unknown", "0")

    fps = Float(min=0.0, max=MAX_FPS, default_value=DEFAULT_FPS).tag(config=True)
    blend_mode = DefaultCaselessStrEnum(
        BlendOp.get_modes(), default_value="screen", allow_none=False
    ).tag(config=True)
    opacity = Float(min=0.0, max=1.0, default_value=1.0).tag(config=True)
    background_color = ColorTrait().tag(config=True)

    height = WriteOnceInt()
    width = WriteOnceInt()
    zindex = Int(default_value=-1)
    running = Bool(False)

    def __init__(self, driver, *args, **kwargs):
        self._avail_q = asyncio.Queue(maxsize=NUM_BUFFERS)
        self._active_q = asyncio.Queue(maxsize=NUM_BUFFERS)

        self.running = False

        self.width = driver.width
        self.height = driver.height

        self._tick = Ticker(1 / DEFAULT_FPS)

        self._input_queue = None
        if hasattr(driver, "input_manager") and driver.input_manager is not None:
            self._input_queue = InputQueue(driver)

        self._logger = Log.get(f"uchroma.{self.__class__.__name__}.{self.zindex}")
        super().__init__(*args, **kwargs)

    @observe("zindex")
    def _z_changed(self, change):
        if change.old == change.new and change.new >= 0:
            return

        self._logger = Log.get(f"uchroma.{self.__class__.__name__}.{change.new}")

    def init(self, frame) -> bool:
        """
        Invoked by AnimationLoop when the effect is activated. At this
        point, the traits will have been set. An implementation
        should perform any final setup here.

        :param frame: The frame instance being configured

        :return: True if the renderer was configured
        """
        return False

    def finish(self, frame):
        """
        Invoked by AnimationLoop when the effect is deactivated.
        An implementation should perform cleanup tasks here.

        :param frame: The frame instance being shut down
        """

    @abstractmethod
    async def draw(self, layer: Layer, timestamp: float) -> bool:
        """
        Coroutine called by AnimationLoop when a new frame needs
        to be drawn. If nothing should be drawn (such as if keyboard
        input is needed), then the implementation should yield until
        ready.

        :param layer: Layer to draw
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
        if self._input_queue is None:
            return 0.0
        return self._input_queue.expire_time

    @key_expire_time.setter
    def key_expire_time(self, expire_time: float):
        """
        Set the duration (in seconds) that key events should remain
        in the queue for. This allows the renderer to act on groups
        of key events over time. If zero, events are not kept after
        being dequeued.
        """
        if self._input_queue is not None:
            self._input_queue.expire_time = expire_time

    async def get_input_events(self):
        """
        Gets input events, yielding until at least one event is
        available. If expiration is not enabled, this returns
        a single item. Otherwise a list of all unexpired events
        is returned.
        """
        if not self.has_key_input or not self._input_queue.attach():
            raise ValueError("Input events are not supported for this device")

        events = await self._input_queue.get_events()
        return events

    @observe("fps")
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

    async def _run(self):
        """
        Coroutine which dequeues buffers for drawing and queues them
        to the AnimationLoop when drawing is done.
        """
        if self.running:
            return

        self.running = True

        while self.running:
            async with self._tick:
                # get a buffer, blocking if necessary
                layer = await self._avail_q.get()
                layer.background_color = self.background_color
                layer.blend_mode = self.blend_mode
                layer.opacity = self.opacity

                try:
                    # draw the layer
                    status = await self.draw(layer, asyncio.get_running_loop().time())
                except Exception as err:
                    self.logger.exception("Exception in renderer, exiting now!", exc_info=err)
                    self.logger.error("Renderer traits: %s", self._trait_values)
                    break

                if not self.running:
                    break

                # submit for composition
                if status:
                    layer.lock(True)
                    await self._active_q.put(layer)

        await self._stop()

    def _flush(self):
        if self.running:
            return
        for _qlen in range(self._avail_q.qsize()):
            self._avail_q.get_nowait()
        for _qlen in range(self._active_q.qsize()):
            self._active_q.get_nowait()

    async def _stop(self):
        if not self.running:
            return

        self.running = False

        self._flush()

        if self.has_key_input:
            await self._input_queue.detach()

        self.logger.info("Renderer stopped: z=%d", self.zindex)
