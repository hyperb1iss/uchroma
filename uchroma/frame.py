from enum import Enum

from grapefruit import Color
import numpy as np


class Frame(object):

    class Command(Enum):
        SET_FRAME_DATA = (0x03, 0x0B, None)


    def __init__(self, driver, width, height, base_color=None):
        self._width = width
        self._height = height
        self._driver = driver

        self._matrix = np.zeros(shape=(width, height, 3), dtype=np.uint8)

        self.set_base_color(base_color)
        self.clear()


    @property
    def width(self):
        return self._width


    @property
    def height(self):
        return self._height


    @property
    def matrix(self):
        return self._matrix


    def set_base_color(self, color):
        if color is None:
            self._base_color = Color.NewFromHtml('black')
        else:
            self._base_color = color


    def clear(self):
        self._matrix.fill(self._base_color.intTuple)


    def put(self, row, col, color):
        self._matrix[row][col] = color.intTuple


    def flip(self, clear=True):
        for row in range(0, self._height):
            self._driver.run_command(Frame.Command.SET_FRAME_DATA, 0xFF, row, 0,
                                     self._width, self._matrix[row].data.tobytes())

        self._driver.show_custom_frame()

        if clear:
            self.clear()


