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
import argparse
import asyncio
import atexit
import logging
import signal

from concurrent import futures

import gbulb

from uchroma.log import Log, LOG_PROTOCOL_TRACE, LOG_TRACE
from uchroma.util import ensure_future

from .dbus import DeviceManagerAPI
from .device_manager import UChromaDeviceManager
from .power import PowerMonitor


class UChromaServer(object):

    def __init__(self):
        gbulb.install()

        parser = argparse.ArgumentParser(description='UChroma daemon')
        parser.add_argument('-v', "--version", action='version', version='self.version')
        parser.add_argument('-d', "--debug", action='append_const', const=True,
                            help="Increase logging verbosity")
        parser.add_argument('-C', "--colorlog", action='store_true',
                            help="Use colored log output")

        args = parser.parse_args()


        self._loop = asyncio.get_event_loop()

        level = logging.INFO
        asyncio_debug = False
        colorlog = False
        if args.colorlog is not None:
            colorlog = args.colorlog

        Log.enable_color(colorlog)
        self._logger = Log.get('uchroma.server')

        if args.debug is not None:
            if len(args.debug) > 2:
                level = LOG_PROTOCOL_TRACE
                asyncio_debug = True
            elif len(args.debug) == 2:
                level = LOG_TRACE
                asyncio_debug = True
            elif len(args.debug) == 1:
                level = logging.DEBUG

        logging.getLogger().setLevel(level)
        self._loop.set_debug(asyncio_debug)


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

        atexit.register(UChromaServer.exit, self._loop)

        dbus = DeviceManagerAPI(dm, self._logger)
        power = PowerMonitor()

        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, self._shutdown_callback)

        try:
            dbus.run()
            power.start()

            ensure_future(dm.monitor_start(), loop=self._loop)

            self._loop.run_forever()

        except KeyboardInterrupt:
            pass

        finally:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self._loop.remove_signal_handler(sig)

            power.stop()

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
