import struct

from enum import Enum

class RGB(object):
    def __init__(self, red=None, green=None, blue=None):
        if red is not None and isinstance(red, tuple):
            self._red = red[0]
            self._green = red[1]
            self._blue = red[2]
        else:
            if red is None:
                self._red = 0
            else:
                self._red = red

            if green is None:
                self._green = 0
            else:
                self._green = green

            if blue is None:
                self._blue = 0
            else:
                self._blue = blue

    def get(self):
        return self._red, self._green, self._blue

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

    def __bytes__(self):
        return struct.pack('=BBB', self._red, self._green, self._blue)


# Splotches
class Splotch(Enum):
    EARTH = (RGB(0, 255, 0), RGB(139, 69, 19))
    AIR = (RGB(255, 255, 255), RGB(128, 128, 128))
    FIRE = (RGB(255, 64, 0), RGB(255, 0, 0))
    WATER = (RGB(0, 0, 255), RGB(128, 128, 128))
    SUN = (RGB(255, 255, 255), RGB(255, 128, 0))
    MOON = (RGB(255, 255, 255), RGB(0, 128, 255))


