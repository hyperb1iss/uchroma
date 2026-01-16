# Custom Animations

Custom animations are rich, software-rendered effects that run on the uchroma daemon. They offer far
more visual complexity than hardware effects, support layering with blend modes, and can react to
your keyboard input.

## Overview

Each animation is implemented as a **Renderer** - a Python class that draws frames to a Layer.
Renderers run in their own async tasks at configurable frame rates (typically 15-30 FPS). Multiple
renderers can be stacked as layers and composited together.

**Key Features:**

- Full RGB control over every LED
- Configurable via traitlets (exposed to CLI and D-Bus)
- Layering with blend modes (screen, soft_light, dodge, etc.)
- Reactive effects that respond to keypresses
- Color schemes and gradients

---

## Ambient Effects

### Plasma

**Classic demoscene plasma effect**

The iconic plasma effect from 90s demoscene - colorful, organic blobs that flow and merge across
your keyboard.

| Parameter         | Type   | Default     | Range               | Description              |
| ----------------- | ------ | ----------- | ------------------- | ------------------------ |
| `color_scheme`    | colors | Qap palette | 2+ colors           | Gradient colors          |
| `preset`          | choice | `Qap`       | ColorScheme presets | Predefined color schemes |
| `gradient_length` | int    | `360`       | 0+                  | Gradient resolution      |

```bash
# Default plasma
uchroma anim add plasma

# With sunset colors
uchroma anim add plasma --preset sunset

# Custom gradient
uchroma anim add plasma --color-scheme '#ff006e' '#8338ec' '#00f5d4'
```

**Visual**: Smooth, flowing blobs of color that merge and separate like oil in water. The effect
uses sine wave interference patterns to create organic, ever-changing shapes.

---

### Rainbow

**Flowing HSV gradient**

A simple but satisfying rainbow that flows across your keyboard. Also known as "Rainflow".

| Parameter | Type | Default | Range | Description                    |
| --------- | ---- | ------- | ----- | ------------------------------ |
| `speed`   | int  | `8`     | 0-20  | Flow speed                     |
| `stagger` | int  | `4`     | 0-100 | Row offset for diagonal effect |

```bash
# Default rainbow
uchroma anim add rainbow

# Fast, steep diagonal
uchroma anim add rainbow --speed 15 --stagger 8

# Slow, horizontal bands
uchroma anim add rainbow --speed 3 --stagger 0
```

**Visual**: A full-spectrum rainbow gradient scrolling horizontally. The stagger parameter offsets
each row, creating a diagonal wave effect.

---

### Aurora

**Northern lights curtains**

Shimmering vertical curtains of light that undulate horizontally, mimicking the aurora borealis.

| Parameter        | Type   | Default           | Range     | Description                         |
| ---------------- | ------ | ----------------- | --------- | ----------------------------------- |
| `speed`          | float  | `1.0`             | 0.2-3.0   | Animation speed                     |
| `drift`          | float  | `0.3`             | 0.1-1.0   | Horizontal drift amount             |
| `curtain_height` | float  | `0.7`             | 0.3-1.0   | How far curtains extend down        |
| `shimmer`        | float  | `0.3`             | 0.0-1.0   | High-frequency brightness variation |
| `color_drift`    | float  | `0.5`             | 0.1-2.0   | Color shift speed                   |
| `color_scheme`   | colors | green/teal/purple | 2+ colors | Aurora colors                       |

```bash
# Classic northern lights
uchroma anim add aurora

# Fast, vibrant aurora
uchroma anim add aurora --speed 2.0 --shimmer 0.5

# Subtle, slow drift
uchroma anim add aurora --speed 0.5 --drift 0.2 --shimmer 0.1
```

**Visual**: Glowing vertical curtains that wave horizontally, fading from bright at the top to
dimmer at the bottom. The default green-teal-purple palette captures the classic aurora look.

---

### Nebula

**Cosmic cloud formations**

Soft, flowing cosmic clouds using procedural noise - like gazing into a nebula.

