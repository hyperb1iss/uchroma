import numpy as np
from grapefruit import Color

from uchroma.device_base import BaseCommand, BaseUChromaDevice


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

    class Command(BaseCommand):
        """
        Enumeration of raw hardware command data
        """
        SET_FRAME_DATA = (0x03, 0x0B, None)


    def __init__(self, driver: BaseUChromaDevice, width: int, height: int,
                 base_color: Color=None):
        self._width = width
        self._height = height
        self._driver = driver

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


    def set_base_color(self, color: Color) -> 'Frame':
        """
        Sets the background color of this Frame

        :param color: Desired background color
        """
        self._base_color = color

        return self


    def clear(self) -> 'Frame':
        """
        Clears this frame with the background color

        Defaults to black if no background color is set.
        """
        if self._base_color is None:
            self._matrix.fill(0)
        else:
            rgb = self._base_color.intTuple
            for row in range(0, self._height):
                for col in range(0, self._width):
                    self._matrix[row][col] = [rgb[0], rgb[1], rgb[2]]

        return self


    def put(self, row: int, col: int, color: Color) -> 'Frame':
        """
        Set the color of an individual pixel

        :param row: Y-coordinate of the pixel
        :param col: X-coordinate of the pixel
        :param color: Color of the pixel

        :return: This Frame instance
        """
        rgb = color.intTuple
        self._matrix[row][col] = [rgb[0], rgb[1], rgb[2]]

        return self


    def flip(self, clear: bool=True, frame_id: int=0xFF) -> 'Frame':
        """
        Display this frame and prepare for the next frame

        Atomically sends this frame to the hardware and displays it.
        The buffer is then cleared by default and the next frame
        can be drawn.

        :param clear: True if the buffer should be cleared after flipping
        :param frame_id: Internal frame identifier

        :return: This Frame instance
        """
        for row in range(0, self._height):
            self._driver.run_command(Frame.Command.SET_FRAME_DATA, frame_id, row, 0,
                                     self._width, self._matrix[row].data.tobytes(),
                                     transaction_id=0x80)

        self._driver.custom_frame()

        if clear:
            self.clear()

        return self
