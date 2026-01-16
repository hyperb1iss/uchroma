# Configuration

UChroma stores preferences and profiles in `~/.config/uchroma/`.

## Directory Structure

```
~/.config/uchroma/
├── preferences.yaml     # Auto-saved device preferences
└── profiles/
    ├── gaming.json      # Saved profile
    ├── work.json        # Another profile
    └── ...
```

## Preferences File

The daemon automatically saves device state to `~/.config/uchroma/preferences.yaml`. This happens
whenever settings change—brightness, effects, LED states.

Example:

```yaml
!preferences
last_updated: 1705432800.123
serial: PM2142XXXXXX
brightness: 80.0
fx: wave
fx_args: !omap
  - direction: right
leds:
  logo:
    color: !color '#ff00ff'
    brightness: 100
```

**You don't need to edit this file manually.** The daemon manages it. But if you want to reset to
defaults, just delete it.

### Hierarchical Preferences

Preferences are keyed by device serial number. If you have multiple devices, each gets its own
section. The daemon looks up preferences by serial when a device connects and restores the saved
state.

## Profiles

Profiles are manual snapshots of device state that you save and load explicitly.

### Save a Profile

```bash
uchroma profile save myprofile
```

Creates `~/.config/uchroma/profiles/myprofile.json`:

```json
{
  "created": "2024-01-16T12:00:00.000000",
  "device_name": "Razer BlackWidow V3",
  "device_type": "KEYBOARD",
  "serial": "PM2142XXXXXX",
  "brightness": 80,
  "fx": "wave",
  "fx_args": {
    "direction": "right"
  },
  "leds": {
    "logo": {
      "color": "#ff00ff",
      "brightness": 100
    }
  },
  "layers": [
    {
      "renderer": "uchroma.fxlib.plasma.Plasma",
      "zindex": 0,
      "args": {
        "gradient_length": 360
      }
    }
  ]
}
```

### Load a Profile

```bash
uchroma profile load myprofile
```

Applies all saved settings to the current device.

### List Profiles

```bash
uchroma profile list
```

```
 Saved Profiles:

          gaming │ Razer BlackWidow V3 (2024-01-15 20:30)
            work │ Razer BlackWidow V3 (2024-01-16 09:00)
```

### Show Profile Contents

```bash
uchroma profile show gaming
```

### Delete a Profile

```bash
uchroma profile delete gaming
```

## Profile Portability

Profiles store the device serial number but will attempt to load on any compatible device. The `fx`
and `leds` sections apply based on what the target device supports—unsupported features are skipped
with warnings.

## Environment Variables

| Variable                           | Default             | Description                                            |
| ---------------------------------- | ------------------- | ------------------------------------------------------ |
| `UCHROMA_LOG_LEVEL`                | `INFO`              | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `UCHROMA_CONFIG_DIR`               | `~/.config/uchroma` | Override config directory location                     |
| `UCHROMA_GTK_DEBUG`                | unset               | Enable GTK-specific debug output                       |
| `UCHROMA_LIVE_PREVIEW_FPS`         | `4`                 | GTK live preview frame rate (1-25)                     |
| `UCHROMA_LIVE_PREVIEW_INTERVAL_MS` | `250`               | Alternative to FPS: interval in ms                     |

### Debug Logging

Enable full debug output:

```bash
UCHROMA_LOG_LEVEL=DEBUG uchromad
```

This shows USB HID communication, D-Bus messages, and internal state changes.

### GTK Debug

Extra output for the GTK frontend:

```bash
UCHROMA_GTK_DEBUG=1 uchroma-gtk
```

Shows renderer loading, D-Bus calls, and UI state transitions.

## Device Data Files

Device definitions live in the package at `uchroma/server/data/`:

```
keyboard.yaml   # Keyboard models
mouse.yaml      # Mice
mousepad.yaml   # Mousepads
headset.yaml    # Headsets
laptop.yaml     # Blade laptops
keypad.yaml     # Keypads
```

These YAML files define:

- Vendor/product IDs
- Matrix dimensions
- Supported LEDs
- Key mappings
- Device quirks

**To add a new device**, create an entry in the appropriate file. See existing entries for the
format.

Example keyboard entry:

```yaml
!device-config
name: Razer BlackWidow V3
manufacturer: Razer
type: KEYBOARD
vendor_id: 0x1532
product_id: 0x024e
dimensions: [6, 22]
supported_leds:
  - backlight
  - logo
key_mapping: !!omap
  - KEY_ESC: [[0, 1]]
  - KEY_F1: [[0, 3]]
  # ...
```

## Systemd Integration

If using systemd, you can pass environment variables in the service file:

```ini
[Service]
Environment="UCHROMA_LOG_LEVEL=DEBUG"
ExecStart=/usr/bin/uchromad
```

Or use an environment file:

```ini
[Service]
EnvironmentFile=%h/.config/uchroma/env
ExecStart=/usr/bin/uchromad
```

With `~/.config/uchroma/env`:

```bash
UCHROMA_LOG_LEVEL=DEBUG
```

## Reset Everything

To reset all UChroma configuration:

```bash
rm -rf ~/.config/uchroma
```

The daemon will recreate the directory with fresh defaults on next run.
