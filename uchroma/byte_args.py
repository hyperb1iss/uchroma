import struct
from enum import Enum

from grapefruit import Color


class ByteArgs(object):
    def __init__(self, size=0, data=None):
        self._size = size

        if data is None:
            self._data = bytearray()
        else:
            self._data = data


    @property
    def data(self):
        if self._size is None or len(self._data) == self._size:
            return self._data
        else:
            return self._data + (b'\x00' * (self._size - len(self._data)))


    @property
    def size(self):
        if self._size is None:
            return len(self._data)
        return self._size


    def _ensure_space(self, size):
        if self._size is None:
            return
        assert (len(self._data) + size) <= self._size, 'Additional argument (len=%d) would exceed size limit %d (cur=%d)' % (size, self._size, len(self._data))


    def clear(self):
        self._data.clear()
        return self


    def put(self, arg):
        if isinstance(arg, Color):
            self._ensure_space(3)
            for component in arg.intTuple:
                self._data += struct.pack('=B', component)
        elif isinstance(arg, Enum):
            self._ensure_space(1)
            self._data += struct.pack('=B', arg.value)
        elif isinstance(arg, bytes):
            self._ensure_space(len(arg))
            self._data += arg
        else:
            self._ensure_space(1)
            self._data += struct.pack('=B', arg)
        return self


    def put_short(self, arg):
        self._ensure_space(2)
        self._data += struct.pack('=H', arg)
        return self


    def put_int(self, arg):
        self._ensure_space(4)
        self._data += struct.pack('=I', arg)
        return self

