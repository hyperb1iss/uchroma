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

# pylint: disable=invalid-name

import asyncio
import re

from dbus_fast import BusType
from dbus_fast.aio import MessageBus

BASE_PATH = '/org/chemlab/UChroma'
SERVICE = 'org.chemlab.UChroma'


class UChromaClient:
    """
    Async D-Bus client for UChroma.
    """

    def __init__(self):
        self._bus = None

    async def connect(self):
        """Connect to the session bus."""
        if self._bus is None:
            self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        return self

    async def disconnect(self):
        """Disconnect from the bus."""
        if self._bus:
            self._bus.disconnect()
            self._bus = None

    async def _get_proxy(self, path):
        """Get a proxy object for a given path."""
        introspection = await self._bus.introspect(SERVICE, path)
        return self._bus.get_proxy_object(SERVICE, path, introspection)

    async def get_device_paths(self) -> list:
        """Get list of device object paths."""
        proxy = await self._get_proxy(BASE_PATH)
        dm = proxy.get_interface('org.chemlab.UChroma.DeviceManager')
        return await dm.call_get_devices()

    async def get_device(self, identifier):
        """Get a device proxy by identifier (path, key, or index)."""
        if identifier is None:
            return None

        use_key = False
        if isinstance(identifier, str):
            if identifier.startswith(BASE_PATH):
                return await self._get_proxy(identifier)

            if re.match(r'\w{4}:\w{4}.\d{2}', identifier):
                use_key = True
            elif re.match(r'\d+', identifier):
                identifier = int(identifier)
            else:
                return None

        for dev_path in await self.get_device_paths():
            dev_proxy = await self._get_proxy(dev_path)
            dev = dev_proxy.get_interface('org.chemlab.UChroma.Device')

            if use_key:
                key = await dev.get_key()
                if identifier == key:
                    return dev_proxy
            else:
                idx = await dev.get_device_index()
                if identifier == idx:
                    return dev_proxy

        return None

    async def get_layer(self, device_path, layer_idx):
        """Get a layer proxy by device and index."""
        dev_proxy = await self._get_proxy(device_path)
        anim = dev_proxy.get_interface('org.chemlab.UChroma.AnimationManager')
        layers = await anim.get_current_renderers()

        if layer_idx >= len(layers):
            raise ValueError("Layer index out of range")

        return await self._get_proxy(layers[layer_idx][1])


class UChromaClientSync:
    """
    Synchronous wrapper around UChromaClient for simple use cases.
    """

    def __init__(self):
        self._client = UChromaClient()
        self._loop = None

    def _get_loop(self):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
        return self._loop

    def connect(self):
        return self._get_loop().run_until_complete(self._client.connect())

    def disconnect(self):
        if self._loop:
            self._loop.run_until_complete(self._client.disconnect())
            self._loop.close()
            self._loop = None

    def get_device_paths(self) -> list:
        return self._get_loop().run_until_complete(self._client.get_device_paths())

    def get_device(self, identifier):
        return self._get_loop().run_until_complete(self._client.get_device(identifier))

    def get_layer(self, device_path, layer_idx):
        return self._get_loop().run_until_complete(self._client.get_layer(device_path, layer_idx))


async def main():
    """Test the client."""
    client = UChromaClient()
    await client.connect()

    try:
        for dev_path in await client.get_device_paths():
            dev_proxy = await client._get_proxy(dev_path)
            dev = dev_proxy.get_interface('org.chemlab.UChroma.Device')

            key = await dev.get_key()
            name = await dev.get_name()
            serial = await dev.get_serial_number()
            firmware = await dev.get_firmware_version()

            print(f'[{key}]: {name} ({serial} / {firmware})')

    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
