# Advanced Commands

Lower-level commands for LED control, matrix manipulation, reactive effects, and monitoring.

## led

Control standalone LEDs like logo lights, scroll wheels, and underglow.

### Synopsis

```
uchroma led [options]
uchroma led <led-name> [led-options]
```

### Options

| Option   | Short | Description                              |
| -------- | ----- | ---------------------------------------- |
| `--list` | `-l`  | List available LEDs and their properties |

### Listing LEDs

```bash
$ uchroma led --list

 Standalone LED control:

logo                           LED: Logo
───────────────────────────────────────────────────────────
state                          on
(bool)                         bool: default: true
───────────────────────────────────────────────────────────
color                          #00ff00
(color)                        color: default: #00ff00
───────────────────────────────────────────────────────────
brightness                     100
(int)                          int: min: 0, max: 100, default: 100

scroll                         LED: Scroll
───────────────────────────────────────────────────────────
state                          on
(bool)                         bool: default: true
───────────────────────────────────────────────────────────
color                          #00ff00
(color)                        color: default: #00ff00
```

### Configuring LEDs

```bash
# Set logo color to red
$ uchroma led logo --color red
Updated LED: logo

# Turn off scroll wheel LED
$ uchroma led scroll --state false
Updated LED: scroll

# Set logo brightness
$ uchroma led logo --brightness 50
Updated LED: logo
```

### Common LED Options

| Option         | Type   | Description                      |
| -------------- | ------ | -------------------------------- |
| `--state`      | bool   | Turn LED on/off (`true`/`false`) |
| `--color`      | color  | LED color                        |
| `--brightness` | int    | Brightness (0-100)               |
| `--effect`     | choice | LED effect (device-dependent)    |

### Available LEDs

Common LEDs by device type:

| Device    | LEDs                             |
| --------- | -------------------------------- |
| Keyboards | `backlight`, `logo`, `underglow` |
| Mice      | `logo`, `scroll`, `side`         |
| Mousepads | `underglow`                      |
| Headsets  | `logo`, `earcup`                 |

Use `uchroma led --list` to see which LEDs your device supports.

---

## input

Configure reactive lighting effects that respond to keyboard input.

### Synopsis

```
uchroma input <command> [options]
uchroma react <command> [options]
uchroma reactive <command> [options]
```

### Commands

| Command  | Aliases   | Description                         |
| -------- | --------- | ----------------------------------- |
| `status` | -         | Show current reactive effect status |
| `list`   | `ls`      | List available reactive effects     |
| `set`    | `enable`  | Enable a reactive effect            |
| `off`    | `disable` | Disable reactive effects            |

### Status

```bash
$ uchroma input status

 Reactive Input Status:

  status          inactive

  Enable with: uchroma input set <effect>
```

When active:

```bash
$ uchroma input status

 Reactive Input Status:

  status          active
  effects         ripple
```

### Listing Effects

```bash
$ uchroma input list

 Available Reactive Effects:

  reaction        Keys change color when pressed
  ripple          Ripples emanate from pressed keys
  typewriter      Warm glow that fades after keypress

  reaction options:
    --color         color (default: #ffffff)
    --background-color  color (default: #000000)
    --speed         int (default: 6)

  ripple options:
    --color         color
    --speed         int (default: 5)
    --ripple-width  int (default: 3)

  typewriter options:
    --glow-color    color (default: #ffaa44)
    --decay-time    float (default: 1.5)
```

### Enabling Effects

```bash
# Enable ripple effect
$ uchroma input set ripple
Enabled: ripple

# Enable with options
$ uchroma input set reaction --color cyan --speed 8
Enabled: reaction
  color: cyan
  speed: 8

# Enable typewriter with custom color
$ uchroma input set typewriter --glow-color "#ff6600"
Enabled: typewriter
  glow_color: #ff6600
```

### Options for `set`

| Option       | Description                        |
| ------------ | ---------------------------------- |
| `--color`    | Primary effect color               |
| `--bg-color` | Background color (reaction effect) |
| `--speed`    | Effect speed (1-9)                 |

### Disabling

```bash
$ uchroma input off
Disabled: ripple
```

---

## matrix

View LED matrix information and control individual pixels.

### Synopsis

```
uchroma matrix <command> [options]
uchroma pixels <command> [options]
uchroma frame <command> [options]
```

### Commands

| Command   | Aliases | Description                             |
| --------- | ------- | --------------------------------------- |
| `info`    | -       | Show matrix dimensions and capabilities |
| `fill`    | `solid` | Fill matrix with solid color            |
| `off`     | `clear` | Turn off all matrix LEDs                |
| `preview` | `show`  | Show ASCII preview of matrix            |

### Matrix Info

