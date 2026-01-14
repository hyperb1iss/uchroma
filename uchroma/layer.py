#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

# pylint: disable=invalid-name, too-many-arguments

import math

import numpy as np
from uchroma.colorlib import Color
from skimage import draw

from uchroma.blending import BlendOp
from uchroma.color import colorarg, ColorType, to_color
from uchroma.log import Log
from uchroma.util import clamp

from uchroma._layer import color_to_np, set_color


class Layer(object):
    """
    Provides utilities and constructs for drawing a single layer of a
    custom display frame. Layers may be stacked and composited together.
    """

    def __init__(self, width: int, height: int, logger=None):
        self._width = width
        self._height = height

        if logger is None:
            self._logger = Log.get('uchroma.frame')
        else:
            self._logger = logger

        self._matrix = np.zeros(shape=(self._height, self._width, 4), dtype=np.float)

        self._bg_color = None
        self._blend_mode = BlendOp.screen
        self._opacity = 1.0


    @property
    def blend_mode(self) -> str:
        """
        Get name of the blending function for this layer (when stacked)

        Defaults to BlendOp.screen
        """
        return self._blend_mode.__name__


    @blend_mode.setter
    def blend_mode(self, mode: str):
        """
        Set the blending function for this layer.

        Corresponds to a function in uchroma.blending.BlendOp
        """
        if mode is None:
            self._blend_mode = BlendOp.screen

        elif isinstance(mode, str):
            if mode in BlendOp.get_modes():
                self._blend_mode = getattr(BlendOp, mode)


    @property
    def opacity(self) -> float:
        """
        The opacity of this layer (when stacked)
        """
        return self._opacity


    @opacity.setter
    def opacity(self, alpha: float):
        """
        Set the opacity of this layer when stacked
        """
        self._opacity = alpha


    @property
    def width(self) -> int:
        """
        The width of this layer in pixels
        """
        return self._width


    @property
    def height(self) -> int:
        """
        The height of this layer in pixels
        """
        return self._height


    @property
    def matrix(self) -> np.ndarray:
        """
        The numpy array backing this layer

        Can be used to perform numpy operations if required.
        """
        return self._matrix


    @property
    def background_color(self) -> Color:
        """
        The background color of this layer
        """
        return self._bg_color


    @background_color.setter
    def background_color(self, color):
        """
        Sets the background color of this layer

        :param color: Desired background color
        """
        self._bg_color = to_color(color)


    def lock(self, lock) -> 'Layer':
        """
        Sets the writable state of the buffer. A locked
        buffer becomes read-only and acts as a safety mechanism
        when moving thru the asynchronous animation system.

        :param lock: True if requesting locked state, False to unlock

        :return: This layer instance
        """
        self.matrix.setflags(write=not lock)
        return self


    def clear(self) -> 'Layer':
        """
        Clears this frame

        :return: This layer instance
        """
        if self._matrix is not None:
            self._matrix.fill(0)
        return self


    def get(self, row: int, col: int) -> Color:
        """
        Get the color of an individual pixel

        :param row: Y coordinate of the pixel
        :param col: X coordinate of the pixel

        :return: Color of the pixel
        """
        return to_color(tuple(self.matrix[row][col]))


    @colorarg
    def put(self, row: int, col: int, *color: ColorType) -> 'Layer':
        """
        Set the color of an individual pixel

        :param row: Y-coordinate of the pixel
        :param col: X-coordinate of the pixel
        :param colors: Color of the pixel (may also be a list)

        :return: This layer instance
        """
        set_color(
            self.matrix, (np.array([row,] * len(color)), np.arange(col, col + len(color))),
            color_to_np(*color))

        return self


    def put_all(self, data: list) -> 'Layer':
        """
        Set the color of all pixels

        :param data: List of lists (row * col) of colors
        """
        for row in range(0, len(data)):
            self.put(row, 0, *data[row])

        return self


    def _draw(self, rr, cc, color, alpha):
        if rr is None or rr.ndim == 0:
            return
        set_color(self.matrix, (rr, cc), color_to_np(color), alpha)


    @colorarg
    def circle(self, row: int, col: int, radius: float,
               color: ColorType, fill: bool=False, alpha=1.0) -> 'Layer':
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
            rr, cc = draw.circle(row, col, round(radius), shape=self.matrix.shape)
            self._draw(rr, cc, color, alpha)

        else:
            rr, cc, aa = draw.circle_perimeter_aa(row, col, round(radius), shape=self.matrix.shape)
            self._draw(rr, cc, color, aa)

        return self


    @colorarg
    def ellipse(self, row: int, col: int, radius_r: float, radius_c: float,
                color: ColorType, fill: bool=False, alpha: float=1.0) -> 'Layer':
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
                                  shape=self.matrix.shape)
            self._draw(rr, cc, color, alpha)

        else:
            rr, cc = draw.ellipse_perimeter(row, col, math.floor(radius_r), math.floor(radius_c),
                                            shape=self.matrix.shape)
            self._draw(rr, cc, color, alpha)

        return self


    @colorarg
    def line(self, row1: int, col1: int, row2: int, col2: int,
             color: ColorType=None, alpha: float=1.0) -> 'Layer':
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
