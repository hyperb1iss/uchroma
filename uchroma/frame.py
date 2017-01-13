import asyncio
import logging
import time

import numpy as np

from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.util import to_rgb


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


    class Command(BaseCommand):
        """
        Enumeration of raw hardware command data
        """
        SET_FRAME_DATA = (0x03, 0x0B, None)


    def __init__(self, driver: BaseUChromaDevice, width: int, height: int,
                 base_color=None, fps: int=30):
        self._driver = driver
        self._width = width
        self._height = height
        self._fps = fps

        self._logger = logging.getLogger('uchroma.frame')

        self._anim_start_time = None
        self._last_frame_time = None

        self._matrix = np.zeros(shape=(height, width, 3), dtype=np.uint8)

        self.set_base_color(base_color)
        self.clear()


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


    def put(self, row: int, col: int, *color) -> 'Frame':
        """
        Set the color of an individual pixel

        :param row: Y-coordinate of the pixel
        :param col: X-coordinate of the pixel
        :param colors: Color of the pixel (may also be a list)

        :return: This Frame instance
        """
        count = min(len(color) + col, self._width - col)
        self._matrix[row][col:col+count] = to_rgb(color[:count])

        return self


    def put_all(self, data: list) -> 'Frame':
        """
        Set the color of all pixels

        :param data: List of lists (row * col) of colors
        """
        for row in range(0, len(data)):
            self.put(row, 0, *data[row])

        return self


    def _set_frame_data(self, frame_id: int=None):
        if frame_id is None:
            frame_id = Frame.DEFAULT_FRAME_ID

        width = min(self._width, Frame.MAX_WIDTH)

        for row in range(0, self._height):
            data = self._matrix[row][0:width].data.tobytes()
            remaining = self._height - row - 1
            self._logger.debug("remaining: %d", remaining)
            self._driver.run_command(Frame.Command.SET_FRAME_DATA, frame_id, row, 0,
                                     width, data, transaction_id=0x80,
                                     remaining_packets=remaining)


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
        self._set_frame_data(frame_id)

        self._driver.custom_frame()

        if clear:
            self.clear()

        return self


    @asyncio.coroutine
    def _frame_loop(self):
        self._anim_start_time = time.perf_counter()

        while self._anim_start_time is not None:
            # yield from self._interactive.wait()

            if self._anim_start_time is not None:
                break

            now = time.perf_counter()

            self._matrix.setflags(write=False)

            # go ahead and send to the hardware now so it's ready
            # in case we need to sync to the next tick
            self._set_frame_data()

            #if self._last_frame_time is not None:
            #    # wait until it's time for the next frame
            #    # since we could have been sleeping
            #    delay = (now - self._last_frame_time) % (1 / self._fps)
            #    yield from asyncio.sleep(delay)

            self._driver.custom_frame()

            self._matrix.setflags(write=True)

            #self._last_frame_time = time.perf_counter()

            # wait for the next tick
            next_tick = now + (1 / self._fps)
            yield from asyncio.sleep(next_tick)



    def start_animation(self, fps: int=30):
        if self._anim_start_time is not None:
            return

        self._anim_start_time = time.perf_counter()


    def stop_animation(self):
        if self._anim_start_time is None:
            return

        self._anim_start_time = None

