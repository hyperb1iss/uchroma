# Quick Start

This guide walks you through basic UChroma usage. Make sure you've completed
[installation](installation.md) first.

## Start the Daemon

The daemon must be running for any commands to work:

```bash
uchromad
```

Leave it running in a terminal, or use systemd for background operation.

## List Devices

```bash
uchroma devices
```

Output:

```
[0]: Razer BlackWidow V3 (PM2142XXXXXX / v1.03)
```

The number in brackets is the device index. Use it to target specific devices with `-d 0`.

## Set Brightness

Query current brightness:

```bash
uchroma brightness
```

```
Razer BlackWidow V3: 100%
```

Set brightness (0-100):

```bash
uchroma brightness 80
```

```
Razer BlackWidow V3 brightness set to 80%
```

## Hardware Effects

List available effects:

```bash
uchroma fx list
```

Apply an effect:

```bash
uchroma fx wave
```

```
Effect: wave
```

Effects with parameters:

```bash
uchroma fx static --color red
uchroma fx reactive --color skyblue --speed 2
uchroma fx breathe --colors "purple,cyan"
uchroma fx starlight --colors "gold,white" --speed 3
```

Turn off all effects:

```bash
uchroma fx disable
```

## Custom Animations

Custom animations use software renderers that draw frames and send them to the device. You can stack
multiple layers with blend modes.

### List Renderers

```bash
uchroma anim list
```

```
Available renderers and arguments:

         plasma │ Colorful moving blobs of plasma
────────────────┼─────────────────────────────────
          author│ Stefanie Jane
         version│ v1.0
────────────────┼─────────────────────────────────
    color_scheme│ colors: default: ['#ff00ff', '#00ffff', ...]
 gradient_length│ int: min: 0, default: 360

         rainbow │ Flowing rainbow gradient
...
```

### Add a Layer

```bash
uchroma anim add plasma
```

```
Created layer 0: Plasma
```

Add more layers:

```bash
uchroma anim add rainbow
```

```
Created layer 1: Rainbow
```

### View Active Layers

```bash
uchroma anim show
```

```
 Active Layers (2)

  [0] Plasma
      Colorful moving blobs of plasma
      │ blend_mode: normal · opacity: 1.0

  [1] Rainbow
      Flowing rainbow gradient
      │ blend_mode: normal · opacity: 1.0
```

### Modify a Layer

Change parameters on an active layer:

```bash
uchroma anim set 0 --gradient-length 180
```

```
Updated layer 0
```

### Remove a Layer

```bash
uchroma anim rm 1
```

```
Removed layer 1
```

### Pause/Resume

```bash
uchroma anim pause
```

```
Animation paused
```

Run again to resume.

### Stop All

```bash
uchroma anim stop
```

```
Animation stopped
```

## Profiles

Save your current setup for later:

```bash
uchroma profile save gaming
```

```
Saved profile: gaming
  ~/.config/uchroma/profiles/gaming.json
```

List saved profiles:

```bash
uchroma profile list
```

Load a profile:

```bash
uchroma profile load gaming
```

## Multiple Devices

Target a specific device by index:

```bash
uchroma -d 0 brightness 100
uchroma -d 1 fx spectrum
```

Or by name (partial match):

```bash
uchroma -d blackwidow fx wave
uchroma -d deathadder brightness 50
```

## Launch the GTK App

For a visual interface:

```bash
uchroma-gtk
```

Or via make:

```bash
make gtk
```

See [GTK App Guide](gtk-app.md) for details.

## Debug Output

For troubleshooting, dump full device info:

```bash
uchroma dump
```

Enable debug logging:

```bash
UCHROMA_LOG_LEVEL=DEBUG uchromad
```

## Command Reference

| Command                          | Description            |
| -------------------------------- | ---------------------- |
| `uchroma devices`                | List connected devices |
| `uchroma brightness [VALUE]`     | Get/set brightness     |
| `uchroma fx <effect>`            | Apply hardware effect  |
| `uchroma fx list`                | List available effects |
| `uchroma anim add <renderer>`    | Add animation layer    |
| `uchroma anim show`              | Show active layers     |
| `uchroma anim set <N> [OPTIONS]` | Modify layer N         |
| `uchroma anim rm <N>`            | Remove layer N         |
| `uchroma anim pause`             | Toggle pause           |
| `uchroma anim stop`              | Stop all animations    |
| `uchroma profile save <name>`    | Save current state     |
| `uchroma profile load <name>`    | Restore saved state    |
| `uchroma dump`                   | Full device dump       |

All commands support `-d <device>` to target specific devices.

## Next Steps

- [GTK App Guide](gtk-app.md) — Visual interface walkthrough
- [Configuration](configuration.md) — Preferences and environment variables
- [Troubleshooting](troubleshooting.md) — Common issues
