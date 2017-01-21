import struct
from enum import Enum

from grapefruit import Color


class ByteArgs(object):
    """
    Helper class for assembling byte arrays from
    argument lists of varying types
    """
    def __init__(self, size=0, data=None):
        self._size = size

        if data is None:
            self._data = bytearray()
        else:
            self._data = data


    @property
    def data(self):
        """
        The byte array assembled from supplied arguments
        """
        if self._size is None or len(self._data) == self._size:
            return self._data
        else:
            return self._data + (b'\x00' * (self._size - len(self._data)))


    @property
    def size(self):
        """
        Size of the byte array
        """
        if self._size is None:
            return len(self._data)
        return self._size


    def _ensure_space(self, size):
        if self._size is None:
            return
        assert (len(self._data) + size) <= self._size, \
                ('Additional argument (len=%d) would exceed size limit %d (cur=%d)'
                 % (size, self._size, len(self._data)))


    def clear(self):
        """
        Empty the contents of the array

        :return: The empty ByteArgs
        :rtype: ByteArgs
        """
        self._data.clear()
        return self


    def put(self, arg, packing='=B'):
        """
        Add an argument to this array

        :param arg: The argument to append
        :type arg: varies

        :param packing: The representation passed to struct.pack
        :type packing: str

        :return: This ByteArgs instance
        :rtype: ByteArgs
        """
        data = bytearray()
        if isinstance(arg, Color):
            for component in arg.intTuple:
                data += struct.pack(packing, component)
        elif isinstance(arg, Enum):
            if hasattr(arg, "opcode"):
                data += struct.pack(packing, arg.opcode)
            else:
                data += struct.pack(packing, arg.value)
        elif isinstance(arg, bytes) or isinstance(arg, bytearray):
            data += arg
        else:
            data += struct.pack(packing, arg)

        if len(data) > 0:
            self._ensure_space(len(data))
            self._data += data

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
