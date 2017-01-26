# pylint: disable=invalid-name, pointless-string-statement
"""
Various helper functions that are used across the library.
"""
import inspect
import math
import struct
import time
import typing

from collections import Iterable
from enum import Enum
from threading import Timer

import wrapt
from grapefruit import Color
from numpy import interp


# Type hint for decorated color arguments
ColorType = typing.Union[Color, str, typing.Iterable[int], typing.Iterable[float], None]

# Type hint for decorated enum arguments
EnumType = typing.Union[Enum, str]


def _autocast_decorator(type_hint, fix_arg_func):
    """
    Decorator which will invoke fix_arg_func for any
    arguments annotated with type_hint. The decorated
    function will then be called with the result.

    :param type_hint: A PEP484 type hint
    :param fix_arg_func: Function to invoke

    :return: decorator
    """
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        sig = inspect.signature(wrapped)
        names = list(sig.parameters.keys())
        hinted_args = [x[0] for x in typing.get_type_hints(wrapped).items() if x[1] == type_hint]

        if len(hinted_args) == 0:
            raise ValueError("No arguments with %s hint found" % type_hint)

        new_args = list(args)
        for hinted_arg in hinted_args:
            if hinted_arg in kwargs:
                kwargs[hinted_arg] = fix_arg_func(kwargs[hinted_arg])

            elif hinted_arg in names:
                idx = names.index(hinted_arg)
                if idx < len(new_args):
                    new_args[idx] = fix_arg_func(new_args[idx])

        return wrapped(*new_args, **kwargs)

    return wrapper


def enumarg(enum_type: Enum):
    """
    Decorator to look up enums by string value if necessary.
    Use with the EnumType hint.

    Example:

    @enumargs(FX)
    def frobozzle(self, fx: EnumType, speed, color1=None, color2=None)
    """
    def fix_enum_arg(arg):
        if isinstance(arg, enum_type):
            return arg
        if isinstance(arg, str):
            return enum_type[arg.upper()]
        raise TypeError("Can't convert %s (%s) to %s" % (arg, type(arg), enum_type))

    return _autocast_decorator(EnumType, fix_enum_arg)


def rgb_from_tuple(arg: tuple) -> Color:
    """
    Convert a 3-tuple of ints or floats to a Grapefruit color

    :param arg: The RGB tuple to convert
    :return: The Color object
    """
    if len(arg) >= 3:
        if arg[0] is None:
            return Color.NewFromRgb(0, 0, 0)
        if all(isinstance(n, int) for n in arg):
            return Color.NewFromRgb(*Color.IntTupleToRgb(arg))
        if all(isinstance(n, float) for n in arg):
            return Color.NewFromRgb(*arg)

    raise TypeError('Unable to convert %s (%s) to color' % (arg, type(arg[0])))


def rgb_to_int_tuple(arg: tuple) -> tuple:
    """
    Convert/sanitize a 3-tuple of ints or floats

    :param arg: Tuple of RGB values

    :return: Tuple of RGB ints
    """
    if len(arg) >= 3:

        return tuple([clamp(round(x), 0, 255) for x in arg[:3]])

    raise TypeError('Unable to convert %s (%s) to color' % (arg, type(arg[0])))


def to_color(*color_args) -> Color:
    """
    Convert various color representations to grapefruit.Color

    Handles RGB triplets, hexcodes, and html color names.

    :return: The color
    """
    colors = []
    for arg in color_args:
        value = None
        if arg is not None:
            if isinstance(arg, Color):
                value = arg
            elif isinstance(arg, str):
                value = Color.NewFromHtml(arg)
            elif isinstance(arg, Iterable):
                value = rgb_from_tuple(arg)
            else:
                raise TypeError('Unable to parse color from \'%s\' (%s)' % (arg, type(arg)))
        colors.append(value)

    if len(colors) == 0:
        return None
    if len(colors) == 1:
        return colors[0]

    return colors


def to_rgb(arg) -> tuple:
    """
    Convert various representations to RGB tuples

    :return: An RGB int tuple
    """
    if arg is None:
        return (0, 0, 0)
    if isinstance(arg, Color):
        return arg.intTuple[:3]
    if isinstance(arg, str):
        return Color.NewFromHtml(arg).intTuple[:3]
    if isinstance(arg, tuple) or isinstance(arg, list):
        if arg[0] is None:
            return (0, 0, 0)

        if isinstance(arg[0], list) or isinstance(arg[0], tuple) \
                or isinstance(arg[0], str) or isinstance(arg[0], Color):
            return [to_rgb(item) for item in arg]
        return rgb_to_int_tuple(arg)

    raise TypeError('Unable to parse color from \'%s\' (%s)' % (arg, type(arg)))


