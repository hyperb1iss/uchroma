#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name

import asyncio
import contextlib
import re
from typing import ClassVar

from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

BASE_PATH = "/io/uchroma"
SERVICE = "io.uchroma"


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
        dm = proxy.get_interface("io.uchroma.DeviceManager")
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
                # Note: when use_key=True, identifier is always a str
                if dev.Key == identifier or dev.Key.startswith(f"{identifier}."):
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
        anim = proxy.get_interface("io.uchroma.AnimationManager")
        return await anim.call_get_layer_info(zindex)


class DeviceProxy:
    """
    Synchronous wrapper for device properties.
    Caches introspected properties for sync access.
    """

    _DYNAMIC_PROPS: ClassVar[set[str]] = {
        "Brightness",
        "BatteryLevel",
        "IsCharging",
        "SerialNumber",
        "FirmwareVersion",
    }

    def __init__(self, proxy, loop=None):
        self._proxy = proxy
        self._device_iface = proxy.get_interface("io.uchroma.Device")
        self._cache = {}
        self._loop = loop
        self._refreshed = False
        self._system_refreshed = False

        # Try to get optional interfaces
        self._fx_iface = None
        self._anim_iface = None
        self._led_iface = None
        self._system_iface = None
        with contextlib.suppress(Exception):
            self._fx_iface = proxy.get_interface("io.uchroma.FXManager")
        with contextlib.suppress(Exception):
            self._anim_iface = proxy.get_interface("io.uchroma.AnimationManager")
        with contextlib.suppress(Exception):
            self._led_iface = proxy.get_interface("io.uchroma.LEDManager")
        with contextlib.suppress(Exception):
            self._system_iface = proxy.get_interface("io.uchroma.SystemControl")

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
        if name in self._DYNAMIC_PROPS and not self._refreshed:
            self.Refresh()
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
        self._refreshed = True

    def Refresh(self):
        """Refresh dynamic device state via D-Bus."""
        if not hasattr(self._device_iface, "call_refresh"):
            self._refreshed = True
            return None

        loop = self._get_loop()
        try:
            raw = loop.run_until_complete(self._device_iface.call_refresh())
        except Exception:
            self._refreshed = True
            return None

        values = self._unwrap_variants(raw)
        if isinstance(values, dict):
            self._cache.update(values)
        self._refreshed = True
        return values

    def RefreshSystemControl(self):
        """Refresh system control state via D-Bus."""
        if self._system_iface is None or not hasattr(self._system_iface, "call_refresh"):
            self._system_refreshed = True
            return None

        loop = self._get_loop()
        try:
            raw = loop.run_until_complete(self._system_iface.call_refresh())
        except Exception:
            self._system_refreshed = True
            return None

        values = self._unwrap_variants(raw)
        if isinstance(values, dict):
            self._cache.update(values)
        self._system_refreshed = True
        return values

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

    def SetLayerTraits(self, zindex, traits):
        if self._anim_iface is None:
            return False
        loop = self._get_loop()
        return loop.run_until_complete(self._anim_iface.call_set_layer_traits(zindex, traits))

    # LED Manager properties and methods
    @property
    def AvailableLEDs(self):
        if self._led_iface is None:
            return None
        if "AvailableLEDs" not in self._cache:
            loop = self._get_loop()
            raw = loop.run_until_complete(self._led_iface.get_available_leds())
            self._cache["AvailableLEDs"] = self._unwrap_variants(raw)
        return self._cache["AvailableLEDs"]

    def GetLED(self, led_name):
        """Get current state of an LED."""
        if self._led_iface is None:
            return None
        loop = self._get_loop()
        raw = loop.run_until_complete(self._led_iface.call_get_led(led_name))
        return self._unwrap_variants(raw)

    def SetLED(self, led_name, props):
        """Set LED properties."""
        if self._led_iface is None:
            return False
        loop = self._get_loop()
        return loop.run_until_complete(self._led_iface.call_set_led(led_name, props))

    # System Control properties and methods
    @property
    def HasSystemControl(self):
        """Check if device supports system control (laptops only)."""
        return self._system_iface is not None

    @property
    def FanRPM(self):
        """Get current fan RPM(s)."""
        if self._system_iface is None:
            return None
        if not self._system_refreshed:
            self.RefreshSystemControl()
        if "FanRPM" in self._cache:
            return self._cache["FanRPM"]
        loop = self._get_loop()
        self._cache["FanRPM"] = loop.run_until_complete(self._system_iface.get_fan_rpm())
        return self._cache["FanRPM"]

    @property
    def FanMode(self):
        """Get current fan mode (auto/manual)."""
        if self._system_iface is None:
            return None
        if not self._system_refreshed:
            self.RefreshSystemControl()
        if "FanMode" in self._cache:
            return self._cache["FanMode"]
        loop = self._get_loop()
        self._cache["FanMode"] = loop.run_until_complete(self._system_iface.get_fan_mode())
        return self._cache["FanMode"]

    @property
    def FanLimits(self):
        """Get fan RPM limits."""
        if self._system_iface is None:
            return None
        if "FanLimits" not in self._cache:
            loop = self._get_loop()
            raw = loop.run_until_complete(self._system_iface.get_fan_limits())
            self._cache["FanLimits"] = self._unwrap_variants(raw)
        return self._cache["FanLimits"]

    @property
    def PowerMode(self):
        """Get current power mode."""
        if self._system_iface is None:
            return None
        if not self._system_refreshed:
            self.RefreshSystemControl()
        if "PowerMode" in self._cache:
            return self._cache["PowerMode"]
        loop = self._get_loop()
        self._cache["PowerMode"] = loop.run_until_complete(self._system_iface.get_power_mode())
        return self._cache["PowerMode"]

    @PowerMode.setter
    def PowerMode(self, mode):
        """Set power mode."""
        if self._system_iface is None:
            return
        loop = self._get_loop()
        loop.run_until_complete(self._system_iface.set_power_mode(mode))
        self._cache["PowerMode"] = mode
        self._system_refreshed = False

    @property
    def AvailablePowerModes(self):
        """Get available power modes."""
        if self._system_iface is None:
            return None
        if "AvailablePowerModes" not in self._cache:
            loop = self._get_loop()
            self._cache["AvailablePowerModes"] = loop.run_until_complete(
                self._system_iface.get_available_power_modes()
            )
        return self._cache["AvailablePowerModes"]

    @property
    def CPUBoost(self):
        """Get current CPU boost mode."""
        if self._system_iface is None:
            return None
        if not self._system_refreshed:
            self.RefreshSystemControl()
        if "CPUBoost" in self._cache:
            return self._cache["CPUBoost"]
        loop = self._get_loop()
        self._cache["CPUBoost"] = loop.run_until_complete(self._system_iface.get_cpu_boost())
        return self._cache["CPUBoost"]

    @CPUBoost.setter
    def CPUBoost(self, mode):
        """Set CPU boost mode."""
        if self._system_iface is None:
            return
        loop = self._get_loop()
        loop.run_until_complete(self._system_iface.set_cpu_boost(mode))
        self._cache["CPUBoost"] = mode
        self._system_refreshed = False

    @property
    def GPUBoost(self):
        """Get current GPU boost mode."""
        if self._system_iface is None:
            return None
        if not self._system_refreshed:
            self.RefreshSystemControl()
        if "GPUBoost" in self._cache:
            return self._cache["GPUBoost"]
        loop = self._get_loop()
        self._cache["GPUBoost"] = loop.run_until_complete(self._system_iface.get_gpu_boost())
        return self._cache["GPUBoost"]

    @GPUBoost.setter
    def GPUBoost(self, mode):
        """Set GPU boost mode."""
        if self._system_iface is None:
            return
        loop = self._get_loop()
        loop.run_until_complete(self._system_iface.set_gpu_boost(mode))
        self._cache["GPUBoost"] = mode
        self._system_refreshed = False

    @property
    def AvailableBoostModes(self):
        """Get available boost modes."""
        if self._system_iface is None:
            return None
        if "AvailableBoostModes" not in self._cache:
            loop = self._get_loop()
            self._cache["AvailableBoostModes"] = loop.run_until_complete(
                self._system_iface.get_available_boost_modes()
            )
        return self._cache["AvailableBoostModes"]

    @property
    def SupportsFanSpeed(self):
        """Check if device supports fan speed reading."""
        if self._system_iface is None:
            return False
        loop = self._get_loop()
        return loop.run_until_complete(self._system_iface.get_supports_fan_speed())

    @property
    def SupportsBoost(self):
        """Check if device supports boost control."""
        if self._system_iface is None:
            return False
        loop = self._get_loop()
        return loop.run_until_complete(self._system_iface.get_supports_boost())

    def SetFanAuto(self):
        """Set fans to automatic control."""
        if self._system_iface is None:
            return False
        loop = self._get_loop()
        result = loop.run_until_complete(self._system_iface.call_set_fan_auto())
        self._system_refreshed = False
        return result

    def SetFanRPM(self, rpm, fan2_rpm=-1):
        """Set manual fan RPM."""
        if self._system_iface is None:
            return False
        loop = self._get_loop()
        result = loop.run_until_complete(self._system_iface.call_set_fan_rpm(rpm, fan2_rpm))
        self._system_refreshed = False
        return result

    # Battery/Wireless properties (from Device interface)
    @property
    def IsWireless(self):
        return self._get_prop("IsWireless")

    @property
    def IsCharging(self):
        return self._get_prop("IsCharging")

    @property
    def BatteryLevel(self):
        return self._get_prop("BatteryLevel")

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
