# Profile Management

Save and restore complete device configurations including brightness, effects, LED states, and
animation layers.

## profile

Manage device presets that capture the full lighting state.

### Synopsis

```
uchroma profile <command> [args]
uchroma preset <command> [args]
uchroma prof <command> [args]
```

### Commands

| Command  | Aliases        | Description               |
| -------- | -------------- | ------------------------- |
| `list`   | `ls`           | List saved profiles       |
| `save`   | -              | Save current device state |
| `load`   | `apply`        | Apply a saved profile     |
| `show`   | `cat`          | Display profile contents  |
| `delete` | `rm`, `remove` | Delete a profile          |

---

## Listing Profiles

Show all saved profiles.

```bash
$ uchroma profile list

 Saved Profiles:

  gaming            Razer BlackWidow V3 (2024-01-15 14:30)
  work              Razer BlackWidow V3 (2024-01-14 09:00)
  night             Razer BlackWidow V3 (2024-01-10 22:15)
```

If no profiles exist:

```bash
$ uchroma profile list

 Saved Profiles:

  No profiles saved yet

  Save one with: uchroma profile save <name>
```

---

## Saving Profiles

Capture the current device state as a named profile.

### Synopsis

```
uchroma profile save <name> [options]
```

### Options

| Option    | Short | Description                |
| --------- | ----- | -------------------------- |
| `--force` | `-f`  | Overwrite existing profile |

### Examples

```bash
# Save current state as "gaming"
$ uchroma profile save gaming
Saved profile: gaming
  ~/.config/uchroma/profiles/gaming.json

# Overwrite existing profile
$ uchroma profile save gaming --force
Saved profile: gaming
  ~/.config/uchroma/profiles/gaming.json
```

### What Gets Saved

- Device name and type
- Serial number (for device matching)
- Brightness level
- Current hardware effect and its parameters
- LED states (logo, scroll wheel, etc.)
- Active animation layers and their settings

---

## Loading Profiles

Apply a saved profile to a device.

### Synopsis

```
uchroma profile load <name>
uchroma profile apply <name>
```

### Examples

```bash
# Load the "gaming" profile
$ uchroma profile load gaming
Loaded profile: gaming

# Load with specific device
$ uchroma -d blackwidow_v3 profile load work
Loaded profile: work
```

### Partial Loading

If some settings cannot be applied (e.g., effect not available on device), a warning is shown but
other settings are still applied:

```bash
$ uchroma profile load gaming
Loaded profile with 1 warning(s)
  fx: Effect 'spectrum' not available on this device
```

---

## Viewing Profile Contents

Display the contents of a saved profile without applying it.

### Synopsis

```
uchroma profile show <name>
uchroma profile cat <name>
```

### Example

```bash
$ uchroma profile show gaming

 Profile: gaming

  device_name    Razer BlackWidow V3
  device_type    keyboard
  serial         XX1234567890
  created        2024-01-15 14:30:00

  brightness     ████████████████████ 100%
  effect         spectrum
  leds           backlight, logo
  layers         plasma, aurora

  File: ~/.config/uchroma/profiles/gaming.json
```

---

## Deleting Profiles

Remove a saved profile.

### Synopsis

```
uchroma profile delete <name>
uchroma profile rm <name>
uchroma profile remove <name>
```

### Example

```bash
$ uchroma profile delete old_profile
Deleted profile: old_profile
```

---

## Profile Storage

Profiles are stored as JSON files in:

```
~/.config/uchroma/profiles/
```

Each profile is a separate file named `<profile-name>.json`.

### Profile Format

```json
{
  "created": "2024-01-15T14:30:00",
  "device_name": "Razer BlackWidow V3",
  "device_type": "keyboard",
  "serial": "XX1234567890",
  "brightness": 100,
  "fx": "spectrum",
  "fx_args": {},
  "leds": {
    "logo": {
      "state": "on",
      "color": "#00ff00"
    }
  },
  "layers": [
    {
      "renderer": "uchroma.fxlib.plasma.Plasma",
      "zindex": 0,
      "args": {
        "preset": "Rainbow"
      }
    }
  ]
}
```

---

## Use Cases

### Gaming Setup

```bash
# Set up your gaming lighting
uchroma brightness 100
uchroma fx disable
uchroma anim add plasma --preset Rainbow
uchroma profile save gaming

# Later, restore it
uchroma profile load gaming
```

### Work Mode

```bash
# Subtle lighting for work
uchroma brightness 30
uchroma fx static --color "#ffffff"
uchroma profile save work
```

### Night Mode

```bash
# Dim lighting for night
uchroma brightness 10
uchroma fx static --color "#ff3300"
uchroma profile save night
```

### Scripting with Profiles

```bash
#!/bin/bash
# Switch profiles based on time of day

hour=$(date +%H)

if [ "$hour" -ge 22 ] || [ "$hour" -lt 6 ]; then
    uchroma profile load night
elif [ "$hour" -ge 9 ] && [ "$hour" -lt 18 ]; then
    uchroma profile load work
else
    uchroma profile load gaming
fi
```

---

## Related Commands

- [`brightness`](brightness.md) - Brightness control
- [`fx`](effects.md) - Hardware effects
- [`anim`](animations.md) - Animation layers
- [`led`](advanced.md#led) - LED configuration
