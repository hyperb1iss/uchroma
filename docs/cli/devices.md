# Device Commands

Commands for listing and inspecting connected Razer devices.

## list

List all connected Razer Chroma devices.

### Synopsis

```
uchroma list [options]
uchroma ls [options]
uchroma devices [options]
```

### Options

| Option    | Short | Description                                     |
| --------- | ----- | ----------------------------------------------- |
| `--all`   | `-a`  | Show all details (serial, firmware, brightness) |
| `--quiet` | `-q`  | Only show device keys (for scripting)           |

### Examples

**Basic listing:**

```bash
$ uchroma list

Devices (2)

[0] Razer BlackWidow V3  keyboard  blackwidow_v3
[1] Razer DeathAdder V2  mouse     deathadder_v2
```

**Detailed listing:**

```bash
$ uchroma list --all

Devices (2)

[0] Razer BlackWidow V3  keyboard  blackwidow_v3
     serial: XX1234567890
     firmware: v1.03
     brightness: 100%

[1] Razer DeathAdder V2  mouse     deathadder_v2
     serial: PM2034567890
     firmware: v1.00
     brightness: 80%
```

**Script-friendly output:**

```bash
$ uchroma list --quiet
blackwidow_v3
deathadder_v2
```

### Output Fields

| Field | Description                                                      |
| ----- | ---------------------------------------------------------------- |
| Index | Numeric index for device selection (e.g., `[0]`)                 |
| Name  | Full device name                                                 |
| Type  | Device type (keyboard, mouse, mousepad, headset, keypad, laptop) |
| Key   | Short identifier for device selection                            |

---

## dump

Display detailed debug information about devices and the system.

### Synopsis

```
uchroma dump [what] [options]
uchroma debug [what] [options]
uchroma info [what] [options]
```

### Arguments

| Argument | Description                                             | Default |
| -------- | ------------------------------------------------------- | ------- |
| `what`   | What to dump: `device`, `hardware`, `version`, or `all` | `all`   |

### Options

| Option   | Description                                 |
| -------- | ------------------------------------------- |
| `--json` | Output as JSON for programmatic consumption |

### Examples

**Full debug dump:**

```bash
$ uchroma dump

Version

  uchroma: 0.10.0
  python: 3.11.4
  traitlets: 5.14.0
  coloraide: 3.2.0

Device

  Razer BlackWidow V3

    type: keyboard
    key: blackwidow_v3
    serial: XX1234567890
    firmware: v1.03
    manufacturer: Razer
    usb: 1532:024e
    matrix: 6x22
    brightness: 100%
    leds: backlight, logo
    effects: breath_dual, breath_random, breath_single, reactive, ...
    renderers: aurora, comets, copper_bars, embers, kaleidoscope, ...
    current_fx: spectrum

Hardware Database

  keyboard: 45
  mouse: 32
  mousepad: 8
  headset: 12
  keypad: 4
  laptop: 6
```

**Version info only:**

```bash
$ uchroma dump version

Version

  uchroma: 0.10.0
  python: 3.11.4
  traitlets: 5.14.0
  coloraide: 3.2.0
```

**Specific device info:**

```bash
$ uchroma -d blackwidow_v3 dump device

Device

  Razer BlackWidow V3

    type: keyboard
    key: blackwidow_v3
    serial: XX1234567890
    ...
```

**JSON output:**

```bash
$ uchroma dump --json
{
  "version": {
    "uchroma": "0.10.0",
    "python": "3.11.4"
  }
}
```

### Device Information Fields

| Field                     | Description                                       |
| ------------------------- | ------------------------------------------------- |
| `type`                    | Device type (keyboard, mouse, etc.)               |
| `key`                     | Short device identifier                           |
| `serial`                  | Device serial number                              |
| `firmware`                | Firmware version                                  |
| `manufacturer`            | Device manufacturer                               |
| `usb`                     | USB vendor:product ID                             |
| `matrix`                  | LED matrix dimensions (rows x columns)            |
| `brightness`              | Current brightness percentage                     |
| `leds`                    | Supported standalone LEDs                         |
| `effects`                 | Available hardware effects                        |
| `renderers`               | Available animation renderers                     |
| `current_fx`              | Currently active effect                           |
| `wireless`                | Whether device is wireless                        |
| `battery`                 | Battery level and charging status (wireless only) |
| `system_control`          | Whether system control is available (laptops)     |
| `power_mode`              | Current power mode (laptops)                      |
| `fan_rpm`                 | Fan speeds (laptops)                              |
| `cpu_boost` / `gpu_boost` | Boost levels (laptops)                            |

### Hardware Database

The hardware database section shows the count of supported devices by type. This reflects the device
configurations bundled with uchroma, not currently connected devices.