| Parameter         | Type   | Default                | Range     | Description                          |
| ----------------- | ------ | ---------------------- | --------- | ------------------------------------ |
| `drift_speed`     | float  | `0.3`                  | 0.1-1.0   | Cloud movement speed                 |
| `scale`           | float  | `0.15`                 | 0.05-0.4  | Cloud size (smaller = larger clouds) |
| `detail`          | int    | `2`                    | 1-3       | Noise octaves (more = finer detail)  |
| `contrast`        | float  | `0.6`                  | 0.3-1.0   | Color contrast                       |
| `base_brightness` | float  | `0.5`                  | 0.3-0.7   | Minimum brightness                   |
| `color_shift`     | float  | `0.3`                  | 0.0-1.0   | Color variation amount               |
| `color_scheme`    | colors | purple/pink/cyan/green | 2+ colors | Nebula colors                        |

```bash
# Cosmic nebula
uchroma anim add nebula

# Large, slow-drifting clouds
uchroma anim add nebula --scale 0.08 --drift-speed 0.15

# High contrast, detailed
uchroma anim add nebula --detail 3 --contrast 0.9
```

**Visual**: Soft, billowing clouds of color that slowly drift and morph. Uses fractal Brownian
motion for organic, natural-looking formations.

---

### Ocean

**Rolling waves with caustics**

Horizontal waves with bright highlights on wave crests, simulating light playing on water.

| Parameter           | Type   | Default            | Range     | Description                      |
| ------------------- | ------ | ------------------ | --------- | -------------------------------- |
| `wave_speed`        | float  | `1.0`              | 0.3-2.5   | Wave animation speed             |
| `wave_height`       | float  | `0.5`              | 0.2-1.0   | Wave amplitude                   |
| `foam_threshold`    | float  | `0.5`              | 0.2-0.8   | When waves produce foam          |
| `caustic_intensity` | float  | `0.3`              | 0.0-0.6   | Brightness of caustic highlights |
| `saturation`        | float  | `0.8`              | 0.4-1.0   | Color saturation                 |
| `color_scheme`      | colors | deep blue gradient | 2+ colors | Water colors                     |

```bash
# Calm ocean
uchroma anim add ocean

# Stormy seas
uchroma anim add ocean --wave-speed 2.0 --wave-height 0.9 --foam-threshold 0.3

# Tropical lagoon
uchroma anim add ocean --wave-speed 0.5 --color-scheme '#006994' '#40E0D0' '#ffffff'
```

**Visual**: Horizontal wave patterns moving across the keyboard, with brighter "caustic" highlights
where waves crest. Foam appears on steep wave slopes.

---

### Vortex

**Swirling spiral tunnel**

A hypnotic vortex centered on your keyboard with spiral arms flowing inward or outward.

| Parameter        | Type   | Default               | Range     | Description                     |
| ---------------- | ------ | --------------------- | --------- | ------------------------------- |
| `arm_count`      | int    | `3`                   | 1-6       | Number of spiral arms           |
| `twist`          | float  | `0.3`                 | 0.1-1.0   | Spiral tightness                |
| `flow_speed`     | float  | `1.0`                 | 0.3-3.0   | Radial flow speed               |
| `flow_direction` | int    | `1`                   | -1 to 1   | Inward (-1) or outward (1) flow |
| `rotation_speed` | float  | `0.5`                 | 0.1-2.0   | Spiral rotation speed           |
| `center_glow`    | float  | `3.0`                 | 1.0-5.0   | Bright center radius            |
| `ring_density`   | float  | `0.5`                 | 0.2-1.5   | Radial ring frequency           |
| `color_scheme`   | colors | pink/purple/blue/teal | 2+ colors | Vortex colors                   |

```bash
# Classic vortex
uchroma anim add vortex

# Fast inward spiral
uchroma anim add vortex --flow-direction -1 --flow-speed 2.0

# Tight 6-arm spiral
uchroma anim add vortex --arm-count 6 --twist 0.8
```

