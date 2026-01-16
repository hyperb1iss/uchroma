# Brightness Control

Control the brightness of device LEDs.

## brightness

Get or set the overall brightness level of a device or specific LED.

### Synopsis

```
uchroma brightness [PERCENT] [options]
uchroma bright [PERCENT] [options]
uchroma br [PERCENT] [options]
```

### Arguments

| Argument  | Description                                               |
| --------- | --------------------------------------------------------- |
| `PERCENT` | Brightness level 0-100. Omit to query current brightness. |

### Options

| Option       | Description                                         |
| ------------ | --------------------------------------------------- |
| `--led NAME` | Target a specific LED instead of overall brightness |

### Supported LEDs

The available LEDs depend on your device. Common options include:

| LED Name    | Description             |
| ----------- | ----------------------- |
| `backlight` | Main keyboard backlight |
| `logo`      | Razer logo LED          |
| `scroll`    | Scroll wheel LED (mice) |
| `underglow` | Underglow lighting      |
| `side`      | Side lighting strips    |

Use `uchroma dump device` to see which LEDs your device supports.

### Examples

**Query current brightness:**

```bash
$ uchroma brightness
Razer BlackWidow V3: 100%
```

**Set brightness to 75%:**

```bash
$ uchroma brightness 75
Razer BlackWidow V3 brightness set to 75%
```

**Set brightness to minimum:**

```bash
$ uchroma brightness 0
Razer BlackWidow V3 brightness set to 0%
```

**Set brightness to maximum:**

```bash
$ uchroma brightness 100
Razer BlackWidow V3 brightness set to 100%
```

**Query logo LED brightness:**

```bash
$ uchroma brightness --led logo
Razer BlackWidow V3 logo: 50%
```

**Set logo LED brightness:**

```bash
$ uchroma brightness 30 --led logo
Razer BlackWidow V3 logo brightness set to 30%
```

**Target specific device:**

```bash
$ uchroma -d deathadder_v2 brightness 80
Razer DeathAdder V2 brightness set to 80%
```

### Notes

- Brightness changes take effect immediately
- Setting brightness to 0 does not turn off the device, just dims the LEDs
- Some devices have separate brightness controls for different LED zones
- Brightness settings are typically saved by the device and persist across reboots
- Use [profiles](profiles.md) to save and restore brightness along with other settings

### Scripting Example

```bash
#!/bin/bash
# Dim all devices to 50% for night mode

for device in $(uchroma list --quiet); do
    uchroma -d "$device" brightness 50
done
```

### Related Commands

- [`led`](advanced.md#led) - Full LED configuration (color, effect, state)
- [`profile`](profiles.md) - Save brightness as part of a profile
