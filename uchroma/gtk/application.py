#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
UChroma GTK4 Application

Main application class with async D-Bus integration and GLib event loop.
"""

import asyncio
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .models.store import DeviceStore  # noqa: E402
from .services.dbus import DBusService  # noqa: E402
from .window import UChromaWindow  # noqa: E402


class UChromaApplication(Adw.Application):
    """Main UChroma GTK application."""

    def __init__(self):
        super().__init__(
            application_id="tech.hyperbliss.UChroma", flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

        self.dbus = DBusService()
        self.device_store = DeviceStore()
        self._window = None
        self._startup_task = None
        self._pending_tasks: set[asyncio.Task] = set()

        # Set up actions
        self._setup_actions()

    def _setup_actions(self):
        """Set up application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Refresh devices
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", self._on_refresh)
        self.add_action(refresh_action)
        self.set_accels_for_action("app.refresh", ["<Control>r"])

        # Settings (placeholder)
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self._on_settings)
        self.add_action(settings_action)

    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)

        # Load custom CSS
        self._load_css()

        # Start async initialization
        self._startup_task = asyncio.create_task(self._startup_async())

    def _load_css(self):
        """Load custom stylesheet."""
        css_provider = Gtk.CssProvider()

        # Try loading from package resources first
        css_path = Path(__file__).parent / "resources" / "style.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
        else:
            # Fallback: try GResource
            try:
                css_provider.load_from_resource("/tech/hyperbliss/UChroma/style.css")
            except GLib.Error:
                print("Warning: Could not load stylesheet")
                return

        display = (
            self.get_active_window().get_display()
            if self.get_active_window()
            else Gdk.Display.get_default()
        )
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    async def _startup_async(self):
        """Async startup: connect to D-Bus and populate devices."""
        try:
            await self.dbus.connect()
            await self.device_store.populate(self.dbus)

            # Subscribe to device changes
            self.dbus.on_devices_changed(self._on_devices_changed)

            # Notify window that devices are ready
            if self._window:
                GLib.idle_add(self._window.on_devices_ready)

        except Exception as e:
            print(f"Failed to connect to UChroma daemon: {e}")
            GLib.idle_add(self._show_daemon_error)

    def _on_devices_changed(self, action: str, device_path: str):
        """Handle D-Bus device changes."""

        async def update():
            if action == "add":
                await self.device_store.add_device(self.dbus, device_path)
            elif action == "remove":
                self.device_store.remove_device(device_path)

        self._schedule_task(update())

    def _show_daemon_error(self):
        """Show error dialog when daemon is not running."""
        if not self._window:
            return

        dialog = Adw.MessageDialog.new(
            self._window,
            "Daemon Not Running",
            "The UChroma daemon is not running. Start it with:\n\n  uchromad",
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()

    def do_activate(self):
        """Called when the application is activated."""
        if not self._window:
            self._window = UChromaWindow(application=self)

            # Load CSS after window is created
            self._load_css()

        self._window.present()

    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutWindow.new()
        about.set_transient_for(self._window)
        about.set_application_name("UChroma")
        about.set_application_icon("preferences-desktop-keyboard")
        about.set_version("2.0.0")
        about.set_developer_name("Hyperbliss")
        about.set_license_type(Gtk.License.LGPL_3_0)
        about.set_website("https://hyperbliss.tech/uchroma")
        about.set_issue_url("https://github.com/hyperbliss/uchroma/issues")
        about.set_copyright("© 2024 Hyperbliss")
        about.set_developers(["Stefanie Jane", "Contributors"])
        about.set_comments("Control your Razer RGB lighting with style")
        about.present()

    def _on_refresh(self, action, param):
        """Refresh device list."""
        self._schedule_task(self.device_store.populate(self.dbus))

    def _on_settings(self, action, param):
        """Show settings dialog."""
        # TODO: Implement settings dialog

    def _schedule_task(self, coro):
        """Schedule an async task and track it to prevent GC."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)


def main():
    """Entry point for the GTK application."""
    # Set up GLib event loop policy for asyncio
    try:
        from gi.events import GLibEventLoopPolicy  # noqa: PLC0415

        asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    except ImportError:
        print("Warning: gi.events not available, async features may not work")

    # Run the application
    app = UChromaApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
