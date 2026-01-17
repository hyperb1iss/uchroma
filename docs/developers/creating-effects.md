# Creating Custom Effects

This tutorial walks you through creating a custom lighting effect from scratch. You will learn the
renderer lifecycle, how to draw pixels, and how to expose configurable parameters.

## The Renderer Class

Every effect in uchroma is a subclass of `Renderer`. The base class handles:

- Async task management
- Double-buffered layer allocation
- Frame rate synchronization
- Trait (parameter) observation

You implement three key methods:

```python
class Renderer(HasTraits):
    def init(self, frame) -> bool:
        """Called when the effect is activated. Return True to proceed."""
        pass

    async def draw(self, layer, timestamp) -> bool:
        """Called each frame. Draw to the layer and return True to display."""
        pass

    def finish(self, frame):
        """Called when the effect is deactivated. Clean up resources."""
        pass
```

## Your First Effect: Color Pulse

Let's create a simple pulsing effect that fades between two colors.

### Step 1: Create the File

Create a new file at `uchroma/fxlib/pulse.py`:

```python
#
# Copyright (C) 2026 UChroma Developers - LGPL-3.0-or-later
#
"""
Pulse - A simple pulsing color effect.
"""

import math

from traitlets import Float

from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait


class Pulse(Renderer):
    """A smooth pulsing effect between two colors."""

    # Metadata - displayed in the UI
    meta = RendererMeta(
        "Pulse",                      # Display name
        "Smooth pulsing between two colors",  # Description
        "Your Name",                  # Author
        "1.0",                        # Version
    )

    # Configurable traits (exposed to UI)
    speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)
    color1 = ColorTrait(default_value="purple").tag(config=True)
    color2 = ColorTrait(default_value="cyan").tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._time = 0.0
        self.fps = 15  # 15 frames per second

    def init(self, frame) -> bool:
        """Initialize the effect."""
        self._time = 0.0
        return True

    async def draw(self, layer, timestamp) -> bool:
        """Draw a single frame."""
        # Calculate blend factor using sine wave (0 to 1)
        t = (math.sin(self._time * self.speed * math.pi) + 1) / 2

        # Get RGB values from colors
        r1, g1, b1 = self.color1.rgb
        r2, g2, b2 = self.color2.rgb

        # Interpolate between colors
        r = r1 + (r2 - r1) * t
        g = g1 + (g2 - g1) * t
        b = b1 + (b2 - b1) * t

        # Fill the entire layer
        for row in range(layer.height):
            for col in range(layer.width):
                layer.matrix[row][col] = (r, g, b, 1.0)

        # Advance time
        self._time += 1 / self.fps

        return True

    def finish(self, frame):
        """Clean up when effect is deactivated."""
        pass
```

### Step 2: Register the Effect

Add your effect to the plugin entry point in `pyproject.toml`:

```toml
[project.entry-points."uchroma.plugins"]
renderers = "uchroma.fxlib"
```

The `renderers` entry point loads all `Renderer` subclasses from the specified module. Since your
file is in `uchroma/fxlib/`, it will be discovered automatically.

### Step 3: Test Your Effect

Rebuild and run the daemon:

```bash
make rebuild
make server-debug
```

In another terminal, add your effect:

```bash
uv run uchroma layer add uchroma.fxlib.pulse.Pulse
```

Or use the GTK frontend to select it from the effect list.

## Understanding the Code

### RendererMeta

```python
meta = RendererMeta(
    "Pulse",                          # display_name
    "Smooth pulsing between colors",  # description
    "Your Name",                      # author
    "1.0",                            # version
)
```

The metadata is displayed in the UI and helps users understand what your effect does.

### Configurable Traits

```python
speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)
color1 = ColorTrait(default_value="purple").tag(config=True)
```

Traits tagged with `config=True` are:

- Exposed in the GTK UI as sliders/pickers
- Accessible via D-Bus API
- Saved to user preferences

### Frame Rate

```python
self.fps = 15  # Set in __init__
```

The `fps` trait controls how often `draw()` is called. Higher values = smoother animation but more
CPU usage. The maximum is 30 FPS.

### The Layer Matrix

```python
layer.matrix[row][col] = (r, g, b, a)
```

The layer's backing matrix is a numpy array of shape `(height, width, 4)` with dtype `float64`.
Values are in the range 0.0 to 1.0 for each RGBA channel.

## Example: Wave Effect

Here is a more complex effect that creates a moving wave pattern:

