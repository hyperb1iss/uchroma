#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
import argparse
import asyncio
import contextlib
import logging
import signal

from uchroma.log import LOG_PROTOCOL_TRACE, LOG_TRACE, Log

from .dbus import DeviceManagerAPI
from .device_manager import UChromaDeviceManager
from .power import PowerMonitor


class UChromaServer:
    def __init__(self):
        parser = argparse.ArgumentParser(description="UChroma daemon")
        parser.add_argument("-v", "--version", action="version", version="self.version")
        parser.add_argument(
            "-d", "--debug", action="append_const", const=True, help="Increase logging verbosity"
        )
        parser.add_argument("-C", "--colorlog", action="store_true", help="Use colored log output")

        args = parser.parse_args()

        self._loop = None
        self._shutdown_event = asyncio.Event()

        level = logging.INFO
        asyncio_debug = False
        colorlog = False
        if args.colorlog is not None:
            colorlog = args.colorlog

        Log.enable_color(colorlog)
        self._logger = Log.get("uchroma.server")

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
        self._asyncio_debug = asyncio_debug

    def _handle_signal(self, sig):
        self._logger.info("Received signal %s, shutting down", sig.name)
        self._shutdown_event.set()

    def run(self):
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self._run())

    async def _run(self):
        self._loop = asyncio.get_event_loop()
        self._loop.set_debug(self._asyncio_debug)

        dm = UChromaDeviceManager()
        dbus = DeviceManagerAPI(dm, self._logger)
        power = PowerMonitor()

        # Set up signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, self._handle_signal, sig)

        try:
            # Start device monitoring
            await dm.monitor_start()

            # Start power monitor
            await power.start()

            # Start D-Bus service (runs until shutdown)
            dbus_task = asyncio.create_task(dbus.run())

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            self._logger.info("Shutting down...")

            # Cancel D-Bus task
            dbus_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await dbus_task

        except asyncio.CancelledError:
            pass

        finally:
            # Clean up signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                self._loop.remove_signal_handler(sig)

            # Stop services
            await power.stop()
            await dm.close_devices()
            await dm.monitor_stop()

            self._logger.info("Shutdown complete")


def run_server():
    UChromaServer().run()
