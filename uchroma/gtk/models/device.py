#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Device Model

GObject-based reactive model for device state, synchronized with D-Bus.
"""

import asyncio
import contextlib

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject  # noqa: E402


class DeviceModel(GObject.Object):
    """Reactive model for a UChroma device."""

    __gtype_name__ = "UChromaDeviceModel"

    # Device properties (read-only from D-Bus)
    name = GObject.Property(type=str, default="Unknown Device")
    device_type = GObject.Property(type=str, default="Unknown")
    serial_number = GObject.Property(type=str, default="")
    firmware_version = GObject.Property(type=str, default="")
    vendor_id = GObject.Property(type=int, default=0)
    product_id = GObject.Property(type=int, default=0)

    # Matrix info
    has_matrix = GObject.Property(type=bool, default=False)
    width = GObject.Property(type=int, default=0)
    height = GObject.Property(type=int, default=0)

    # Wireless info
    is_wireless = GObject.Property(type=bool, default=False)
    is_charging = GObject.Property(type=bool, default=False)
    battery_level = GObject.Property(type=float, default=-1.0, minimum=-1.0, maximum=100.0)

    # Controllable properties
    brightness = GObject.Property(type=float, default=100.0, minimum=0.0, maximum=100.0)
    suspended = GObject.Property(type=bool, default=False)

    # Effect state
    current_fx = GObject.Property(type=str, default="")
    is_animating = GObject.Property(type=bool, default=False)

    def __init__(self, dbus_path: str, dbus_service=None):
        super().__init__()

        self._path = dbus_path
        self._dbus = dbus_service
        self._device_proxy = None
        self._fx_proxy = None
        self._anim_proxy = None
        self._props_proxy = None
        self._pending_tasks: set[asyncio.Task] = set()

        self._syncing = False  # Prevent feedback loops
        self._props_subscribed = False

    @property
    def path(self) -> str:
        """Get the D-Bus object path."""
        return self._path

    @property
    def product_id_hex(self) -> str:
        """Get product ID as hex string."""
        return f"0x{self.product_id:04x}"

    @property
    def icon_name(self) -> str:
        """Get icon name based on device type."""
        icons = {
            "Laptop": "computer-symbolic",
            "Keyboard": "input-keyboard-symbolic",
            "Mouse": "input-mouse-symbolic",
            "Headset": "audio-headset-symbolic",
            "Mousepad": "input-tablet-symbolic",
            "Keypad": "input-dialpad-symbolic",
        }
        return icons.get(self.device_type, "preferences-desktop-keyboard-symbolic")

    async def sync_from_dbus(self, device_proxy, fx_proxy=None, anim_proxy=None):
        """Synchronize model state from D-Bus proxies."""
        self._device_proxy = device_proxy
        self._fx_proxy = fx_proxy
        self._anim_proxy = anim_proxy

        if self._dbus is not None:
            with contextlib.suppress(Exception):
                self._props_proxy = await self._dbus.get_properties_proxy(self._path)

        self._syncing = True
        try:
            # Read device properties
            self.name = await device_proxy.get_name()
            self.device_type = await device_proxy.get_device_type()

            with contextlib.suppress(Exception):
                self.serial_number = await device_proxy.get_serial_number()

            with contextlib.suppress(Exception):
                self.firmware_version = await device_proxy.get_firmware_version()

            try:
                self.vendor_id = await device_proxy.get_vendor_id()
                self.product_id = await device_proxy.get_product_id()
            except Exception:
                pass

            try:
                self.has_matrix = await device_proxy.get_has_matrix()
                if self.has_matrix:
                    self.width = await device_proxy.get_width()
                    self.height = await device_proxy.get_height()
            except Exception:
                pass

            with contextlib.suppress(Exception):
                self.brightness = await device_proxy.get_brightness()

            with contextlib.suppress(Exception):
                self.suspended = await device_proxy.get_suspended()

            # FX state
            if fx_proxy:
                try:
                    current = await fx_proxy.get_current_fx()
                    if current:
                        self.current_fx = current[0]
                except Exception:
                    pass

            # Animation state
            if anim_proxy:
                try:
                    state = await anim_proxy.get_animation_state()
                    self.is_animating = state == "running"
                except Exception:
                    pass

            # Subscribe to property changes
            self._setup_dbus_sync()

        finally:
            self._syncing = False

    def _setup_dbus_sync(self):
        """Set up bidirectional D-Bus synchronization."""
        if not self._device_proxy:
            return

        # When model changes, push to D-Bus
        self.connect("notify::brightness", self._on_brightness_changed)
        self.connect("notify::suspended", self._on_suspended_changed)

        if self._props_proxy and not self._props_subscribed:
            with contextlib.suppress(Exception):
                self._props_proxy.on_properties_changed(self.on_dbus_properties_changed)
                self._props_subscribed = True

    def _on_brightness_changed(self, obj, pspec):
        """Push brightness change to D-Bus."""
        if self._syncing or not self._device_proxy:
            return

        self._schedule_task(self._set_brightness_async())

    async def _set_brightness_async(self):
        """Async brightness setter."""
        try:
            await self._device_proxy.set_brightness(self.brightness)
        except Exception as e:
            print(f"Failed to set brightness: {e}")

    def _on_suspended_changed(self, obj, pspec):
        """Push suspended change to D-Bus."""
        if self._syncing or not self._device_proxy:
            return

        self._schedule_task(self._set_suspended_async())

    async def _set_suspended_async(self):
        """Async suspended setter."""
        try:
            await self._device_proxy.set_suspended(self.suspended)
        except Exception as e:
            print(f"Failed to set suspended: {e}")

    def on_dbus_properties_changed(self, interface, changed, invalidated):
        """Handle D-Bus property changes."""

        def _unwrap(value):
            return value.value if hasattr(value, "value") else value

        self._syncing = True
        try:
            if interface == "io.uchroma.Device":
                if "Brightness" in changed:
                    self.brightness = _unwrap(changed["Brightness"])
                if "Suspended" in changed:
                    self.suspended = _unwrap(changed["Suspended"])
            elif interface == "io.uchroma.AnimationManager":
                if "AnimationState" in changed:
                    self.is_animating = _unwrap(changed["AnimationState"]) == "running"
            elif interface == "io.uchroma.FXManager":
                if "CurrentFX" in changed:
                    current = _unwrap(changed["CurrentFX"])
                    if isinstance(current, (list, tuple)) and current:
                        self.current_fx = current[0]
        finally:
            self._syncing = False

    def _schedule_task(self, coro):
        """Schedule an async task and track it to prevent GC."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def __repr__(self):
        return f"<DeviceModel '{self.name}' ({self.product_id_hex})>"
