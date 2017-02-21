# pylint: disable=invalid-name, pointless-string-statement, no-member, unsubscriptable-object
"""
Various helper functions that are used across the library.
"""
import asyncio
import inspect
import logging
import math
import re
import struct
import time
import typing
import weakref

from collections import Iterable, OrderedDict
from threading import Timer

import colorlog
import wrapt
from grapefruit import Color
from numpy import interp


# Trace log levels
LOG_TRACE = 5
LOG_PROTOCOL_TRACE = 4


# Type hint for decorated color arguments
ColorType = typing.Union[Color, str, typing.Iterable[int], typing.Iterable[float], None]
ColorList = typing.List[ColorType]


AUTOCAST_CACHE = {}

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
        hinted_args = names = None
        cache_key = '%s-%s-%s' % (wrapped.__class__.__name__,
                                  wrapped.__name__, str(type_hint))

        if cache_key in AUTOCAST_CACHE:
            hinted_args, names = AUTOCAST_CACHE[cache_key]
        else:
            sig = inspect.signature(wrapped)
            names = list(sig.parameters.keys())
            hinted_args = [x[0] for x in typing.get_type_hints(wrapped).items() \
                    if x[1] == type_hint or x[1] == typing.Union[type_hint, None]]
            AUTOCAST_CACHE[cache_key] = hinted_args, names

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


def snake_to_camel(name: str) -> str:
    """
    Returns a CamelCaseName from a snake_case_name
    """
    return re.sub(r'(?:^|_)([a-z])', lambda x: x.group(1).upper(), name)


def camel_to_snake(name: str) -> str:
    """
    Returns a snake_case_name from a CamelCaseName
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class MagicalEnum(object):
    """
    Mixin which adds "magical" capabilities to Enums

    Right now this is just a type conversion decorator.
    """

    @classmethod
    def enumarg(cls):
        """
        Decorator to look up enums by string value if necessary.
        If placed on a method and it is called with a string
        instead of an enum instance, the string will be uppercased
        and the corresponding value from the enum will be passed
        into the method instead of the string.

        Useful for situations where an external client like a D-Bus
        API would be calling the method.

        Example:

        @FX.enumarg()
        def frobozzle(self, fx: FX, speed, color1=None, color2=None)
        """
        def fix_enum_arg(arg):
            if arg is None:
                return None
            if isinstance(arg, cls):
                return arg
            if isinstance(arg, str):
                if arg.upper() not in cls.__members__:
                    return None
                return cls[arg.upper()]
            raise TypeError("Can't convert %s (%s) to %s" % (arg, type(arg), cls))

        return _autocast_decorator(cls, fix_enum_arg)


def get_logger(tag):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter( \
        ' %(log_color)s%(name)s/%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s'))
    logger = logging.getLogger(tag)
    logger.addHandler(handler)
    return logger

def max_keylen(d) -> int:
    """
    Get the length of the longest key
    """
    return max(map(len, d))


class ArgsDict(OrderedDict):
    def __init__(self, *args, **kwargs):
        super(ArgsDict, self).__init__(*args, **kwargs)
        empty_keys = []
        for k, v in self.items():
            if v is None:
                empty_keys.append(k)
        for empty_key in empty_keys:
            self.pop(empty_key)


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
                if arg != '':
                    # grapefruit's default str() spews a string repr of a tuple
                    strtuple = re.match(r'\((.*, .*, .*, .*)\)', arg)
                    if strtuple:
                        value = Color.NewFromRgb(*[float(x) for x in strtuple.group(1).split(', ')])
                    else:
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
    now = time.monotonic()

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


def ensure_future(coro, loop=None):
    """
    Wrapper for asyncio.ensure_future which dumps exceptions
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    fut = asyncio.ensure_future(coro, loop=loop)
    def exception_logging_done_cb(fut):
        try:
            e = fut.exception()
        except asyncio.CancelledError:
            return
        if e is not None:
            loop.call_exception_handler({
                'message': 'Unhandled exception in async future',
                'future': fut,
                'exception': e,
            })
    fut.add_done_callback(exception_logging_done_cb)
    return fut


