import argparse
import asyncio
import atexit
import logging
import signal

from concurrent import futures

import gbulb

from uchroma.dbus import DeviceManagerAPI
from uchroma.device_base import BaseUChromaDevice
from uchroma.device_manager import UChromaDeviceManager
from uchroma.util import ensure_future, get_logger, LOG_PROTOCOL_TRACE, LOG_TRACE


class UChromaServer(object):

    def __init__(self):
        self._logger = get_logger('uchroma.server')

        gbulb.install()

        parser = argparse.ArgumentParser(description='UChroma daemon')
        parser.add_argument("-v", "--version", action='version', version='self.version')
        parser.add_argument("-d", "--debug", action='append_const', const=True,
                            help='Enable debug output')

        args = parser.parse_args()


        self._loop = asyncio.get_event_loop()

        if args.debug is not None:
            if len(args.debug) > 2:
                level = LOG_PROTOCOL_TRACE
            elif len(args.debug) == 2:
                level = LOG_TRACE
            elif len(args.debug) == 1:
                level = logging.DEBUG

            logging.getLogger().setLevel(level)
            self._loop.set_debug(True)


    @asyncio.coroutine
    def _dm_callback(self, action: str, device: BaseUChromaDevice):
        self._logger.info('%s: %s', action, device)
        if action == 'add':
            device.restore_prefs()


    def _shutdown_callback(self):
        self._logger.info("Shutting down")
        self._loop.stop()


    def run(self):
        try:
            self._run()
        except KeyboardInterrupt:
            pass


    def _run(self):
        dm = UChromaDeviceManager()
        dm.callbacks.append(self._dm_callback)

        atexit.register(UChromaServer.exit, self._loop)

        dbus = DeviceManagerAPI(dm)

        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, self._shutdown_callback)

        try:
            ensure_future(dm.monitor_start(), loop=self._loop)
            dbus.run()

            self._loop.run_forever()

        except KeyboardInterrupt:
            pass

        finally:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self._loop.remove_signal_handler(sig)

            self._loop.run_until_complete(asyncio.wait( \
                    [dm.close_devices(), dm.monitor_stop()],
                    return_when=futures.ALL_COMPLETED))


    @staticmethod
    def exit(loop):
        try:
            loop.run_until_complete(asyncio.wait( \
                    list(asyncio.Task.all_tasks()),
                    return_when=futures.ALL_COMPLETED))
            loop.close()

        except KeyboardInterrupt:
            pass


def run_server():
    UChromaServer().run()
