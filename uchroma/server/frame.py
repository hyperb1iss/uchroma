#
# uchroma - Copyright (C) 2017 Steve Kondik
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

# pylint: disable=invalid-name, too-many-arguments, no-member

import time
import warnings

import numpy as np

from uchroma.blending import blend
from uchroma.color import ColorUtils
from uchroma.layer import Layer

from .hardware import Quirks
from .types import BaseCommand


class Frame:
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


    def __init__(self, driver, width: int, height: int):
        self._driver = driver
        self._width = width
        self._height = height

        self._logger = driver.logger

        self._report = None

        self._debug_opts = {}


    def create_layer(self) -> Layer:
        """
        Create a new layer which can be used for
        creating custom effects and animations.
        Multiple layers can be composited together for
        advanced effects or stacked animations. Currently
        only layers which match the physical size of the
        lighting matrix are supported.
        """
        return Layer(self._width, self._height, logger=self._logger)


    @property
    def device_name(self) -> str:
        """
        Get the current device name
        """
        return self._driver.name


    @property
    def width(self) -> int:
        """
        The width of this Frame in pixels
        """
        return self._width


    @property
    def height(self) -> int:
        """
        The height of this Frame in pixels
        """
        return self._height


    @property
    def debug_opts(self) -> dict:
        """
        Dict of arbitrary values for internal use. This is
        currently only used by the device bringup tool.
        """
        return self._debug_opts


    @staticmethod
    def compose(layers: list) -> np.ndarray:
        """
        Render a list of Layers into an RGB image

        The layer matrices are populated with RGBA tuples and must
        be blended according to z-order (using the blend mode specified
        by each layer) then alpha-composited into a single RGB image
        before sending to the hardware. If the background color is
        set on a layer, it is only honored if it is the base layer.
        """
        if not layers:
            return None

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            out = layers[0].matrix

            # blend all the layers by z-order
            if len(layers) > 1:
                for l_idx in range(1, len(layers)):
                    layer = layers[l_idx]
                    if layer is None or layer.matrix.ndim < 3:
                        continue
                    out = blend(out, layer.matrix, layer.blend_mode, layer.opacity)

            return ColorUtils.rgba2rgb(out, bg_color=layers[0].background_color)


    def _set_frame_data_single(self, img, frame_id: int):
        width = min(self._width, Frame.MAX_WIDTH)
        self._driver.run_command(Frame.Command.SET_FRAME_DATA_SINGLE,
                                 0, width, img[0][:width].tobytes(),
                                 transaction_id=0x80)


    def _get_frame_data_report(self, remaining_packets: int, *args):
        if self._report is None:
            tid = 0xFF
            if self._driver.has_quirk(Quirks.CUSTOM_FRAME_80):
                tid = 0x80

            self._report = self._driver.get_report( \
                *Frame.Command.SET_FRAME_DATA_MATRIX.value, transaction_id=tid)

        self._report.clear()
        self._report.args.put_all(args)

        self._report.remaining_packets = remaining_packets
        return self._report


    def _set_frame_data_matrix(self, img, frame_id: int):
        width = self._width
        multi = False

        #perform two updates if we exceeded 24 columns
        if width > Frame.MAX_WIDTH:
            multi = True
            width = int(width / 2)

        if hasattr(self._driver, 'align_key_matrix'):
            img = self._driver.align_key_matrix(self, img)

        for row in range(0, self._height):
            rowdata = img[row]

            start_col = 0
            if hasattr(self._driver, 'get_row_offset'):
                start_col = self._driver.get_row_offset(self, row)

            remaining = self._height - row - 1
            if multi:
                remaining = (remaining * 2) + 1

            data = rowdata[:width]
            self._driver.run_report(self._get_frame_data_report(remaining, \
                frame_id, row, start_col, len(data) - 1, data))

            if multi:
                time.sleep(0.001)
                data = rowdata[width:]
                self._driver.run_report(self._get_frame_data_report(remaining - 1, \
                    frame_id, row, width, width + len(data) - 1, data))

            time.sleep(0.001)


    def _set_frame_data(self, img, frame_id: int = None):
        if frame_id is None:
            frame_id = Frame.DEFAULT_FRAME_ID

        if self._height == 1:
            self._set_frame_data_single(img, frame_id)
        else:
            self._set_frame_data_matrix(img, frame_id)


    def _set_custom_frame(self):
        self._driver.fx_manager.activate('custom_frame')


    def commit(self, layers, frame_id: int = None, show=True) -> 'Frame':
        """
        Display this frame and prepare for the next frame

        Atomically sends this frame to the hardware and displays it.
        The buffer is then cleared by default and the next frame
        can be drawn.

        :param clear: True if the buffer should be cleared after commit
        :param frame_id: Internal frame identifier

        :return: This Frame instance
        """
        img = Frame.compose(layers)
        self._set_frame_data(img, frame_id)
        if show:
            self._set_custom_frame()

        return self


    def reset(self, frame_id: int = None) -> 'Frame':
        """
        Clear the frame on the hardware.

        :return: This frame instance
        """
        self.commit([self.create_layer()], show=False)

        return self
