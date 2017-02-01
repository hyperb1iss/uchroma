# pylint: disable=unused-argument, no-member, no-self-use
import asyncio
import importlib
import logging
import sys
import time

from uchroma.frame import Frame


DEFAULT_FPS = 15


class Renderer(object):
    """
    Base class for custom effects renderers.
    """

    def __init__(self, *args, **kwargs):
        super(Renderer, self).__init__(*args, **kwargs)


    @asyncio.coroutine
    def draw(self, frame: Frame, timestamp: float) -> bool:
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


    def init(self, frame: Frame, *args, **kwargs) -> bool:
        """
        Invoked by AnimationLoop when the effect is activated. An
        arbitrary set of arguments may be passed, and an implementation
        should performa any necessary setup here.

        :param frame: The frame instance being configured
        :param fps: The requested frame rate
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


class AnimationLoop(object):
    """
    Component which activates and manages a Renderer for displaying custom
    effects.
    """

    def __init__(self, frame: Frame, fps: int=DEFAULT_FPS, *renderers: Renderer):
        self.daemon = True

        self._frame = frame
        self._renderers = list(renderers)
        self._fps = 1 / fps

        self._running = False
        self._anim_task = None
        self._error = False

        self.logger = logging.getLogger('uchroma.animloop')


    @asyncio.coroutine
    def _draw(self, timestamp):
        bad_layers = []
        for layer in range(0, len(self._renderers)):
            try:
                self._frame.set_active_layer(layer)
                yield from self._renderers[layer].draw(self._frame, timestamp)
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug('LAYER %d: %s', layer, self._frame.matrix)

            except Exception as err:
                self.logger.exception("Exception during animation, removing renderer", exc_info=err)
                bad_layers.append(layer)

        for bad_layer in sorted(bad_layers, reverse=True):
            bad = self._renderers.pop(bad_layer)
            bad.finish(self._frame)
            self._frame.set_layer_count(len(self._renderers))

        self._frame.set_active_layer(0)

        draw_time = time.time() - timestamp
        self.logger.debug('Draw time: %f remaining: %f', draw_time, self._fps - draw_time)

        return True


    @asyncio.coroutine
    def _animate(self):
        """
        Main loop

        Invokes the draw() method of the configured Renderer, flips the buffer,
        and sleeps asynchronously until the next frame.
        """
        timestamp = time.time()
        self.logger.info("AnimationLoop is starting..")

        while self._running:
            yield from self._draw(timestamp)

            if not self._running or self._error:
                break

            # display the frame
            self._frame.commit()

            # calculate how long we will need to sleep, and sleep
            # until the deadline. autocorrect if necessary.
            next_tick = time.time() - timestamp

            if next_tick > self._fps:
                next_tick = next_tick % self._fps
            else:
                next_tick = self._fps - next_tick

            yield from asyncio.sleep(next_tick)

            timestamp = time.time()

        self.logger.info("AnimationLoop is exiting..")

        if self._error:
            self.logger.error("Shutting down event loop due to error")
            self.stop()


    def _renderer_done(self, future):
        """
        Invoked when the renderer exits
        """
        self.logger.info("Renderer is exiting!")
        for renderer in self._renderers:
            renderer.finish(self._frame)

        self._anim_task = None
        self._error = False
        self._frame.reset()


    def start(self) -> bool:
        """
        Start the AnimationLoop

        Initializes the renderer, zeros the buffer, and starts the loop
        which runs at the requested FPS. An arbitrary set of arguments
        may be passed by the container in order to configure the effect
        based on user preferences.

        Requires an active asyncio event loop.

        :param args: Arbitrary arguments passed to the Renderer

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
        self._anim_task = asyncio.ensure_future(self._animate())
        self._anim_task.add_done_callback(self._renderer_done)

        return True


    @asyncio.coroutine
    def stop(self):
        """
        Stop this AnimationLoop

        Shuts down the loop and triggers cleanup tasks. Note that
        cleanup is asynchronous and waits for the Renderer to finish.
        """
        if self._running:
            self._running = False

            if self._anim_task is not None:
                yield from self._anim_task.cancel()


    def __del__(self):
        yield from self.stop()


class AnimationManager(object):

    """
    WIP
    """

    def __init__(self, driver):
        self._driver = driver
        self._renderers = {}
        self._loop = None
        self._standalone = False
        self._running = False

        self._logger = logging.getLogger('uchroma.animmgr')


    def _get_renderer(self, renderer, module):
        try:
            if isinstance(renderer, str):
                if module is None:
                    module = sys.modules[__name__]
                elif isinstance(module, str):
                    module = importlib.import_module(module)
                else:
                    self._logger.error('Invalid module: %s', module)
                    return None
                try:
                    renderer = getattr(module, renderer)
                except AttributeError as err:
                    self._logger.exception('Invalid renderer name: %s',
                                           renderer, exc_info=err)
                    return None
            if isinstance(renderer, type):
                renderer = renderer(self._driver)

            return renderer
        except ImportError as err:
            self._logger.exception('Invalid renderer: %s (module=%s)',
                                   renderer, module, exc_info=err)
            return None

        return renderer


    def add_renderer(self, renderer, module=None, *args, **kwargs) -> str:
        renderer = self._get_renderer(renderer, module)
        if renderer is None:
            self._logger.error('Renderer failed to load')
            return None

        if not renderer.init(self._driver.frame_control, *args, **kwargs):
            self._logger.error('Renderer failed to initialize')
            return None

        cookie = 'anim-%s-%s' % (self._driver.serial_number, renderer.__class__.__name__)
        self._renderers[cookie] = renderer

        self._driver.frame_control.set_layer_count(len(self._renderers))

        return cookie


    def start(self, fps: int=DEFAULT_FPS, standalone: bool=False, blend_mode: str=None) -> bool:
        if self._renderers is None or len(self._renderers) == 0:
            self._logger.error('No renderers were configured')
            return False

        self._loop = AnimationLoop(self._driver.frame_control, fps,
                                   *self._renderers.values())

        self._standalone = standalone
        self._driver.frame_control.blend_mode = blend_mode

        if self._loop.start():
            self._running = True
            if standalone:
                try:
                    asyncio.get_event_loop().run_forever()
                except KeyboardInterrupt:
                    self._logger.info("Shutting down event loop")
                finally:
                    return self.stop()
            return True

        return False


    def stop(self) -> bool:
        if not self._running:
            return False

        self._renderers.clear()
        self._running = False

        result = yield from self._loop.stop()

        self._driver.frame_control.set_layer_count(1)

        return result


    @property
    def is_running(self) -> bool:
        return self._running


    def __del__(self):
        if self.is_running:
            self.stop()
