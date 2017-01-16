import asyncio
import logging
import time

import numpy as np
from grapefruit import Color

from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.util import to_color, to_rgb


class Frame(object):
    """
    A simple framebuffer for creating custom effects.

    Internally represented by a 2D numpy array of
    Grapefruit Color objects. Individual pixels of
    the framebuffer should be set to the desired colors
    and will be sent to the hardware atomically when flip() is
    called. The buffer is then (optionally) cleared with the
    base color (black/off by default) so the next frame can
    be drawn without jank or flicker (double-buffering).

    NOTE: This API is not yet complete and may change as
    support for multiple device layouts and animations
    is introduced in a future release.
    """

    MAX_WIDTH = 24
    DEFAULT_FRAME_ID = 0xFF
    DEFAULT_FPS = 30

    class Command(BaseCommand):
        """
        Enumeration of raw hardware command data
        """
        SET_FRAME_DATA = (0x03, 0x0B, None)


    def __init__(self, driver: BaseUChromaDevice, width: int, height: int,
                 base_color=None, fps: int=None):
        self._driver = driver
        self._width = width
        self._height = height

        if fps is None:
            self._fps = 1 / Frame.DEFAULT_FPS
        else:
            self._fps = 1 / fps

        self._logger = logging.getLogger('uchroma.frame')

        self._anim_task = None
        self._callback = None
        self._running = False
        self._matrix = np.zeros(shape=(height, width, 3), dtype=np.uint8)

        self.set_base_color(base_color)
        self.reset()


    def __del__(self):
        self.stop_animation()


    @property
    def callback(self):
        return self._callback


    @callback.setter
    def callback(self, callback):
        self._callback = callback


    @property
    def width(self):
        """
        The width of this Frame in pixels
        """
        return self._width


    @property
    def height(self):
        """
        The height of this Frame in pixels
        """
        return self._height


    @property
    def matrix(self):
        """
        The numpy array backing this Frame

        Can be used to perform numpy operations if required.
        """
        return self._matrix


    def set_base_color(self, color) -> 'Frame':
        """
        Sets the background color of this Frame

        :param color: Desired background color
        """
        if color is None:
            self._base_color = None
        else:
            self._base_color = to_rgb(color)

        return self


    def clear(self) -> 'Frame':
        """
        Clears this frame with the background color

        Defaults to black if no background color is set.
        """
        if self._base_color is None:
            self._matrix.fill(0)
        else:
            for row in range(0, self._height):
                self._matrix[row] = [self._base_color] * self._width

        return self


    def get(self, row: int, col: int) -> Color:
        """
        Get the color of an individual pixel

        :param row: Y coordinate of the pixel
        :param col: X coordinate of the pixel

        :return: Color of the pixel
        """
        return to_color(tuple(self._matrix[row][col]))


    def put(self, row: int, col: int, *color, blend: float=None) -> 'Frame':
        """
        Set the color of an individual pixel

        :param row: Y-coordinate of the pixel
        :param col: X-coordinate of the pixel
        :param colors: Color of the pixel (may also be a list)

        :return: This Frame instance
        """
        count = min(len(color) + col, self._width - col)
        rgb = color[:count]
        if blend is not None:
            rgb = [x.ColorWithAlpha(blend).AlphaBlend(to_color(self.get(row, col))) for x in rgb]

        self._matrix[row][col:col+count] = to_rgb(rgb)

        return self


    def put_all(self, data: list) -> 'Frame':
        """
        Set the color of all pixels

        :param data: List of lists (row * col) of colors
        """
        for row in range(0, len(data)):
            self.put(row, 0, *data[row])

        return self


    def prepare(self, frame_id: int=None):
        try:
            self._matrix.setflags(write=False)
            self._set_frame_data(frame_id)
        finally:
            self._matrix.setflags(write=True)

        self.clear()


    def commit(self):
        self._driver.custom_frame()


    def _set_frame_data(self, frame_id: int=None):
        if frame_id is None:
            frame_id = Frame.DEFAULT_FRAME_ID

        width = min(self._width, Frame.MAX_WIDTH)

        for row in range(0, self._height):
            data = self._matrix[row][0:width].data.tobytes()
            remaining = self._height - row - 1
            self._driver.run_command(Frame.Command.SET_FRAME_DATA, frame_id, row, 0,
                                     width, data, transaction_id=0x80,
                                     remaining_packets=remaining)


    def update(self, frame_id: int=None):
        try:
            self._matrix.setflags(write=False)
            self._set_frame_data(frame_id)
            self.commit()
        finally:
            self._matrix.setflags(write=True)


    def flip(self, clear: bool=True, frame_id: int=None) -> 'Frame':
        """
        Display this frame and prepare for the next frame

        Atomically sends this frame to the hardware and displays it.
        The buffer is then cleared by default and the next frame
        can be drawn.

        :param clear: True if the buffer should be cleared after flipping
        :param frame_id: Internal frame identifier

        :return: This Frame instance
        """
        self.update(frame_id)

        if clear:
            self.clear()

        return self


    def reset(self, frame_id: int=None) -> 'Frame':
        """
        Clear the frame with the base color, flip the buffer and
        get a fresh start.

        :return: This frame instance
        """
        self.clear()
        self.update(frame_id)

        return self


    @asyncio.coroutine
    def _frame_callback(self) -> bool:
        if not self._callback:
            return False

        try:
            yield from self._callback(self.matrix)

        except Exception as err:
            self._logger.exception("Exception during animation", exc_info=err)
            return False

        return True


    @asyncio.coroutine
    def _frame_loop(self):
        timestamp = time.perf_counter()

        while self._running:
            yield from self._frame_callback()

            if not self._running:
                break

            self.update()

            next_tick = time.perf_counter() - timestamp
            if next_tick > self._fps:
                next_tick = next_tick % self._fps
            else:
                next_tick = self._fps - next_tick

            yield from asyncio.sleep(next_tick)

            timestamp = time.perf_counter()


    def start_animation(self, fps: int=None):
        if self._running:
            return

        if fps is None:
            self._fps = 1.0 / Frame.DEFAULT_FPS
        else:
            self._fps = 1.0 / fps

        self.reset()
        self._running = True
        self._anim_task = asyncio.ensure_future(self._frame_loop())


    def stop_animation(self):
        if self._running:
            self._running = False
            self._anim_task.cancel()
            self.reset()
