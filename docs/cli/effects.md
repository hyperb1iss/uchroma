# Hardware Effects

Control built-in hardware lighting effects that run directly on the device.

## fx

Apply hardware lighting effects to your device. Hardware effects run on the device itself and
persist even when the daemon is not running.

### Synopsis

```
uchroma fx [options]
uchroma fx <effect> [effect-options]
uchroma effect <effect> [effect-options]
```

### Options

| Option   | Short | Description                                  |
| -------- | ----- | -------------------------------------------- |
| `--list` | `-l`  | List available effects with their parameters |

### Examples

**List available effects:**

```bash
$ uchroma fx --list

 Built-in effects and arguments:

breath_dual                    Dual color breathing effect
───────────────────────────────────────────────────────────
color1                         color (default: #00ff00)
color2                         color (default: #0000ff)

breath_random                  Random color breathing
───────────────────────────────────────────────────────────
(no parameters)

breath_single                  Single color breathing effect
───────────────────────────────────────────────────────────
color                          color (default: #00ff00)

...
```

**Apply an effect:**

```bash
$ uchroma fx spectrum
Effect: spectrum
```

**Apply effect with parameters:**

```bash
$ uchroma fx static --color "#ff0088"
Effect: static
```

---

## Available Effects

The following hardware effects are commonly available. Actual availability depends on your device.

### Static Effects

#### static

Solid color across all LEDs.

| Option    | Type  | Default   | Description |
| --------- | ----- | --------- | ----------- |
| `--color` | color | `#00ff00` | LED color   |

```bash
uchroma fx static --color red
uchroma fx static --color "#ff5500"
uchroma fx static --color "rgb(255, 0, 128)"
```

#### disable

Turn off all LEDs.

```bash
uchroma fx disable
```

### Breathing Effects

#### breath_single

Single color breathing (pulsing) effect.

| Option    | Type  | Default   | Description     |
| --------- | ----- | --------- | --------------- |
| `--color` | color | `#00ff00` | Breathing color |

```bash
uchroma fx breath_single --color cyan
```

#### breath_dual

Two-color breathing effect that alternates between colors.

| Option     | Type  | Default   | Description  |
| ---------- | ----- | --------- | ------------ |
| `--color1` | color | `#00ff00` | First color  |
| `--color2` | color | `#0000ff` | Second color |

```bash
uchroma fx breath_dual --color1 red --color2 blue
```

#### breath_random

Breathing effect with random colors.

```bash
uchroma fx breath_random
```

### Cycling Effects

#### spectrum

Continuous spectrum cycling through all colors.

```bash
uchroma fx spectrum
```

#### wave

Color wave that moves across the device.

| Option        | Type   | Default | Description                                   |
| ------------- | ------ | ------- | --------------------------------------------- |
| `--direction` | choice | `right` | Wave direction: `left`, `right`, `up`, `down` |

```bash
uchroma fx wave --direction left
```

### Reactive Effects

#### reactive

Keys light up when pressed and fade out.

| Option    | Type  | Default   | Description                          |
| --------- | ----- | --------- | ------------------------------------ |
| `--color` | color | `#00ff00` | Reaction color                       |
| `--speed` | int   | `3`       | Fade speed (1-4, where 4 is fastest) |

```bash
uchroma fx reactive --color orange --speed 2
```

#### starlight

Random twinkling stars effect.

| Option    | Type  | Default   | Description         |
| --------- | ----- | --------- | ------------------- |
| `--color` | color | `#ffffff` | Star color          |
| `--speed` | int   | `2`       | Twinkle speed (1-3) |

```bash
uchroma fx starlight --color yellow --speed 3
```

### Game Integration Effects

#### ripple

Ripples emanate from pressed keys.

| Option    | Type  | Default   | Description  |
| --------- | ----- | --------- | ------------ |
| `--color` | color | `#00ff00` | Ripple color |

```bash
uchroma fx ripple --color purple
```

#### ripple_random

Ripples with random colors.

```bash
uchroma fx ripple_random
```

---

## Color Formats

Effects that accept color parameters support multiple formats:

| Format        | Example                          |
| ------------- | -------------------------------- |
| Named colors  | `red`, `blue`, `cyan`, `magenta` |
| Hex (6-digit) | `#ff0088`                        |
| Hex (3-digit) | `#f08`                           |
| RGB           | `rgb(255, 0, 128)`               |
| HSL           | `hsl(330, 100%, 50%)`            |

```bash
# All equivalent
uchroma fx static --color red
uchroma fx static --color "#ff0000"
uchroma fx static --color "rgb(255, 0, 0)"
```

---

## Hardware vs Software Effects

**Hardware effects** (this page):

- Run directly on the device firmware
- Persist when the daemon stops
- Limited selection and customization
- Lower CPU usage

**Software animations** ([anim command](animations.md)):

- Run in the uchroma daemon
- Stop when the daemon stops
- Extensive customization and layering
- More complex visual effects

Use hardware effects for simple, persistent lighting. Use software animations for complex, layered
effects.

---

## Checking Current Effect

Use `uchroma dump device` to see the currently active effect:

```bash
$ uchroma dump device | grep current_fx
    current_fx: spectrum
```

---

## Related Commands

- [`anim`](animations.md) - Software animation layers with more options
- [`brightness`](brightness.md) - Control effect brightness
- [`led`](advanced.md#led) - Per-LED effects and colors
- [`profile`](profiles.md) - Save effects as profiles
