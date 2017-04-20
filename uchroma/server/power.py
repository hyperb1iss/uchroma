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

# pylint: disable=broad-except

from pydbus import SessionBus, SystemBus

from uchroma.log import Log
from uchroma.util import Singleton
from .device_manager import UChromaDeviceManager


SCREENSAVERS = (('org.freedesktop.ScreenSaver', '/org/freedesktop/ScreenSaver'),
                ('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver'),
                ('org.mate.ScreenSaver', '/org/mate/ScreenSaver'),
                ('com.canonical.Unity', '/org/gnome/ScreenSaver'))

LOGIN_SERVICE = 'org.freedesktop.login1'


class PowerMonitor(metaclass=Singleton):
    """
    Watches for changes to the system's suspend state and
    screensaver, signalling devices to suspend if necessary.
    """
    def __init__(self):
        self._logger = Log.get('uchroma.power')
        self._name_watchers = []
        self._running = False
        self._sleeping = False

        self._session_bus = SessionBus()
        self._system_bus = SystemBus()
        self._dm = UChromaDeviceManager() #singleton


    def _suspend(self, sleeping, fast):
        if self._sleeping == sleeping:
            return

        self._sleeping = sleeping
        for name, device in self._dm.devices.items():
            if sleeping:
                self._logger.info("Suspending device: %s", name)
                device.suspend(fast=fast)
            else:
                self._logger.info("Resuming device: %s", name)
                device.resume()


    def _prepare_for_sleep(self, sleeping):
        self._suspend(sleeping, True)


    def _active_changed(self, active):
        self._suspend(active, False)


    def start(self):
        """
        Connects to the PrepareForSleep signal from login1 to monitor
        system suspend, and sets up watches for known screensaver
        instances.
        """
        if self._running:
            return

        for name, path in SCREENSAVERS:
            def connect_screensaver(*args, bus_name=name, object_path=path):
                """
                Connects the callback when the service appears.
                """
                try:
                    saver = self._session_bus.get(bus_name=bus_name, object_path=object_path)
                    saver.ActiveChanged.connect(self._active_changed)
                    self._logger.info("Connected screensaver: %s:%s %s", bus_name, object_path, args)

                except Exception:
                    self._logger.warn("Could not connect to %s:%s service", bus_name, object_path)


            self._name_watchers.append(self._session_bus.watch_name( \
                    name, name_appeared=connect_screensaver))


        def connect_login1(*args):
            try:
                login1 = self._system_bus.get(LOGIN_SERVICE)
                login1.PrepareForSleep.connect(self._prepare_for_sleep)
                self._logger.info("Connected to %s %s", LOGIN_SERVICE, args)

            except Exception:
                self._logger.warn("Could not connect to login1 service")

        self._name_watchers.append(self._system_bus.watch_name( \
                LOGIN_SERVICE, name_appeared=connect_login1))

        self._running = True


    def stop(self):
        """
        Disable the monitor
        """
        if not self._running:
            return

        for watcher in self._name_watchers:
            watcher.unwatch()

        self._name_watchers.clear()

        self._running = False

