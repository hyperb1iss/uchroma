# Troubleshooting

Common issues and how to fix them.

## Device Not Detected

### Check USB Connection

```bash
lsusb | grep -i razer
```

Expected output:

```
Bus 001 Device 005: ID 1532:024e Razer USA, Ltd BlackWidow V3
```

If nothing appears, check your cable and USB port.

### Verify Udev Rules

```bash
ls -la /etc/udev/rules.d/*uchroma*
```

If missing, create `/etc/udev/rules.d/70-uchroma.rules`:

```udev
ACTION=="add|change", SUBSYSTEM=="usb", ATTR{idVendor}=="1532", TAG+="uchroma"
ACTION=="add|change", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1532", TAG+="uaccess", TAG+="uchroma"
ACTION=="add|change", SUBSYSTEM=="input", ATTRS{idVendor}=="1532", TAG+="uaccess"
```

Reload rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Unplug and replug your device** after changing udev rules.

### Check Permissions

```bash
ls -la /dev/hidraw*
```

Your user should have read/write access. The `uaccess` tag handles this automatically on systemd
systems. If not working:

```bash
# Check if your user is in the input group
groups

# Add yourself if needed
sudo usermod -aG input $USER
# Then log out and back in
```

### HID Device in Use

Another driver might be claiming the device. Check:

```bash
cat /sys/class/hidraw/hidraw*/device/uevent | grep -A5 1532
```

If a kernel driver is bound, you may need to unbind it or blacklist it.

## Daemon Won't Start

### Check D-Bus

```bash
busctl --user list | grep uchroma
```

If the daemon is running, you'll see:

```
io.uchroma    12345 uchromad ...
```

### Port Already in Use

```
Failed to acquire D-Bus name: io.uchroma
```

Another instance is running. Kill it:

```bash
pkill uchromad
```

Or find the process:

```bash
pgrep -a uchromad
```

### Missing Dependencies

```
ModuleNotFoundError: No module named 'dbus_fast'
```

Install dependencies:

```bash
uv pip install uchroma
# or
pip install uchroma
```

### HIDAPI Errors

```
OSError: Unable to open device
```

The hidapi library can't open the device. This is usually a permissions issue—see "Check
Permissions" above.

Also verify hidapi is installed:

```bash
python -c "import hid; print(hid.enumerate())"
```

## Effects Not Working

### Daemon Not Running

```bash
uchroma fx wave
```

```
Error: Could not connect to daemon
```

Start the daemon:

```bash
uchromad
```

### Effect Not Supported

```
Effect 'ripple' not supported on this device
```

Not all effects work on all devices. Some are keyboard-only, some require specific hardware. Use
`uchroma fx list` to see what's available for your device.

### Custom Animation Not Displaying

If `uchroma anim add plasma` succeeds but nothing shows:

1. Check the daemon logs for errors
2. Verify the device supports custom frames:
   ```bash
   uchroma dump | grep -i frame
   ```
3. Some older devices don't support the custom frame protocol

## GTK App Issues

### App Won't Launch

```
Gtk-WARNING: cannot open display
```

You need a running display server. On Wayland:

```bash
GDK_BACKEND=wayland uchroma-gtk
```

On X11:

```bash
GDK_BACKEND=x11 uchroma-gtk
```

### "Daemon Not Running" Dialog

The GTK app can't connect to D-Bus. Start the daemon first:

```bash
uchromad &
uchroma-gtk
```

### Preview Not Updating

The preview might be paused. Check if animation is running:

```bash
uchroma anim show
```

If in hardware mode, the preview shows a simulated effect—it won't match hardware exactly.

### Missing GTK Dependencies

```
ValueError: Namespace Gtk not available
```

Install GTK4 bindings:

```bash
# Debian/Ubuntu
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1

# Fedora
sudo dnf install python3-gobject gtk4 libadwaita

# Arch
sudo pacman -S python-gobject gtk4 libadwaita
```

## Debug Logging

### Enable Debug Mode

```bash
UCHROMA_LOG_LEVEL=DEBUG uchromad
```

This shows:

- USB HID report contents
- D-Bus method calls
- Device initialization steps
- Animation frame timing

### GTK Debug

```bash
UCHROMA_GTK_DEBUG=1 uchroma-gtk
```

Shows renderer loading, D-Bus responses, and UI state.

### Full Trace

For maximum verbosity:

```bash
UCHROMA_LOG_LEVEL=DEBUG python -u -m uchroma.server.server 2>&1 | tee uchroma.log
```

Share `uchroma.log` when reporting issues.

## Device-Specific Issues

### Blade Laptops

Blade laptops have additional quirks:

- **System control** requires root for some operations
- **Per-key RGB** might need firmware updates
- **Sleep/wake** can reset lighting—use systemd hooks to restore

### Wireless Devices

Wireless mice/keyboards have limited bandwidth:

- Animation frame rates may be lower
- Some features only work when wired
- Battery status shown via `uchroma battery`

### Multi-Device Setups

When controlling multiple devices:

```bash
uchroma -d 0 fx wave
uchroma -d 1 fx spectrum
```

Or target by name:

```bash
uchroma -d blackwidow fx wave
uchroma -d deathadder fx spectrum
```

## Known Limitations

### Hardware Effect Limitations

- Effects run on device firmware—parameters are limited
- Some combinations aren't possible (e.g., reactive + wave simultaneously)
- Color accuracy varies by hardware

### Custom Animation Limitations

- Maximum ~30 FPS due to USB bandwidth
- High CPU usage with many layers
- Some devices don't support custom frames

### Protocol Variations

Razer devices use different protocols by generation. Newer devices use "extended" commands. UChroma
auto-detects this, but some features may vary.

## Getting Help

### Check Existing Issues

[GitHub Issues](https://github.com/hyperbliss/uchroma/issues)

### Report a Bug

Include:

1. Device model and `uchroma dump` output
2. UChroma version (`uchroma --version`)
3. OS/distro and kernel version
4. Debug log output
5. Steps to reproduce

### Device Support Request

If your Razer device isn't detected:

1. Get the USB ID: `lsusb | grep -i razer`
2. Check if it's listed in `uchroma/server/data/*.yaml`
3. Open an issue with the USB ID and device name

Adding new devices is usually straightforward—just need the product ID and matrix dimensions.
