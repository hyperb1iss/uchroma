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
import contextlib
import re

from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

BASE_PATH = "/org/chemlab/UChroma"
SERVICE = "org.chemlab.UChroma"


class UChromaClientAsync:
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
        dm = proxy.get_interface("org.chemlab.UChroma.DeviceManager")
        return await dm.call_get_devices()

    async def get_device(self, identifier, loop=None):
        """Get a device proxy by identifier (path, key, or index)."""
        if identifier is None:
            return None

        use_key = False
        if isinstance(identifier, str):
            if identifier.startswith(BASE_PATH):
                proxy = await self._get_proxy(identifier)
                return DeviceProxy(proxy, loop=loop)

            if re.match(r"\w{4}:\w{4}(\.\d{2})?$", identifier):
                use_key = True
            elif re.match(r"\d+", identifier):
                identifier = int(identifier)
            else:
                return None

        for dev_path in await self.get_device_paths():
            proxy = await self._get_proxy(dev_path)
            dev = DeviceProxy(proxy, loop=loop)
            # Pre-fetch identity props to avoid nested run_until_complete
            await dev._prefetch_identity()

            if use_key:
                # Support partial key matching (1532:026c matches 1532:026c.01)
                if dev.Key == identifier or dev.Key.startswith(identifier + "."):
                    return dev
            else:
                if identifier == dev.DeviceIndex:
                    return dev

        return None

    async def get_layer_info(self, device_path, zindex):
        """Get layer info by device and zindex."""
        # Handle DeviceProxy or string path
        if isinstance(device_path, DeviceProxy):
            device_path = device_path._proxy.path
        proxy = await self._get_proxy(device_path)
        anim = proxy.get_interface("org.chemlab.UChroma.AnimationManager")
        return await anim.call_get_layer_info(zindex)


