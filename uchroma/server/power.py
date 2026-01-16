#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=broad-except


from dbus_fast import BusType
from dbus_fast.aio import MessageBus

from uchroma.log import Log
from uchroma.util import Singleton

from .device_manager import UChromaDeviceManager

SCREENSAVERS = (
    ("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver"),
    ("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver"),
    ("org.mate.ScreenSaver", "/org/mate/ScreenSaver"),
    ("com.canonical.Unity", "/org/gnome/ScreenSaver"),
)

LOGIN_SERVICE = "org.freedesktop.login1"


class PowerMonitor(metaclass=Singleton):
    """
    Watches for changes to the system's suspend state and
    screensaver, signalling devices to suspend if necessary.
    """

    def __init__(self):
        self._logger = Log.get("uchroma.power")
        self._running = False
        self._sleeping = False
        self._user_active = False

        self._session_bus = None
        self._system_bus = None
        self._dm = UChromaDeviceManager()  # singleton
        self._login1_proxy = None

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

    async def start(self):
        """
        Connects to the PrepareForSleep signal from login1 to monitor
        system suspend, and sets up watches for known screensaver
        instances.
        """
        if self._running:
            return

        try:
            # Connect to session bus for screensavers
            self._session_bus = await MessageBus(bus_type=BusType.SESSION).connect()

            # Connect to system bus for login1 (suspend/resume)
            self._system_bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

            # Connect to login1 for PrepareForSleep
            await self._connect_login1()

            # Try to connect to screensavers
            for name, path in SCREENSAVERS:
                await self._try_connect_screensaver(name, path)

            self._running = True
            self._logger.info("Power monitor started")

        except Exception as e:
            self._logger.exception("Failed to start power monitor: %s", e)

    async def _connect_login1(self):
        """Connect to login1 for suspend/resume signals."""
        try:
            introspection = await self._system_bus.introspect(
                LOGIN_SERVICE, "/org/freedesktop/login1"
            )
            self._login1_proxy = self._system_bus.get_proxy_object(
                LOGIN_SERVICE, "/org/freedesktop/login1", introspection
            )

            manager = self._login1_proxy.get_interface("org.freedesktop.login1.Manager")

            # Connect to PrepareForSleep signal
            manager.on_prepare_for_sleep(self._on_prepare_for_sleep)

            self._logger.info("Connected to %s", LOGIN_SERVICE)

        except Exception as e:
            self._logger.warning("Could not connect to login1 service: %s", e)

    def _on_prepare_for_sleep(self, sleeping: bool):
        """Handler for PrepareForSleep signal."""
        self._prepare_for_sleep(sleeping)

    async def _try_connect_screensaver(self, bus_name: str, object_path: str):
        """Try to connect to a screensaver service."""
        try:
            introspection = await self._session_bus.introspect(bus_name, object_path)
            proxy = self._session_bus.get_proxy_object(bus_name, object_path, introspection)

            # Try to get ScreenSaver interface
            try:
                screensaver = proxy.get_interface("org.freedesktop.ScreenSaver")
                screensaver.on_active_changed(self._on_active_changed)
                self._logger.info("Connected screensaver: %s:%s", bus_name, object_path)
            except Exception:
                # Try alternate interface name
                try:
                    screensaver = proxy.get_interface("org.gnome.ScreenSaver")
                    screensaver.on_active_changed(self._on_active_changed)
                    self._logger.info("Connected screensaver: %s:%s", bus_name, object_path)
                except Exception:
                    pass

        except Exception:
            # Screensaver not available, that's OK
            pass

    def _on_active_changed(self, active: bool):
        """Handler for screensaver ActiveChanged signal."""
        self._active_changed(active)

    async def stop(self):
        """
        Disable the monitor
        """
        if not self._running:
            return

        if self._session_bus:
            self._session_bus.disconnect()
            self._session_bus = None

        if self._system_bus:
            self._system_bus.disconnect()
            self._system_bus = None

        self._login1_proxy = None
        self._running = False
        self._logger.info("Power monitor stopped")
