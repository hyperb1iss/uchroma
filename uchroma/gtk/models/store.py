"""
Device Store

Gio.ListStore wrapper for managing devices.
"""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, GObject  # noqa: E402

from .device import DeviceModel  # noqa: E402


class DeviceStore(GObject.Object, Gio.ListModel):
    """ListStore for UChroma devices."""

    __gtype_name__ = "UChromaDeviceStore"

    def __init__(self):
        super().__init__()
        self._store = Gio.ListStore.new(DeviceModel)
        self._devices_by_path = {}

    # Gio.ListModel implementation
    def do_get_item_type(self):
        return DeviceModel.__gtype__

    def do_get_n_items(self):
        return self._store.get_n_items()

    def do_get_item(self, position):
        return self._store.get_item(position)

    def __len__(self):
        return self._store.get_n_items()

    def get_item(self, position):
        return self._store.get_item(position)

    async def populate(self, dbus_service):
        """Populate store from D-Bus service."""
        try:
            device_paths = await dbus_service.get_devices()

            # Clear existing
            self._store.remove_all()
            self._devices_by_path.clear()

            # Add each device
            for path in device_paths:
                await self.add_device(dbus_service, path)

        except Exception as e:
            print(f"Failed to populate devices: {e}")

    async def add_device(self, dbus_service, path: str):
        """Add a device from D-Bus path."""
        if path in self._devices_by_path:
            return

        try:
            device = DeviceModel(path, dbus_service)

            # Get D-Bus proxies
            device_proxy = await dbus_service.get_device_proxy(path)
            fx_proxy = await dbus_service.get_fx_proxy(path)
            anim_proxy = await dbus_service.get_anim_proxy(path)

            # Sync state
            await device.sync_from_dbus(device_proxy, fx_proxy, anim_proxy)

            # Add to store
            self._store.append(device)
            self._devices_by_path[path] = device

            # Emit items-changed signal
            pos = self._store.get_n_items() - 1
            GLib.idle_add(lambda: self.items_changed(pos, 0, 1))

        except Exception as e:
            print(f"Failed to add device {path}: {e}")

    def remove_device(self, path: str):
        """Remove a device by D-Bus path."""
        device = self._devices_by_path.pop(path, None)
        if not device:
            return

        # Find position and remove
        for i in range(self._store.get_n_items()):
            if self._store.get_item(i) is device:
                self._store.remove(i)
                position = i  # Capture value to avoid late binding
                GLib.idle_add(lambda pos=position: self.items_changed(pos, 1, 0))
                break

    def get_device_by_path(self, path: str) -> DeviceModel:
        """Get device by D-Bus path."""
        return self._devices_by_path.get(path)