class DeviceProxy:
    """
    Synchronous wrapper for device properties.
    Caches introspected properties for sync access.
    """

    def __init__(self, proxy, loop=None):
        self._proxy = proxy
        self._device_iface = proxy.get_interface("org.chemlab.UChroma.Device")
        self._cache = {}
        self._loop = loop

        # Try to get optional interfaces
        self._fx_iface = None
        self._anim_iface = None
        self._led_iface = None
        with contextlib.suppress(Exception):
            self._fx_iface = proxy.get_interface("org.chemlab.UChroma.FXManager")
        with contextlib.suppress(Exception):
            self._anim_iface = proxy.get_interface("org.chemlab.UChroma.AnimationManager")
        with contextlib.suppress(Exception):
            self._led_iface = proxy.get_interface("org.chemlab.UChroma.LEDManager")

    async def _prefetch_identity(self):
        """Pre-fetch Key and DeviceIndex for sync access during device lookup."""
        self._cache["Key"] = await self._device_iface.get_key()
        self._cache["DeviceIndex"] = await self._device_iface.get_device_index()

    def _get_loop(self):
        """Get or create event loop."""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def _get_prop(self, name):
        """Get property synchronously via cache or async fetch."""
        if name not in self._cache:
            loop = self._get_loop()
            # Convert CamelCase to snake_case for dbus-fast
            snake_name = "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")
            getter = getattr(self._device_iface, f"get_{snake_name}")
            self._cache[name] = loop.run_until_complete(getter())
        return self._cache[name]

    def _set_prop(self, name, value):
        """Set property synchronously."""
        loop = self._get_loop()
        # Convert CamelCase to snake_case for dbus-fast
        snake_name = "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")
        setter = getattr(self._device_iface, f"set_{snake_name}")
        loop.run_until_complete(setter(value))
        self._cache[name] = value

    @property
    def Name(self):
        return self._get_prop("Name")

    @property
    def Key(self):
        return self._get_prop("Key")

    @property
    def DeviceType(self):
        return self._get_prop("DeviceType")

    @property
    def DeviceIndex(self):
        return self._get_prop("DeviceIndex")

    @property
    def SerialNumber(self):
        return self._get_prop("SerialNumber")

    @property
    def FirmwareVersion(self):
        return self._get_prop("FirmwareVersion")

    @property
    def Manufacturer(self):
        return self._get_prop("Manufacturer")

    @property
    def VendorId(self):
        return self._get_prop("VendorId")

    @property
    def ProductId(self):
        return self._get_prop("ProductId")

    @property
    def Brightness(self):
        return self._get_prop("Brightness")

    @Brightness.setter
    def Brightness(self, value):
        self._set_prop("Brightness", value)

    @property
    def Suspended(self):
        return self._get_prop("Suspended")

    @Suspended.setter
    def Suspended(self, value):
        self._set_prop("Suspended", value)

    @property
    def HasMatrix(self):
        return self._get_prop("HasMatrix")

    @property
    def Width(self):
        return self._get_prop("Width")

    @property
    def Height(self):
        return self._get_prop("Height")

    @property
    def SupportedLeds(self):
        return self._get_prop("SupportedLeds")

    @property
    def BusPath(self):
        return self._get_prop("BusPath")

    # FX Manager properties
    @property
    def AvailableFX(self):
        if self._fx_iface is None:
            return None
        if "AvailableFX" not in self._cache:
            loop = self._get_loop()
            raw = loop.run_until_complete(self._fx_iface.get_available_fx())
            # Unwrap dbus_fast Variants
            self._cache["AvailableFX"] = self._unwrap_variants(raw)
        return self._cache["AvailableFX"]

    def _unwrap_variants(self, obj):
        """Recursively unwrap dbus_fast Variants."""
        if isinstance(obj, Variant):
            return self._unwrap_variants(obj.value)
        elif isinstance(obj, dict):
            return {k: self._unwrap_variants(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return type(obj)(self._unwrap_variants(item) for item in obj)
        return obj

    @property
    def CurrentFX(self):
        if self._fx_iface is None:
            return None
        loop = self._get_loop()
        return loop.run_until_complete(self._fx_iface.get_current_fx())

    def SetFX(self, name, args):
        if self._fx_iface is None:
            return False
        loop = self._get_loop()
        return loop.run_until_complete(self._fx_iface.call_set_fx(name, args))

    # Animation Manager properties
    @property
    def AvailableRenderers(self):
        if self._anim_iface is None:
            return None
        if "AvailableRenderers" not in self._cache:
            loop = self._get_loop()
            raw = loop.run_until_complete(self._anim_iface.get_available_renderers())
            self._cache["AvailableRenderers"] = self._unwrap_variants(raw)
        return self._cache["AvailableRenderers"]

    @property
    def CurrentRenderers(self):
        if self._anim_iface is None:
            return None
        loop = self._get_loop()
        return loop.run_until_complete(self._anim_iface.get_current_renderers())

    def AddRenderer(self, name, zindex, traits):
        if self._anim_iface is None:
            return None
        loop = self._get_loop()
        return loop.run_until_complete(self._anim_iface.call_add_renderer(name, zindex, traits))

    def RemoveRenderer(self, zindex):
        if self._anim_iface is None:
            return False
        loop = self._get_loop()
        return loop.run_until_complete(self._anim_iface.call_remove_renderer(zindex))

    # LED Manager properties
    @property
    def AvailableLEDs(self):
        if self._led_iface is None:
            return None
        if "AvailableLEDs" not in self._cache:
            loop = self._get_loop()
            self._cache["AvailableLEDs"] = loop.run_until_complete(
                self._led_iface.get_available_le_ds()
            )
        return self._cache["AvailableLEDs"]

    def get_interface(self, name):
        """Get a specific interface from the proxy."""
        return self._proxy.get_interface(name)

    def GetAll(self, interface_name=None):
        """Get all properties as a dictionary (for dump command compatibility)."""
        props = {}
        for attr in [
            "Name",
            "Key",
            "DeviceType",
            "DeviceIndex",
            "SerialNumber",
            "FirmwareVersion",
            "Manufacturer",
            "VendorId",
            "ProductId",
            "Brightness",
            "Suspended",
            "HasMatrix",
            "Width",
            "Height",
            "SupportedLeds",
            "BusPath",
        ]:
            with contextlib.suppress(Exception):
                props[attr] = getattr(self, attr)
        return props


class UChromaClient:
    """
    Synchronous D-Bus client for UChroma CLI.
    """

    def __init__(self):
        self._async_client = UChromaClientAsync()
        self._loop = None
        self._connected = False

    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def _run(self, coro):
        """Run coroutine synchronously."""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    def _ensure_connected(self):
        if not self._connected:
            self._run(self._async_client.connect())
            self._connected = True

    def get_device_paths(self) -> list:
        self._ensure_connected()
        return self._run(self._async_client.get_device_paths())

    def get_device(self, identifier):
        self._ensure_connected()
        loop = self._get_loop()
        return self._run(self._async_client.get_device(identifier, loop=loop))

    def get_layer_info(self, device_path, zindex):
        self._ensure_connected()
        return self._run(self._async_client.get_layer_info(device_path, zindex))


async def main():
    """Test the async client."""
    client = UChromaClientAsync()
    await client.connect()

    try:
        for dev_path in await client.get_device_paths():
            dev = await client.get_device(dev_path)
            print(f"[{dev.Key}]: {dev.Name} ({dev.SerialNumber} / {dev.FirmwareVersion})")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
