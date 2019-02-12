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
import struct
from enum import Enum

import numpy as np
from grapefruit import Color


class ByteArgs:
    """
    Helper class for assembling byte arrays from
    argument lists of varying types
    """
    def __init__(self, size, data=None):
        self._data_ptr = 0

        if data is None:
            self._data = np.zeros(shape=(size,), dtype=np.uint8)
        else:
            self._data = np.frombuffer(data, dtype=np.uint8)


    @property
    def data(self):
        """
        The byte array assembled from supplied arguments
        """
        return self._data


    @property
    def size(self):
        """
        Size of the byte array
        """
        return len(self._data)


    def _ensure_space(self, size):
        assert len(self._data) > size + self._data_ptr, \
                ('Additional argument (len=%d) would exceed size limit %d (cur=%d)'
                 % (size, len(self._data), self._data_ptr))


    def clear(self):
        """
        Empty the contents of the array

        :return: The empty ByteArgs
        :rtype: ByteArgs
        """
        self._data.fill(0)
        self._data_ptr = 0
        return self


    def put(self, arg, packing=None):
        """
        Add an argument to this array

        :param arg: The argument to append
        :type arg: varies

        :param packing: The representation passed to struct.pack
        :type packing: str

        :return: This ByteArgs instance
        :rtype: ByteArgs
        """
        data = None
        if packing is not None:
            data = struct.pack(packing, arg)
        elif isinstance(arg, Color):
            data = struct.pack("=BBB", *arg.intTuple)
        elif isinstance(arg, Enum):
            if hasattr(arg, "opcode"):
                data = arg.opcode
            else:
                data = arg.value
        elif isinstance(arg, np.ndarray):
            data = arg.flatten()
        elif isinstance(arg, (bytearray, bytes)):
            data = arg
        else:
            data = struct.pack("=B", arg)

        if isinstance(data, int):
            if self._data_ptr + 1 > len(self._data):
                raise ValueError('No space left in argument list')

            self._ensure_space(1)
            self._data[self._data_ptr] = data
            self._data_ptr += 1
        else:
            datalen = len(data)
            if datalen > 0:
                if self._data_ptr + datalen > len(self._data):
                    raise ValueError('No space left in argument list')

                if not isinstance(data, np.ndarray):
                    data = np.frombuffer(data, dtype=np.uint8)
                self._data[self._data_ptr:self._data_ptr+datalen] = data
                self._data_ptr += datalen

        return self


    def put_all(self, args, packing=None):
        for arg in args:
            self.put(arg, packing=packing)
        return self


    def put_short(self, arg):
        """
        Convenience method to add an argument as a short to
        the array

        :param arg: The argument to append
        :type arg: varies

        :return: This ByteArgs instance
        :rtype: ByteArgs
        """
        return self.put(arg, '=H')


    def put_int(self, arg):
        """
        Convenience method to add an argument as an integer to
        the array

        :param arg: The argument to append
        :type arg: varies

        :return: This ByteArgs instance
        :rtype: ByteArgs
        """
        return self.put(arg, '=I')