```python
import math
from traitlets import Float, Int

from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait


class Wave(Renderer):
    """Colorful waves moving across the device."""

    meta = RendererMeta(
        "Wave",
        "Colorful waves sweeping across",
        "Your Name",
        "1.0",
    )

    # Configurable parameters
    speed = Float(default_value=2.0, min=0.5, max=10.0).tag(config=True)
    wavelength = Float(default_value=4.0, min=1.0, max=20.0).tag(config=True)
    direction = Int(default_value=1, min=-1, max=1).tag(config=True)

    color_scheme = ColorSchemeTrait(
        minlen=2,
        default_value=list(ColorScheme.Rainbow.value)
    ).tag(config=True)

    preset = ColorPresetTrait(
        ColorScheme,
        default_value=ColorScheme.Rainbow
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._time = 0.0
        self._gradient = None
        self.fps = 20

    def _gen_gradient(self):
        """Generate gradient from color scheme."""
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    def init(self, frame) -> bool:
        self._time = 0.0
        self._gen_gradient()
        return True

    async def draw(self, layer, timestamp) -> bool:
        if self._gradient is None:
            return False

        gradient = self._gradient
        grad_len = len(gradient)
        width = layer.width
        height = layer.height

        for row in range(height):
            for col in range(width):
                # Calculate wave position
                wave_pos = col / self.wavelength + self._time * self.speed * self.direction

                # Map to gradient index
                idx = int((wave_pos * 20) % grad_len)
                color = gradient[idx]

                layer.matrix[row][col] = (*color.rgb, 1.0)

        self._time += 1 / self.fps
        return True
```

## Example: Keyboard-Reactive Effect

Effects can react to keyboard input. Here is a simple key highlight effect:

```python
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait


class KeyHighlight(Renderer):
    """Highlights keys when pressed."""

    meta = RendererMeta(
        "Key Highlight",
        "Keys light up when pressed",
        "Your Name",
        "1.0",
    )

    color = ColorTrait(default_value="white").tag(config=True)
    fade_speed = Float(default_value=0.5, min=0.1, max=2.0).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fps = 30
        self.key_expire_time = 0.5  # Keep events for 0.5 seconds

    def init(self, frame) -> bool:
        # Check if device supports key input
        if not self.has_key_input:
            self.logger.error("Device does not support key input")
            return False
        return True

    async def draw(self, layer, timestamp) -> bool:
        # Wait for keyboard events
        events = await self.get_input_events()

        if not events:
            return False

        for event in events:
            if event.coords is None:
                continue

            # Calculate fade based on time remaining
            intensity = event.percent_complete

            # Draw the key
            for coord in event.coords:
                r, g, b = self.color.rgb
                layer.put(coord.y, coord.x, (r * intensity, g * intensity, b * intensity, 1.0))

        return True
```

Key input properties:

| Property             | Description                           |
| -------------------- | ------------------------------------- |
| `has_key_input`      | True if device supports key events    |
| `key_expire_time`    | How long to keep events (seconds)     |
| `get_input_events()` | Async method returning list of events |

Each `KeyInputEvent` contains:

| Field              | Description                   |
| ------------------ | ----------------------------- |
| `timestamp`        | When the key was pressed      |
| `keycode`          | The key name (e.g., "KEY_A")  |
| `coords`           | List of (row, col) positions  |
| `percent_complete` | 0.0 to 1.0, time until expiry |
| `data`             | Dict for storing custom data  |

## Best Practices

### Do

- Set `fps` appropriately (15-20 for most effects, 30 for reactive)
- Return `False` from `draw()` if there is nothing to display
- Use numpy operations for bulk pixel manipulation
- Observe traits to regenerate gradients when colors change

### Do Not

- Block in `draw()` - it is an async method
- Create allocations in the draw loop
- Exceed 30 FPS - it will not display faster
- Forget to return `True` from `init()`

### Performance Tips

```python
# Instead of nested loops:
for row in range(height):
    for col in range(width):
        layer.matrix[row][col] = color

# Use numpy broadcasting:
layer.matrix[:, :] = color  # Much faster!
```

## Effect Registration

Effects are discovered via Python entry points. When the daemon starts:

1. Loads all modules registered under `uchroma.plugins`
2. Finds all `Renderer` subclasses
3. Validates each has proper `meta` defined
4. Registers them with `AnimationManager`

Your effect key will be `module.ClassName`, e.g., `uchroma.fxlib.pulse.Pulse`.

## Next Steps

- [Layer API](./layer-api) - Full drawing primitive reference
- [Traits](./traits) - All available trait types
- [Colors](./colors) - Color handling and gradients
- [Advanced](./advanced) - Rust extensions, D-Bus API
