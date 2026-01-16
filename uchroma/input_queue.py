#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=too-many-function-args, invalid-name, too-many-instance-attributes

import asyncio
import time
from typing import NamedTuple

from uchroma.log import LOG_TRACE
from uchroma.util import clamp


class _KeyInputEvent(NamedTuple):
    timestamp: float
    expire_time: float
    keycode: str
    scancode: str
    keystate: int
    coords: list | None
    data: dict


class KeyInputEvent(_KeyInputEvent):
    """
    Container of all values of a keyboard input event
    with optional expiration time.
    """

    @property
    def time_remaining(self) -> float:
        """
        The number of seconds until this event expires
        """
        return max(0.0, self.expire_time - time.time())

    @property
    def percent_complete(self) -> float:
        """
        Percentage of elapsed time until this event expires
        """
        duration = self.expire_time - self.timestamp
        return clamp(self.time_remaining / duration, 0.0, 1.0)


class InputQueue:
    """
    Asynchronous input event queue

    After calling attach(), users of this class may await get_events()
    until a new event is produced from the keyboard. If an expiration time
    is set, events will not be purged until the time has lapsed-
    subsequents yield/await on get_events will return all active events.
    """

    KEY_UP = 1
    KEY_DOWN = 2
    KEY_HOLD = 4

    def __init__(self, driver, expire_time=None):
        self._logger = driver.logger
        self._input_manager = driver.input_manager
        self._key_mapping = driver.hardware.key_mapping
        self._expire_time = 0
        if expire_time is not None:
            self._expire_time = expire_time
        self._attached = False

        self._q = asyncio.Queue()
        self._events = []
        self._keystates = InputQueue.KEY_DOWN

    def attach(self) -> bool:
        """
        Start listening for input events

        :return: True if successful
        """
        if self._attached:
            return True

        if self._input_manager is None:
            raise ValueError("Input events are not supported on this device")

        if not self._input_manager.add_callback(self._input_callback):
            return False

        self._attached = True
        self._logger.debug("InputQueue attached")
        return True

    async def detach(self):
        """
        Stop listening for input events
        """
        if not self._attached:
            return

        await self._input_manager.remove_callback(self._input_callback)
        self._attached = False
        self._logger.debug("InputQueue detached")

    async def get_events(self):
        """
        Get all active (new and unexpired) events from the queue.

        This is a coroutine, and will yield until new data is available.
        """
        if not self._attached:
            self._logger.error("InputQueue is not attached!")
            return None

        if self._expire_time is None or self._expire_time <= 0:
            event = await self._q.get()
            return event

        self._expire()

        while len(self._events) == 0:
            await self._q.get()

        return self._events[:]

    @property
    def keystates(self) -> int:
        """
        The keystates to report as a bitmask
        """
        return self._keystates

    @keystates.setter
    def keystates(self, mask: int):
        """
        Set the keystates to report.

        By default, only KEY_DOWN is reported.
        """
        self._keystates = mask

    def get_events_nowait(self):
        """
        Version of get_events which returns immediately
        """
        return self._events[:]

    async def _input_callback(self, ev):
        """
        Coroutine called by the evdev module when data is available
        """
        self._expire()

        if ev.keystate == ev.key_up and not self._keystates & InputQueue.KEY_UP:
            return

        if ev.keystate == ev.key_down and not self.keystates & InputQueue.KEY_DOWN:
            return

        if ev.keystate == ev.key_hold and not self.keystates & InputQueue.KEY_HOLD:
            return

        coords = None
        if self._key_mapping is not None:
            coords = self._key_mapping.get(ev.keycode, None)

        event = KeyInputEvent(
            ev.event.timestamp(),
            ev.event.timestamp() + self._expire_time,
            ev.keycode,
            ev.scancode,
            ev.keystate,
            coords,
            {},
        )

        if self._logger.isEnabledFor(LOG_TRACE):
            self._logger.debug("Input event: %s", event)

        if self._expire_time is not None:
            for idx in range(len(self._events)):
                if self._events[idx].keycode == event.keycode:
                    self._events[idx] = None
            self._events = [x for x in self._events if x is not None]

            self._events.append(event)

            await self._q.put(event)

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
        # Note: detach() is async, but we can't await in __del__.
        # Just mark as not attached; cleanup happens when InputManager is destroyed.
        if hasattr(self, "_attached"):
            self._attached = False
