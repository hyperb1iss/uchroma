# pylint: disable=no-member, invalid-name
import asyncio
import functools
import logging
import time

from typing import NamedTuple

import evdev

from uchroma.hardware import PointList
from uchroma.util import clamp


class InputManager(object):

    def __init__(self, driver, input_devices: list):

        self._driver = driver
        self._input_devices = input_devices
        self._event_devices = []
        self._event_callbacks = []

        self._logger = logging.getLogger('uchroma-input-%s' % driver.name)

        self._opened = False
        self._tasks = []


    @asyncio.coroutine
    def _evdev_callback(self, device):
        while self._opened:
            try:
                events = yield from device.async_read()
                for event in events:
                    if event.type == evdev.ecodes.EV_KEY:
                        ev = evdev.categorize(event)

                        for callback in self._event_callbacks:
                            yield from callback(ev)

            except (OSError, IOError, asyncio.futures.InvalidStateError) as err:
                if not isinstance(err, asyncio.futures.InvalidStateError):
                    self._logger.exception("Event device error", exc_info=err)
                break


    def _evdev_close(self, event_device, future):
        self._logger.info('Closing event device %s', event_device)
        event_device.close()
        self._event_devices.remove(event_device)


    def _open_input_devices(self):
        if self._opened:
            return

        for input_device in self._input_devices:
            event_device = evdev.InputDevice(input_device)
            self._event_devices.append(event_device)

            task = asyncio.ensure_future(self._evdev_callback(event_device))
            task.add_done_callback(functools.partial(self._evdev_close, event_device))
            self._tasks.append(task)

            self._logger.info('Opened event device %s', event_device)

        self._opened = True


    def _close_input_devices(self):
        if not hasattr(self, '_opened') or not self._opened:
            return

        self._opened = False

        for task in self._tasks:
            task.cancel()


    def add_callback(self, callback):
        if callback in self._event_callbacks:
            return

        self._event_callbacks.append(callback)
        if len(self._event_callbacks) == 1:
            self._open_input_devices()


    def remove_callback(self, callback):
        if callback not in self._event_callbacks:
            return

        self._event_callbacks.remove(callback)

        if len(self._event_callbacks) == 0:
            self._close_input_devices()


    def shutdown(self):
        self._close_input_devices()
        self._event_callbacks.clear()


    @property
    def input_devices(self):
        return self._input_devices


    def __del__(self):
        self.shutdown()


_KeyInputEvent = NamedTuple('KeyInputEvent', \
    [('timestamp', float),
     ('expire_time', float),
     ('keycode', str),
     ('scancode', str),
     ('keystate', int),
     ('coords', PointList),
     ('data', dict)])


class KeyInputEvent(_KeyInputEvent, object):

    @property
    def time_remaining(self) -> float:
        return max(0.0, self.expire_time - time.time())

    @property
    def percent_complete(self) -> float:
        duration = self.expire_time - self.timestamp
        return clamp(self.time_remaining / duration, 0.0, 1.0)


class InputQueue(object):

    def __init__(self, driver, expire_time=None):

        self._logger = logging.getLogger('uchroma.inputqueue')
        self._input_manager = driver.input_manager
        self._key_mapping = driver.hardware.key_mapping
        self._expire_time = expire_time
        self._attached = False

        self._q = asyncio.Queue()
        self._events = []


    def attach(self):
        """
        Start listening for input events
        """
        if self._attached:
            return

        if self._input_manager is None:
            raise ValueError('Input events are not supported on this device')

        self._input_manager.add_callback(self._input_callback)
        self._attached = True
        self._logger.debug("InputQueue attached")


    def detach(self):
        """
        Stop listening for input events
        """
        if not self._attached:
            return

        self._input_manager.remove_callback(self._input_callback)
        self._attached = False
        self._logger.debug("InputQueue detached")


    @asyncio.coroutine
    def get_events(self):
        if not self._attached:
            self._logger.error("InputQueue is not attached!")
            return None

        if self._expire_time is None or self._expire_time <= 0:
            event = yield from self._q.get()
            return event

        self._expire()

        while len(self._events) == 0:
            yield from self._q.get()

        return self._events[:]


    def get_events_nowait(self):
        return self._events[:]


    @asyncio.coroutine
    def _input_callback(self, ev):
        """
        Coroutine called by the evdev module when data is available
        """
        self._expire()

        if ev.keystate != ev.key_down:
            return

        coords = None
        if self._key_mapping is not None:
            coords = self._key_mapping.get(ev.keycode, None)

        event = KeyInputEvent(timestamp=ev.event.timestamp(),
                              expire_time=ev.event.timestamp() + self._expire_time,
                              keycode=ev.keycode, scancode=ev.scancode,
                              keystate=ev.keystate, coords=coords, data={})

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug('Input event: %s', event)

        if self._expire_time is not None:
            for idx in range(0, len(self._events)):
                if self._events[idx].keycode == event.keycode:
                    self._events[idx] = None
            self._events = [x for x in self._events if x is not None]

            self._events.append(event)

            yield from self._q.put(event)


    def _expire(self):
        """
        Clear all events which have passed the deadline
        """
        if self._expire_time is None:
            return

        now = time.time()

        # Remove expired events from queue
        try:
            while self._events[0].expire_time < now:
                self._events.pop(0)

        except IndexError:
            pass


    @property
    def expire_time(self):
        """
        Number of seconds to store entries for
        """
        return self._expire_time


    @expire_time.setter
    def expire_time(self, seconds):
        """
        Set the number of seconds to store entries
        """
        self._expire_time = seconds


    def __del__(self):
        if hasattr(self, '_input_manager'):
            if self._input_manager is not None:
                self.detach()
