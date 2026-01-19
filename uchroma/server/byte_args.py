#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
ByteArgs helper for headset protocol.

Headsets use a different protocol than other Razer devices - they use
interrupt transfers with a custom report format, not the standard 90-byte
feature reports used by keyboards, mice, etc.

This is kept minimal until interrupt transfer support is added to Rust.
"""

import struct

import numpy as np

from uchroma.colorlib import Color


class ByteArgs:
    """
    Helper class for assembling byte arrays from argument lists.
    Used by headset protocol which has its own packet format.
    """

    def __init__(self, size, data=None):
        self._data_ptr = 0
        if data is None:
            self._data = np.zeros(shape=(size,), dtype=np.uint8)
        else:
            self._data = np.frombuffer(data, dtype=np.uint8)

    @property
    def data(self):
        return self._data

    def put(self, arg, packing=None):
        """Add an argument to this array."""
        data = None
        if packing is not None:
            data = struct.pack(packing, arg)
        elif isinstance(arg, Color):
            data = struct.pack("=BBB", *arg.intTuple[:3])
        elif isinstance(arg, np.ndarray):
            data = arg.flatten()
        elif isinstance(arg, (bytearray, bytes)):
            data = arg
        else:
            data = struct.pack("=B", arg)

        if isinstance(data, int):
            self._data[self._data_ptr] = data
            self._data_ptr += 1
        else:
            datalen = len(data)
            if datalen > 0:
                if not isinstance(data, np.ndarray):
                    data = np.frombuffer(data, dtype=np.uint8)
                self._data[self._data_ptr : self._data_ptr + datalen] = data
                self._data_ptr += datalen

        return self
