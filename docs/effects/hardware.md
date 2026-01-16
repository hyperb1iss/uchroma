# Hardware Effects

Hardware effects run directly on your device's firmware, requiring zero CPU usage from your
computer. These effects persist even when the uchroma daemon isn't running.

## Overview

Hardware effects are simple, predefined lighting patterns built into Razer device firmware. They're
set via USB HID commands and run entirely on the device's embedded controller.

**Protocols**: Razer devices use two protocol versions:

- **Legacy** (Class 0x03): Older devices, broader effect support
- **Extended** (Class 0x0F): Modern devices, streamlined effects

Most common effects work on both protocols. Effect availability depends on what your specific device
supports.

---

## Static

**Solid color across all LEDs**

The simplest effect - sets every LED to a single color. Perfect for a clean, consistent look.

### Parameters

| Parameter | Type  | Default | Description          |
| --------- | ----- | ------- | -------------------- |
| `color`   | color | `green` | The color to display |

### Examples

```bash
# Solid red
uchroma fx static --color red

# Hex color
uchroma fx static --color '#ff6b35'

# RGB values work too
uchroma fx static --color 'rgb(255, 107, 53)'
```

### Visual

A uniform field of your chosen color across the entire device. No animation or variation.

---

## Wave

**Rainbow colors flowing across the device**

A classic effect where a rainbow gradient smoothly scrolls horizontally across your keyboard or
device.

### Parameters

| Parameter         | Type   | Default | Description                                         |
| ----------------- | ------ | ------- | --------------------------------------------------- |
| `direction`       | choice | `right` | Wave direction: `left` or `right`                   |
| `trackpad_effect` | bool   | `false` | Enable circular trackpad animation (Blade Pro only) |

### Examples

```bash
# Default right-flowing wave
uchroma fx wave

# Left-flowing wave
uchroma fx wave --direction left

# With trackpad chase effect (supported devices)
uchroma fx wave --direction right --trackpad-effect
```

### Visual

A smooth rainbow gradient scrolling horizontally. Colors cycle through the full spectrum (red,
orange, yellow, green, cyan, blue, purple) in a continuous loop.

### Device Support

All devices with matrix support. The trackpad chase variants only work on devices with illuminated
trackpads (e.g., Blade Pro).

---

## Spectrum

**Slow color cycling through the entire spectrum**

All LEDs simultaneously cycle through the color spectrum in a slow, hypnotic fade.

### Parameters

None - this effect has no configurable parameters.

### Examples

```bash
uchroma fx spectrum
```

### Visual

The entire device slowly fades through red, orange, yellow, green, cyan, blue, purple, and back to
red. Unlike Wave, all LEDs show the same color at any given moment.

---

## Breathe

**Colors pulse in and out**

LEDs fade between bright and dim in a smooth "breathing" pattern. Can use random colors, a single
color, or alternate between two colors.

### Parameters

| Parameter | Type   | Default | Description                                             |
| --------- | ------ | ------- | ------------------------------------------------------- |
| `colors`  | colors | (empty) | 0-2 colors. Empty = random, 1 = single, 2 = alternating |

### Examples

```bash
# Random colors
uchroma fx breathe

# Single color breathing
uchroma fx breathe --colors '#00ff00'

# Alternate between two colors
uchroma fx breathe --colors '#ff00ff' '#00ffff'
```

### Visual

- **Random mode**: Each breath cycle uses a different random color
- **Single mode**: Smooth fade in/out of your chosen color
- **Dual mode**: Alternates between two colors with each breath

---

## Reactive

**Keys light up when pressed**

Each key illuminates when you press it, then fades back to dark. Great for seeing exactly where
you're typing.

### Parameters

| Parameter | Type  | Default   | Description                            |
| --------- | ----- | --------- | -------------------------------------- |
| `color`   | color | `skyblue` | Color when keys are pressed            |
| `speed`   | int   | `1`       | Fade speed (1-4, higher = faster fade) |

### Examples

```bash
# Default blue glow
uchroma fx reactive

# Red with fast fade
uchroma fx reactive --color red --speed 4

# Slow orange fade
uchroma fx reactive --color '#ff6b35' --speed 1
```

### Visual

Keys start dark. When pressed, they instantly illuminate in your chosen color, then smoothly fade
back to dark. The fade duration is controlled by the speed parameter.

### Device Support

Requires keyboard with per-key lighting. Not available on single-LED devices.

---

## Starlight

**Sparkling effect across the device**

Random keys twinkle on and off like stars, creating a gentle, ambient sparkle effect.

### Parameters

| Parameter | Type   | Default | Description                                        |
| --------- | ------ | ------- | -------------------------------------------------- |
| `colors`  | colors | (empty) | 0-2 colors. Empty = random, 1-2 = specified colors |
| `speed`   | int    | `1`     | Sparkle speed (1-4)                                |

### Examples

```bash
# Random colored stars
uchroma fx starlight

# White stars
uchroma fx starlight --colors white

# Pink and cyan stars
uchroma fx starlight --colors '#ff69b4' '#00ffff' --speed 2
```