**Visual**: A swirling tunnel effect with spiral arms radiating from the center. The center glows
brighter, and depth rings create a 3D tunnel illusion.

---

## Retro Effects

### Copper Bars

**Classic Amiga demoscene raster bars**

Horizontal color bands flow and warp with sine-wave displacement - the iconic "copper bar" look from
80s/90s demos.

| Parameter         | Type   | Default   | Range               | Description              |
| ----------------- | ------ | --------- | ------------------- | ------------------------ |
| `speed`           | float  | `1.0`     | 0.2-3.0             | Animation speed          |
| `wave_amplitude`  | float  | `0.5`     | 0.0-2.0             | Vertical wave intensity  |
| `wave_frequency`  | float  | `0.8`     | 0.2-2.0             | Wave frequency           |
| `band_width`      | int    | `40`      | 10-100              | Color band width         |
| `horizontal_wave` | bool   | `false`   | -                   | Add per-column variation |
| `color_scheme`    | colors | Rainbow   | 2+ colors           | Bar colors               |
| `preset`          | choice | `Rainbow` | ColorScheme presets | Predefined palettes      |
| `gradient_length` | int    | `360`     | 60-720              | Gradient resolution      |

```bash
# Classic rainbow bars
uchroma anim add copper_bars

# With horizontal wave
uchroma anim add copper_bars --horizontal-wave

# Neon palette, fast
uchroma anim add copper_bars --preset neon --speed 2.0 --wave-amplitude 1.0
```

**Visual**: Horizontal bands of color flowing vertically, with sine-wave displacement creating a
wavy, organic motion. A tribute to the Amiga demo scene.

---

## Geometric Effects

### Kaleidoscope

**Rotating symmetric patterns**

Hypnotic geometric patterns using polar coordinate transforms and n-fold symmetry.

| Parameter        | Type   | Default                 | Range              | Description                    |
| ---------------- | ------ | ----------------------- | ------------------ | ------------------------------ |
| `symmetry`       | int    | `6`                     | 3-12               | Number of symmetric segments   |
| `rotation_speed` | float  | `0.5`                   | 0.1-2.0            | Pattern rotation speed         |
| `pattern_mode`   | choice | `spiral`                | spiral/rings/waves | Pattern type                   |
| `ring_frequency` | float  | `0.5`                   | 0.2-1.5            | Radial pattern frequency       |
| `spiral_twist`   | float  | `2.0`                   | 0.5-5.0            | Spiral tightness (spiral mode) |
| `hue_rotation`   | float  | `30.0`                  | 0.0-120.0          | Color rotation speed           |
| `saturation`     | float  | `0.9`                   | 0.5-1.0            | Color saturation               |
| `color_scheme`   | colors | pink/yellow/teal/purple | 2+ colors          | Pattern colors                 |

```bash
# Classic kaleidoscope
uchroma anim add kaleidoscope

# 8-fold symmetry with rings
uchroma anim add kaleidoscope --symmetry 8 --pattern-mode rings

# Slow, tight spiral
uchroma anim add kaleidoscope --rotation-speed 0.2 --spiral-twist 4.0
```

**Visual**: Symmetric patterns that rotate and morph, creating mandala-like effects. The symmetry
parameter controls how many times the pattern repeats around the center.

---

## Organic Effects

### Metaballs

**Organic lava lamp blobs**

Soft, blobby shapes that slowly drift, merge when close, and split apart - like a lava lamp.

| Parameter         | Type   | Default               | Range     | Description            |
| ----------------- | ------ | --------------------- | --------- | ---------------------- |
| `blob_count`      | int    | `4`                   | 2-8       | Number of blobs        |
| `speed`           | float  | `0.5`                 | 0.1-2.0   | Blob movement speed    |
| `threshold`       | float  | `1.0`                 | 0.5-2.0   | Merge threshold        |
| `glow_falloff`    | float  | `2.0`                 | 1.0-4.0   | Glow intensity falloff |
| `base_brightness` | float  | `0.2`                 | 0.0-0.4   | Background brightness  |
| `blob_radius`     | float  | `3.0`                 | 1.5-5.0   | Blob size              |
| `color_scheme`    | colors | pink/purple/blue/teal | 2+ colors | Blob colors            |

