#
# uchroma - Copyright (C) 2021 Stefanie Kondik
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
import asyncio

from evdev.uinput import UInput

from uchroma.input_queue import InputQueue
from uchroma.util import ensure_future


class MacroDevice:

    def __init__(self, driver):

        if driver.input_manager is None:
            raise ValueError('This device does not support input events')

        self._driver = driver
        self._logger = driver.logger

        self._macro_keys = driver.hardware.macro_keys

        self._uinput = None
        self._queue = None

        self._task = None
        self._running = False


    async def _listen(self):
        while self._running:
            event = await self._queue.get_events()
            self._logger.info('event: %s', event)
            if event.scancode in self._macro_keys['numeric']: 
                self._logger.info('macro')


    def start(self):
        if self._running:
            return

        self._uinput = UInput.from_device(driver.input_manager.input_devices[0], \
            name='UChroma Virtual Macro Device %d' % driver.device_index)
        self._queue = InputQueue(driver)

        self._queue.attach()
        self._driver.input_manager.grab(True)

        self._task = ensure_future(self._listen())
        self._running = True


    def stop(self):
        if not self._running:
            return

        self._running = False

        self._task.cancel()

        self._driver.input_manager.grab(False)
        ensure_future(self._queue.detach())

