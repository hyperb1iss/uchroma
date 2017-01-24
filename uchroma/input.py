import asyncio
import logging

import evdev

from wrapt import synchronized


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
        if not self._opened:
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
