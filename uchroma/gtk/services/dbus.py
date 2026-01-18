#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
D-Bus Service

Async wrapper for UChroma D-Bus communication with automatic reconnection.
"""

import asyncio
import contextlib
from collections.abc import Callable
from enum import Enum, auto

from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

from uchroma.dbus_utils import dbus_prepare
from uchroma.log import Log

SERVICE_NAME = "io.uchroma"
ROOT_PATH = "/io/uchroma"

# Reconnection settings
RECONNECT_INITIAL_DELAY = 1.0  # seconds
RECONNECT_MAX_DELAY = 30.0  # seconds
RECONNECT_BACKOFF_FACTOR = 2.0

_logger = Log.get("uchroma.gtk.dbus")


class ConnectionState(Enum):
    """D-Bus connection states."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()


class DBusService:
    """Async D-Bus client for UChroma daemon with auto-reconnection."""

    def __init__(self):
        self._bus: MessageBus | None = None
        self._manager_proxy = None
        self._device_proxies = {}
        self._change_callbacks = []
        self._state_callbacks: list[Callable[[ConnectionState], None]] = []
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_task: asyncio.Task | None = None
        self._disconnect_monitor: asyncio.Task | None = None
        self._should_reconnect = True

    @property
    def connected(self) -> bool:
        """Check if connected to D-Bus."""
        return self._bus is not None and self._bus.connected

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    def _set_state(self, state: ConnectionState):
        """Update connection state and notify callbacks."""
        if self._state != state:
            old_state = self._state
            self._state = state
            _logger.debug("Connection state: %s -> %s", old_state.name, state.name)
            for callback in self._state_callbacks:
                try:
                    callback(state)
                except Exception as e:
                    _logger.warning("State callback error: %s", e)

    def on_state_changed(self, callback: Callable[[ConnectionState], None]):
        """Register callback for connection state changes."""
        self._state_callbacks.append(callback)

    async def connect(self):
        """Connect to the session bus and get manager proxy."""
        self._set_state(ConnectionState.CONNECTING)
        self._should_reconnect = True

        try:
            self._bus = await MessageBus(bus_type=BusType.SESSION).connect()

            # Get device manager proxy
            introspection = await self._bus.introspect(SERVICE_NAME, ROOT_PATH)
            proxy = self._bus.get_proxy_object(SERVICE_NAME, ROOT_PATH, introspection)

            self._manager_proxy = proxy.get_interface("io.uchroma.DeviceManager")

            # Subscribe to device changes
            await self._subscribe_device_changes()

            # Monitor for disconnection in background
            self._disconnect_monitor = asyncio.create_task(self._monitor_disconnect())

            self._set_state(ConnectionState.CONNECTED)
            _logger.info("Connected to UChroma daemon")

        except Exception:
            self._set_state(ConnectionState.DISCONNECTED)
            raise

    async def _monitor_disconnect(self):
        """Monitor for bus disconnection and trigger reconnect."""
        if not self._bus:
            return

        try:
            await self._bus.wait_for_disconnect()
        except Exception as e:
            _logger.debug("Disconnect monitor error: %s", e)

        # Only handle if we haven't already cleaned up
        if self._bus is not None:
            self._on_bus_disconnect()

    def _on_bus_disconnect(self):
        """Handle bus disconnection."""
        _logger.warning("D-Bus connection lost")
        self._clear_state()
        self._set_state(ConnectionState.DISCONNECTED)

        if self._should_reconnect and not self._reconnect_task:
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    def _clear_state(self):
        """Clear all cached state after disconnection."""
        self._bus = None
        self._manager_proxy = None
        self._device_proxies.clear()
        self._disconnect_monitor = None

    async def _reconnect_loop(self):
        """Attempt to reconnect with exponential backoff."""
        delay = RECONNECT_INITIAL_DELAY

        while self._should_reconnect:
            self._set_state(ConnectionState.RECONNECTING)
            _logger.info("Attempting to reconnect in %.1fs...", delay)

            await asyncio.sleep(delay)

            if not self._should_reconnect:
                break

            try:
                await self.connect()
                _logger.info("Reconnected to UChroma daemon")
                self._reconnect_task = None
                return
            except Exception as e:
                _logger.debug("Reconnection failed: %s", e)
                delay = min(delay * RECONNECT_BACKOFF_FACTOR, RECONNECT_MAX_DELAY)

        self._reconnect_task = None

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
                "props": None,
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

            with contextlib.suppress(Exception):
                self._device_proxies[path]["props"] = proxy.get_interface(
                    "org.freedesktop.DBus.Properties"
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

    async def get_properties_proxy(self, path: str):
        """Get proxy for org.freedesktop.DBus.Properties."""
        if path not in self._device_proxies:
            await self.get_device_proxy(path)
        return self._device_proxies.get(path, {}).get("props")

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
            prepared, _sig = dbus_prepare(traits or {}, variant=True)
            return await anim_proxy.call_set_layer_traits(zindex, prepared)
        except Exception as e:
            print(f"Failed to set layer traits: {e}")
            return False

    async def set_effect(self, path: str, effect_name: str, params: dict | None = None):
        """Set an effect on a device."""
        fx_proxy = await self.get_fx_proxy(path)
        if not fx_proxy:
            return False

        try:
            prepared, _sig = dbus_prepare(params or {}, variant=True)
            return await fx_proxy.call_set_fx(effect_name, prepared)
        except Exception as e:
            print(f"Failed to set effect: {e}")
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

    async def add_renderer(
        self, path: str, name: str, zindex: int = -1, traits: dict | None = None
    ):
        """Add an animation renderer."""
        anim_proxy = await self.get_anim_proxy(path)
        if not anim_proxy:
            return None

        try:
            prepared, _sig = dbus_prepare(traits or {}, variant=True)
            return await anim_proxy.call_add_renderer(name, zindex, prepared)
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
        """Disconnect from D-Bus and stop reconnection attempts."""
        self._should_reconnect = False

        if self._reconnect_task:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

        if self._bus:
            self._bus.disconnect()

        self._clear_state()
        self._set_state(ConnectionState.DISCONNECTED)