```bash
# Classic metaballs
uchroma anim add metaballs

# Many small blobs
uchroma anim add metaballs --blob-count 8 --blob-radius 2.0

# Large, slow, glowy
uchroma anim add metaballs --blob-count 3 --blob-radius 4.5 --speed 0.2
```

**Visual**: Soft, glowing blobs that drift around, merging seamlessly when they get close and
splitting apart as they separate. Classic demoscene algorithm.

---

## Motion Effects

### Comets

**Streaking light trails**

Bright points zoom horizontally across the keyboard, leaving glowing trails.

| Parameter         | Type   | Default                   | Range     | Description            |
| ----------------- | ------ | ------------------------- | --------- | ---------------------- |
| `comet_count`     | int    | `3`                       | 1-6       | Number of comets       |
| `speed`           | float  | `1.5`                     | 0.5-4.0   | Movement speed         |
| `trail_length`    | int    | `8`                       | 3-15      | Trail length in pixels |
| `trail_decay`     | float  | `0.3`                     | 0.1-0.6   | Trail fade rate        |
| `head_brightness` | float  | `1.0`                     | 0.7-1.0   | Comet head brightness  |
| `color_scheme`    | colors | cyan/magenta/yellow/green | 2+ colors | Comet colors           |

```bash
# Shooting stars
uchroma anim add comets

# Single fast comet with long trail
uchroma anim add comets --comet-count 1 --speed 3.0 --trail-length 12

# Many slow comets
uchroma anim add comets --comet-count 5 --speed 0.8
```

**Visual**: Bright white comet heads streak across the keyboard, leaving colorful fading trails
behind them. Multiple comets at different speeds create depth.

---

## Particle Effects

### Embers

**Warm glowing particles**

A field of warm glowing particles that drift slowly upward, pulse in brightness, and occasionally
flare brighter.

| Parameter         | Type  | Default   | Range   | Description               |
| ----------------- | ----- | --------- | ------- | ------------------------- |
| `particle_count`  | int   | `8`       | 3-15    | Number of embers          |
| `drift_speed`     | float | `0.3`     | 0.1-1.0 | Upward drift speed        |
| `pulse_speed`     | float | `1.5`     | 0.5-4.0 | Brightness pulse rate     |
| `glow_radius`     | float | `2.0`     | 1.0-4.0 | Ember glow size           |
| `color`           | color | `#ff6b35` | -       | Ember color (warm orange) |
| `base_brightness` | float | `0.6`     | 0.3-0.8 | Base glow intensity       |
| `flare_chance`    | float | `0.02`    | 0.0-0.1 | Random flare probability  |

```bash
# Campfire embers
uchroma anim add embers

# Many small, fast-rising embers
uchroma anim add embers --particle-count 12 --drift-speed 0.6 --glow-radius 1.5

# Slow, pulsing with frequent flares
uchroma anim add embers --pulse-speed 0.8 --flare-chance 0.05
```

**Visual**: Warm orange-red particles float upward like embers from a dying fire. They pulse gently
and occasionally flare to full brightness.

---

## Reactive Effects

Reactive effects respond to your keyboard input, creating visual feedback as you type.

### Ripple (Custom) {#ripple-custom}

**Ripples emanate from keypresses**

When you press a key, colorful circular ripples expand outward from that position.

| Parameter      | Type   | Default | Range               | Description                   |
| -------------- | ------ | ------- | ------------------- | ----------------------------- |
| `ripple_width` | int    | `3`     | 1-5                 | Ring thickness                |
| `speed`        | int    | `5`     | 1-9                 | Ripple expansion speed        |
| `preset`       | choice | -       | ColorScheme presets | Color preset                  |
| `random`       | bool   | `true`  | -                   | Random rainbow colors         |
| `color`        | color  | -       | -                   | Fixed color (disables random) |

