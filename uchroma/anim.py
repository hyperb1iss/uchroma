import asyncio
import logging
import signal
import time

from uchroma.device import UChromaDevice
from uchroma.frame import Frame


DEFAULT_FPS = 30


class Renderer(object):

    def __init__(self, *args, **kwargs):
        super(Renderer, self).__init__(*args, **kwargs)


    @asyncio.coroutine
    def draw(self, frame: Frame, timestamp: float) -> bool:
        return False


    def init(self, frame: Frame, fps: int, *args, **kwargs) -> bool:
        return False

    
    def finish(self):
        pass


class AnimationLoop(object):

    def __init__(self, name: str, frame: Frame, renderer: Renderer, fps: int=DEFAULT_FPS):
        self.name = name
        self.daemon = True

        self._frame = frame
        self._renderer = renderer
        self._fps = 1 / fps

        self._running = False
        self._anim_task = None
        self._error = False

        self.logger = logging.getLogger('uchroma.%s' % name)


    @asyncio.coroutine
    def _draw(self, timestamp):
        try:
            yield from self._renderer.draw(self._frame, timestamp)

        except Exception as err:
            self.logger.exception("Exception during animation", exc_info=err)
            return False

        return True


    @asyncio.coroutine
    def _animate(self):
        timestamp = time.time()
        self.logger.info("AnimationLoop is starting..")

        while self._running:
            yield from self._draw(timestamp)

            if not self._running or self._error:
                break

            # Send the buffer we just got to the hardware
            self._frame.prepare()

            # calculate how long we will need to sleep, and sleep
            # until the deadline. autocorrect if necessary.
            next_tick = time.time() - timestamp

            if next_tick > self._fps:
                next_tick = next_tick % self._fps
            else:
                next_tick = self._fps - next_tick

            yield from asyncio.sleep(next_tick)

            # display the frame
            self._frame.commit()

            timestamp = time.time()

        self.logger.info("AnimationLoop is exiting..")

        if self._error:
            self.logger.error("Shutting down event loop due to error")
            self.stop()


    def _renderer_done(self, future):
        self.logger.info("Renderer is exiting!")
        self._renderer.finish()
        self._renderer = None
        self._anim_task = None
        self._error = False
        self._frame.reset()


    def start(self, *args, **kwargs):
        if self._running:
            return

        self._renderer.init(self._frame, self._fps, *args, **kwargs)
        self._frame.reset()

        self._running = True
        self._anim_task = asyncio.ensure_future(self._animate())
        self._anim_task.add_done_callback(self._renderer_done)


    def stop(self):
        if self._running:
            self._running = False

            if self._anim_task is not None:
                self._anim_task.cancel()


    def __del__(self):
        self.stop()


class AnimationManager(object):

    def __init__(self, driver: UChromaDevice):
        self._driver = driver
        self._loops = {}


    def submit(self, renderer: Renderer) -> str:
        task_name = 'anim-%s-%f' % (self._driver.serial_number, time.time())

        loop = AnimationLoop(task_name, self._driver.frame_control, renderer)
        self._loops[task_name] = loop
        loop.start()

        return task_name


    def end(self, key: str) -> bool:
        loop = self._loops.pop(key, None)

        if loop is None:
            return False

        loop.stop()

        return True

    def shutdown(self):
        for key in list(self._loops.keys())[:]:
            self.end(key)

