# pylint: disable=invalid-name, no-member, attribute-defined-outside-init, bad-builtin
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

from collections import OrderedDict

import colorlog
from numpy import interp
from wrapt import decorator, synchronized


# Trace log levels
LOG_TRACE = 5
LOG_PROTOCOL_TRACE = 4


AUTOCAST_CACHE = {}

def autocast_decorator(type_hint, fix_arg_func):
    """
    Decorator which will invoke fix_arg_func for any
    arguments annotated with type_hint. The decorated
    function will then be called with the result.

    :param type_hint: A PEP484 type hint
    :param fix_arg_func: Function to invoke

    :return: decorator
    """
    @decorator
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


LOGGERS = {}

@synchronized
def get_logger(tag):
    """
    Get the global logger instance for the given tag

    :param tag: the log tag
    :return: the logger instance
    """
    if tag not in LOGGERS:
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter( \
            ' %(log_color)s%(name)s/%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s'))
        logger = logging.getLogger(tag)
        logger.addHandler(handler)

        LOGGERS[tag] = logger

    return LOGGERS[tag]


def max_keylen(d) -> int:
    """
    Get the length of the longest key
    """
    return max(map(len, d))


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


class ArgsDict(OrderedDict):
    """
    Extension of OrderedDict which does not allow empty keys

    FIXME: Get rid of this
    """
    def __init__(self, *args, **kwargs):
        super(ArgsDict, self).__init__(*args, **kwargs)
        empty_keys = []
        for k, v in self.items():
            if v is None:
                empty_keys.append(k)
        for empty_key in empty_keys:
            self.pop(empty_key)


class Signal(object):
    """
    A simple signalling construct.

    Listeners may connect() to this signal, and their handlers will
    be invoked when fire() is called.
    """
    def __init__(self):
        self._handlers = set()


    def connect(self, handler):
        """
        Connect a handler to this signal

        :param handler: Function to invoke when the signal fires
        """
        self._handlers.add(handler)


    def fire(self, *args, **kwargs):
        """
        Fire the signal, invoking all connected handlers

        :params args: Arguments to call handlers with
        """
        for handler in self._handlers:
            handler(*args, **kwargs)


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


class Ticker(object):
    """
    Framerate synchronizer

    Provides a context manager for code which needs to execute
    on an interval. The tick starts when the context is entered
    and sleeps for the remainder of the interval on exit. If
    the interval was missed, sync to the next interval.
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


    async def tick(self):
        """
        Sleep until the next tick
        """
        await asyncio.sleep(self._next_tick)


    async def __aenter__(self):
        return self.__enter__()


    async def __aexit__(self, *args):
        self.__exit__(self, *args)
        await self.tick()


    @property
    def interval(self):
        """
        The interval between ticks
        """
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


    async def _animate(self, start, end):
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
            async with tick:
                current = clamp(current + step, min(start, end), max(start, end))
                await self._callback(current)

        self._task = None


    def animate(self, start: float, end: float, done_cb=None):
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
            if done_cb is not None:
                self._task.add_done_callback(done_cb)
        else:
            self._callback(end)
