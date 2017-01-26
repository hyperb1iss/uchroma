import logging

import hidapi

from grapefruit import Color
from wrapt import synchronized

from uchroma.byte_args import ByteArgs
from uchroma.color import Splotch
from uchroma.device_base import BaseUChromaDevice
from uchroma.hardware import Hardware
from uchroma.types import BaseCommand
from uchroma.util import colorarg, ColorType, smart_delay, set_bits, scale_brightness, \
    test_bit, to_byte, to_color, to_rgb


# Output report 4, input report 5
REPORT_ID_OUT = 4
REPORT_ID_IN = 5
REPORT_LENGTH_OUT = 37
REPORT_LENGTH_IN = 33

# Sleep time 25ms
DELAY_TIME = 0.025

# Destination for requests
READ_RAM = 0x00
READ_EEPROM = 0x20
WRITE_RAM = 0x40

# EEPROM
ADDR_FIRMWARE_VERSION = 0x0030
ADDR_SERIAL_NUMBER = 0x7f00

# RAM
ADDR_KYLIE_LED_MODE = 0x172D
ADDR_KYLIE_BREATHING1_START = 0x1741
ADDR_KYLIE_BREATHING2_START = 0x1745
ADDR_KYLIE_BREATHING3_START = 0x174D

ADDR_RAINIE_LED_MODE = 0x1008
ADDR_RAINIE_BREATHING1_START = 0x15DE


class EffectBits(object):
    """
    The effect mode on this hardware is represented by a single
    integer. This class assists with managing the bits of
    this value.
    """
    def __init__(self, value: int=0):
        self.on = test_bit(value, 0)
        self.breathe_single = test_bit(value, 1)
        self.spectrum = test_bit(value, 2)
        self.sync = test_bit(value, 3)
        self.breathe_double = test_bit(value, 4)
        self.breathe_triple = test_bit(value, 5)


    @property
    def value(self) -> int:
        """
        Return the state as an integer
        """
        return set_bits(0, self.on, self.breathe_single, self.spectrum,
                        self.sync, self.breathe_double, self.breathe_triple)


    @property
    def color_count(self) -> int:
        """
        Returns the number of colors currently in use
        """
        if self.breathe_triple:
            return 3
        elif self.breathe_double:
            return 2
        elif self.breathe_single:
            return 1
        elif self.on == 1:
            return 1
        return 0



