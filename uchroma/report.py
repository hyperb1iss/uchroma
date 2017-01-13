import logging
import struct
import time

from enum import Enum

from uchroma.byte_args import ByteArgs


# response codes
class Status(Enum):
    """
    Enumeration of status codes returned by the hardware
    """
    BUSY = 0x01
    OK = 0x02
    FAIL = 0x03
    TIMEOUT = 0x04
    UNSUPPORTED = 0x05


class RazerReport(object):
    """
    Generates and parses HID reports to and from the hardware.

    The HID set_report is sent to report id 2 and the result is
    read with get_report from report id 0.

    The raw report data is always 90 bytes and has the following
    structure:

        Bytes       Contents
        ---------   ----------------------
        0           Status code
        1           Transaction id
        2           Remaining packets
        3           Protocol type
        4           Data size
        5           Command class
        6           Command id
        8 - 87      Report data
        88          CRC
        89          Reserved byte (zero)

    When sending a report, the status code is not sent and the bytes
    are shifted by one.
    """
    REQ_HEADER = '=BHBBBB'
    RSP_HEADER = '=BBHBBBB'

    REQ_REPORT_ID = b'\x02'
    RSP_REPORT_ID = b'\x00'

    BUF_SIZE = 90
    DATA_BUF_SIZE = 80

    # Time to sleep between requests, needed to avoid BUSY replies
    CMD_DELAY_TIME = 0.007

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
        self._last_cmd_time = None

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


    def _hexdump(self, data, tag=""):
        self._logger.debug('%s%s', tag, "".join('%02x ' % b for b in data))


    def _delay(self, delay: float=None):
        if delay is None:
            delay = RazerReport.CMD_DELAY_TIME

        now = time.perf_counter()

        if self._remaining_packets == 0 and self._last_cmd_time is not None and delay > 0:
            delta = now - self._last_cmd_time
            if delta < delay:
                sleeptime = delay - delta
                self._logger.debug('delay: %f', sleeptime)
                time.sleep(sleeptime)

        self._last_cmd_time = now


    def run(self, delay: float=None) -> bool:
        """
        Run this report and retrieve the result from the hardware.

        Sends the feature report and parses the result. A small delay
        is required between calls to the hardware or a BUSY status
        will be returned. This delay may need adjusted on a per-model
        basis.

        If debug loglevel is enabled, the raw report data from both
        the request and the response will be logged.

        :param delay: Time to delay between requests (defaults to 0.005 sec)

        :return: The parsed result from the hardware
        """
        retry_count = 3

        while retry_count > 0:
            self._ensure_open()
            req = self._pack_request()
            self._hexdump(req, '--> ')
            self._delay(delay)
            self._hid.send_feature_report(req, self.REQ_REPORT_ID)
            if self._remaining_packets > 0:
                return True

            self._delay(delay)
            resp = self._hid.get_feature_report(self.RSP_REPORT_ID, self.BUF_SIZE)
            self._hexdump(resp, '<-- ')
            if self._unpack_response(resp):
                return True

            if self.status == Status.FAIL or self.status == Status.UNSUPPORTED:
                return False

            self._logger.debug("Retrying request due to status %s (%d)",
                               self.status.name, retry_count)

            time.sleep(0.1)

            retry_count -= 1

        return False


    @property
    def args(self) -> bytes:
        """
        The byte array containing the raw report data to be sent to
        the hardware when run() is called.
        """
        return self._data


    @property
    def status(self) -> int:
        """
        Status code of this report.
        """
        return self._status


    @property
    def result(self) -> bytes:
        """
        The byte array containing the raw result data after run() is called.
        """
        return bytes(self._result)


    @staticmethod
    def _calculate_crc(buf: bytearray) -> int:
        """
        Calculated the CRC byte for the given buffer

        The CRC is calculated by iteratively XORing all bytes.
        It is verified by the hardware and we verify it when parsing
        result reports.

        :param buf: The 90-byte array of the report
        :type buf: bytearray

        :return: The calculated crc
        :rtype: int
        """
        crc = 0
        for byte in buf[1:87]:
            crc ^= int(byte)
        return crc


    def _pack_request(self) -> bytes:
        buf = bytearray(self.BUF_SIZE)

        struct.pack_into(self.REQ_HEADER, buf, 0, self._transaction_id, self._remaining_packets,
                         self._protocol_type, self.args.size, self._command_class, self._command_id)

        data_buf = self.args.data
        if len(data_buf) > 0:
            buf[7:len(data_buf) + 7] = data_buf

        assert len(buf) == self.BUF_SIZE, \
                'Packed struct should be %d bytes, got %d' % (self.BUF_SIZE, len(buf))
        struct.pack_into('B', buf, 87, RazerReport._calculate_crc(buf))

        return bytes(buf)


    def _unpack_response(self, buf: bytes) -> bool:
        assert len(buf) == self.BUF_SIZE, \
                'Packed struct should be %d bytes, got %d' % (self.BUF_SIZE, len(buf))

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

        crc_check = RazerReport._calculate_crc(buf[1:88])

        assert crc == crc_check, 'Checksum of data should be %d, got %d' % (crc, crc_check)
        assert transaction_id == self._transaction_id, 'Transaction id does not match (%d vs %d)' \
                % (transaction_id, self._transaction_id)
        assert command_class == self._command_class, 'Command class does not match'
        assert command_id == self._command_id, 'Command id does not match'
        assert protocol_type == self._protocol_type, 'Protocol type does not match'

        self._status = Status(status)
        self._result = data

        if self._status == Status.OK:
            return True

        self._logger.error("Got error %s for command %02x,%02x (raw response: %s)",
                           self._status.name, self._command_class, self._command_id, repr(data))

        return False

