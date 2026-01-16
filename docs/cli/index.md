# CLI Reference

The `uchroma` command-line interface provides full control over Razer Chroma devices from your
terminal.

## Installation

The CLI is included with uchroma. After installing uchroma, the `uchroma` command is available
system-wide.

```bash
# Verify installation
uchroma --help
```

## Usage Pattern

```
uchroma [global options] <command> [command options]
```

### Global Options

| Option            | Short | Description                                                   |
| ----------------- | ----- | ------------------------------------------------------------- |
| `--help`          | `-h`  | Show help message and exit                                    |
| `--device <SPEC>` | `-d`  | Select a specific device by index, key, serial, or D-Bus path |

### Device Selection

When multiple devices are connected, use `-d` to target a specific one:

```bash
# By index (shown in `uchroma list`)
uchroma -d 0 brightness 80

# By device key
uchroma -d blackwidow_v3 fx spectrum

# By serial number
uchroma -d XX1234567890 brightness 100

# By D-Bus path
uchroma -d /io/uchroma/device/0 fx static --color red
```

If only one device is connected, it is selected automatically.

## Command Categories

### Device Information

| Command                   | Aliases         | Description                          |
| ------------------------- | --------------- | ------------------------------------ |
| [`list`](devices.md)      | `ls`, `devices` | List connected devices               |
| [`dump`](devices.md#dump) | `debug`, `info` | Show detailed device and system info |

### Lighting Control

| Command                        | Aliases           | Description                                  |
| ------------------------------ | ----------------- | -------------------------------------------- |
| [`brightness`](brightness.md)  | `bright`, `br`    | Get or set device brightness                 |
| [`fx`](effects.md)             | `effect`          | Apply hardware lighting effects              |
| [`led`](advanced.md#led)       | -                 | Control standalone LEDs (logo, scroll wheel) |
| [`matrix`](advanced.md#matrix) | `pixels`, `frame` | LED matrix information and direct control    |

### Animation System

| Command                      | Aliases              | Description                    |
| ---------------------------- | -------------------- | ------------------------------ |
| [`anim`](animations.md)      | `animation`, `layer` | Manage custom animation layers |
| [`input`](advanced.md#input) | `react`, `reactive`  | Configure reactive key effects |

### Device Management

| Command                       | Aliases           | Description                         |
| ----------------------------- | ----------------- | ----------------------------------- |
| [`profile`](profiles.md)      | `preset`, `prof`  | Save and load device presets        |
| [`power`](power.md)           | `fan`, `boost`    | System control for laptops          |
| [`battery`](power.md#battery) | `bat`, `wireless` | Battery status for wireless devices |
| [`watch`](advanced.md#watch)  | `monitor`, `live` | Live monitoring of device status    |

## Quick Examples

```bash
# List all connected devices
uchroma list

# Set brightness to 75%
uchroma brightness 75

# Apply a spectrum cycling effect
uchroma fx spectrum

# Apply static color
uchroma fx static --color "#ff0088"

# Add a plasma animation layer
uchroma anim add plasma

# Save current settings as a profile
uchroma profile save gaming

# Monitor fan speed in real-time (laptops)
uchroma watch --fan
```

## Exit Codes

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| 0    | Success                                                       |
| 1    | Error (device not found, invalid arguments, operation failed) |

## Environment Variables

| Variable            | Description                                                 |
| ------------------- | ----------------------------------------------------------- |
| `UCHROMA_LOG_LEVEL` | Set logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `NO_COLOR`          | Disable colored output when set                             |

## See Also

- [Device Commands](devices.md) - Listing and inspecting devices
- [Brightness Control](brightness.md) - Brightness management
- [Hardware Effects](effects.md) - Built-in lighting effects
- [Custom Animations](animations.md) - Animation layer system
- [Profiles](profiles.md) - Saving and loading configurations
- [Power Management](power.md) - Laptop-specific features
- [Advanced Commands](advanced.md) - LED, matrix, input, and monitoring
