# Custom Animations

The animation system provides software-rendered effects with full customization, layering, and
blending.

## anim

Manage custom animation layers that run in the uchroma daemon.

### Synopsis

```
uchroma anim [options]
uchroma anim <command> [args]
uchroma animation <command> [args]
uchroma layer <command> [args]
```

### Options

| Option   | Short | Description              |
| -------- | ----- | ------------------------ |
| `--list` | `-l`  | List available renderers |

### Commands

| Command | Aliases         | Description                              |
| ------- | --------------- | ---------------------------------------- |
| `list`  | `ls`            | List available renderers with parameters |
| `show`  | `status`        | Show currently active layers             |
| `add`   | -               | Add a new renderer layer                 |
| `rm`    | `del`, `remove` | Remove a layer by index                  |
| `set`   | `mod`           | Modify layer properties                  |
| `pause` | -               | Toggle animation pause                   |
| `stop`  | `clear`         | Stop and clear all layers                |

---

## Listing Renderers

Show all available animation renderers and their configurable parameters.

```bash
$ uchroma anim list

 Available renderers and arguments:

aurora                         Shimmering northern lights curtains
───────────────────────────────────────────────────────────
author                         uchroma
version                        1.0
───────────────────────────────────────────────────────────
speed                          float [0.2..3.0] default: 1.0
drift                          float [0.1..1.0] default: 0.3
curtain_height                 float [0.3..1.0] default: 0.7
shimmer                        float [0.0..1.0] default: 0.3
color_drift                    float [0.1..2.0] default: 0.5
color_scheme                   colors

...
```

---

## Adding Layers

Add a renderer as a new animation layer.

### Synopsis

```
uchroma anim add <renderer> [options]
```

### Options

| Option                    | Description                          |
| ------------------------- | ------------------------------------ |
| `-z`, `--zindex`          | Layer index (default: auto-assigned) |
| Renderer-specific options | See renderer parameters              |

### Examples

```bash
# Add plasma with default settings
uchroma anim add plasma

# Add aurora with custom speed
uchroma anim add aurora --speed 2.0

# Add at specific layer index
uchroma anim add rainbow -z 0
```

---

## Viewing Active Layers

Show currently running animation layers.

```bash
$ uchroma anim show

 Active Layers (2)

  [0] Plasma
      Colorful moving blobs of plasma
      | preset: Qap | gradient_length: 360

  [1] Aurora
      Shimmering northern lights curtains
      | speed: 2.0 | shimmer: 0.5
```

---

## Modifying Layers

Change properties of an active layer.

### Synopsis

```
uchroma anim set <layer-index> [options]
```

### Examples

```bash
# Change layer 0 speed
uchroma anim set 0 --speed 1.5

# Change layer 1 color scheme
uchroma anim set 1 --color-scheme "#ff0000,#00ff00,#0000ff"
```

---

## Removing Layers

Remove a layer by its z-index.

```bash
# Remove layer at index 0
uchroma anim rm 0

# Remove layer at index 1
uchroma anim remove 1
```

---

## Pause and Stop

```bash
# Toggle pause (freezes animation)
uchroma anim pause

# Stop and clear all layers
uchroma anim stop
```

---

## Built-in Renderers

### Plasma

Classic demoscene plasma effect with flowing colored blobs.

| Parameter         | Type   | Range               | Default       | Description         |
| ----------------- | ------ | ------------------- | ------------- | ------------------- |
| `preset`          | choice | ColorScheme presets | `Qap`         | Color preset        |
| `color_scheme`    | colors | -                   | preset colors | Custom color scheme |
| `gradient_length` | int    | 0+                  | 360           | Gradient resolution |

```bash
uchroma anim add plasma --preset Rainbow
```

### Rainbow (Rainflow)

Simple flowing rainbow colors across the keyboard.

| Parameter | Type | Range | Default | Description                  |
| --------- | ---- | ----- | ------- | ---------------------------- |
| `speed`   | int  | 0-20  | 8       | Animation speed              |
| `stagger` | int  | 0-100 | 4       | Row offset for diagonal flow |

```bash
uchroma anim add rainbow --speed 12 --stagger 8
```

### Aurora

Shimmering northern lights with undulating curtains.

| Parameter        | Type   | Range   | Default           | Description                    |
| ---------------- | ------ | ------- | ----------------- | ------------------------------ |
| `speed`          | float  | 0.2-3.0 | 1.0               | Animation speed                |
| `drift`          | float  | 0.1-1.0 | 0.3               | Horizontal drift amount        |
| `curtain_height` | float  | 0.3-1.0 | 0.7               | Curtain height (0=top, 1=full) |
| `shimmer`        | float  | 0.0-1.0 | 0.3               | High-frequency shimmer         |
| `color_drift`    | float  | 0.1-2.0 | 0.5               | Color shift speed              |
| `color_scheme`   | colors | -       | green/teal/purple | Custom colors                  |

```bash
uchroma anim add aurora --curtain-height 0.5 --shimmer 0.6
```

### Vortex

