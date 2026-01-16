#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
D-Bus Service

Async wrapper for UChroma D-Bus communication.
"""

import contextlib
from collections.abc import Callable

from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

SERVICE_NAME = "io.uchroma"
ROOT_PATH = "/io/uchroma"


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

        self._manager_proxy = proxy.get_interface("io.uchroma.DeviceManager")

        # Subscribe to device changes
        await self._subscribe_device_changes()

    async def _subscribe_device_changes(self):
        """Subscribe to DevicesChanged signal."""
        if not self._manager_proxy:
            return

        # The signal subscription depends on the interface definition
        # This is a simplified version - actual implementation depends on dbus-fast API
        with contextlib.suppress(AttributeError):
            self._manager_proxy.on_devices_changed(self._on_devices_changed)

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
                "device": proxy.get_interface("io.uchroma.Device"),
                "fx": None,
                "anim": None,
                "led": None,
                "system": None,
            }

            # Try to get additional interfaces
            with contextlib.suppress(Exception):
                self._device_proxies[path]["fx"] = proxy.get_interface("io.uchroma.FXManager")

            with contextlib.suppress(Exception):
                self._device_proxies[path]["anim"] = proxy.get_interface(
                    "io.uchroma.AnimationManager"
                )

            with contextlib.suppress(Exception):
                self._device_proxies[path]["led"] = proxy.get_interface("io.uchroma.LEDManager")

            with contextlib.suppress(Exception):
                self._device_proxies[path]["system"] = proxy.get_interface(
                    "io.uchroma.SystemControl"
                )

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

    async def get_system_proxy(self, path: str):
        """Get proxy for SystemControl interface."""
        if path not in self._device_proxies:
            await self.get_device_proxy(path)
        return self._device_proxies.get(path, {}).get("system")

    def _unwrap_variants(self, obj):
        """Recursively unwrap dbus_fast Variants."""
        if isinstance(obj, Variant):
            return self._unwrap_variants(obj.value)
        if isinstance(obj, dict):
            return {k: self._unwrap_variants(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return type(obj)(self._unwrap_variants(item) for item in obj)
        return obj

    async def get_available_fx(self, path: str) -> dict:
        """Fetch available effects with trait metadata."""
        fx_proxy = await self.get_fx_proxy(path)
        if not fx_proxy:
            return {}

        try:
            raw = await fx_proxy.get_available_fx()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get available FX: {e}")
            return {}

    async def get_current_fx(self, path: str):
        """Fetch current effect and params."""
        fx_proxy = await self.get_fx_proxy(path)
        if not fx_proxy:
            return ("", {})

        try:
            raw = await fx_proxy.get_current_fx()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get current FX: {e}")
            return ("", {})

    async def get_available_renderers(self, path: str) -> dict:
        """Fetch available renderers with metadata."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return {}

        try:
            raw = await anim_proxy.get_available_renderers()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get available renderers: {e}")
            return {}

    async def get_current_renderers(self, path: str):
        """Fetch current renderer stack."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return []

        try:
            raw = await anim_proxy.get_current_renderers()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get current renderers: {e}")
            return []

    async def get_animation_state(self, path: str) -> str:
        """Fetch animation state string."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return ""

        try:
            return await anim_proxy.get_animation_state()
        except Exception as e:
            print(f"Failed to get animation state: {e}")
            return ""

    async def get_current_frame(self, path: str) -> dict:
        """Fetch current composed frame for live preview."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return {}

        try:
            raw = await anim_proxy.call_get_current_frame()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get current frame: {e}")
            return {}

    async def get_layer_info(self, path: str, zindex: int) -> dict:
        """Fetch layer trait values."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return {}

        try:
            raw = await anim_proxy.call_get_layer_info(zindex)
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get layer info: {e}")
            return {}

    async def set_layer_traits(self, path: str, zindex: int, traits: dict):
        """Set renderer traits for a layer."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return False

        try:
            dbus_traits = {}
            for k, v in traits.items():
                if isinstance(v, bool):
                    dbus_traits[k] = Variant("b", v)
                elif isinstance(v, int):
                    dbus_traits[k] = Variant("i", v)
                elif isinstance(v, float):
                    dbus_traits[k] = Variant("d", v)
                elif isinstance(v, str):
                    dbus_traits[k] = Variant("s", v)
                elif isinstance(v, list):
                    dbus_traits[k] = Variant("as", v)

            return await anim_proxy.call_set_layer_traits(zindex, dbus_traits)
        except Exception as e:
            print(f"Failed to set layer traits: {e}")
            return False

    async def set_effect(self, path: str, effect_name: str, params: dict | None = None):
        """Set an effect on a device."""
        fx_proxy = await self.get_fx_proxy(path)
        if not fx_proxy:
            return False

    async def get_key_mapping(self, path: str) -> dict:
        """Fetch key mapping layout for a device."""
        device_proxy = await self.get_device_proxy(path)
        if not device_proxy:
            return {}

        try:
            raw = await device_proxy.get_key_mapping()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get key mapping: {e}")
            return {}

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

    async def add_renderer(
        self, path: str, name: str, zindex: int = -1, traits: dict | None = None
    ):
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
                    elif isinstance(v, list):
                        dbus_traits[k] = Variant("as", v)

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

    async def pause_animation(self, path: str):
        """Toggle pause/resume animation on a device."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return False

        try:
            return await anim_proxy.call_pause_animation()
        except Exception as e:
            print(f"Failed to pause animation: {e}")
            return False

    async def set_brightness(self, path: str, value: float):
        """Set device brightness (0.0-100.0)."""
        device_proxy = await self.get_device_proxy(path)
        if not device_proxy:
            return False

        try:
            await device_proxy.set_brightness(value)
            return True
        except Exception as e:
            print(f"Failed to set brightness: {e}")
            return False

    async def set_suspended(self, path: str, suspended: bool):
        """Set device suspended state."""
        device_proxy = await self.get_device_proxy(path)
        if not device_proxy:
            return False

        try:
            await device_proxy.set_suspended(suspended)
            return True
        except Exception as e:
            print(f"Failed to set suspended: {e}")
            return False

    async def get_fan_rpm(self, path: str) -> list[int]:
        """Get current fan RPM list."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return []

        try:
            raw = await system_proxy.get_fan_rpm()
            return list(self._unwrap_variants(raw))
        except Exception as e:
            print(f"Failed to get fan RPM: {e}")
            return []

    async def get_fan_mode(self, path: str) -> str:
        """Get current fan mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return ""

        try:
            return await system_proxy.get_fan_mode()
        except Exception as e:
            print(f"Failed to get fan mode: {e}")
            return ""

    async def get_fan_limits(self, path: str) -> dict:
        """Get fan RPM limits."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return {}

        try:
            raw = await system_proxy.get_fan_limits()
            return self._unwrap_variants(raw)
        except Exception as e:
            print(f"Failed to get fan limits: {e}")
            return {}

    async def set_fan_auto(self, path: str) -> bool:
        """Set fans to automatic control."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return False

        try:
            return await system_proxy.call_set_fan_auto()
        except Exception as e:
            print(f"Failed to set fan auto: {e}")
            return False

    async def set_fan_rpm(self, path: str, rpm: int, fan2_rpm: int = -1) -> bool:
        """Set manual fan RPM."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return False

        try:
            return await system_proxy.call_set_fan_rpm(rpm, fan2_rpm)
        except Exception as e:
            print(f"Failed to set fan RPM: {e}")
            return False

    async def get_power_mode(self, path: str) -> str:
        """Get current power mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return ""

        try:
            return await system_proxy.get_power_mode()
        except Exception as e:
            print(f"Failed to get power mode: {e}")
            return ""

    async def set_power_mode(self, path: str, mode: str) -> bool:
        """Set power mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return False

        try:
            await system_proxy.set_power_mode(mode)
            return True
        except Exception as e:
            print(f"Failed to set power mode: {e}")
            return False

    async def get_available_power_modes(self, path: str) -> list[str]:
        """Get available power modes."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return []

        try:
            raw = await system_proxy.get_available_power_modes()
            return list(self._unwrap_variants(raw))
        except Exception as e:
            print(f"Failed to get available power modes: {e}")
            return []

    async def get_cpu_boost(self, path: str) -> str:
        """Get current CPU boost mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return ""

        try:
            return await system_proxy.get_cpu_boost()
        except Exception as e:
            print(f"Failed to get CPU boost: {e}")
            return ""

    async def set_cpu_boost(self, path: str, mode: str) -> bool:
        """Set CPU boost mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return False

        try:
            await system_proxy.set_cpu_boost(mode)
            return True
        except Exception as e:
            print(f"Failed to set CPU boost: {e}")
            return False

    async def get_gpu_boost(self, path: str) -> str:
        """Get current GPU boost mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return ""

        try:
            return await system_proxy.get_gpu_boost()
        except Exception as e:
            print(f"Failed to get GPU boost: {e}")
            return ""

    async def set_gpu_boost(self, path: str, mode: str) -> bool:
        """Set GPU boost mode."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return False

        try:
            await system_proxy.set_gpu_boost(mode)
            return True
        except Exception as e:
            print(f"Failed to set GPU boost: {e}")
            return False

    async def get_available_boost_modes(self, path: str) -> list[str]:
        """Get available boost modes."""
        system_proxy = await self.get_system_proxy(path)
        if not system_proxy:
            return []

        try:
            raw = await system_proxy.get_available_boost_modes()
            return list(self._unwrap_variants(raw))
        except Exception as e:
            print(f"Failed to get available boost modes: {e}")
            return []

    async def disconnect(self):
        """Disconnect from D-Bus."""
        if self._bus:
            self._bus.disconnect()
            self._bus = None
            self._manager_proxy = None
            self._device_proxies.clear()
