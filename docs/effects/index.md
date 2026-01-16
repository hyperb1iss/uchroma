# Effects Gallery

uchroma supports two fundamentally different types of lighting effects: **hardware effects** that
run directly on your device's firmware, and **custom animations** that are rendered by the uchroma
daemon on your computer.

## Hardware Effects vs Custom Animations

| Aspect             | Hardware Effects                 | Custom Animations                |
| ------------------ | -------------------------------- | -------------------------------- |
| **Execution**      | Runs on device firmware          | Rendered by uchromad on host     |
| **CPU Usage**      | Zero - device handles everything | Low - daemon runs at 15-30 FPS   |
| **Persistence**    | Survives daemon restart/crash    | Requires daemon to be running    |
| **Complexity**     | Simple, predefined patterns      | Rich, layered, reactive          |
| **Customization**  | Limited parameters               | Full control via traitlets       |
| **Key Reactivity** | Basic (reactive, ripple)         | Advanced (ripple, typewriter)    |
| **Layering**       | Single effect only               | Multiple layers with blend modes |

## When to Use Which

### Choose Hardware Effects When:

- You want zero CPU overhead
- You need the effect to persist when the daemon isn't running
- A simple built-in effect meets your needs
- Battery life matters (laptops, wireless devices)

### Choose Custom Animations When:

- You want rich, complex visual effects
- You need multiple layered effects with blending
- You want effects that react to your typing
- You want fine-grained control over parameters
- You're creating a custom look for your setup

## Quick Reference

### Hardware Effects

| Effect                               | Description         | Key Parameters                 |
| ------------------------------------ | ------------------- | ------------------------------ |
| [Static](./hardware.md#static)       | Solid color         | `color`                        |
| [Wave](./hardware.md#wave)           | Moving rainbow wave | `direction`                    |
| [Spectrum](./hardware.md#spectrum)   | Slow color cycling  | -                              |
| [Breathe](./hardware.md#breathe)     | Pulsing colors      | `colors` (0-2)                 |
| [Reactive](./hardware.md#reactive)   | Keys light on press | `color`, `speed`               |
| [Starlight](./hardware.md#starlight) | Sparkling effect    | `colors`, `speed`              |
| [Ripple](./hardware.md#ripple)       | Keypress ripples    | `color`, `speed`               |
| [Fire](./hardware.md#fire)           | Animated flames     | `color`, `speed`               |
| [Sweep](./hardware.md#sweep)         | Color sweep         | `color`, `direction`, `speed`  |
| [Morph](./hardware.md#morph)         | Color morphing      | `color`, `base_color`, `speed` |

### Custom Animations

| Renderer                                 | Description                 | Category  |
| ---------------------------------------- | --------------------------- | --------- |
| [Plasma](./custom.md#plasma)             | Classic demoscene plasma    | Ambient   |
| [Rainbow](./custom.md#rainbow)           | Flowing HSV gradient        | Ambient   |
| [Aurora](./custom.md#aurora)             | Northern lights curtains    | Ambient   |
| [Nebula](./custom.md#nebula)             | Cosmic cloud formations     | Ambient   |
| [Ocean](./custom.md#ocean)               | Rolling waves with caustics | Ambient   |
| [Vortex](./custom.md#vortex)             | Swirling spiral tunnel      | Ambient   |
| [Copper Bars](./custom.md#copper-bars)   | Amiga-style raster bars     | Retro     |
| [Kaleidoscope](./custom.md#kaleidoscope) | Rotating symmetry           | Geometric |
| [Metaballs](./custom.md#metaballs)       | Organic lava lamp blobs     | Organic   |
| [Comets](./custom.md#comets)             | Streaking light trails      | Motion    |
| [Embers](./custom.md#embers)             | Warm floating particles     | Particle  |
| [Ripple](./custom.md#ripple-custom)      | Keypress ripples            | Reactive  |
| [Reaction](./custom.md#reaction)         | Key color change            | Reactive  |
| [Typewriter](./custom.md#typewriter)     | Warm key glow fade          | Reactive  |

## CLI Commands

### Hardware Effects

```bash
# List available effects
uchroma fx --list

# Set an effect
uchroma fx static --color '#ff0000'
uchroma fx wave --direction left
uchroma fx breathe --colors '#ff00ff' '#00ffff'

# Disable effects
uchroma fx disable
```

### Custom Animations

```bash
# List available renderers
uchroma anim --list

# Add a renderer layer
uchroma anim add plasma --preset sunset
uchroma anim add aurora --speed 1.5

# Show active layers
uchroma anim show

# Modify a layer
uchroma anim set 0 --speed 2.0

# Remove a layer
uchroma anim rm 0

# Stop all animations
uchroma anim stop
```

## Layering and Blending

Custom animations can be stacked in layers with blend modes, creating complex visual effects:

```bash
# Create a layered effect
uchroma anim add aurora --speed 0.5   # Base layer (z=0)
uchroma anim add ripple                # React to keys (z=1)
```

Each layer has a z-index determining its stack position. Higher z-index layers render on top. See
[Layer Compositing](../developers/architecture.md) for details on blend modes.

## Device Support

Not all devices support all effects. Hardware effect availability depends on the device's firmware.
Custom animations work on any device with an addressable LED matrix.

To check what your device supports:

```bash
# See available hardware effects
uchroma fx --list

# See device capabilities
uchroma devices --verbose
```
