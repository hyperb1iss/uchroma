import logging

import numpy as np
from grapefruit import Color
from skimage import draw, filters

from uchroma.color import ColorUtils
from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.models import Quirks
from uchroma.util import clamp, colorarg, to_color


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
        SET_FRAME_DATA_MATRIX = (0x03, 0x0B, None)
        SET_FRAME_DATA_SINGLE = (0x03, 0x0C, None)


    def __init__(self, driver: BaseUChromaDevice, width: int, height: int):
        self._driver = driver
        self._width = width
        self._height = height

        self._bg_color = None
        self._logger = logging.getLogger('uchroma.frame')

        self._matrix = np.zeros(shape=(height, width, 4), dtype=np.float32)


    @property
    def device_name(self):
        """
        Get the current device name
        """
        return self._driver.name


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


    @property
    def background_color(self) -> Color:
        return self._bg_color


    @background_color.setter
    def background_color(self, color):
        """
        Sets the background color of this Frame

        :param color: Desired background color
        """
        self._bg_color = to_color(color)
        self.reset()


    def clear(self) -> 'Frame':
        """
        Clears this frame with the background color

        Defaults to black if no background color is set.
        """
        self._matrix.fill(0)

        return self


    def get(self, row: int, col: int) -> Color:
        """
        Get the color of an individual pixel

        :param row: Y coordinate of the pixel
        :param col: X coordinate of the pixel

        :return: Color of the pixel
        """
        return to_color(tuple(self._matrix[row][col]))


    @colorarg('color')
    def put(self, row: int, col: int, color: Color) -> 'Frame':
        """
        Set the color of an individual pixel

        :param row: Y-coordinate of the pixel
        :param col: X-coordinate of the pixel
        :param colors: Color of the pixel (may also be a list)

        :return: This Frame instance
        """
        Frame._set_color(self._matrix, (np.atleast_1d(row), np.atleast_1d(col)), tuple(color))

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
        """
        Send the current frame to the hardware but do not
        display it. This frees up the buffer for drawing
        the next frame. Call commit() to display the
        frame after calling this method.

        Use flip() unless you you need custom behavior.
        """
        try:
            self._matrix.setflags(write=False)
            self._set_frame_data(frame_id)
        finally:
            self._matrix.setflags(write=True)

        self.clear()


    def commit(self):
        """
        Display the last frame sent to the hardware

        Use flip() unless you need custom behavior.
        """
        self._driver.custom_frame()


    def _as_img(self):
        return ColorUtils.rgba2rgb(self._matrix, self._bg_color)


    def _set_frame_data_single(self, frame_id: int):
        width = min(self._width, Frame.MAX_WIDTH)
        self._driver.run_command(Frame.Command.SET_FRAME_DATA_SINGLE,
                                 0, width, self._as_img()[0][:width].tobytes(),
                                 transaction_id=0x80)


    def _set_frame_data_matrix(self, frame_id: int):
        width = min(self._width, Frame.MAX_WIDTH)

        tid = None
        if self._driver.has_quirk(Quirks.CUSTOM_FRAME_80):
            tid = 0x80

        img = self._as_img()

        for row in range(0, self._height):
            data = img[row][:width].tobytes()
            remaining = self._height - row - 1

            self._driver.run_command(Frame.Command.SET_FRAME_DATA_MATRIX,
                                     frame_id, row, 0, width, data,
                                     transaction_id=tid,
                                     remaining_packets=remaining)


    def _set_frame_data(self, frame_id: int=None):
        if frame_id is None:
            frame_id = Frame.DEFAULT_FRAME_ID

        if self._height == 1:
            self._set_frame_data_single(frame_id)
        else:
            self._set_frame_data_matrix(frame_id)


    def update(self, frame_id: int=None):
        """
        Sends the current frame to the hardware and displays it.

        Use flip() unless you need custom behavior.
        """
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


    @colorarg('color')
    def circle(self, row: int, col: int, radius: float,
               color: Color, fill: bool=False) -> 'Frame':
        """
        Draw a circle centered on the specified row and column,
        with the given radius.

        :param row: Center row of circle
        :param col: Center column of circle
        :param radius: Radius of circle
        :param color: Color to draw with
        :param fill: True if the circle should be filled

        :return: This frame instance
        """
        if fill:
            rr, cc = draw.circle(row, col, round(radius), shape=self._matrix.shape)
            Frame._set_color(self._matrix, (rr, cc), tuple(color))

        else:
            rr, cc, aa = draw.circle_perimeter_aa(row, col, round(radius), shape=self._matrix.shape)
            Frame._set_color(self._matrix, (rr, cc), tuple(color), aa)

        return self


    @colorarg('color')
    def line(self, row1: int, col1: int, row2: int, col2: int, color: Color=None) -> 'Frame':
        """
        Draw a line between two points

        :param row1: Start row
        :param col1: Start column
        :param row2: End row
        :param col2: End column
        :param color: Color to draw with
        """
        rr, cc, aa = draw.line_aa(clamp(0, self.height, row1), clamp(0, self.width, col1),
                                  clamp(0, self.height, row2), clamp(0, self.width, col2))

        Frame._set_color(self._matrix, (rr, cc, aa), tuple(color), aa)

        return self


    # a few methods pulled from skimage-dev for blending support
    # remove these when 1.9 is released

    @staticmethod
    def _coords_inside_image(rr, cc, shape, val=None):
        mask = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
        if val is None:
            return rr[mask], cc[mask]
        else:
            return rr[mask], cc[mask], val[mask]


    @staticmethod
    def _set_color(img, coords, color, alpha=1):
        rr, cc = coords

        if img.ndim == 2:
            img = img[..., np.newaxis]

        color = np.array(color, ndmin=1, copy=False)

        if img.shape[-1] != color.shape[-1]:
            raise ValueError('Color shape ({}) must match last '
                             'image dimension ({}).'.format(color.shape[0],
                                                            img.shape[-1]))

        if np.isscalar(alpha):
            alpha = np.ones_like(rr) * alpha

        rr, cc, alpha = Frame._coords_inside_image(rr, cc, img.shape, val=alpha)

        alpha = alpha[..., np.newaxis]

        color = color * alpha
        vals = img[rr, cc] * (1 - alpha)

        img[rr, cc] = vals + color
