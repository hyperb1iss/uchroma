#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=import-error, no-name-in-module, invalid-name

import struct
import time
from enum import Enum

import numpy as np

from uchroma._native import fast_crc
from uchroma.log import LOG_PROTOCOL_TRACE
from uchroma.util import smart_delay

from .byte_args import ByteArgs


# response codes
class Status(Enum):
    """
    Enumeration of status codes returned by the hardware
    """

    UNKNOWN = 0x00
    BUSY = 0x01
    OK = 0x02
    FAIL = 0x03
    TIMEOUT = 0x04
    UNSUPPORTED = 0x05
    BAD_CRC = 0xFE
    OSERROR = 0xFF


class RazerReport:
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

    The status byte is 0x00 when sending, and contains the result code
    when receiving.
    """

    # Request and response have same structure
    REQ_HEADER = "=BBHBBBB"  # status, trans_id, remaining, proto, size, class, cmd
    RSP_HEADER = "=BBHBBBB"

    # OpenRazer uses report ID 0 for both send and receive
    REQ_REPORT_ID = b"\x00"
    RSP_REPORT_ID = b"\x00"

    BUF_SIZE = 90
    DATA_BUF_SIZE = 80

    # Time to sleep between requests, needed to avoid BUSY replies
    CMD_DELAY_TIME = 0.007

    def __init__(
        self,
        driver,
        command_class,
        command_id,
        data_size,
        status=0x00,
        transaction_id=0xFF,
        remaining_packets=0x00,
        protocol_type=0x00,
        data=None,
        crc=None,
        reserved=None,
    ):
        self._logger = driver.logger

        self._driver = driver

        self._status = status
        self._transaction_id = transaction_id
        self._remaining_packets = remaining_packets
        self._protocol_type = protocol_type
        self._data_size = data_size  # Store the actual command data size

        self._command_class = command_class
        self._command_id = command_id

        self._result = None

        self._data = ByteArgs(RazerReport.DATA_BUF_SIZE, data=data)

        self._buf = np.zeros(shape=(RazerReport.BUF_SIZE,), dtype=np.uint8)

        if reserved is None:
            self._reserved = 0
        else:
            self._reserved = reserved

        if crc is None:
            self._crc = 0
        else:
            self._crc = crc

    def _hexdump(self, data, tag=""):
        if self._logger.isEnabledFor(LOG_PROTOCOL_TRACE):
            self._logger.debug("%s%s", tag, "".join(f"{b:02x} " for b in data))

    def clear(self):
        self._buf.fill(0)
        self._data.clear()
        self._status = 0x00
        self._remaining_packets = 0x00
        self._result = None

    def run(self, delay: float | None = None, timeout_cb=None) -> bool:
        """
        Run this report and retrieve the result from the hardware.

        Sends the feature report and parses the result. A small delay
        is required between calls to the hardware or a BUSY status
        will be returned. This delay may need adjusted on a per-model
        basis.

        If debug loglevel is enabled, the raw report data from both
        the request and the response will be logged.

        :param delay: Time to delay between requests (defaults to 0.005 sec)
        :param timeout_cb: Callback to run when a TIMEOUT is returned

        :return: The parsed result from the hardware
        """
        if delay is None:
            delay = RazerReport.CMD_DELAY_TIME

        retry_count = 3

        with self._driver.device_open():
            while retry_count > 0:
                try:
                    req = self._pack_request()
                    self._hexdump(req, "--> ")
                    if self._remaining_packets == 0:
                        self._driver.last_cmd_time = smart_delay(
                            delay, self._driver.last_cmd_time, self._remaining_packets
                        )
                    self._driver.hid.send_feature_report(req, self.REQ_REPORT_ID)
                    if self._remaining_packets > 0:
                        return True

                    self._driver.last_cmd_time = smart_delay(
                        delay, self._driver.last_cmd_time, self._remaining_packets
                    )
                    resp = self._driver.hid.get_feature_report(self.RSP_REPORT_ID, self.BUF_SIZE)
                    self._hexdump(resp, "<-- ")
                    if self._unpack_response(resp):
                        if timeout_cb is not None:
                            timeout_cb(self.status, None)
                        return True

                    if self.status == Status.UNSUPPORTED:
                        # UNSUPPORTED is normal for features the device doesn't have
                        self._logger.debug("Command unsupported: %s", self.status.name)
                        return False

                    if self.status == Status.FAIL:
                        self._logger.error("Command failed with status %s", self.status.name)
                        return False

                    if timeout_cb is not None and self.status == Status.TIMEOUT:
                        timeout_cb(self.status, self.result)
                        return False

                    self._logger.warning(
                        "Retrying request due to status %s (%d)", self.status.name, retry_count
                    )

                    time.sleep(0.1)

                    retry_count -= 1

                except OSError:
                    self._status = Status.OSERROR
                    raise

        return False

    @property
    def args(self) -> ByteArgs:
        """
        The byte array containing the raw report data to be sent to
        the hardware when run() is called.
        """
        return self._data

    @property
    def status(self) -> int | Status:
        """
        Status code of this report.
        """
        return self._status

    @property
    def result(self) -> bytes:
        """
        The byte array containing the raw result data after run() is called.
        """
        return self._result.tobytes()

    @property
    def remaining_packets(self) -> int:
        return self._remaining_packets

    @remaining_packets.setter
    def remaining_packets(self, num):
        self._remaining_packets = num

    def _pack_request(self) -> bytes:
        # Use actual args size if data_size was None
        data_size = self._data_size if self._data_size is not None else self._data._data_ptr

        # Pack header: status=0x00 for requests, then transaction_id, etc.
        struct.pack_into(
            RazerReport.REQ_HEADER,
            self._buf,
            0,
            0x00,  # status byte (0 for requests)
            self._transaction_id,
            self._remaining_packets,
            self._protocol_type,
            data_size,
            self._command_class,
            self._command_id,
        )

        # Args at offset 8 (after 8-byte header)
        self._buf[8:88] = self.args.data

        # CRC calculation - fast_crc XORs bytes 1-86 (transaction_id through args[78])
        self._buf[88] = fast_crc(self._buf.tobytes())

        return self._buf.tobytes()

    def _unpack_response(self, buf: bytes) -> bool:
        assert len(buf) == self.BUF_SIZE, (
            f"Packed struct should be {self.BUF_SIZE} bytes, got {len(buf)}"
        )

        header = struct.unpack(self.RSP_HEADER, buf[:8])
        status = header[0]
        header[1]
        header[2]
        header[3]
        data_size = header[4]
        header[5]
        header[6]

        data = np.frombuffer(buf[8 : 8 + data_size], dtype=np.uint8)
        buf[88]
        buf[89]

        # CRC check - fast_crc XORs bytes 1-86 (transaction_id through args[78])
        fast_crc(buf)

        self._status = Status(status)
        self._result = data

        if self._status == Status.OK:
            # Note: Some devices (like Blade 2021) return CRC=0x00, so we skip CRC validation
            # on successful responses. This matches razer-laptop-control behavior.
            return True

        # UNSUPPORTED is not an error - it's a normal response for unsupported commands
        if self._status == Status.UNSUPPORTED:
            self._logger.debug(
                "Command %02x,%02x returned UNSUPPORTED",
                self._command_class,
                self._command_id,
            )
        else:
            self._logger.error(
                "Got error %s for command %02x,%02x",
                self._status.name,
                self._command_class,
                self._command_id,
            )
            self._hexdump(data, "raw response: ")

        return False