Hypnotic swirling spiral tunnel effect.

| Parameter        | Type   | Range    | Default               | Description             |
| ---------------- | ------ | -------- | --------------------- | ----------------------- |
| `arm_count`      | int    | 1-6      | 3                     | Number of spiral arms   |
| `twist`          | float  | 0.1-1.0  | 0.3                   | Spiral twist amount     |
| `flow_speed`     | float  | 0.3-3.0  | 1.0                   | Radial flow speed       |
| `flow_direction` | int    | -1, 0, 1 | 1                     | Flow direction (in/out) |
| `rotation_speed` | float  | 0.1-2.0  | 0.5                   | Rotation speed          |
| `center_glow`    | float  | 1.0-5.0  | 3.0                   | Center brightness boost |
| `ring_density`   | float  | 0.2-1.5  | 0.5                   | Ring pattern density    |
| `color_scheme`   | colors | -        | pink/purple/blue/teal | Custom colors           |

```bash
uchroma anim add vortex --arm-count 5 --twist 0.8
```

### Nebula

Flowing cosmic clouds using procedural noise.

| Parameter         | Type   | Range    | Default                | Description                  |
| ----------------- | ------ | -------- | ---------------------- | ---------------------------- |
| `drift_speed`     | float  | 0.1-1.0  | 0.3                    | Cloud movement speed         |
| `scale`           | float  | 0.05-0.4 | 0.15                   | Cloud size scale             |
| `detail`          | int    | 1-3      | 2                      | Noise octaves (detail level) |
| `contrast`        | float  | 0.3-1.0  | 0.6                    | Color contrast               |
| `base_brightness` | float  | 0.3-0.7  | 0.5                    | Minimum brightness           |
| `color_shift`     | float  | 0.0-1.0  | 0.3                    | Color variation amount       |
| `color_scheme`    | colors | -        | purple/pink/cyan/green | Custom colors                |

```bash
uchroma anim add nebula --scale 0.25 --detail 3
```

### Ocean

Rolling waves with foam and caustic highlights.

| Parameter           | Type   | Range   | Default            | Description               |
| ------------------- | ------ | ------- | ------------------ | ------------------------- |
| `wave_speed`        | float  | 0.3-2.5 | 1.0                | Wave animation speed      |
| `wave_height`       | float  | 0.2-1.0 | 0.5                | Wave amplitude            |
| `foam_threshold`    | float  | 0.2-0.8 | 0.5                | Foam appearance threshold |
| `caustic_intensity` | float  | 0.0-0.6 | 0.3                | Caustic light intensity   |
| `saturation`        | float  | 0.4-1.0 | 0.8                | Color saturation          |
| `color_scheme`      | colors | -       | deep blue to white | Custom colors             |

```bash
uchroma anim add ocean --wave-height 0.8 --foam-threshold 0.4
```

### Comets

Bright streaks with glowing trails zooming across.

| Parameter         | Type   | Range   | Default                   | Description            |
| ----------------- | ------ | ------- | ------------------------- | ---------------------- |
| `comet_count`     | int    | 1-6     | 3                         | Number of comets       |
| `speed`           | float  | 0.5-4.0 | 1.5                       | Movement speed         |
| `trail_length`    | int    | 3-15    | 8                         | Trail length in pixels |
| `trail_decay`     | float  | 0.1-0.6 | 0.3                       | Trail fade rate        |
| `head_brightness` | float  | 0.7-1.0 | 1.0                       | Comet head brightness  |
| `color_scheme`    | colors | -       | cyan/magenta/yellow/green | Custom colors          |

```bash
uchroma anim add comets --comet-count 5 --trail-length 12
```

### Embers

Warm glowing particles drifting upward like fireplace embers.

| Parameter         | Type  | Range   | Default   | Description              |
| ----------------- | ----- | ------- | --------- | ------------------------ |
| `particle_count`  | int   | 3-15    | 8         | Number of particles      |
| `drift_speed`     | float | 0.1-1.0 | 0.3       | Upward drift speed       |
| `pulse_speed`     | float | 0.5-4.0 | 1.5       | Brightness pulse speed   |
| `glow_radius`     | float | 1.0-4.0 | 2.0       | Particle glow size       |
| `color`           | color | -       | `#ff6b35` | Ember color              |
| `base_brightness` | float | 0.3-0.8 | 0.6       | Base glow level          |
| `flare_chance`    | float | 0.0-0.1 | 0.02      | Random flare probability |

```bash
uchroma anim add embers --particle-count 12 --color "#ff4400"
```

### Copper Bars

Classic Amiga demoscene raster bar effect.

| Parameter         | Type   | Range               | Default       | Description              |
| ----------------- | ------ | ------------------- | ------------- | ------------------------ |
| `speed`           | float  | 0.2-3.0             | 1.0           | Scroll speed             |
| `wave_amplitude`  | float  | 0.0-2.0             | 0.5           | Wave distortion amount   |
| `wave_frequency`  | float  | 0.2-2.0             | 0.8           | Wave frequency           |
| `band_width`      | int    | 10-100              | 40            | Color band width         |
| `horizontal_wave` | bool   | -                   | false         | Add horizontal variation |
| `preset`          | choice | ColorScheme presets | `Rainbow`     | Color preset             |
| `color_scheme`    | colors | -                   | preset colors | Custom colors            |
| `gradient_length` | int    | 60-720              | 360           | Gradient resolution      |

