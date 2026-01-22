#!/usr/bin/env python3
#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Key Configuration Tool for UChroma.

An interactive curses-based tool for creating key-to-LED mappings.
Uses the Alignment renderer to display a color grid pattern and captures
key presses via evdev to map physical keys to LED matrix coordinates.

Usage:
    uv run python -m uchroma.tools.keyconfig [device] [-f FILE]
    uv run python -m uchroma.tools.keyconfig 1532:026c -f blade15.yaml

Controls:
    Arrow keys  - Move cursor
    Mouse click - Toggle edit mode
    W           - Write mappings to file
    C           - Clear mapping at cursor
    ESC         - Exit
"""

import argparse
import asyncio
import contextlib
import curses
import glob
import os
import re
import signal
import sys
import textwrap
import time
from typing import TYPE_CHECKING

import evdev
from dbus_fast import BusType
from dbus_fast.aio import MessageBus

from uchroma.client.dbus_client import UChromaClient
from uchroma.dbus_utils import dbus_prepare
from uchroma.server.hardware import Hardware, KeyMapping, Point

if TYPE_CHECKING:
    from uchroma.client.dbus_client import DeviceProxy

SERVICE = "io.uchroma"


class KeyConfigTool:
    """Interactive key configuration tool."""

    STATUS_TAG = "uChroma Key Config"

    def __init__(self, device: "DeviceProxy", config_file: str | None = None):
        self._device = device
        # Use absolute path to ensure tempfile and rename work correctly
        config_name = config_file or self._get_config_filename()
        self._config_file = os.path.abspath(config_name)

        self._position = Point(0, 0)
        self._hardware = Hardware.get_device(device.ProductId)
        self._load_hardware()

        self._mapping = KeyMapping()
        if self._hardware and self._hardware.key_mapping is not None:
            self._mapping = self._hardware.key_mapping

        self._stdscr = None
        self._editmode = False
        self._shutdown = False
        self._event_devices: list[evdev.InputDevice] = []
        self._last_key_debug = ""  # Debug: last key received

        # Async D-Bus connection for use during event loop
        self._async_bus = None
        self._async_anim_iface = None

    def _get_config_filename(self) -> str:
        """Generate default config filename based on device name."""
        name = re.sub(r"[\W]+", "", self._device.Name.lower().replace(" ", "_"))
        return f"{self._device.DeviceType.lower()}-{name}.yaml"

    def _load_hardware(self):
        """Load existing hardware config if available."""
        if self._config_file is None:
            return

        with contextlib.suppress(FileNotFoundError):
            self._hardware = Hardware.load_yaml(self._config_file)

    def _write_mappings(self):
        """Save current mappings to YAML file."""
        if self._config_file is None:
            self._last_key_debug = "Cannot save: no config file"
            return False

        try:
            # Create minimal Hardware if we don't have one from builtin configs
            if self._hardware is not None:
                hdict = self._hardware._asdict()
            else:
                hdict = {
                    "name": self._device.Name,
                    "manufacturer": self._device.Manufacturer,
                    "type": Hardware.Type[self._device.DeviceType.upper()],
                    "vendor_id": self._device.VendorId,
                    "product_id": self._device.ProductId,
                    "dimensions": Point(self._device.Height, self._device.Width),
                }

            hdict["key_mapping"] = self._mapping
            hardware = Hardware(**hdict)
            hardware.save_yaml(self._config_file)

            # Show full path so user knows where file was saved
            full_path = os.path.abspath(self._config_file)
            self._update_statusbar(f"Saved to '{full_path}'", self.color_action)
            self._last_key_debug = f"Wrote {len(self._mapping)} mappings"
            self._refresh()
            return True
        except Exception as e:
            self._last_key_debug = f"Save error: {str(e)[:40]}"
            return False

    def _find_mappings(self, position: Point) -> dict:
        """Find all key mappings that include the given position."""
        mappings = {}
        for key, mapping in self._mapping.items():
            if tuple(position) in [tuple(p) for p in mapping]:
                mappings[key] = mapping
        return mappings

    def _clear_mappings(self, position: Point):
        """Clear all mappings at the given position."""
        mappings = self._find_mappings(position)
        for key in mappings:
            self._mapping.pop(key)

    async def _async_setup(self):
        """Set up async D-Bus connection for use during event loop."""
        try:
            self._async_bus = await MessageBus(bus_type=BusType.SESSION).connect()
            # Get the device path from the sync proxy
            device_path = self._device._proxy.path
            introspection = await self._async_bus.introspect(SERVICE, device_path)
            proxy = self._async_bus.get_proxy_object(SERVICE, device_path, introspection)
            self._async_anim_iface = proxy.get_interface("io.uchroma.AnimationManager")
        except Exception as e:
            if self._stdscr:
                self._stdscr.addstr(0, 0, f"D-Bus setup error: {e}"[: curses.COLS - 1])
                self._stdscr.refresh()

    async def _async_cleanup(self):
        """Clean up async D-Bus connection."""
        if self._async_bus:
            self._async_bus.disconnect()
            self._async_bus = None
            self._async_anim_iface = None

    async def _update_alignment_cursor(self):
        """Update the Alignment renderer's cursor position."""
        if self._async_anim_iface is None:
            # Async D-Bus not set up - this shouldn't happen during event loop
            self._last_key_debug = "ERROR: No async D-Bus"
            return

        try:
            traits = {"cur_row": self._position.y, "cur_col": self._position.x}
            prepared, _sig = dbus_prepare(traits, variant=True)
            await self._async_anim_iface.call_set_layer_traits(0, prepared)
        except Exception as e:
            # Store error for display (don't write to row 0 - status bar overwrites)
            self._last_key_debug = f"Cursor err: {str(e)[:40]}"

    def _setup_alignment_effect(self) -> bool:
        """Set up the Alignment renderer on the device."""
        # Remove existing renderers individually
        # When we go to 0 layers, AnimationLoop auto-calls stop() which is async
        for _renderer_type, path in self._device.CurrentRenderers or []:
            zindex = int(path.rsplit("/", 1)[-1])
            self._device.RemoveRenderer(zindex)

        # Wait for the animation to fully stop (async cleanup)
        for _ in range(20):  # Max 2 seconds
            state = self._device.AnimationState
            if state == "stopped" or state == "" or state is None:
                break
            time.sleep(0.1)

        # Add the Alignment renderer
        result = self._device.AddRenderer(
            "uchroma.fxlib.alignment.Alignment",
            0,
            {"cur_row": 0, "cur_col": 0},
        )

        if result is None or result == "/":
            return False

        # Verify the renderer was added by checking CurrentRenderers
        return bool(self._device.CurrentRenderers)

    def _find_input_devices(self) -> list[str]:
        """Find input devices for the keyboard."""
        paths = []

        # Look for devices by vendor/product ID
        vendor_id = self._device.VendorId
        product_id = self._device.ProductId

        for dev_path in glob.glob("/dev/input/event*"):
            try:
                dev = evdev.InputDevice(dev_path)
                # Check if this is our device
                if dev.info.vendor == vendor_id and dev.info.product == product_id:
                    # Only add devices that have key events
                    caps = dev.capabilities()
                    if evdev.ecodes.EV_KEY in caps:
                        paths.append(dev_path)
                        dev.close()
                        continue
                dev.close()
            except (OSError, PermissionError):
                continue

        # Fallback: use sys_path from device if available
        if not paths and self._device.BusPath:
            bus_path = self._device.BusPath
            input_paths = glob.glob(f"{bus_path}/*:*:*/input/input*/event*")
            for p in input_paths:
                dev_name = os.path.basename(p)
                dev_path = f"/dev/input/{dev_name}"
                if os.path.exists(dev_path):
                    paths.append(dev_path)

        return paths

    def _open_input_devices(self) -> bool:
        """Open evdev input devices."""
        paths = self._find_input_devices()

        if not paths:
            # Fall back to letting user choose from all keyboards
            all_devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
            keyboards = [d for d in all_devices if evdev.ecodes.EV_KEY in d.capabilities()]
            if keyboards:
                paths = [keyboards[0].path]
                for d in all_devices:
                    d.close()

        for path in paths:
            try:
                dev = evdev.InputDevice(path)
                self._event_devices.append(dev)
            except (OSError, PermissionError) as e:
                print(f"Failed to open {path}: {e}", file=sys.stderr)
                continue

        return bool(self._event_devices)

    def _close_input_devices(self):
        """Close all open input devices."""
        for dev in self._event_devices:
            dev.close()
        self._event_devices.clear()

    async def _read_input(self):
        """Async loop to read keyboard input from evdev."""
        if not self._event_devices:
            return

        # Create selector for all devices
        selector = {dev.fd: dev for dev in self._event_devices}

        while not self._shutdown:
            # Wait for input with timeout
            try:
                r, _, _ = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: __import__("select").select(list(selector.keys()), [], [], 0.1),
                )
            except Exception:
                await asyncio.sleep(0.1)
                continue

            for fd in r:
                dev = selector.get(fd)
                if dev is None:
                    continue

                try:
                    for event in dev.read():
                        if event.type == evdev.ecodes.EV_KEY:
                            ev = evdev.categorize(event)
                            if ev.keystate == ev.key_down:
                                await self._handle_key(ev.keycode, ev.scancode)
                except (OSError, BlockingIOError):
                    continue

    async def _handle_key(self, keycode: str | tuple[str, ...], scancode: int):
        """Handle a key press event."""
        moved = False

        # Debug: save keycode info for display
        key_str = keycode if isinstance(keycode, str) else str(keycode)
        self._last_key_debug = f"Last: {key_str[:25]} edit={self._editmode}"

        if self._editmode:
            # In edit mode, map the pressed key to current cursor position
            codes = [keycode] if isinstance(keycode, str) else list(keycode)

            for code in codes:
                mapping = self._mapping.get(code, None)
                if mapping is None:
                    mapping = []

                if self._position not in mapping:
                    self._mapping[code] = [*mapping, self._position]

            await self._advance_key_position()

        else:
            # Navigation mode - normalize keycode to string for comparison
            key = keycode if isinstance(keycode, str) else keycode[0] if keycode else ""
            pos = self._position

            if key == "KEY_UP":
                if pos.y > 0:
                    self._position = Point(pos.y - 1, pos.x)
                    moved = True

            elif key == "KEY_DOWN":
                if pos.y < self._device.Height - 1:
                    self._position = Point(pos.y + 1, pos.x)
                    moved = True

            elif key == "KEY_RIGHT":
                if pos.x < self._device.Width - 1:
                    self._position = Point(pos.y, pos.x + 1)
                    moved = True

            elif key == "KEY_LEFT":
                if pos.x > 0:
                    self._position = Point(pos.y, pos.x - 1)
                    moved = True

            elif key == "KEY_ESC":
                self._shutdown = True
                return

            elif key == "KEY_C":
                self._clear_mappings(self._position)

            elif key == "KEY_W":
                self._write_mappings()
                return

            if moved:
                await self._update_alignment_cursor()

        self._update_display()

    async def _advance_key_position(self):
        """Advance cursor to next position in edit mode."""
        cur_pos = self._position
        moved = False

        if cur_pos.x < self._device.Width - 1:
            self._position = Point(cur_pos.y, cur_pos.x + 1)
            moved = True
        elif cur_pos.y < self._device.Height - 1:
            self._position = Point(cur_pos.y + 1, 0)
            moved = True
        else:
            # Reached end of matrix
            self._editmode = False

        if moved:
            await self._update_alignment_cursor()

    async def _read_mouse(self):
        """Async loop to read curses mouse/key input."""
        while not self._shutdown:
            try:
                event = await asyncio.get_event_loop().run_in_executor(None, self._stdscr.getch)
            except Exception:
                await asyncio.sleep(0.1)
                continue

            if event == -1:
                continue

            if event == curses.KEY_MOUSE:
                # Toggle edit mode on mouse click
                self._editmode = not self._editmode
                self._update_display()

    def _update_display(self):
        """Update the curses display."""
        self._print_header()

        # Show current mapping at cursor
        key_mapping = None
        for key, mapping in self._find_mappings(self._position).items():
            info = f"{key} {mapping!r}"
            if key_mapping is None:
                key_mapping = info
            else:
                key_mapping += f", {info}"

        # Add debug info to bottom bar
        bottom_text = key_mapping or ""
        if self._last_key_debug:
            bottom_text = (
                f"{self._last_key_debug}  |  {bottom_text}" if bottom_text else self._last_key_debug
            )
        self._update_bottombar(bottom_text)

        # Status bar
        status = f"Row: [{self._position.y:2d}]  Col: [{self._position.x:2d}]"

        color = None
        if self._editmode:
            color = self.color_warn
            status += "  (EDIT MODE - press keys to map)"

        self._update_statusbar(status, color)
        self._refresh()

    def _print_header(self):
        """Print help text header."""
        self._stdscr.clear()

        header = (
            "Key Configuration Tool for UChroma\n\n"
            "The Alignment effect shows a repeating color pattern. The white cursor "
            "shows the current matrix position. Use arrow keys to navigate.\n\n"
            "Click mouse to toggle EDIT MODE. In edit mode, press any key to map it "
            "to the current cursor position. Multiple cells can be assigned to one key.\n\n"
            "Controls: Arrows=Move, W=Write, C=Clear, ESC=Exit, Mouse=Toggle Edit\n"
        )

        row = 1
        for text in textwrap.wrap(header, curses.COLS - 4):
            self._stdscr.addstr(row, 2, text)
            row += 1

    def _update_statusbar(self, status: str, color=None):
        """Update the status bar at top."""
        if color is None:
            color = self.color_status

        # Calculate available space for status (leave room for tag and padding)
        max_width = max(1, curses.COLS - 1)
        tag_len = len(self.STATUS_TAG) + 2  # " TAG "
        max_status = max(0, max_width - tag_len - 2)  # " status "
        status = status[:max_status]

        padding_len = max(0, max_width - len(status) - tag_len - 1)
        line = f" {status}{' ' * padding_len}{self.STATUS_TAG} "

        # Truncate to screen width to avoid curses error
        with contextlib.suppress(curses.error):
            self._stdscr.addnstr(0, 0, line, max_width, color)

    def _update_bottombar(self, status: str | None, color=None):
        """Update the bottom bar."""
        if color is None:
            color = self.color_status

        if status is None:
            status = ""

        # Truncate status to fit screen
        max_width = max(1, curses.COLS - 1)
        max_status = max(0, max_width - 2)  # " status "
        status = status[:max_status]

        padding_len = max(0, max_width - len(status) - 2)
        line = f" {status}{' ' * padding_len} "

        # Use addnstr with explicit max length to avoid curses error
        with contextlib.suppress(curses.error):
            self._stdscr.addnstr(curses.LINES - 1, 0, line, max_width, color)

    def _refresh(self):
        """Refresh the screen."""
        self._stdscr.refresh()

    @property
    def color_warn(self):
        return curses.color_pair(2) | curses.A_BOLD

    @property
    def color_status(self):
        return curses.color_pair(3) | curses.A_BOLD

    @property
    def color_action(self):
        return curses.color_pair(4) | curses.A_BOLD

    def start(self, stdscr, *args, **kwargs):
        """Main entry point for curses wrapper."""
        self._stdscr = stdscr
        curses.mousemask(1)
        curses.use_default_colors()

        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_GREEN)

        self._stdscr.timeout(100)

        # Set up the alignment effect (sync, before event loop)
        if not self._setup_alignment_effect():
            self._stdscr.addstr(curses.LINES // 2, 2, "ERROR: Failed to set up Alignment effect!")
            self._stdscr.addstr(
                curses.LINES // 2 + 1, 2, "Make sure the daemon is running and responsive."
            )
            self._stdscr.refresh()
            self._stdscr.getch()
            return self._mapping

        # Initial cursor update - retry a few times in case of race condition
        for attempt in range(5):
            try:
                self._device.SetLayerTraits(0, {"cur_row": 0, "cur_col": 0})
                break
            except Exception as e:
                if attempt < 4:
                    time.sleep(0.1)  # Wait for layer to be registered
                else:
                    self._last_key_debug = f"Initial cursor err: {str(e)[:30]}"

        self._update_display()

        # Open input devices
        if not self._open_input_devices():
            self._stdscr.addstr(curses.LINES // 2, 2, "ERROR: Could not open any input devices!")
            self._stdscr.addstr(
                curses.LINES // 2 + 1, 2, "Make sure you have permission to access /dev/input/*"
            )
            self._stdscr.refresh()
            self._stdscr.getch()
            return self._mapping

        # Run the async event loops
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._async_main())
        except KeyboardInterrupt:
            pass
        finally:
            self._close_input_devices()
            loop.close()

        return self._mapping

    async def _async_main(self):
        """Async main loop - sets up D-Bus and runs input handlers."""
        # Set up async D-Bus connection for cursor updates during event loop
        await self._async_setup()

        # Show connection status
        if self._stdscr:
            if self._async_anim_iface is None:
                self._stdscr.addstr(
                    curses.LINES // 2,
                    2,
                    "ERROR: Failed to connect async D-Bus - cursor won't update",
                )
                self._stdscr.refresh()
            else:
                self._update_display()

        try:
            await asyncio.gather(
                self._read_input(),
                self._read_mouse(),
            )
        finally:
            await self._async_cleanup()

    @staticmethod
    def run(device: "DeviceProxy", config_file: str | None = None):
        """Run the key config tool."""
        tool = KeyConfigTool(device, config_file)

        # Save and restore SIGTSTP handler
        sigtstp = signal.getsignal(signal.SIGTSTP)
        try:
            curses.wrapper(tool.start)
        finally:
            signal.signal(signal.SIGTSTP, sigtstp)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Key configuration tool for UChroma",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "device",
        nargs="?",
        help="Device identifier (index, vendor:product, or path)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        metavar="FILE",
        help="Configuration file to use",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List available devices",
    )

    args = parser.parse_args()

    # Connect to D-Bus
    client = UChromaClient()

    try:
        paths = client.get_device_paths()
    except Exception as e:
        print(f"Error: Could not connect to uchromad: {e}", file=sys.stderr)
        print("Make sure the daemon is running (uchromad or 'make server')", file=sys.stderr)
        sys.exit(1)

    if not paths:
        print("No devices found.", file=sys.stderr)
        sys.exit(1)

    # List devices if requested
    if args.list:
        print("Available devices:")
        for i, path in enumerate(paths):
            device = client.get_device(path)
            print(f"  [{i}] {device.Key}: {device.Name}")
        sys.exit(0)

    # Get device
    identifier = args.device
    if identifier is None:
        # Use first keyboard-type device, or first device
        for path in paths:
            device = client.get_device(path)
            if device.DeviceType.lower() == "keyboard":
                break
        else:
            device = client.get_device(paths[0])
    else:
        device = client.get_device(identifier)

    if device is None:
        print(f"Error: Device '{identifier}' not found.", file=sys.stderr)
        print("Use -l to list available devices.", file=sys.stderr)
        sys.exit(1)

    if not device.HasMatrix:
        print(f"Error: Device '{device.Name}' does not have an LED matrix.", file=sys.stderr)
        sys.exit(1)

    print(f"Using device: {device.Name} ({device.Key})")
    print(f"Matrix size: {device.Width}x{device.Height}")

    KeyConfigTool.run(device, args.file)


if __name__ == "__main__":
    main()
