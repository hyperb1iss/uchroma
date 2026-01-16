"""
UChroma Main Window

Split-view layout with device sidebar and content pages.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from .views.device_sidebar import DeviceSidebar
from .views.dashboard_page import DashboardPage
from .views.lighting_page import LightingPage
from .views.zones_page import ZonesPage


class UChromaWindow(Adw.ApplicationWindow):
    """Main application window with navigation."""

    __gtype_name__ = 'UChromaWindow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title('UChroma')
        self.set_default_size(1200, 800)
        self.set_size_request(800, 600)

        self._current_device = None
        self._pages = {}

        self._build_ui()
        self._setup_bindings()

    def _build_ui(self):
        """Build the window UI."""
        # Main layout: Navigation split view
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_max_sidebar_width(280)
        self.split_view.set_min_sidebar_width(240)
        self.set_content(self.split_view)

        # === SIDEBAR ===
        sidebar_page = Adw.NavigationPage.new(
            self._build_sidebar(),
            'Devices'
        )
        self.split_view.set_sidebar(sidebar_page)

        # === CONTENT ===
        content_page = Adw.NavigationPage.new(
            self._build_content(),
            'UChroma'
        )
        self.split_view.set_content(content_page)

    def _build_sidebar(self) -> Gtk.Widget:
        """Build the device sidebar."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class('navigation-sidebar')

        # Header bar for sidebar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)

        # Refresh button
        refresh_btn = Gtk.Button.new_from_icon_name('view-refresh-symbolic')
        refresh_btn.set_action_name('app.refresh')
        refresh_btn.set_tooltip_text('Refresh devices')
        header.pack_start(refresh_btn)

        box.append(header)

        # Device list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        app = self.get_application()
        self.sidebar = DeviceSidebar(app.device_store if app else None)
        self.sidebar.connect('device-selected', self._on_device_selected)
        scroll.set_child(self.sidebar)

        box.append(scroll)

        # Footer with settings
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        footer.set_margin_top(8)
        footer.set_margin_bottom(8)
        footer.set_margin_start(12)
        footer.set_margin_end(12)

        settings_btn = Gtk.Button.new_from_icon_name('emblem-system-symbolic')
        settings_btn.add_css_class('flat')
        settings_btn.set_tooltip_text('Settings')
        footer.append(settings_btn)

        about_btn = Gtk.Button.new_from_icon_name('help-about-symbolic')
        about_btn.add_css_class('flat')
        about_btn.set_action_name('app.about')
        about_btn.set_tooltip_text('About UChroma')
        about_btn.set_hexpand(True)
        about_btn.set_halign(Gtk.Align.END)
        footer.append(about_btn)

        box.append(footer)

        return box

    def _build_content(self) -> Gtk.Widget:
        """Build the main content area with view stack."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar with view switcher
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)

        # View switcher in title
        self.view_switcher = Adw.ViewSwitcher()
        self.view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(self.view_switcher)

        box.append(header)

        # View stack
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        self.view_switcher.set_stack(self.view_stack)

        # Add pages
        self._pages['dashboard'] = DashboardPage()
        self.view_stack.add_titled_with_icon(
            self._pages['dashboard'],
            'dashboard',
            'Dashboard',
            'go-home-symbolic'
        )

        self._pages['lighting'] = LightingPage()
        self.view_stack.add_titled_with_icon(
            self._pages['lighting'],
            'lighting',
            'Lighting',
            'starred-symbolic'
        )

        self._pages['zones'] = ZonesPage()
        self.view_stack.add_titled_with_icon(
            self._pages['zones'],
            'zones',
            'LED Zones',
            'preferences-color-symbolic'
        )

        box.append(self.view_stack)

        # View switcher bar for narrow windows
        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self.view_stack)
        box.append(switcher_bar)

        # Bind reveal based on window width
        self.view_switcher.connect('notify::visible', lambda *_:
            switcher_bar.set_reveal(not self.view_switcher.get_visible()))

        return box

    def _setup_bindings(self):
        """Set up property bindings."""
        pass

    def _on_device_selected(self, sidebar, device):
        """Handle device selection."""
        self._current_device = device

        # Update all pages with new device
        for page in self._pages.values():
            if hasattr(page, 'set_device'):
                page.set_device(device)

        # Update window title
        if device:
            self.split_view.get_content().set_title(device.name)
        else:
            self.split_view.get_content().set_title('UChroma')

    def on_devices_ready(self):
        """Called when devices are loaded."""
        # Select first device if available
        app = self.get_application()
        if app and len(app.device_store) > 0:
            first_device = app.device_store.get_item(0)
            self.sidebar.select_device(first_device)

    @property
    def current_device(self):
        """Get the currently selected device."""
        return self._current_device
