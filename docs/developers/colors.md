# Color System

uchroma uses [ColorAide](https://facelessuser.github.io/coloraide/) for color manipulation, wrapped
with a grapefruit-compatible API for convenience. This guide covers color parsing, gradients, and
predefined schemes.

## Color Parsing

### to_color()

The `to_color()` function converts various color representations to `Color` objects:

```python
from uchroma.color import to_color

# Named colors
color = to_color("red")
color = to_color("cornflowerblue")

# Hex codes
color = to_color("#ff0000")
color = to_color("#f00")      # Short form
color = to_color("#ff000080") # With alpha

# RGB tuples (floats 0-1)
color = to_color((1.0, 0.0, 0.0))
color = to_color((1.0, 0.0, 0.0, 0.5))  # With alpha

# RGB tuples (ints 0-255)
color = to_color((255, 0, 0))

# Multiple colors at once
colors = to_color("red", "green", "blue")  # Returns list
```

### Color Objects

The `Color` class (from `uchroma.colorlib`) provides grapefruit-style methods:

```python
from uchroma.colorlib import Color

# Factory methods
color = Color.NewFromHtml("purple")
color = Color.NewFromRgb(1.0, 0.0, 0.5)        # RGB floats
color = Color.NewFromHsv(270, 1.0, 1.0)        # HSV (h: 0-360, s/v: 0-1)
color = Color.NewFromHsl(270, 1.0, 0.5)        # HSL (h: 0-360, s/l: 0-1)

# With alpha
color = Color.NewFromRgb(1.0, 0.0, 0.5, 0.75)

# From ColorAide color space
color = Color("oklch", [0.7, 0.15, 30])
```

### Color Properties

```python
color = to_color("purple")

# RGB values (0-1 floats)
color.rgb      # (0.5, 0.0, 0.5)
color.rgba     # (0.5, 0.0, 0.5, 1.0)

# HSL values
color.hsl      # (300.0, 1.0, 0.25)
color.hsla     # (300.0, 1.0, 0.25, 1.0)

# HSV values
color.hsv      # (300.0, 1.0, 0.5)

# Integer tuple (0-255)
color.intTuple # (128, 0, 128, 255)

# HTML hex string
color.html     # #800080

# Alpha channel
color.alpha()  # 1.0
```

### Color Manipulation

```python
color = to_color("blue")

# Modify hue (returns new color)
red = color.ColorWithHue(0)
green = color.ColorWithHue(120)

# Modify saturation (0-1)
muted = color.ColorWithSaturation(0.5)

# Modify lightness (0-1)
light = color.ColorWithLightness(0.8)
dark = color.ColorWithLightness(0.2)

# Modify alpha
transparent = color.ColorWithAlpha(0.5)

# Blend with another color
mixed = color.blend(to_color("red"), 0.5)  # 50% blend
```

### Color Schemes

Generate related colors:

```python
color = to_color("purple")

# Analogous (similar hues)
c1, c2 = color.AnalogousScheme(angle=30)

# Triadic (evenly spaced)
c1, c2 = color.TriadicScheme(angle=120)

# Complementary (opposite)
complement = color.ComplementaryScheme()
```

## ColorUtils

The `ColorUtils` class provides gradient generation and color utilities:

```python
from uchroma.color import ColorUtils
```

### Gradients

#### hue_gradient()

Generate a gradient spanning all hues:

```python
# Full rainbow, 360 steps
gradient = ColorUtils.hue_gradient(start=0.0, length=360)

# Half rainbow starting at blue
gradient = ColorUtils.hue_gradient(start=240, length=180)
```

#### hsv_gradient()

Smooth gradient between two colors in HSV space:

```python
gradient = ColorUtils.hsv_gradient(
    color1="red",
    color2="blue",
    steps=100
)
```

#### gradient()

Multi-color gradient with automatic looping:

```python
# Rainbow gradient
gradient = ColorUtils.gradient(
    360,                          # Number of steps
    "red", "yellow", "green",     # Color stops
    "cyan", "blue", "magenta",
    loop=True                     # Connect end to start
)

# Non-looping gradient
gradient = ColorUtils.gradient(
    100,
    "#000000", "#ffffff",
    loop=False
)
```

### Color Generators

Infinite generators for continuous color streams:

```python
# Rainbow colors
gen = ColorUtils.rainbow_generator(
    randomize=False,   # Sequential vs random
    alternate=False,   # Alternating direction
    steps=33,          # Gradient smoothness
    rgb=False          # Return Color objects vs RGB tuples
)

for _ in range(10):
    color = next(gen)

# Random colors (golden ratio distribution)
gen = ColorUtils.random_generator(rgb=False)

# Color scheme generator
gen = ColorUtils.scheme_generator(
    color="blue",
    base_color="black",
    randomize=False,
    alternate=True,
    steps=11
)
```

### Color Utilities

```python
# Relative luminance (WCAG 2.0)
lum = ColorUtils.luminance("white")  # 1.0
lum = ColorUtils.luminance("black")  # 0.0

# Contrast ratio (WCAG 2.0)
ratio = ColorUtils.contrast_ratio("white", "black")  # 21.0

# Invert a color
inverted = ColorUtils.inverse("red")  # cyan

# Increase contrast for visibility
adjusted = ColorUtils.increase_contrast("darkgray")
```

## Predefined Color Schemes

The `ColorScheme` enum provides curated color palettes:

```python
from uchroma.color import ColorScheme

# Access colors
colors = ColorScheme.Rainbow.value
# ("red", "yellow", "lime", "aqua", "blue", "magenta")

# Generate gradient
gradient = ColorScheme.Neon.gradient(length=360)

# Use in traits
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait

preset = ColorPresetTrait(ColorScheme, default_value=ColorScheme.Cyberpunk)
scheme = ColorSchemeTrait(default_value=list(ColorScheme.Aurora.value))
```

### Available Schemes

#### Original

| Name       | Description                        |
| ---------- | ---------------------------------- |
| `Emma`     | Purple, pink, gold                 |
| `Best`     | Teal, green, red accent            |
| `Variety`  | Red, purple, cyan mix              |
| `Redd`     | Red, orange, teal                  |
| `Bluticas` | Blue, cyan, pink, gold             |
| `Newer`    | Dark blue to green                 |
| `Bright`   | Yellow, orange, pink, purple, blue |
| `Qap`      | Navy, red, orange, cream, teal     |
| `Rainbow`  | Classic rainbow                    |

#### Dark Purple / Synthwave

| Name           | Description          |
| -------------- | -------------------- |
| `Nightshade`   | Deep purple to coral |
| `Ultraviolet`  | Purple neon glow     |
| `DeepAmethyst` | Rich purple gradient |
| `Obsidian`     | Black to purple      |
| `Twilight`     | Muted purple pastels |
| `Cosmos`       | Deep space purples   |
| `Vaporwave`    | Magenta and cyan     |
| `Witching`     | Dark magic purple    |

#### Cyberpunk / Neon

| Name        | Description             |
| ----------- | ----------------------- |
| `Neon`      | Bright neon primaries   |
| `Cyberpunk` | Red, cyan, magenta      |
| `Hotline`   | 80s synthwave           |
| `Outrun`    | Purple, magenta, orange |
| `Glitch`    | Digital error colors    |

#### Nature / Organic

| Name     | Description             |
| -------- | ----------------------- |
| `Forest` | Green forest tones      |
| `Ocean`  | Deep blue to light blue |
| `Sunset` | Orange to coral         |
| `Aurora` | Teal to green           |
| `Sakura` | Cherry blossom pink     |
| `Moss`   | Earthy greens           |

#### Cool / Icy

| Name      | Description          |
| --------- | -------------------- |
| `Arctic`  | Light blue icy tones |
| `Glacier` | Cool grays and blues |
| `Frost`   | Pastel winter        |

#### Warm / Fire

| Name      | Description          |
| --------- | -------------------- |
| `Ember`   | Dark red to orange   |
| `Lava`    | Black to yellow fire |
| `Inferno` | Deep red to gold     |

#### Pastel / Soft

| Name        | Description    |
| ----------- | -------------- |
| `Candy`     | Soft pinks     |
| `Dreamy`    | Pastel rainbow |
| `Bubblegum` | Bright pastels |
| `Lavender`  | Purple pastels |

#### Monochrome

| Name        | Description       |
| ----------- | ----------------- |
| `Grayscale` | Black to white    |
| `Purple`    | Purple monochrome |
| `Emerald`   | Green monochrome  |

## Using Colors in Effects

### With ColorTrait

```python
from uchroma.traits import ColorTrait

class MyEffect(Renderer):
    color = ColorTrait(default_value="purple").tag(config=True)

    async def draw(self, layer, timestamp):
        r, g, b = self.color.rgb
        layer.matrix[:, :] = (r, g, b, 1.0)
        return True
```

### With ColorSchemeTrait

```python
from uchroma.traits import ColorSchemeTrait
from uchroma.color import ColorScheme, ColorUtils

class MyEffect(Renderer):
    color_scheme = ColorSchemeTrait(
        minlen=2,
        default_value=list(ColorScheme.Neon.value)
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gradient = None

    @observe("color_scheme")
    def _scheme_changed(self, change):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)

    def init(self, frame):
        self._gradient = ColorUtils.gradient(360, *self.color_scheme)
        return True

    async def draw(self, layer, timestamp):
        for col in range(layer.width):
            idx = int(col / layer.width * len(self._gradient))
            color = self._gradient[idx]
            layer.matrix[:, col] = (*color.rgb, 1.0)
        return True
```

### With ColorPresetTrait

```python
from traitlets import observe
from uchroma.traits import ColorPresetTrait, ColorSchemeTrait
from uchroma.color import ColorScheme, ColorUtils

class MyEffect(Renderer):
    # Preset dropdown in UI
    preset = ColorPresetTrait(
        ColorScheme,
        default_value=ColorScheme.Rainbow
    ).tag(config=True)

    # Underlying color list
    color_scheme = ColorSchemeTrait(
        minlen=2,
        default_value=list(ColorScheme.Rainbow.value)
    ).tag(config=True)

    @observe("preset")
    def _preset_changed(self, change):
        with self.hold_trait_notifications():
            if change.new is not None:
                self.color_scheme = list(change.new.value)
```

## Interference Patterns

Generate rainbow colors using sine wave interference:

```python
gradient = ColorUtils.interference(
    length=100,
    freq1=0.3,      # Red frequency
    freq2=0.3,      # Green frequency
    freq3=0.3,      # Blue frequency
    phase1=0.0,     # Red phase
    phase2=2.0,     # Green phase
    phase3=4.0,     # Blue phase
    center=128.0,   # Midpoint
    width=127.0     # Amplitude
)
```

## Color Conversion

### RGB to Int Tuple

```python
from uchroma.color import to_rgb

# Various inputs to (r, g, b) int tuple
rgb = to_rgb("red")           # (255, 0, 0)
rgb = to_rgb("#00ff00")       # (0, 255, 0)
rgb = to_rgb((0.0, 0.0, 1.0)) # (0, 0, 255)

# Convert Color object
color = to_color("purple")
rgb = to_rgb(color)           # (128, 0, 128)
```

### Alpha Compositing

```python
import numpy as np
from uchroma.color import ColorUtils

# Composite RGBA array onto background
rgba_array = np.zeros((6, 22, 4), dtype=np.float64)
rgb_result = ColorUtils.rgba2rgb(rgba_array, bg_color="black")
```

## Next Steps

- [Traits](./traits) - Using ColorTrait and ColorSchemeTrait
- [Layer API](./layer-api) - Drawing with colors
- [Creating Effects](./creating-effects) - Full renderer tutorial