class UChromaHeadset(BaseUChromaDevice):
    """
    Additional functionality for Chroma Headsets
    The protocol on these devices is different than
    the rest of the Chroma line.
    """

    class Command(BaseCommand):
        """
        Commands used for headset features

        0: Destination
        1: Length
        2-3: Address
        """
        GET_SERIAL = (READ_EEPROM, 0x16, ADDR_SERIAL_NUMBER)
        GET_FIRMWARE_VERSION = (READ_EEPROM, 0x02, ADDR_FIRMWARE_VERSION)

        KYLIE_GET_LED_MODE = (READ_RAM, 0x01, ADDR_KYLIE_LED_MODE)
        KYLIE_SET_LED_MODE = (WRITE_RAM, 0x01, ADDR_KYLIE_LED_MODE)

        KYLIE_GET_RGB_1 = (READ_RAM, 0x04, ADDR_KYLIE_BREATHING1_START)
        KYLIE_GET_RGB_2 = (READ_RAM, 0x08, ADDR_KYLIE_BREATHING2_START)
        KYLIE_GET_RGB_3 = (READ_RAM, 0x0C, ADDR_KYLIE_BREATHING3_START)
        KYLIE_SET_RGB_1 = (WRITE_RAM, 0x04, ADDR_KYLIE_BREATHING1_START)
        KYLIE_SET_RGB_2 = (WRITE_RAM, 0x08, ADDR_KYLIE_BREATHING2_START)
        KYLIE_SET_RGB_3 = (WRITE_RAM, 0x0C, ADDR_KYLIE_BREATHING3_START)

        RAINIE_GET_LED_MODE = (READ_RAM, 0x01, ADDR_RAINIE_LED_MODE)
        RAINIE_SET_LED_MODE = (WRITE_RAM, 0x01, ADDR_RAINIE_LED_MODE)

        RAINIE_GET_RGB = (WRITE_RAM, 0x04, ADDR_RAINIE_BREATHING1_START)
        RAINIE_SET_RGB = (WRITE_RAM, 0x04, ADDR_RAINIE_BREATHING1_START)


        def __init__(self, destination, length, address):
            self._destination = destination
            self._length = length
            self._address = address


        @property
        def destination(self):
            return self._destination


        @property
        def length(self):
            return self._length


        @property
        def address(self):
            return self._address



    def __init__(self, hardware: Hardware, devinfo: hidapi.DeviceInfo, *args, **kwargs):
        super(UChromaHeadset, self).__init__(hardware, devinfo, *args, **kwargs)

        self._last_cmd_time = None

        if self.hardware.revision == 1:
            self._cmd_get_led = UChromaHeadset.Command.RAINIE_GET_LED_MODE
            self._cmd_set_led = UChromaHeadset.Command.RAINIE_SET_LED_MODE
            self._cmd_get_rgb = [UChromaHeadset.Command.RAINIE_GET_RGB]
            self._cmd_set_rgb = [UChromaHeadset.Command.RAINIE_SET_RGB]

        elif self.hardware.revision == 2:
            self._cmd_get_led = UChromaHeadset.Command.KYLIE_GET_LED_MODE
            self._cmd_set_led = UChromaHeadset.Command.KYLIE_SET_LED_MODE
            self._cmd_get_rgb = [UChromaHeadset.Command.KYLIE_GET_RGB_1,
                                 UChromaHeadset.Command.KYLIE_GET_RGB_2,
                                 UChromaHeadset.Command.KYLIE_GET_RGB_3]
            self._cmd_set_rgb = [UChromaHeadset.Command.KYLIE_SET_RGB_1,
                                 UChromaHeadset.Command.KYLIE_SET_RGB_2,
                                 UChromaHeadset.Command.KYLIE_SET_RGB_3]
        else:
            raise ValueError('Incompatible model (%s)' % repr(self.hardware))

        self._logger = logging.getLogger('uchroma.headset')



    @staticmethod
    def _pack_request(command: BaseCommand, *args) -> bytes:
        req = ByteArgs(size=REPORT_LENGTH_OUT)
        req.put(command.destination)
        req.put(command.length)
        req.put(command.address, packing='>H')

        if args is not None:
            for arg in args:
                if arg is not None:
                    req.put(arg)

        return req.data


    def _hexdump(self, data: bytes, tag=""):
        if data is not None:
            self._logger.debug('%s%s', tag, "".join('%02x ' % b for b in data))


    @synchronized
    def run_command(self, command: BaseCommand, *args) -> bool:
        """
        Run a command against the Kraken hardware

        :param command: The command tuple
        :param args: Argument list (varargs)

        :return: True if successful
        """
        try:
            data = UChromaHeadset._pack_request(command, *args)
            self._hexdump(data, '--> ')
            self._ensure_open()
            self._last_cmd_time = smart_delay(DELAY_TIME, self._last_cmd_time, 0)
            self._dev.write(data, report_id=to_byte(REPORT_ID_OUT))
            return True

        except (OSError, IOError) as err:
            self._logger.exception('Caught exception running command', exc_info=err)

        finally:
            self._close()

        return False


    @synchronized
    def run_with_result(self, command: BaseCommand, *args) -> bytes:
        """
        Run a command against the Kraken hardware and fetch the result

        :param command: The command tuple
        :param args: Argument list (varargs)

        :return: Raw response bytes
        """
        try:
            if not self.run_command(command, *args):
                self._close(True)
                return None

            self._ensure_open()

            self._last_cmd_time = smart_delay(DELAY_TIME, self._last_cmd_time, 0)
            resp = self._dev.read(REPORT_LENGTH_IN, timeout_ms=500)
            self._hexdump(resp, '<-- ')

            if resp is None or len(resp) == 0:
                return None

            assert resp[0] == REPORT_ID_IN, \
                'Inbound report should have id %02x (was %02x)' % \
                (REPORT_ID_IN, resp[0])

            return resp[1:command.length+1]

        except (OSError, IOError) as err:
            self._logger.exception('Caught exception running command', exc_info=err)

        finally:
            self._close()

        return None


    def _get_serial_number(self) -> str:
        """
        Get the serial number from the hardware directly
        """
        return self._decode_serial(
            self.run_with_result(UChromaHeadset.Command.GET_SERIAL))


    def _get_firmware_version(self) -> str:
        """
        Get the firmware version from the hardware directly
        """
        return self.run_with_result(UChromaHeadset.Command.GET_FIRMWARE_VERSION)


    def _get_led_mode(self) -> 'UChromaHeadset.EffectBits':
        value = self.run_with_result(self._cmd_get_led)
        bits = 0
        if value is not None and len(value) > 0:
            bits = value[0]
        return EffectBits(bits)


    def _set_led_mode(self, bits: EffectBits) -> bool:
        return self.run_command(self._cmd_set_led, bits.value)


    def _get_rgb(self) -> list:
        bits = self._get_led_mode()
        if bits.color_count == 0:
            return None

        value = self.run_with_result(self._cmd_get_rgb[bits.color_count - 1])
        if value is None:
            return None

        it = iter(value)
        values = list(iter(zip(it, it, it, it)))

        return [to_color(x) for x in values]


    def _set_rgb(self, *colors, brightness: float=None) -> bool:
        if colors is None or len(colors) == 0:
            self._logger.error('RGB group out of range')
            return False

        # only allow what the hardware permits
        colors = colors[0:len(self._cmd_set_rgb)]

        if brightness is None:
            brightness = self.brightness
            if brightness == 0.0:
                brightness = 80.0

        brightness = scale_brightness(brightness)

        args = []
        for color in colors:
            args.append(to_color(color))
            args.append(brightness)

        return self.run_command(self._cmd_set_rgb[len(colors) - 1], *args)


    def get_current_effect(self) -> EffectBits:
        """
        Gets the current effects configuration

        :return: EffectBits populated from the hardware
        """
        return self._get_led_mode()


    def get_current_colors(self) -> list:
        """
        Gets the colors currently in use

        :return: List of RGB tuples
        """
        colors = self._get_rgb()
        if colors is None or len(colors) == 0:
            return None

        return [to_rgb(color) for color in colors]


    @property
    def brightness(self) -> float:
        """
        The current brightness level
        """
        bits = self._get_led_mode()
        if bits.color_count == 0:
            if bits.on:
                return 100.0
            else:
                return 0.0

        value = self.run_with_result(self._cmd_get_rgb[bits.color_count - 1])
        if value is None:
            return 0.0

        return scale_brightness(value[3], True)


    @brightness.setter
    def brightness(self, brightness: float) -> bool:
        """
        Set the brightness level
        """
        bits = self._get_led_mode()
        if bits.color_count == 0:
            return False

        value = self.run_with_result(self._cmd_get_rgb[bits.color_count - 1])
        if value is None:
            return False

        level = scale_brightness(brightness)

        data = bytearray(value)
        for num in range(0, bits.color_count):
            data[(num * 4) + 3] = level

        return self.run_command(self._cmd_set_rgb[bits.color_count -1], data)


    def disable(self) -> bool:
        """
        Disable all effects

        :return: True if successful
        """
        bits = EffectBits()
        bits.spectrum = True
        return self._set_led_mode(bits)


    def spectrum(self) -> bool:
        """
        Cycle thru all colors of the spectrum

        :return: True if successful
        """
        bits = EffectBits()
        bits.on = bits.spectrum = True
        return self._set_led_mode(bits)


    @colorarg
    def static(self, color: ColorType=None) -> bool:
        """
        Sets lighting to a static color

        :param color: The color to apply

        :return: True if successful
        """
        if color is None:
            color = Color.NewFromHtml('green')

        bits = EffectBits()
        bits.on = True
        if self._set_rgb(color):
            return self._set_led_mode(bits)

        return False


    @colorarg
    def breathe(self, color1: ColorType=None, color2: ColorType=None,
                color3: ColorType=None, splotch: Splotch=None) -> bool:
        """
        Breathing color effect. Accepts up to three colors on v2 hardware

        :param color1: Primary color
        :param color2: Secondary color
        :param color3: Tertiary color
        :param splotch: Predefinied color pair

        :return True if successful:
        """
        if splotch is not None:
            color1 = splotch.first
            color2 = splotch.second

        args = []

        color_count = 0
        if color1 is not None:
            args.append(color1)
            color_count += 1
        if color2 is not None:
            args.append(color2)
            color_count += 1
        if color3 is not None:
            args.append(color3)
            color_count += 1

        bits = EffectBits()
        bits.on = True
        bits.sync = True
        if color_count == 3:
            bits.breathe_triple = True
        elif color_count == 2:
            bits.breathe_double = True
        elif color_count == 1:
            bits.breathe_single = True

        if self._set_rgb(*args):
            return self._set_led_mode(bits)

        return False
