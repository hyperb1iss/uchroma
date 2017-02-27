# pylint: disable=invalid-name, no-member

"""
Fixups are mixins which adjust input/output data in some form.
"""
import numpy as np
from numpy import array

from .hardware import Hardware


class KeyboardFixup(object):
    """
    Fixup which adjusts key coordinates in order to achieve a linear matrix.
    """
    def __init__(self, *args, **kwargs):
        super(KeyboardFixup, self).__init__(*args, **kwargs)

        self._alignment_map = self._hardware.key_fixup_mapping
        self._row_offsets = self._hardware.key_row_offsets


    @staticmethod
    def _insert(rowdata: array, col: int) -> array:
        """
        Inserts a "spacer" into the output row, effectively sliding right.

        :param rowdata: The current data for the current row
        :param col: The column number where the empty cell should be inserted

        :return: The updated row data
        """
        return np.insert(rowdata, col, [0, 0, 0], axis=0)


    @staticmethod
    def _delete(rowdata: array, col: int) -> array:
        """
        Deletes a cell from the output row, effectively sliding left.

        :param rowdata: The current data for the current row
        :param col: The column number where a cell should be removed

        :return: The updated row data
        """
        return np.delete(rowdata, col, axis=0)


    @staticmethod
    def _copy(matrix: array, src: tuple, dst: tuple) -> array:
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
    def _update_debug_info(frame, debug_position: tuple,
                           in_data: array=None, out_data: array=None):
        """
        Used by the alignment utility.
        """
        if debug_position is not None and len(debug_position) == 2:
            row = debug_position[0]

            if in_data is not None:
                frame.debug_opts['in_data'] = np.copy(in_data[row])
            if out_data is not None:
                frame.debug_opts['out_data'] = np.copy(out_data[row])


    def _align_matrix(self, frame, matrix: array) -> array:
        """
        Apply the alignment map to the given matrix, performing
        inserts, deletes, and copies (in this order).

        :param matrix: The input matrix

        :return: The updated matrix
        """
        skip_fixups = frame.debug_opts.get('skip_fixups', False)
        debug_position = frame.debug_opts.get('debug_position', None)

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
        if self._row_offsets is None or frame.debug_opts.get('skip_fixups'):
            return 0

        return self._row_offsets[row]


    def align_key_matrix(self, frame, matrix: array) -> array:
        """
        Perform alignment of the matrix. Columns may be inserted,
        deleted, or copied from other locations.

        :param matrix: The input data matrix

        :return: The aligned matrix
        """
        return self._align_matrix(frame, matrix)



BLADE_PRO_KEY_ALIGNMENT_MAP = {
    'insert': [],
    'delete': [],
    'copy': [((5, 11), (5, 10)),   # right alt misaligned under spacebar
             ((0, 22), (2, 22)),  # wheel is backwards and under trackpad
             ((0, 21), (0, 22))]
}
