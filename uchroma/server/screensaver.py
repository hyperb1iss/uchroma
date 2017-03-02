from pydbus import SessionBus

from uchroma.util import get_logger, Signal, Singleton
from .device_manager import UChromaDeviceManager


SCREENSAVERS = ('org.freedesktop.ScreenSaver',
                'org.gnome.ScreenSaver',
                'org.mate.ScreenSaver')


class ScreenSaverWatcher(metaclass=Singleton):
    """
    Watches for changes to the session's screensaver,
    signalling devices to suspend if necessary.
    """

    class Watcher(object):
        """
        Watches an individual screensaver instance
        via D-Bus.
        """
        def __init__(self, bus, name, logger):
            self._bus = bus
            self._name = name
            self._logger = logger
            self._active = False
            self._dm = UChromaDeviceManager() #singleton

            service = self._bus.get(self._name)
            service.ActiveChanged.connect(self._active_changed)


        def _active_changed(self, active):
            if self._active == active:
                return

            self._active = active
            self._logger.debug("Screensaver %s changed: %s", self._name, active)
            for k, v in self._dm.devices.items():
                if active:
                    self._logger.info("Suspending device: %s", k)
                    v.suspend()
                else:
                    self._logger.info("Resuming device: %s", k)
                    v.resume()


    def __init__(self):
        self._logger = get_logger('uchroma.power')
        self._name_watchers = []
        self._watchers = {}
        self._running = False
        self._bus = None


    def start(self):
        """
        Start watching for screensaver events.

        Initially sets up D-Bus name watches to determine which signals
        to connect.
        """
        if self._running:
            return

        self._bus = SessionBus()

        for name in SCREENSAVERS:
            def appeared(*args, service=name):
                self._logger.info("Found screensaver: %s %s", service, args)
                self._watchers[service] = \
                    ScreenSaverWatcher.Watcher(self._bus, service,
                                               self._logger)

            def vanished(*args, service=name):
                if service in self._watchers:
                    self._logger.info("Screensaver vanished: %s (%s)", service, args)
                    del self._watchers[service]


            self._name_watchers.append(self._bus.watch_name( \
                    name, name_appeared=appeared, name_vanished=vanished))

        self._running = True


    def stop(self):
        """
        Disable the watcher
        """
        if not self._running:
            return

        for watcher in self._name_watchers:
            watcher.unwatch()

        self._name_watchers.clear()
        self._watchers.clear()

        self._running = False

