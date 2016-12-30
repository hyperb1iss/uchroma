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

        self._matrix = np.zeros(shape=(height, width, 3), dtype=np.uint8)

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
        self._base_color = color


    def clear(self):
        if self._base_color is None:
            self._matrix.fill(0)
        else:
            rgb = self._base_color.intTuple
            for row in range(0, self._height):
                for col in range(0, self._width):
                    self._matrix[row][col] = [rgb[0], rgb[1], rgb[2]]


    def put(self, row, col, color):
        rgb = color.intTuple
        self._matrix[row][col] = [rgb[0], rgb[1], rgb[2]]


    def flip(self, frame_id=0xFF, clear=True):
        for row in range(0, self._height):
            self._driver.run_command(Frame.Command.SET_FRAME_DATA, frame_id, row, 0,
                                     self._width, self._matrix[row].data.tobytes(),
                                     transaction_id=0x80)

        self._driver.custom_frame()

        if clear:
            self.clear()