_CHANGER_METHODS = set("__setitem__ __setslice__ __delitem__ update append extend add insert pop popitem remove setdefault __iadd__".split())


def _observable_factory(cls):
    def observers(self):
        if not hasattr(self, '__observers'):
            setattr(self, '__observers', weakref.WeakSet())
        return getattr(self, '__observers')

    def add_observer(self, observer):
        self.observers().add(observer)

    def remove_observer(self, observer):
        self.observers().remove(observer)

    def notify_observers(self):
        for observer in self.observers():
            observer(self)

    def observable(func, callback):
        def wrapper(self, *args, **kw):
            value = func(self, *args, **kw)
            print('wrapper args=%s value=%s' % (args, value))
            callback(self)
            return value
        wrapper.__name__ = func.__name__
        return wrapper

    new_dict = cls.__dict__.copy()
    for name, method in new_dict.items():
        if name in _CHANGER_METHODS:
            new_dict[name] = observable(method, notify_observers)

    new_dict['observers'] = observers
    new_dict['add_observer'] = add_observer
    new_dict['remove_observer'] = remove_observer

    return type('Observable%s' % cls.__name__.title(), (cls,), new_dict)


ObservableDict = _observable_factory(dict)
ObservableList = _observable_factory(list)
ObservableOrderedDict = _observable_factory(OrderedDict)


class Singleton(type):
    """
    Metaclass for creating singletons
    """
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
            return cls.__instance


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


class Ticker(object):
    """
    Framerate synchronizer

    Provides a context manager for code which needs to execute
    on an interval. The tick starts when the context is entered
    and sleeps for the remainder of the interval on exit. If
    the interval was missed, sync to the next interval.

    Since Python 3.4 doesn't support asynchronous context
    managers, it's required to call "yield from tick.tick()"
    after exiting the context manually. On Python 3.6+,
    code can simply be called using "async with".
    """
    def __init__(self, interval: float):
        self._interval = interval
        self._tick_start = 0.0
        self._next_tick = 0.0

    def __enter__(self):
        self._tick_start = time.monotonic()
        return self


    def __exit__(self, *args):
        next_tick = time.monotonic() - self._tick_start

        if next_tick > self._interval:
            next_tick = next_tick % self._interval
        else:
            self._next_tick = self._interval - next_tick


    @asyncio.coroutine
    def tick(self):
        yield from asyncio.sleep(self._next_tick)


    @asyncio.coroutine
    def __aenter__(self):
        return self.__enter__()


    @asyncio.coroutine
    def __aexit__(self, *args):
        self.__exit__(self, *args)
        yield from self.tick()


    @property
    def interval(self):
        return self._interval


    @interval.setter
    def interval(self, value: float):
        self._interval = value


class ValueAnimator(object):
    """
    Animates a value over a duration from a start to end,
    invoking a callback at each interval.
    """
    def __init__(self, callback, min_value: float=0.0,
                 max_value: float=100.0, max_time: float=1.5,
                 fps: float=30.0):
        self._callback = callback
        self._range = max_value - min_value
        self._max_time = max_time
        self._fps = 1.0 / float(fps)
        self._task = None


    @asyncio.coroutine
    def _animate(self, start, end):
        # animation duration
        duration = (abs(end - start) / self._range) * self._max_time

        if duration == 0:
            return

        # step size
        step = self._range / (duration / self._fps)
        if end < start:
            step *= -1

        # animate
        tick = Ticker(self._fps)
        current = start
        while current != end:
            with tick:
                current = clamp(current + step, min(start, end), max(start, end))
                self._callback(current)
                yield from tick.tick()

        self._task = None


    def animate(self, start: float, end: float):
        """
        Executes the given callback over the period of max_time
        at the given FPS, to animate from start to end.
        This can be used for things like brightness levels.

        :param start: Starting value
        :param end: Ending value
        """
        if asyncio.get_event_loop().is_running():
            if self._task is not None:
                self._task.cancel()
            self._task = ensure_future(self._animate(start, end))
        else:
            self._callback(end)



