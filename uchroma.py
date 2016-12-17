import logging
import struct
import time

from enum import Enum

import hidapi

RAZER_VENDOR_ID = 0x1532

class Status(Enum):
    # response codes
    BUSY = 0x01
    OK = 0x02
    FAIL = 0x03
    TIMEOUT = 0x04
    UNSUPPORTED = 0x05

class Command(Enum):
    # info queries, command class 0
    SET_DEVICE_MODE = (0x00, 0x04, 0x02)

    GET_FIRMWARE_VERSION = (0x00, 0x81, 0x02)
    GET_SERIAL = (0x00, 0x82, 0x16)
    GET_DEVICE_MODE = (0x00, 0x84, 0x02)

    # state commands, command class 3
    SET_LED_STATE = (0x03, 0x00, 0x03)
    SET_LED_RGB = (0x03, 0x01, 0x05)
    SET_LED_EFFECT = (0x03, 0x02, 0x03)
    SET_LED_BRIGHTNESS = (0x03, 0x03, 0x03)

    SET_EFFECT = (0x03, 0x0A, None)

    GET_LED_STATE = (0x03, 0x80, 0x03)
    GET_LED_RGB = (0x03, 0x81, 0x05)
    GET_LED_EFFECT = (0x03, 0x82, 0x03)
    GET_LED_BRIGHTNESS = (0x03, 0x83, 0x03)


# LED states
class LEDState(Enum):
    OFF = 0x00
    ON = 0x01

# LED types
class LEDType(Enum):
    SCROLL_WHEEL = 0x01
    BATTERY = 0x03
    LOGO = 0x04
    BACKLIGHT = 0x05
    MACRO = 0x07
    GAME = 0x08
    PROFILE_RED = 0x0E
    PROFILE_GREEN = 0x0C
    PROFILE_BLUE = 0x0D

# LED modes
class LEDMode(Enum):
    STATIC = 0x00
    BLINK = 0x01
    PULSE = 0x02
    SPECTRUM = 0x04

# Effects
class ChromaEffect(Enum):
    NONE = 0x00
    WAVE = 0x01
    REACTIVE = 0x02
    BREATHE = 0x03
    SPECTRUM = 0x04
    CUSTOM = 0x05
    STATIC = 0x06
    STARLIGHT = 0x19

WAVE_MODE_RIGHT = 0
WAVE_MODE_LEFT = 2
WAVE_MODE_LEFT_CHASE = 3
WAVE_MODE_RIGHT_CHASE = 4

STARLIGHT_MODE_RANDOM = 0
STARLIGHT_MODE_SINGLE = 1
STARLIGHT_MODE_DUAL = 2

BREATHE_MODE_RANDOM = 0
BREATHE_MODE_SINGLE = 1
BREATHE_MODE_DUAL = 2

class RGB:
    def __init__(self, red=None, green=None, blue=None):
        if red is not None and isinstance(red, tuple):
            self._red = red[0]
            self._green = red[1]
            self._blue = red[2]
        else:
            if red is None:
                self._red = 0
            else:
                self._red = red

            if green is None:
                self._green = 0
            else:
                self._green = green

            if blue is None:
                self._blue = 0
            else:
                self._blue = blue

    def get(self):
        return self._red, self._green, self._blue

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

    def __bytes__(self):
        return struct.pack('=BBB', self._red, self._green, self._blue)


