# Configuration with Traitlets

Traitlets provide type-safe, observable properties for your renderers. When you tag a trait with
`config=True`, it becomes:

- Editable in the GTK UI
- Accessible via D-Bus API
- Automatically saved to user preferences

## Basic Usage

```python
from traitlets import Float, Int, Bool
from uchroma.renderer import Renderer, RendererMeta


class MyEffect(Renderer):
    meta = RendererMeta("My Effect", "Description", "Author", "1.0")

    # Configurable traits
    speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)
    intensity = Int(default_value=50, min=0, max=100).tag(config=True)
    enabled = Bool(default_value=True).tag(config=True)
```

## Built-in Trait Types

### Numeric Traits

#### Float

Floating-point numbers with optional bounds.

```python
from traitlets import Float

# Basic usage
brightness = Float(default_value=1.0).tag(config=True)

# With bounds
speed = Float(default_value=1.0, min=0.1, max=10.0).tag(config=True)

# Allow None
opacity = Float(default_value=1.0, allow_none=True).tag(config=True)
```

#### Int

Integer values with optional bounds.

```python
from traitlets import Int

# Basic usage
count = Int(default_value=5).tag(config=True)

# With bounds
level = Int(default_value=50, min=0, max=100).tag(config=True)
```

### Boolean Trait

```python
from traitlets import Bool

# Toggle option
random_colors = Bool(default_value=False).tag(config=True)
```

### String Traits

#### Unicode

General string values.

```python
from traitlets import Unicode

name = Unicode(default_value="default").tag(config=True)
```

#### CaselessStrEnum

String limited to specific values (case-insensitive).

```python
from traitlets import CaselessStrEnum

direction = CaselessStrEnum(
    values=["left", "right", "up", "down"],
    default_value="right"
).tag(config=True)
```

### Container Traits

#### List

A list of values.

```python
from traitlets import List, Float

# List of floats
points = List(Float(), default_value=[0.0, 0.5, 1.0]).tag(config=True)
```

## UChroma Custom Traits

These are defined in `uchroma/traits.py`:

### ColorTrait

A single color value supporting multiple input formats.

```python
from uchroma.traits import ColorTrait

# Default to named color
color = ColorTrait(default_value="purple").tag(config=True)

# Default to hex
highlight = ColorTrait(default_value="#ff00ff").tag(config=True)

# Allow None
accent = ColorTrait(allow_none=True).tag(config=True)
```

**Accepted Formats:**

- Color names: `"red"`, `"cornflowerblue"`
- Hex codes: `"#ff0000"`, `"#f00"`
- RGB tuples: `(1.0, 0.0, 0.0)` or `(255, 0, 0)`
- Color objects: `Color.NewFromHsv(180, 1.0, 1.0)`

### ColorSchemeTrait

A list of colors for gradients and palettes.

```python
from uchroma.traits import ColorSchemeTrait
from uchroma.color import ColorScheme

# Custom colors
color_scheme = ColorSchemeTrait(
    minlen=2,
    default_value=["#ff0000", "#00ff00", "#0000ff"]
).tag(config=True)

# From predefined scheme
color_scheme = ColorSchemeTrait(
    minlen=2,
    default_value=list(ColorScheme.Neon.value)
).tag(config=True)
```

### ColorPresetTrait

A dropdown selection from a predefined color scheme enum.

```python
from uchroma.traits import ColorPresetTrait
from uchroma.color import ColorScheme

# Preset selector
preset = ColorPresetTrait(
    ColorScheme,
    default_value=ColorScheme.Rainbow
).tag(config=True)
```

This creates a dropdown in the UI with all values from `ColorScheme`.

### DefaultCaselessStrEnum

Like `CaselessStrEnum` but with better default handling.

```python
from uchroma.traits import DefaultCaselessStrEnum
from uchroma.blending import BlendOp

# Blend mode selector
blend_mode = DefaultCaselessStrEnum(
    BlendOp.get_modes(),
    default_value="screen",
    allow_none=False
).tag(config=True)
```

## Observing Changes

React to trait changes with the `@observe` decorator:

```python
from traitlets import Float, observe


class MyEffect(Renderer):
    speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)
    color_scheme = ColorSchemeTrait(minlen=2).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None

    @observe("speed")
    def _speed_changed(self, change):
        """Called when speed changes."""
        self.logger.info(f"Speed changed: {change.old} -> {change.new}")

    @observe("color_scheme")
    def _colors_changed(self, change):
        """Regenerate gradient when colors change."""
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    # Observe multiple traits
    @observe("speed", "color_scheme")
    def _params_changed(self, change):
        """Called when any listed trait changes."""
        self.logger.info(f"{change.name} changed")
```

**The `change` object contains:**