```bash
uchroma anim add copper_bars --wave-amplitude 1.5 --horizontal-wave
```

### Metaballs

Organic lava-lamp style blobs that merge and split.

| Parameter         | Type   | Range   | Default               | Description             |
| ----------------- | ------ | ------- | --------------------- | ----------------------- |
| `blob_count`      | int    | 2-8     | 4                     | Number of blobs         |
| `speed`           | float  | 0.1-2.0 | 0.5                   | Movement speed          |
| `threshold`       | float  | 0.5-2.0 | 1.0                   | Blob boundary threshold |
| `glow_falloff`    | float  | 1.0-4.0 | 2.0                   | Glow fade rate          |
| `base_brightness` | float  | 0.0-0.4 | 0.2                   | Background brightness   |
| `blob_radius`     | float  | 1.5-5.0 | 3.0                   | Blob size               |
| `color_scheme`    | colors | -       | pink/purple/blue/teal | Custom colors           |

```bash
uchroma anim add metaballs --blob-count 6 --speed 0.8
```

### Kaleidoscope

Rotating symmetric patterns with n-fold symmetry.

| Parameter        | Type   | Range                | Default                 | Description              |
| ---------------- | ------ | -------------------- | ----------------------- | ------------------------ |
| `symmetry`       | int    | 3-12                 | 6                       | Number of symmetry folds |
| `rotation_speed` | float  | 0.1-2.0              | 0.5                     | Rotation speed           |
| `pattern_mode`   | choice | spiral, rings, waves | `spiral`                | Pattern type             |
| `ring_frequency` | float  | 0.2-1.5              | 0.5                     | Ring pattern frequency   |
| `spiral_twist`   | float  | 0.5-5.0              | 2.0                     | Spiral twist amount      |
| `hue_rotation`   | float  | 0.0-120.0            | 30.0                    | Color rotation speed     |
| `saturation`     | float  | 0.5-1.0              | 0.9                     | Color saturation         |
| `color_scheme`   | colors | -                    | pink/yellow/teal/purple | Custom colors            |

```bash
uchroma anim add kaleidoscope --symmetry 8 --pattern-mode rings
```

### Reactive Renderers

These renderers respond to keyboard input. They require a device with key matrix support.

#### Ripple

Ripples of color emanate from pressed keys.

| Parameter      | Type   | Range               | Default | Description        |
| -------------- | ------ | ------------------- | ------- | ------------------ |
| `ripple_width` | int    | 1-5                 | 3       | Ripple ring width  |
| `speed`        | int    | 1-9                 | 5       | Animation speed    |
| `preset`       | choice | ColorScheme presets | -       | Color preset       |
| `random`       | bool   | -                   | true    | Random colors      |
| `color`        | color  | -                   | -       | Fixed ripple color |

```bash
uchroma anim add ripple --speed 7 --ripple-width 4
```

#### Reaction

Keys change color when pressed and fade back.

| Parameter          | Type  | Range | Default | Description   |
| ------------------ | ----- | ----- | ------- | ------------- |
| `speed`            | int   | 1-9   | 6       | Fade speed    |
| `background_color` | color | -     | black   | Resting color |
| `color`            | color | -     | white   | Active color  |

```bash
uchroma anim add reaction --color cyan --background-color "#111111"
```

#### Typewriter

Warm incandescent glow that fades after keypress.

| Parameter         | Type  | Range   | Default   | Description              |
| ----------------- | ----- | ------- | --------- | ------------------------ |
| `glow_color`      | color | -       | `#ffaa44` | Glow color               |
| `decay_time`      | float | 0.5-5.0 | 1.5       | Fade duration (seconds)  |
| `spread`          | float | 0.0-0.6 | 0.3       | Glow spread to neighbors |
| `base_brightness` | float | 0.0-0.3 | 0.15      | Resting brightness       |
| `peak_brightness` | float | 0.7-1.0 | 1.0       | Maximum brightness       |
| `warmth`          | float | 0.0-0.6 | 0.3       | White shift at peak      |

```bash
uchroma anim add typewriter --decay-time 2.0 --spread 0.5
```

---

## Layer Compositing

When multiple layers are active, they are composited in z-order (lowest index on bottom). Each layer
can have opacity and blend mode settings.

**Blend modes** available:

- `normal` - Standard alpha blending
- `screen` - Additive-like brightening
- `soft_light` - Subtle contrast enhancement
- `dodge` - Strong brightening

---

## Related Commands

- [`fx`](effects.md) - Hardware effects (simpler, persistent)
- [`input`](advanced.md#input) - Shortcut for reactive effects
- [`profile`](profiles.md) - Save animation layers in profiles
