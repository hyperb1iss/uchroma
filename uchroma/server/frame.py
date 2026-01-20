#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name, too-many-arguments, no-member

import asyncio
import time
import warnings

import numpy as np

from uchroma.blending import blend
from uchroma.color import ColorUtils
from uchroma.layer import Layer
from uchroma.util import ensure_future

from . import hid
from .hardware import Hardware, Quirks
from .protocol import get_protocol_from_quirks, get_transaction_id
from .report_utils import put_arg
from .standard_fx import FX, ExtendedFX, StandardFX
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

    DEFAULT_FRAME_ID = 0xFF

    class Command(BaseCommand):
        """
        Enumeration of raw hardware command data
        """

        SET_FRAME_DATA_MATRIX = (0x03, 0x0B, None)
        SET_FRAME_DATA_SINGLE = (0x03, 0x0C, None)
        SET_FRAME_EXTENDED = (0x0F, 0x03, None)

    def __init__(self, driver, width: int, height: int):
        self._driver = driver
        self._width = width
        self._height = height

        self._logger = driver.logger

        self._report = None
        self._last_frame = None
        self._frame_seq = 0
        self._last_frame_ts = 0.0

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
    def last_frame(self) -> np.ndarray | None:
        """Last composed RGB frame (uint8) sent to hardware, if available."""
        return self._last_frame

    @property
    def frame_seq(self) -> int:
        return self._frame_seq

    @property
    def last_frame_ts(self) -> float:
        return self._last_frame_ts

    @property
    def debug_opts(self) -> dict:
        """
        Dict of arbitrary values for internal use. This is
        currently only used by the device bringup tool.
        """
        return self._debug_opts

    @staticmethod
    def compose(layers: list) -> np.ndarray | None:
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
            warnings.simplefilter("ignore")
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
        prefix_len = 2
        max_cols = (hid.DATA_SIZE - prefix_len) // 3
        if max_cols <= 0:
            raise ValueError("frame payload too small")
        width = self._width
        start_col = 0

        while start_col < width:
            segment = img[0][start_col : start_col + max_cols]
            seg_width = len(segment)
            self._driver.run_command(
                Frame.Command.SET_FRAME_DATA_SINGLE,
                start_col,
                seg_width,
                segment.tobytes(),
                transaction_id=0x80,
            )
            start_col += seg_width
            if start_col < width:
                time.sleep(0.001)
        return img

    async def _set_frame_data_single_async(self, img, frame_id: int):
        prefix_len = 2
        max_cols = (hid.DATA_SIZE - prefix_len) // 3
        if max_cols <= 0:
            raise ValueError("frame payload too small")
        width = self._width
        start_col = 0

        while start_col < width:
            segment = img[0][start_col : start_col + max_cols]
            seg_width = len(segment)
            await self._driver.run_command_async(
                Frame.Command.SET_FRAME_DATA_SINGLE,
                start_col,
                seg_width,
                segment.tobytes(),
                transaction_id=0x80,
            )
            start_col += seg_width
            if start_col < width:
                await asyncio.sleep(0.001)
        return img

    def _get_frame_data_report(self, remaining_packets: int, *args):
        if self._report is None:
            # Determine command and transaction ID based on device quirks
            if self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS):
                cmd = Frame.Command.SET_FRAME_EXTENDED.value
                tid = None  # Use device default
            elif self._driver.has_quirk(Quirks.CUSTOM_FRAME_80):
                cmd = Frame.Command.SET_FRAME_DATA_MATRIX.value
                tid = 0x80
            else:
                cmd = Frame.Command.SET_FRAME_DATA_MATRIX.value
                tid = 0xFF

            self._report = self._driver.get_report(*cmd, transaction_id=tid)

        self._report.clear()
        for arg in args:
            put_arg(self._report, arg)

        self._report.set_remaining_packets(remaining_packets)
        return self._report

    def _build_extended_frame_args(self, row: int, start_col: int, stop_col: int, data):
        """Build argument list for extended frame command (0x0F, 0x03).

        Per OpenRazer razer_chroma_extended_matrix_set_custom_frame2:
        - arguments[0-1]: Reserved (0x00)
        - arguments[2]: row index
        - arguments[3]: start column
        - arguments[4]: stop column
        - arguments[5+]: RGB data
        """
        return [
            0x00,  # arguments[0] - reserved
            0x00,  # arguments[1] - reserved
            row,  # arguments[2] - row index
            start_col,  # arguments[3] - start column
            stop_col,  # arguments[4] - stop column
            data,  # arguments[5+] - RGB data
        ]

    def _set_frame_data_matrix(self, img, frame_id: int):
        width = self._width
        is_extended = self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS)
        prefix_len = 5 if is_extended else 4
        max_cols = (hid.DATA_SIZE - prefix_len) // 3
        if max_cols <= 0:
            raise ValueError("frame payload too small")
        segments_per_row = max(1, (width + max_cols - 1) // max_cols)
        total_packets = self._height * segments_per_row
        packet_index = 0

        if hasattr(self._driver, "align_key_matrix"):
            img = self._driver.align_key_matrix(self, img)

        for row in range(self._height):
            rowdata = img[row]

            row_offset = 0
            if hasattr(self._driver, "get_row_offset"):
                row_offset = self._driver.get_row_offset(self, row)

            start_col = 0
            while start_col < width:
                data = rowdata[start_col : start_col + max_cols]
                seg_width = len(data)
                start_idx = row_offset + start_col
                stop_col = start_idx + seg_width - 1
                remaining = total_packets - packet_index - 1

                if is_extended:
                    # Extended format: [varstore, led_id, effect_id, reserved, row, start, stop, rgb...]
                    args = self._build_extended_frame_args(row, start_idx, stop_col, data)
                else:
                    # Legacy format: [frame_id, row, start, stop, rgb...]
                    args = [frame_id, row, start_idx, stop_col, data]

                self._driver.run_report(self._get_frame_data_report(remaining, *args))
                packet_index += 1
                start_col += seg_width
                if start_col < width:
                    time.sleep(0.001)
        return img

    async def _set_frame_data_matrix_async(self, img, frame_id: int):
        if hasattr(self._driver, "align_key_matrix"):
            img = self._driver.align_key_matrix(self, img)

        if img is None:
            return img

        if (
            not isinstance(img, np.ndarray)
            or img.dtype != np.uint8
            or not img.flags["C_CONTIGUOUS"]
        ):
            img = np.ascontiguousarray(img, dtype=np.uint8)

        row_offsets = None
        if hasattr(self._driver, "get_row_offset"):
            row_offsets = [self._driver.get_row_offset(self, row) for row in range(self._height)]

        is_extended = self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS)
        if is_extended:
            transaction_id = get_transaction_id(self._driver.hardware)
        elif self._driver.has_quirk(Quirks.CUSTOM_FRAME_80):
            transaction_id = 0x80
        else:
            transaction_id = 0xFF

        proto = get_protocol_from_quirks(self._driver.hardware)
        pre_delay_ms = max(0, int(proto.inter_command_delay * 1000))

        if self._driver._async_lock is None:
            self._driver._async_lock = asyncio.Lock()

        async with self._driver._async_lock, self._driver.device_open_async():
            await hid.send_frame_async(
                self._driver.hid_device,
                img,
                frame_id=frame_id,
                transaction_id=transaction_id,
                is_extended=is_extended,
                row_offsets=row_offsets,
                pre_delay_ms=pre_delay_ms,
                post_delay_ms=1,
            )
        return img

    def _set_frame_data(self, img, frame_id: int | None = None):
        if frame_id is None:
            frame_id = Frame.DEFAULT_FRAME_ID

        if self._height == 1:
            img = self._set_frame_data_single(img, frame_id)
        else:
            img = self._set_frame_data_matrix(img, frame_id)

        if img is not None:
            self._last_frame = img
            self._frame_seq += 1
            self._last_frame_ts = time.monotonic()

    def _set_custom_frame(self):
        self._driver.fx_manager.activate("custom_frame")

    async def _set_frame_data_async(self, img, frame_id: int | None = None):
        if frame_id is None:
            frame_id = Frame.DEFAULT_FRAME_ID

        if self._height == 1:
            img = await self._set_frame_data_single_async(img, frame_id)
        else:
            img = await self._set_frame_data_matrix_async(img, frame_id)

        if img is not None:
            self._last_frame = img
            self._frame_seq += 1
            self._last_frame_ts = time.monotonic()

    async def _set_custom_frame_async(self):
        uses_extended = self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS)

        if uses_extended:
            varstore = 0x00  # NOSTORE
            led_id = 0x00  # ZERO_LED
            await self._driver.run_command_async(
                StandardFX.Command.SET_EFFECT_EXTENDED,
                varstore,
                led_id,
                ExtendedFX.CUSTOM_FRAME.value,
            )
            return

        varstore = 0x01
        if self._driver.device_type == Hardware.Type.MOUSE:
            varstore = 0x00

        await self._driver.run_command_async(
            StandardFX.Command.SET_EFFECT, FX.CUSTOM_FRAME.value, varstore
        )

    async def commit_async(self, layers, frame_id: int | None = None, show=True) -> "Frame":
        img = Frame.compose(layers)
        await self._set_frame_data_async(img, frame_id)
        if show:
            await self._set_custom_frame_async()

        return self

    def commit(self, layers, frame_id: int | None = None, show=True) -> "Frame":
        """
        Display this frame and prepare for the next frame

        Atomically sends this frame to the hardware and displays it.
        The buffer is then cleared by default and the next frame
        can be drawn.

        :param clear: True if the buffer should be cleared after commit
        :param frame_id: Internal frame identifier

        :return: This Frame instance
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as err:
            raise RuntimeError(
                "Frame.commit requires an active event loop; use await commit_async()"
            ) from err

        ensure_future(self.commit_async(layers, frame_id=frame_id, show=show), loop=loop)

        return self

    async def reset_async(self, frame_id: int | None = None) -> "Frame":
        await self.commit_async([self.create_layer()], show=False)
        return self

    def reset(self, frame_id: int | None = None) -> "Frame":
        """
        Clear the frame on the hardware.

        :return: This frame instance
        """
        self.commit([self.create_layer()], show=False)

        return self
