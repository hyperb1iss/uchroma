from enum import Enum

import numpy as np

from color import RGB



class Frame(object):

    class Command(Enum):
        SET_FRAME_DATA = (0x03, 0x0B, None)


    def __init__(self, driver, width, height, base_rgb=None):
        self._width = width
        self._height = height
        self._driver = driver

        self._matrix = np.zeros(shape=(width, height, 3), dtype=np.uint8)

        self.set_base_color(base_rgb)
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


    def set_base_color(self, rgb):
        if rgb is None:
            self._base_rgb = RGB().get()
        else:
            self._base_rgb = rgb.get()


    def clear(self):
        self._matrix.fill(self._base_rgb)


    def put(self, row, col, rgb):
        self._matrix[row][col] = rgb.get()


    def flip(self, clear=True):
        for row in range(0, self._height):
            self._driver.run_command(Frame.Command.SET_FRAME_DATA, 0xFF, row, 0,
                                     self._width, self._matrix[row].data.tobytes())

        self._driver.show_custom_frame()

        if clear:
            self.clear()


