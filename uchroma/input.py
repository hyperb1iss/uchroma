# pylint: disable=no-member, invalid-name
import asyncio
import logging
import time

from typing import NamedTuple

import evdev

from wrapt import synchronized

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
        self._task = None


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

            except (OSError, IOError) as err:
                self._logger.exception("Event device error", exc_info=err)
                break


    def _open_input_devices(self):
        if self._opened:
            return

        for input_device in self._input_devices:
            event_device = evdev.InputDevice(input_device)
            self._event_devices.append(event_device)

            self._opened = True
            self._task = asyncio.ensure_future(
                self._evdev_callback(event_device))


    def _close_input_devices(self):
        if not hasattr(self, '_opened') or not self._opened:
            return

        self._opened = False

        for event_device in self._event_devices:
            event_device.close()

        self._event_devices.clear()


    @synchronized
    def add_callback(self, callback):
        if callback in self._event_callbacks:
            return

        self._event_callbacks.append(callback)
        if len(self._event_callbacks) == 1:
            self._open_input_devices()


    @synchronized
    def remove_callback(self, callback):
        if callback not in self._event_callbacks:
            return

        self._event_callbacks.remove(callback)

        if len(self._event_callbacks) == 0:
            self._close_input_devices()


    @synchronized
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

    def __init__(self, driver, expire_time=0, *args, **kwargs):

        super(InputQueue, self).__init__(*args, **kwargs)

        self._logger = logging.getLogger('uchroma.inputqueue')
        self._driver = driver
        self._expire_time = expire_time
        self._attached = False

        self._queue = []


    def attach(self):
        """
        Start listening for input events
        """
        if self._attached:
            return

        self._driver.input_manager.add_callback(self._input_callback)
        self._attached = True
        self._logger.debug("InputQueue attached")


    def detach(self):
        """
        Stop listening for input events
        """
        if not self._attached:
            return

        self._driver.input_manager.add_callback(self._input_callback)
        self._attached = False
        self._logger.debug("InputQueue detached")


    @asyncio.coroutine
    def _interaction(self, key):
        """
        Coroutine invoked when keys have been added to the queue
        """
        pass


    def _process_event(self, event) -> tuple:
        """
        If a subclass needs to modify or add data to the event,
        this method can be overridden.
        """
        return event


    @asyncio.coroutine
    def _input_callback(self, ev):
        """
        Coroutine called by the evdev module when data is available
        """
        self._expire()

        if ev.keystate != ev.key_down:
            return

        coords = None
        if self._driver.has_matrix:
            coords = self._driver.key_mapping.get(ev.keycode, None)

        event = KeyInputEvent(timestamp=ev.event.timestamp(),
                              expire_time=ev.event.timestamp() + self._expire_time,
                              keycode=ev.keycode, scancode=ev.scancode,
                              keystate=ev.keystate, coords=coords, data={})

        event = self._process_event(event)

        self._logger.debug('Input event: %s', event)

        if event is None:
            return

        if self._expire_time is not None:
            for idx in range(0, self.queue_len):
                if self._queue[idx].keycode == event.keycode:
                    self._queue[idx] = None
            self._queue = [x for x in self._queue if x is not None]

            self._queue.append(event)

        if self._interaction is not None:
            yield from self._interaction(event)


    def _expire(self):
        """
        Clear all events which have passed the deadline
        """
        if self._expire_time is None:
            return

        now = time.time()

        # Remove expired events from queue
        try:
            while self._queue[0].expire_time < now:
                self._queue.pop(0)

        except IndexError:
            pass


    @property
    def queue(self):
        """
        Get the list of keys which have not expired

        This returns a copy of the current state.
        """
        self._expire()
        return self._queue[:]


    @property
    def queue_len(self):
        """
        Get the number of keys in the queue
        """
        return len(self._queue)


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
        if hasattr(self, '_driver'):
            if self._driver is not None:
                self.detach()

