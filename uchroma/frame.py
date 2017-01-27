# pylint: disable=invalid-name, too-many-arguments
import logging
import math
import warnings

import numpy as np
from grapefruit import Color
from skimage import draw

from uchroma.color import ColorUtils
from uchroma.device_base import BaseCommand, BaseUChromaDevice
from uchroma.hardware import Quirks
from uchroma.util import clamp, colorarg, ColorType, to_color


class Frame(object):
    """
    A simple framebuffer for creating custom effects.

    Internally represented by a 2D numpy array of
    Grapefruit Color objects. Individual pixels of
    the framebuffer should be set to the desired colors
    and will be sent to the hardware atomically when commit() is
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

        self._matrix = np.zeros(shape=(height, width, 4), dtype=np.float)

        self._debug_opts = {}


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


    @property
    def debug_opts(self) -> dict:
        return self._debug_opts


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


    @colorarg
    def put(self, row: int, col: int, *color: ColorType) -> 'Frame':
        """
        Set the color of an individual pixel

        :param row: Y-coordinate of the pixel
        :param col: X-coordinate of the pixel
        :param colors: Color of the pixel (may also be a list)

        :return: This Frame instance
        """
        Frame._set_color(
            self._matrix, (np.array([row,] * len(color)), np.arange(col, col + len(color))),
            Frame._color_to_np(*color))

        return self


    def put_all(self, data: list) -> 'Frame':
        """
        Set the color of all pixels

        :param data: List of lists (row * col) of colors
        """
        for row in range(0, len(data)):
            self.put(row, 0, *data[row])

        return self


    def _as_img(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return ColorUtils.rgba2rgb(self._matrix, self._bg_color)


    def _set_frame_data_single(self, frame_id: int):
        width = min(self._width, Frame.MAX_WIDTH)
        self._driver.run_command(Frame.Command.SET_FRAME_DATA_SINGLE,
                                 0, width, self._as_img()[0][:width].tobytes(),
                                 transaction_id=0x80)


    def _set_frame_data_matrix(self, frame_id: int):
        width = self._width
        multi = False

        #perform two updates if we exceeded 24 columns
        if width > Frame.MAX_WIDTH:
            multi = True
            width = int(width / 2)

        tid = None
        if self._driver.has_quirk(Quirks.CUSTOM_FRAME_80):
            tid = 0x80

        img = self._as_img()

        if hasattr(self._driver, 'align_key_matrix'):
            img = self._driver.align_key_matrix(self, img)

        for row in range(0, self._height):
            rowdata = img[row]

            start_col = 0
            if hasattr(self._driver, 'get_row_offset'):
                start_col = self._driver.get_row_offset(self, row)

            remaining = self._height - row - 1
            if multi:
                remaining *= 2

            data = rowdata[:width]
            self._driver.run_command(Frame.Command.SET_FRAME_DATA_MATRIX, frame_id,
                                     row, start_col, len(data) - 1,
                                     data.tobytes(),
                                     transaction_id=tid,
                                     remaining_packets=remaining)

            if multi:
                data = rowdata[width:]
                self._driver.run_command(Frame.Command.SET_FRAME_DATA_MATRIX, frame_id,
                                         row, width, width + len(data) - 1,
                                         data.tobytes(),
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

        Use commit() unless you need custom behavior.
        """
        try:
            self._matrix.setflags(write=False)
            self._set_frame_data(frame_id)
            self._driver.custom_frame()
        finally:
            self._matrix.setflags(write=True)


    def commit(self, clear: bool=True, frame_id: int=None) -> 'Frame':
        """
        Display this frame and prepare for the next frame

        Atomically sends this frame to the hardware and displays it.
        The buffer is then cleared by default and the next frame
        can be drawn.

        :param clear: True if the buffer should be cleared after commit
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


    def _draw(self, rr, cc, color, alpha):
        if rr is None or rr.ndim == 0:
            return
        Frame._set_color(self._matrix, (rr, cc), Frame._color_to_np(color), alpha)


    @colorarg
    def circle(self, row: int, col: int, radius: float,
               color: ColorType, fill: bool=False, alpha=1.0) -> 'Frame':
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
            self._draw(rr, cc, color, alpha)

        else:
            rr, cc, aa = draw.circle_perimeter_aa(row, col, round(radius), shape=self._matrix.shape)
            self._draw(rr, cc, color, aa)

        return self


    @colorarg
    def ellipse(self, row: int, col: int, radius_r: float, radius_c: float,
                color: ColorType, fill: bool=False, alpha: float=1.0) -> 'Frame':
        """
        Draw an ellipse centered on the specified row and column,
        with the given radiuses.

        :param row: Center row of ellipse
        :param col: Center column of ellipse
        :param radius_r: Radius of ellipse on y axis
        :param radius_c: Radius of ellipse on x axis
        :param color: Color to draw with
        :param fill: True if the circle should be filled

        :return: This frame instance
        """
        if fill:
            rr, cc = draw.ellipse(row, col, math.floor(radius_r), math.floor(radius_c),
                                  shape=self._matrix.shape)
            self._draw(rr, cc, color, alpha)

        else:
            rr, cc = draw.ellipse_perimeter(row, col, math.floor(radius_r), math.floor(radius_c),
                                            shape=self._matrix.shape)
            self._draw(rr, cc, color, alpha)

        return self


    @colorarg
    def line(self, row1: int, col1: int, row2: int, col2: int,
             color: ColorType=None, alpha: float=1.0) -> 'Frame':
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
        self._draw(rr, cc, color, aa)

        return self


    # a few methods pulled from skimage-dev for blending support
    # remove these when 1.9 is released

    @staticmethod
    def _color_to_np(*color: ColorType):
        colors = to_color(*color)
        if len(color) == 1:
            colors = [colors]

        return np.array([(*x.rgb, x.alpha) for x in colors], dtype=np.float)


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
                             'image dimension ({}). color=({})'.format( \
                                     color.shape[0], img.shape[-1], color))

        if np.isscalar(alpha):
            alpha = np.ones_like(rr) * alpha

        rr, cc, alpha = Frame._coords_inside_image(rr, cc, img.shape, val=alpha)

        color = color * alpha[..., np.newaxis]

        if np.all(img[rr, cc] == 0):
            img[rr, cc] = color
        else:

            src_alpha = color[..., -1][..., np.newaxis]
            src_rgb = color[..., :-1]

            dst_alpha = img[rr, cc][..., -1][..., np.newaxis] * 0.75
            dst_rgb = img[rr, cc][..., :-1]

            out_alpha = src_alpha + dst_alpha * (1 - src_alpha)
            out_rgb = (src_rgb * src_alpha + dst_rgb *dst_alpha * (1- src_alpha)) / out_alpha

            img[rr, cc] = np.clip(np.hstack([out_rgb, out_alpha]), a_min=0, a_max=1)
