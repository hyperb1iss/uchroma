import logging
import struct
import time

from enum import Enum

from uchroma.byte_args import ByteArgs


# response codes
class Status(Enum):
    BUSY = 0x01
    OK = 0x02
    FAIL = 0x03
    TIMEOUT = 0x04
    UNSUPPORTED = 0x05


class RazerReport(object):

    REQ_HEADER = '=BHBBBB'
    RSP_HEADER = '=BBHBBBB'

    REQ_REPORT_ID = b'\x02'
    RSP_REPORT_ID = b'\x00'

    BUF_SIZE = 90
    DATA_BUF_SIZE = 80

    def __init__(self, hid, command_class, command_id, data_size,
                 status=0x00, transaction_id=0xFF, remaining_packets=0x00,
                 protocol_type=0x00, data=None, crc=None, reserved=None):

        self._logger = logging.getLogger('uchroma.report')

        self._hid = hid

        self._status = status
        self._transaction_id = transaction_id
        self._remaining_packets = remaining_packets
        self._protocol_type = protocol_type

        self._command_class = command_class
        self._command_id = command_id

        self._result = None

        self._data = ByteArgs(data=data, size=data_size)

        if reserved is None:
            self._reserved = 0
        else:
            self._reserved = reserved

        if crc is None:
            self._crc = 0
        else:
            self._crc = crc

    def _ensure_open(self):
        if self._hid is None:
            raise ValueError('No valid HID device!')

    def run(self):
        self._ensure_open()

        self._hid.send_feature_report(self._pack_request(), self.REQ_REPORT_ID)
        time.sleep(0.2)
        return self._unpack_response(self._hid.get_feature_report(self.RSP_REPORT_ID, self.BUF_SIZE))

    @property
    def args(self):
        return self._data

    @property
    def status(self):
        return self._status

    @property
    def result(self):
        return bytes(self._result)

    def _calculate_crc(self, buf):
        crc = 0
        for byte in buf[1:87]:
            crc ^= int(byte)
        return crc

    def _pack_request(self):
        buf = bytearray(self.BUF_SIZE)

        struct.pack_into(self.REQ_HEADER, buf, 0, self._transaction_id, self._remaining_packets,
                         self._protocol_type, self.args.size, self._command_class, self._command_id)

        data_buf = self.args.data
        if len(data_buf) > 0:
            buf[7:len(data_buf) + 7] = data_buf

        assert len(buf) == self.BUF_SIZE, 'Packed struct should be %d bytes, got %d' % (self.BUF_SIZE, len(buf))
        struct.pack_into('B', buf, 87, self._calculate_crc(buf))

        return bytes(buf)

    def _unpack_response(self, buf):
        assert len(buf) == self.BUF_SIZE, 'Packed struct should be %d bytes, got %d' % (self.BUF_SIZE, len(buf))

        header = struct.unpack(self.RSP_HEADER, buf[:8])
        status = header[0]
        transaction_id = header[1]
        remaining_packets = header[2]
        protocol_type = header[3]
        data_size = header[4]
        command_class = header[5]
        command_id = header[6]

        data = bytearray(buf[8:8 + data_size])
        crc = buf[88]
        reserved = buf[89]

        crc_check = self._calculate_crc(buf[1:88])


        assert crc == crc_check, 'Checksum of data should be %d, got %d' % (crc, crc_check)
        assert transaction_id == self._transaction_id, 'Transaction id does not match'
        assert command_class == self._command_class, 'Command class does not match'
        assert command_id == self._command_id, 'Command id does not match'
        assert protocol_type == self._protocol_type, 'Protocol type does not match'

        self._status = Status(status)
        self._result = data

        if self._status == Status.OK:
            return True

        self._logger.error("Got error %s for command %02x,%02x (raw response: %s)", self._status.name,
                           self._command_class, self._command_id, repr(data))

        return False

