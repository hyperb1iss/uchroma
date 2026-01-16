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

# pylint: disable=invalid-name, no-member

"""
Fixups are mixins which adjust input/output data in some form.
"""

import numpy as np
from numpy import ndarray


class KeyboardFixup:
    """
    Fixup which adjusts key coordinates in order to achieve a linear matrix.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._alignment_map = self._hardware.key_fixup_mapping
        self._row_offsets = self._hardware.key_row_offsets

    @staticmethod
    def _insert(rowdata: ndarray, col: int) -> ndarray:
        """
        Inserts a "spacer" into the output row, effectively sliding right.

        :param rowdata: The current data for the current row
        :param col: The column number where the empty cell should be inserted

        :return: The updated row data
        """
        return np.insert(rowdata, col, [0, 0, 0], axis=0)

    @staticmethod
    def _delete(rowdata: ndarray, col: int) -> ndarray:
        """
        Deletes a cell from the output row, effectively sliding left.

        :param rowdata: The current data for the current row
        :param col: The column number where a cell should be removed

        :return: The updated row data
        """
        return np.delete(rowdata, col, axis=0)

    @staticmethod
    def _copy(matrix: ndarray, src: tuple, dst: tuple) -> ndarray:
        """
        Copy a cell from the source to the destination, effectively moving a key.

        :param matrix: The original input frame
        :param src: Source position, tuple of (row, column)
        :param dst: Destination position, tuple of (row, column)

        :return: The updated row data
        """
        src_row, src_col = src
        dst_row, dst_col = dst
        matrix[dst_row][dst_col] = np.copy(matrix[src_row][src_col])

        return matrix

    @staticmethod
    def _update_debug_info(
        frame,
        debug_position: tuple,
        in_data: ndarray | None = None,
        out_data: ndarray | None = None,
    ):
        """
        Used by the alignment utility.
        """
        if debug_position is not None and len(debug_position) == 2:
            row = debug_position[0]

            if in_data is not None:
                frame.debug_opts["in_data"] = np.copy(in_data[row])
            if out_data is not None:
                frame.debug_opts["out_data"] = np.copy(out_data[row])

    def _align_matrix(self, frame, matrix: ndarray) -> ndarray:
        """
        Apply the alignment map to the given matrix, performing
        inserts, deletes, and copies (in this order).

        :param matrix: The input matrix

        :return: The updated matrix
        """
        skip_fixups = frame.debug_opts.get("skip_fixups", False)
        debug_position = frame.debug_opts.get("debug_position", None)

        KeyboardFixup._update_debug_info(frame, debug_position, in_data=matrix)

        if self._alignment_map is not None and not skip_fixups:
            inserts = self._alignment_map.insert
            if inserts is not None:
                for insert in inserts:
                    rr, cc = insert
                    matrix[rr] = KeyboardFixup._insert(matrix[rr], cc)

            deletes = self._alignment_map.delete
            if deletes is not None:
                for delete in deletes:
                    rr, cc = delete
                    matrix[rr] = KeyboardFixup._delete(matrix[rr], cc)

            copies = self._alignment_map.copy
            if copies is not None:
                for copy in copies:
                    src, dst = copy
                    matrix = KeyboardFixup._copy(matrix, src, dst)

        KeyboardFixup._update_debug_info(frame, debug_position, out_data=matrix)

        return matrix

    def get_row_offset(self, frame, row: int) -> int:
        """
        Get the offset for the given row. This effectively pads the entire
        row to the right by the given offset.

        :param row: The current row

        :return: Column offset for the given row
        """
        if self._row_offsets is None or frame.debug_opts.get("skip_fixups"):
            return 0

        return self._row_offsets[row]

    def align_key_matrix(self, frame, matrix: ndarray) -> ndarray:
        """
        Perform alignment of the matrix. Columns may be inserted,
        deleted, or copied from other locations.

        :param matrix: The input data matrix

        :return: The aligned matrix
        """
        return self._align_matrix(frame, matrix)