### Visual

Individual keys randomly light up and fade out at different times, creating a twinkling starfield
effect. The distribution appears random across the keyboard.

---

## Ripple

**Ripples emanate from keypresses**

When you press a key, a circular ripple of color expands outward from that position.

### Parameters

| Parameter | Type  | Default | Description                  |
| --------- | ----- | ------- | ---------------------------- |
| `color`   | color | `green` | Ripple color                 |
| `speed`   | int   | `3`     | Ripple expansion speed (1-8) |

### Examples

```bash
# Green ripples
uchroma fx ripple

# Fast blue ripples
uchroma fx ripple --color blue --speed 6
```

### Visual

Each keypress spawns a circular wave that expands outward. Multiple keypresses create overlapping
ripples. The background is dark, with only the expanding rings visible.

### Device Support

Legacy protocol only. Modern devices should use the
[custom Ripple renderer](./custom.md#ripple-custom) for similar functionality.

---

## Ripple Solid

**Ripples on a solid color background**

Similar to Ripple, but with a solid color background instead of darkness.

### Parameters

| Parameter | Type  | Default | Description                  |
| --------- | ----- | ------- | ---------------------------- |
| `color`   | color | `green` | Ripple and background color  |
| `speed`   | int   | `3`     | Ripple expansion speed (1-8) |

### Examples

```bash
uchroma fx ripple_solid --color purple --speed 4
```

### Visual

The keyboard shows a solid color. Keypresses create brighter ripples that expand outward before
fading back into the base color.

### Device Support

Legacy protocol only.

---

## Fire

**Animated flames**

A dynamic fire effect with flames rising from the bottom of the keyboard.

### Parameters

| Parameter | Type  | Default | Description                    |
| --------- | ----- | ------- | ------------------------------ |
| `color`   | color | `red`   | Base flame color               |
| `speed`   | int   | `64`    | Flame animation speed (16-128) |

### Examples

```bash
# Classic orange/red fire
uchroma fx fire

# Blue flames
uchroma fx fire --color blue --speed 80

# Slow, smoldering fire
uchroma fx fire --color '#ff4500' --speed 32
```

### Visual

Animated flames flicker upward from the bottom edge of the keyboard. The effect uses your chosen
color as the base, with brightness variations creating the illusion of dancing flames.

### Device Support

Legacy protocol only. Not available on devices with extended protocol.

---

## Sweep

**Colors sweep across the device**

A color transition that sweeps horizontally across the keyboard.

### Parameters

| Parameter    | Type   | Default | Description                        |
| ------------ | ------ | ------- | ---------------------------------- |
| `color`      | color  | `green` | Sweep color                        |
| `base_color` | color  | `black` | Background color                   |
| `direction`  | choice | `right` | Sweep direction: `left` or `right` |
| `speed`      | int    | `15`    | Sweep speed (1-30)                 |

### Examples

```bash
# Green sweep on black
uchroma fx sweep --color green

# Cyan sweep on purple background
uchroma fx sweep --color cyan --base-color purple --speed 20

# Left-moving red sweep
uchroma fx sweep --color red --direction left
```

### Visual

A band of color moves across the keyboard, transitioning between the base color and sweep color.
Creates a clean, directional animation.

### Device Support

Legacy protocol only.

---

## Morph

**Color morphing on keypress**

Keys morph between colors when pressed, creating a flowing, organic effect.

### Parameters

| Parameter    | Type  | Default    | Description        |
| ------------ | ----- | ---------- | ------------------ |
| `color`      | color | `magenta`  | Color when pressed |
| `base_color` | color | `darkblue` | Resting color      |
| `speed`      | int   | `2`        | Morph speed (1-4)  |

### Examples

```bash
# Magenta flashes on blue background
uchroma fx morph

# Orange on dark purple
uchroma fx morph --color orange --base-color '#1a0033'

# Fast green on black
uchroma fx morph --color '#00ff00' --base-color black --speed 4
```

### Visual

The keyboard displays the base color. When you press a key, it flashes to the accent color and the
color smoothly "morphs" outward to neighboring keys before fading back.

### Device Support

Legacy protocol only.

---

## Disable

**Turn off all lighting**

Disables all effects, turning off the LEDs.

### Parameters

None.

### Examples

```bash
uchroma fx disable
```

---

## Effect Availability by Device

Effect support varies by device. Here's a general guide:

| Effect       | Legacy Devices | Extended Devices |
| ------------ | -------------- | ---------------- |
| Disable      | Yes            | Yes              |
| Static       | Yes            | Yes              |
| Wave         | Yes            | Yes              |
| Spectrum     | Yes            | Yes              |
| Breathe      | Yes            | Yes              |
| Reactive     | Yes            | Yes              |
| Starlight    | Yes            | Yes              |
| Ripple       | Yes            | No               |
| Ripple Solid | Yes            | No               |
| Fire         | Yes            | No               |
| Sweep        | Yes            | No               |
| Morph        | Yes            | No               |

To see exactly which effects your device supports:

```bash
uchroma fx --list
```

This shows all available effects with their configurable parameters and current values.
