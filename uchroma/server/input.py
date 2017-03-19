#
# uchroma - Copyright (C) 2017 Steve Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

# pylint: disable=no-member, invalid-name

import asyncio
import functools

from concurrent import futures

import evdev

from uchroma.util import ensure_future


class InputManager(object):
    """
    Manages event devices associated with a physical device instance and
    allows for callback registration. Reader loop is fully asynchronous.
    See the InputQueue class for a higher level API.
    """
    def __init__(self, driver, input_devices: list):

        self._driver = driver
        self._input_devices = input_devices
        self._event_devices = []
        self._event_callbacks = []

        self._logger = driver.logger

        self._opened = False
        self._closing = False

        self._tasks = []


    async def _evdev_callback(self, device):
        async for event in device.async_read_loop():
            try:
                if not self._opened:
                    return

                if event.type == evdev.ecodes.EV_KEY:
                    ev = evdev.categorize(event)

                    for callback in self._event_callbacks:
                        await callback(ev)

                if not self._opened:
                    return

            except (OSError, IOError) as err:
                self._logger.exception("Event device error", exc_info=err)
                break


    def _evdev_close(self, event_device, future):
        self._logger.info('Closing event device %s', event_device)


    def _open_input_devices(self):
        if self._opened:
            return True

        for input_device in self._input_devices:
            try:
                event_device = evdev.InputDevice(input_device)
                self._event_devices.append(event_device)

                task = ensure_future(self._evdev_callback(event_device))
                task.add_done_callback(functools.partial(self._evdev_close, event_device))
                self._tasks.append(task)

                self._logger.info('Opened event device %s', event_device)

            except Exception as err:
                self._logger.exception("Failed to open device: %s", input_device, exc_info=err)

        if len(self._event_devices) > 0:
            self._opened = True

        return self._opened


    async def _close_input_devices(self):
        if not hasattr(self, '_opened') or not self._opened:
            return

        self._opened = False

        for event_device in self._event_devices:
            asyncio.get_event_loop().remove_reader(event_device.fileno())
            event_device.close()

        tasks = []
        for task in self._tasks:
            if not task.done():
                task.cancel()
                tasks.append(task)

        await asyncio.wait(tasks, return_when=futures.ALL_COMPLETED)
        self._event_devices.clear()


    def add_callback(self, callback) -> bool:
        """
        Add a new callback (coroutine) which will fire when new
        input events are received.

        :param callback: coroutine to add
        :return: True if successful
        """
        if callback in self._event_callbacks:
            return True

        if not self._opened:
            if not self._open_input_devices():
                return False

        self._event_callbacks.append(callback)
        return True


    async def remove_callback(self, callback):
        """
        Removes a previously registered callback

        :param callback: coroutine to remove
        """
        if callback not in self._event_callbacks:
            return

        self._event_callbacks.remove(callback)

        if len(self._event_callbacks) == 0:
            await self._close_input_devices()


    async def shutdown(self):
        """
        Shuts down the InputManager and disconnects any active callbacks
        """
        for callback in self._event_callbacks:
            await ensure_future(self.remove_callback(callback))


    def grab(self, excl: bool):
        """
        Get exclusive access to the device

        WARNING: Calling this on your primary input device might
        cause you a bad day (or at least a reboot)! Use with devices
        (like keypads) where we don't want other apps to see actual
        scancodes.

        :param excl: True to gain exclusive access, False to release
        """
        if not self._opened:
            return

        for event_device in self._event_devices:
            if excl:
                event_device.grab()
            else:
                event_device.ungrab()


    @property
    def input_devices(self):
        """
        List of input devices associated with the parent device
        """
        return self._input_devices


    def __del__(self):
        self.shutdown()