```bash
# Rainbow ripples
uchroma anim add ripple

# Single color ripples
uchroma anim add ripple --color '#00ffff' --no-random

# Fast, thin ripples with preset
uchroma anim add ripple --preset sunset --speed 8 --ripple-width 1
```

**Visual**: Each keypress spawns an expanding circular wave. Multiple keypresses create beautiful
overlapping ripple patterns. Colors can be random, from a preset, or fixed.

**Note**: Requires a device with key input support (keyboards).

---

### Reaction

**Keys change color when pressed**

A simple reactive effect where keys flash a color when pressed and fade back to a background color.

| Parameter          | Type  | Default | Range | Description              |
| ------------------ | ----- | ------- | ----- | ------------------------ |
| `speed`            | int   | `6`     | 1-9   | Fade speed (9 = fastest) |
| `background_color` | color | `black` | -     | Resting color            |
| `color`            | color | `white` | -     | Flash color              |

```bash
# White flash on black
uchroma anim add reaction

# Cyan flash on dark blue
uchroma anim add reaction --color cyan --background-color '#001133'

# Fast green flash
uchroma anim add reaction --color '#00ff00' --speed 9
```

**Visual**: Keys rest at the background color. When pressed, they instantly flash to the accent
color, then smoothly fade back. Creates a gradient trail as you type.

**Note**: Requires a device with key input support (keyboards).

---

### Typewriter

**Warm incandescent glow fade**

Keys illuminate with a warm, incandescent glow when pressed and slowly fade like old typewriter
keys. Creates a "heat map" of your typing.

| Parameter         | Type  | Default   | Range   | Description                |
| ----------------- | ----- | --------- | ------- | -------------------------- |
| `glow_color`      | color | `#ffaa44` | -       | Glow color (warm amber)    |
| `decay_time`      | float | `1.5`     | 0.5-5.0 | Seconds to fade to ~10%    |
| `spread`          | float | `0.3`     | 0.0-0.6 | Spread to neighboring keys |
| `base_brightness` | float | `0.15`    | 0.0-0.3 | Ambient glow level         |
| `peak_brightness` | float | `1.0`     | 0.7-1.0 | Maximum brightness         |
| `warmth`          | float | `0.3`     | 0.0-0.6 | Shift toward white at peak |

```bash
# Classic typewriter
uchroma anim add typewriter

# Slow decay, high spread (heat map)
uchroma anim add typewriter --decay-time 3.0 --spread 0.5

# Cool blue glow, no spread
uchroma anim add typewriter --glow-color '#4488ff' --spread 0.0
```

**Visual**: Keys glow warmly when pressed, with the brightness shifting toward white at peak
intensity (like heated metal). The glow spreads slightly to neighbors and slowly fades, leaving a
visual trail of your recent typing.

**Note**: Requires a device with key input support (keyboards).

---

## CLI Quick Reference

```bash
# List all available renderers with parameters
uchroma anim --list

# Add a renderer (auto-assigns z-index)
uchroma anim add <renderer> [--param value ...]

# Add at specific z-index
uchroma anim add -z 0 plasma

# Show active layers
uchroma anim show

# Modify a layer's parameters
uchroma anim set <zindex> --param value

# Remove a layer
uchroma anim rm <zindex>

# Stop all animations
uchroma anim stop

# Pause/unpause
uchroma anim pause
```

## Layering Examples

Stack multiple effects for complex visuals:

```bash
# Aurora with reactive ripples
uchroma anim add aurora --speed 0.5
uchroma anim add ripple

# Nebula with typing heat map
uchroma anim add nebula --drift-speed 0.2
uchroma anim add typewriter --spread 0.4

# Ocean with shooting comets
uchroma anim add ocean --wave-speed 0.7
uchroma anim add comets --comet-count 2 --speed 2.0
```

Higher z-index layers render on top. Blend modes determine how layers combine (see
[Animation System](../developers/architecture.md) for details).