class RazerChromaDriver:

    def __init__(self, path):

        self._path = path
        self._logger = logging.getLogger('uchroma.driver')
        self._devinfo = None

        devinfos = hidapi.enumerate()
        for devinfo in devinfos:
            if devinfo.path == str.encode(path) and devinfo.vendor_id == RAZER_VENDOR_ID:
                self._devinfo = devinfo
                break

        if self._devinfo is None:
            self._logger.error('No compatible Razer devices found')
            return

        try:
            self._dev = hidapi.Device(self._devinfo)
        except Exception as ex:
            self._logger.error('Error opening %s: %s', path, ex)
            raise

    def get_firmware_version(self):
        report = RazerReport(self._dev, Command.GET_FIRMWARE_VERSION)
        if not report.run():
            return None

        return 'v%d.%d' % (report.result[0], report.result[1])

    def _set_chroma_effect(self, effect, *args):
        report = RazerReport(self._dev, Command.SET_EFFECT)
        report.args.put_byte(effect.value)
        if args is not None:
            for arg in args:
                if arg is not None:
                    report.args.put_byte(arg)

        return report.run()

    def disable_effects(self):
        return self._set_chroma_effect(ChromaEffect.NONE)


    def set_color(self, rgb=None):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        return self._set_chroma_effect(ChromaEffect.STATIC, rgb)


    def wave_effect(self, direction=0):
        return self._set_chroma_effect(ChromaEffect.WAVE, direction)


    def spectrum_effect(self):
        return self._set_chroma_effect(ChromaEffect.SPECTRUM)


    def reactive_effect(self, rgb=None, speed=1):
        if rgb is None:
            rgb = RGB(0, 64, 255)

        if speed < 1 or speed > 4:
            raise ValueError('Speed for reactive effect must be between 1 and 4 (got: %d)', speed)

        return self._set_chroma_effect(ChromaEffect.REACTIVE, speed, rgb.red, rgb.green, rgb.blue)


    def starlight_effect(self, mode=STARLIGHT_MODE_RANDOM, rgb1=None, rgb2=None, speed=1):
        if speed < 1 or speed > 4:
            raise ValueError('Speed for starlight effect must be between 1 and 4 (got: %d)', speed)

        if mode == STARLIGHT_MODE_RANDOM:
            return self._set_chroma_effect(ChromaEffect.STARLIGHT, mode, speed)

        elif mode == STARLIGHT_MODE_SINGLE:
            if rgb1 is None:
                rgb1 = RGB(0, 0, 255)

            return self._set_chroma_effect(ChromaEffect.STARLIGHT, mode, speed, rgb1)
        elif mode == STARLIGHT_MODE_DUAL:
            if rgb1 is None:
                rgb1 = RGB(0, 0, 255)
            if rgb2 is None:
                rgb2 = RGB(255, 255, 255)

            return self._set_chroma_effect(ChromaEffect.STARLIGHT, mode, speed, rgb1, rgb2)

        raise ValueError('Invalid mode (%d) for starlight effect', mode)


    def breathe_effect(self, mode=BREATHE_MODE_RANDOM, rgb1=None, rgb2=None, speed=1):
        if speed < 1 or speed > 4:
            raise ValueError('Speed for breathe effect must be between 1 and 4 (got: %d)', speed)

        if mode == BREATHE_MODE_RANDOM:
            return self._set_chroma_effect(ChromaEffect.BREATHE, mode, speed)

        elif mode == BREATHE_MODE_SINGLE:
            if rgb1 is None:
                rgb1 = RGB(0, 0, 255)

            return self._set_chroma_effect(ChromaEffect.BREATHE, mode, speed, rgb1)

        elif mode == BREATHE_MODE_DUAL:
            if rgb1 is None:
                rgb1 = RGB(0, 0, 255)
            if rgb2 is None:
                rgb2 = RGB(255, 255, 255)

            return self._set_chroma_effect(ChromaEffect.BREATHE, mode, speed, rgb1, rgb2)

        raise ValueError('Invalid mode (%d) for breathe effect', mode)


class RazerReport:

    REQ_HEADER = '=BHBBBB'
    RSP_HEADER = '=BBHBBBB'

    REQ_REPORT_ID = b'\x02'
    RSP_REPORT_ID = b'\x00'

    BUF_SIZE = 90
    DATA_BUF_SIZE = 80

    def __init__(self, hid, cmd, status=0x00, transaction_id=0xFF, remaining_packets=0x00,
                 protocol_type=0x00, data=None, crc=None, reserved=None):

        self._logger = logging.getLogger('uchroma.report')

        self._hid = hid

        self._status = status
        self._transaction_id = transaction_id
        self._remaining_packets = remaining_packets
        self._protocol_type = protocol_type

        self._command_name = cmd.name

        self._command_class = cmd.value[0]
        self._command_id = cmd.value[1]

        self._result = None

        self._data = RazerReport.Args(data=data, size=cmd.value[2])

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

        self._logger.error("Got error %s for %s (raw response: %s)", self._status.name,
                           self._command_name, repr(data))

        return False

    class Args:
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
            assert (len(self._data) + size) <= self._size, 'Additional argument would exceed size limit %d (%d)' % (self._size, len(self._data) + size)

        def clear(self):
            self._data.clear()
            return self

        def put_byte(self, arg):
            if isinstance(arg, RGB):
                self._ensure_space(3)
                self._data += bytes(arg)
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