| Attribute | Description                     |
| --------- | ------------------------------- |
| `name`    | Name of the trait that changed  |
| `old`     | Previous value                  |
| `new`     | New value                       |
| `owner`   | The object containing the trait |

## Suppressing Notifications

When updating multiple related traits, suppress intermediate notifications:

```python
@observe("preset")
def _preset_changed(self, change):
    with self.hold_trait_notifications():
        # These won't trigger observers until the block exits
        self.color_scheme = list(change.new.value)
        self.speed = 1.0
        self._regenerate_gradient()
```

## Built-in Renderer Traits

The base `Renderer` class includes these traits:

| Trait              | Type       | Default  | Description                |
| ------------------ | ---------- | -------- | -------------------------- |
| `fps`              | Float      | 15.0     | Frames per second (0-30)   |
| `blend_mode`       | Enum       | "screen" | Layer blending mode        |
| `opacity`          | Float      | 1.0      | Layer opacity (0-1)        |
| `background_color` | ColorTrait | None     | Background for compositing |

## Example: Complete Effect with Traits

```python
from traitlets import Float, Int, Bool, observe

from uchroma.color import ColorScheme, ColorUtils
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait, ColorTrait


class ConfigurableWave(Renderer):
    """A highly configurable wave effect."""

    meta = RendererMeta(
        "Configurable Wave",
        "Waves with many options",
        "Your Name",
        "1.0",
    )

    # Speed and movement
    speed = Float(default_value=2.0, min=0.1, max=10.0).tag(config=True)
    wavelength = Float(default_value=5.0, min=1.0, max=20.0).tag(config=True)
    amplitude = Float(default_value=1.0, min=0.1, max=2.0).tag(config=True)

    # Color options
    color_scheme = ColorSchemeTrait(
        minlen=2,
        default_value=list(ColorScheme.Rainbow.value)
    ).tag(config=True)

    preset = ColorPresetTrait(
        ColorScheme,
        default_value=ColorScheme.Rainbow
    ).tag(config=True)

    # Toggle options
    vertical = Bool(default_value=False).tag(config=True)
    bidirectional = Bool(default_value=False).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None
        self._time = 0.0
        self.fps = 20

    def _gen_gradient(self):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    @observe("color_scheme")
    def _scheme_changed(self, change):
        self._gen_gradient()

    @observe("preset")
    def _preset_changed(self, change):
        with self.hold_trait_notifications():
            if change.new is not None:
                self.color_scheme = list(change.new.value)

    def init(self, frame) -> bool:
        self._time = 0.0
        self._gen_gradient()
        return True

    async def draw(self, layer, timestamp) -> bool:
        import math

        if self._gradient is None:
            return False

        gradient = self._gradient
        grad_len = len(gradient)

        for row in range(layer.height):
            for col in range(layer.width):
                # Choose wave axis
                if self.vertical:
                    pos = row / self.wavelength
                else:
                    pos = col / self.wavelength

                # Calculate wave
                wave = math.sin(pos * math.pi * 2 + self._time * self.speed)
                wave *= self.amplitude

                if self.bidirectional:
                    wave = abs(wave)

                # Map to gradient
                idx = int((wave + 1) / 2 * (grad_len - 1)) % grad_len
                color = gradient[idx]

                layer.matrix[row][col] = (*color.rgb, 1.0)

        self._time += 1 / self.fps
        return True
```

## Trait Metadata

Add custom metadata to traits for UI hints:

```python
speed = Float(
    default_value=1.0,
    min=0.1,
    max=5.0
).tag(
    config=True,
    label="Animation Speed",
    description="How fast the effect animates",
    unit="x"
)
```

## Validation

Traits automatically validate values:

```python
# This will raise TraitError
renderer.speed = -5.0  # Below min
renderer.speed = "fast"  # Wrong type
```

Custom validation:

```python
from traitlets import validate


class MyRenderer(Renderer):
    count = Int(default_value=5).tag(config=True)

    @validate("count")
    def _validate_count(self, proposal):
        if proposal["value"] % 2 != 0:
            raise TraitError("count must be even")
        return proposal["value"]
```

## D-Bus Integration

Traits tagged with `config=True` are automatically exposed via D-Bus:

```python
# Get available traits for a renderer
client = UChromaClient()
device = client.get_device(0)
renderers = device.AvailableRenderers
print(renderers["uchroma.fxlib.plasma.Plasma"]["traits"])

# Set traits when adding a renderer
device.AddRenderer("uchroma.fxlib.plasma.Plasma", -1, {
    "speed": 2.0,
    "preset": "Neon"
})

# Modify traits on an active layer
device.SetLayerTraits(0, {"speed": 3.0})
```

## Next Steps

- [Colors](./colors) - Color handling and gradients
- [Layer API](./layer-api) - Drawing primitives
- [Creating Effects](./creating-effects) - Full renderer tutorial