"""
Decorator to parse various color representations

Invokes to_color on any arguments listed in decls. This will cause
the listed arguments to be resolved to grapefruit.Color objects from
the various different representations that might be in use.

Example:

@colorarg
def frobizzle(self, speed, color1: ColorType=None, color2: ColorType=None)
"""
colorarg = _autocast_decorator(ColorType, to_color)


def clamp(value, min_, max_):
    """
    Constrain a value to the specified range

    :param value: Input value
    :param min_: Range minimum
    :param max_: Range maximum

    :return: The constrained value
    """
    return max(min_, min(value, max_))


def scale(value, src_min, src_max, dst_min, dst_max, round_=False):
    """
    Scale a value from one range to another.

    :param value: Input value
    :param src_min: Min value of input range
    :param src_max: Max value of input range
    :param dst_min: Min value of output range
    :param dst_max: Max value of output range
    :param round_: True if the scale value should be rounded to an integer

    :return: The scaled value
    """
    scaled = interp(clamp(value, src_min, src_max), [src_min, src_max], [dst_min, dst_max])
    if round_:
        scaled = int(round(scaled))

    return scaled


def scale_brightness(brightness, from_hw=False):
    """
    Converts a brightness value between float percentage (0 - 100)
    and an integer value (0 - 255). All API methods should deal in
    percentages, but interaction with the hardware will use the
    integer value.

    :param brightness: The brightness level
    :param from_hw: True if we are converting from integer to percentage

    :return: The scaled value
    """
    if from_hw:
        if brightness < 0 or brightness > 255:
            raise ValueError('Integer brightness must be between 0 and 255 (%d)' % brightness)

        if brightness is None:
            return 0.0

        return round(float(brightness) * (100.0 / 255.0), 2)

    if brightness < 0.0 or brightness > 100.0:
        raise ValueError('Float brightness must be between 0 and 100 (%f)' % brightness)

    if brightness is None:
        return 0

    return int(round(brightness * (255.0 / 100.0)))


def to_byte(value: int) -> bytes:
    """
    Convert a single int to a single byte
    """
    return struct.pack('=B', value)


def smart_delay(delay: float, last_cmd: float, remain: int=0) -> float:
    """
    A "smart" delay mechanism which tries to reduce the
    delay as much as possible based on the time the last
    delay happened.

    :param delay: delay in seconds
    :param last_cmd: time of last command
    :param remain: counter, skip delay unless it's zero

    :return: timestamp to feed to next invocation
    """
    now = time.perf_counter()

    if remain == 0 and last_cmd is not None and delay > 0.0:

        delta = now - last_cmd
        if delta < delay:
            sleep = delay - delta
            time.sleep(sleep)

    return now


def test_bit(value: int, bit: int) -> bool:
    """
    Test if the bit at the specified position is set.

    :param value: The value to test
    :param bit: The bit to check

    :return: True if the bit is set
    """
    return (value & 1 << bit) == 1 << bit


def set_bits(value: int, *bits) -> int:
    """
    Given a list of bools, set (or clear) the bits in
    value and return it as an int.

    :param value: The initial value
    :param bits: Tuple of bools

    :return: Integer with bits set or cleared
    """
    for bit in range(0, len(bits)):
        if bits[bit]:
            value |= 1 << bit
        else:
            value &= ~(1 << bit)

    return value


def lerp(start: float, end: float, amount: float) -> float:
    """
    Linear interpolation

    Return a value between start and stop at the requested percentage

    :param start: Range start
    :param end: Range end
    :param amount: Position in range (0.0 - 1.0)

    :return: The interpolated value
    """
    return start + (end - start) * amount


def lerp_degrees(start: float, end: float, amount: float) -> float:
    """
    Linear interpolation between angles

    :param start: Range start angle in degrees
    :param end: Range end angle in degrees
    :param amount: Angle in range (0.0 - 1.0)

    :return: The interpolated angle in degrees
    """
    start_r = math.radians(start)
    end_r = math.radians(end)
    delta = math.atan2(math.sin(end_r - start_r), math.cos(end_r - start_r))
    return (math.degrees(start_r + delta * amount) + 360.0) % 360.0



class RepeatingTimer(object):
    def __init__(self, interval, func, *args, **kwargs):
        self._interval = interval
        self._func = func
        self._args = args
        self._kwargs = kwargs

        self._timer = None
        self._running = False
        self._finished = False

    def _callback(self):
        self._func(*self._args, **self._kwargs)
        self._running = False

    def cancel(self):
        self._timer.cancel()
        self._running = False

    def start(self):
        if self._finished:
            raise ValueError('Timer has been shut down')

        if self._timer is not None:
            self._timer.cancel()
        self._timer = Timer(self._interval, self._callback)
        self._timer.daemon = True
        self._timer.start()
        self._running = True

    @property
    def is_running(self):
        return self._running

    @property
    def is_finished(self):
        return self._finished

    def set_defaults(self):
        self._running = False