```bash
$ uchroma matrix info

 Matrix Info: Razer BlackWidow V3

  has_matrix       yes
  dimensions       22 x 6
  total_leds       132
  layout           6 rows, 22 columns

  Grid layout (22x6):

    +---------------------------------------------+
   0| . . . . . . . . . . . . . . . . . . . . . . |
   1| . . . . . . . . . . . . . . . . . . . . . . |
   2| . . . . . . . . . . . . . . . . . . . . . . |
   3| . . . . . . . . . . . . . . . . . . . . . . |
   4| . . . . . . . . . . . . . . . . . . . . . . |
   5| . . . . . . . . . . . . . . . . . . . . . . |
    +---------------------------------------------+
      0 1 2 3 4 5 6 7 8 9
```

### Fill Matrix

```bash
# Fill with red
$ uchroma matrix fill red
Matrix filled: red

# Fill with hex color
$ uchroma matrix fill "#00ff88"
Matrix filled: #00ff88
```

### Clear Matrix

```bash
$ uchroma matrix off
Matrix LEDs disabled
```

### Preview

Show current matrix state with active effect/layer info.

```bash
$ uchroma matrix preview

 Matrix Preview: Razer BlackWidow V3

  Current effect: spectrum

  Matrix grid (22x6):

   0 ░▒▓█░▒▓█░▒▓█░▒▓█░▒▓█░▒
   1 ▒▓█░▒▓█░▒▓█░▒▓█░▒▓█░▒▓
   2 ▓█░▒▓█░▒▓█░▒▓█░▒▓█░▒▓█
   3 █░▒▓█░▒▓█░▒▓█░▒▓█░▒▓█░
   4 ░▒▓█░▒▓█░▒▓█░▒▓█░▒▓█░▒
   5 ▒▓█░▒▓█░▒▓█░▒▓█░▒▓█░▒▓

  Note: Real-time pixel preview requires GTK frontend
```

---

## watch

Live monitoring of device status with real-time updates.

### Synopsis

```
uchroma watch [options]
uchroma monitor [options]
uchroma live [options]
```

### Options

| Option       | Short | Default | Description                         |
| ------------ | ----- | ------- | ----------------------------------- |
| `--interval` | `-i`  | 1.0     | Update interval in seconds          |
| `--count`    | `-n`  | 0       | Stop after N updates (0 = infinite) |
| `--fan`      | -     | false   | Show fan speed only                 |
| `--battery`  | -     | false   | Show battery only                   |
| `--compact`  | -     | false   | Compact single-line output          |

### Panel Mode (Default)

Displays a live-updating panel with gauges and history.

```bash
$ uchroma watch

╭─────────────────────────────────────────────────╮
│  Razer Blade 15 - 14:30:00                      │
│                                                 │
│  Fan Mode   Auto                                │
│  RPM        ████████░░░░░░░░░░░░ 2400           │
│  History    ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆                │
│─────────────────────────────────────────────────│
│                                                 │
│  Battery    ████████████████░░░░ 85%            │
│  Status     Discharging                         │
│                                                 │
╰─────────────────────────────────────────────────╯
  Press Ctrl+C to stop - Interval: 1.0s
```

### Compact Mode

Single-line output suitable for status bars.

```bash
$ uchroma watch --compact
14:30:00 | Fan: 2400 RPM ▁▂▃▄▅▆▇█ | Bat: ████████████████ 85%
```

### Fan Only

```bash
$ uchroma watch --fan

╭─────────────────────────────────────────────────╮
│  Razer Blade 15 - 14:30:00                      │
│                                                 │
│  Fan Mode   Auto                                │
│  RPM        ████████░░░░░░░░░░░░ 2400           │
│  RPM 2      ████████░░░░░░░░░░░░ 2350           │
│  History    ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆                │
│                                                 │
╰─────────────────────────────────────────────────╯
```

### Battery Only

```bash
$ uchroma watch --battery

╭─────────────────────────────────────────────────╮
│  Razer DeathAdder V3 Pro - 14:30:00             │
│                                                 │
│  Battery    ████████████████░░░░ 85%            │
│  Status     Discharging                         │
│                                                 │
╰─────────────────────────────────────────────────╯
```

### Limited Duration

```bash
# Monitor for 10 updates then stop
$ uchroma watch --count 10 --interval 0.5
```

### Scripting

```bash
# Log fan RPM every 5 seconds
$ uchroma watch --fan --compact --interval 5 >> fan_log.txt
```

---

## Requirements

| Command           | Requirement                      |
| ----------------- | -------------------------------- |
| `led`             | Device with standalone LEDs      |
| `input`           | Keyboard with key matrix support |
| `matrix`          | Device with LED matrix           |
| `watch --fan`     | Razer laptop with system control |
| `watch --battery` | Wireless device                  |

---

## Related Commands

- [`brightness`](brightness.md) - Overall brightness control
- [`fx`](effects.md) - Hardware effects
- [`anim`](animations.md) - Software animations
- [`power`](power.md) - Power modes and boost
