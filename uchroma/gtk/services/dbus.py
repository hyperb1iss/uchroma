"""
D-Bus Service

Async wrapper for UChroma D-Bus communication.
"""

from collections.abc import Callable

from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

SERVICE_NAME = "org.chemlab.UChroma"  # TODO: migrate to tech.hyperbliss.UChroma
ROOT_PATH = "/org/chemlab/UChroma"


class DBusService:
    """Async D-Bus client for UChroma daemon."""

    def __init__(self):
        self._bus: MessageBus | None = None
        self._manager_proxy = None
        self._device_proxies = {}
        self._change_callbacks = []

    @property
    def connected(self) -> bool:
        """Check if connected to D-Bus."""
        return self._bus is not None and self._bus.connected

    async def connect(self):
        """Connect to the session bus and get manager proxy."""
        self._bus = await MessageBus(bus_type=BusType.SESSION).connect()

        # Get device manager proxy
        introspection = await self._bus.introspect(SERVICE_NAME, ROOT_PATH)
        proxy = self._bus.get_proxy_object(SERVICE_NAME, ROOT_PATH, introspection)

        self._manager_proxy = proxy.get_interface("org.chemlab.UChroma.DeviceManager")

        # Subscribe to device changes
        await self._subscribe_device_changes()

    async def _subscribe_device_changes(self):
        """Subscribe to DevicesChanged signal."""
        if not self._manager_proxy:
            return

        # The signal subscription depends on the interface definition
        # This is a simplified version - actual implementation depends on dbus-fast API
        try:
            self._manager_proxy.on_devices_changed(self._on_devices_changed)
        except AttributeError:
            # Signal might not be available
            pass

    def _on_devices_changed(self, action: str, device_path: str):
        """Handle DevicesChanged signal."""
        for callback in self._change_callbacks:
            callback(action, device_path)

    def on_devices_changed(self, callback: Callable[[str, str], None]):
        """Register callback for device changes."""
        self._change_callbacks.append(callback)

    async def get_devices(self) -> list[str]:
        """Get list of device paths."""
        if not self._manager_proxy:
            return []

        try:
            devices = await self._manager_proxy.call_get_devices()
            return list(devices)
        except Exception as e:
            print(f"Failed to get devices: {e}")
            return []

    async def get_device_proxy(self, path: str):
        """Get proxy for Device interface."""
        if path in self._device_proxies:
            return self._device_proxies[path].get("device")

        try:
            introspection = await self._bus.introspect(SERVICE_NAME, path)
            proxy = self._bus.get_proxy_object(SERVICE_NAME, path, introspection)

            self._device_proxies[path] = {
                "device": proxy.get_interface("org.chemlab.UChroma.Device"),
                "fx": None,
                "anim": None,
                "led": None,
            }

            # Try to get additional interfaces
            try:
                self._device_proxies[path]["fx"] = proxy.get_interface(
                    "org.chemlab.UChroma.FXManager"
                )
            except Exception:
                pass

            try:
                self._device_proxies[path]["anim"] = proxy.get_interface(
                    "org.chemlab.UChroma.AnimationManager"
                )
            except Exception:
                pass

            try:
                self._device_proxies[path]["led"] = proxy.get_interface(
                    "org.chemlab.UChroma.LEDManager"
                )
            except Exception:
                pass

            return self._device_proxies[path]["device"]

        except Exception as e:
            print(f"Failed to get device proxy for {path}: {e}")
            return None

    async def get_fx_proxy(self, path: str):
        """Get proxy for FXManager interface."""
        if path not in self._device_proxies:
            await self.get_device_proxy(path)
        return self._device_proxies.get(path, {}).get("fx")

    async def get_anim_proxy(self, path: str):
        """Get proxy for AnimationManager interface."""
        if path not in self._device_proxies:
            await self.get_device_proxy(path)
        return self._device_proxies.get(path, {}).get("anim")

    async def get_led_proxy(self, path: str):
        """Get proxy for LEDManager interface."""
        if path not in self._device_proxies:
            await self.get_device_proxy(path)
        return self._device_proxies.get(path, {}).get("led")

    async def set_effect(self, path: str, effect_name: str, params: dict = None):
        """Set an effect on a device."""
        fx_proxy = await self.get_fx_proxy(path)
        if not fx_proxy:
            return False

        try:
            # Convert params to D-Bus variants
            dbus_params = {}
            if params:
                for k, v in params.items():
                    if isinstance(v, bool):
                        dbus_params[k] = Variant("b", v)
                    elif isinstance(v, int):
                        dbus_params[k] = Variant("i", v)
                    elif isinstance(v, float):
                        dbus_params[k] = Variant("d", v)
                    elif isinstance(v, str):
                        dbus_params[k] = Variant("s", v)
                    elif isinstance(v, list):
                        # Assume list of strings for now
                        dbus_params[k] = Variant("as", v)

            return await fx_proxy.call_set_fx(effect_name, dbus_params)
        except Exception as e:
            print(f"Failed to set effect: {e}")
            return False

    async def add_renderer(self, path: str, name: str, zindex: int = -1, traits: dict = None):
        """Add an animation renderer."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return None

        try:
            dbus_traits = {}
            if traits:
                for k, v in traits.items():
                    if isinstance(v, bool):
                        dbus_traits[k] = Variant("b", v)
                    elif isinstance(v, int):
                        dbus_traits[k] = Variant("i", v)
                    elif isinstance(v, float):
                        dbus_traits[k] = Variant("d", v)
                    elif isinstance(v, str):
                        dbus_traits[k] = Variant("s", v)

            return await anim_proxy.call_add_renderer(name, zindex, dbus_traits)
        except Exception as e:
            print(f"Failed to add renderer: {e}")
            return None

    async def remove_renderer(self, path: str, zindex: int):
        """Remove an animation renderer."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return False

        try:
            return await anim_proxy.call_remove_renderer(zindex)
        except Exception as e:
            print(f"Failed to remove renderer: {e}")
            return False

    async def stop_animation(self, path: str):
        """Stop animation on a device."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return False

        try:
            return await anim_proxy.call_stop_animation()
        except Exception as e:
            print(f"Failed to stop animation: {e}")
            return False

    async def disconnect(self):
        """Disconnect from D-Bus."""
        if self._bus:
            self._bus.disconnect()
            self._bus = None
            self._manager_proxy = None
            self._device_proxies.clear()
