# Layer API Reference

The `Layer` class provides drawing primitives for custom effects. Each layer is a 2D surface backed
by a numpy array that you can draw to using high-level methods or direct matrix access.

## Layer Basics

### Dimensions

```python
layer.width   # Number of columns (X axis)
layer.height  # Number of rows (Y axis)
```

### Coordinate System

Layers use a row-major coordinate system where:

- **Row** (Y) is the first index, starting from 0 at the top
- **Column** (X) is the second index, starting from 0 at the left

```
         col 0   col 1   col 2   col 3  ...
        ┌───────┬───────┬───────┬───────┐
row 0   │ (0,0) │ (0,1) │ (0,2) │ (0,3) │
        ├───────┼───────┼───────┼───────┤
row 1   │ (1,0) │ (1,1) │ (1,2) │ (1,3) │
        ├───────┼───────┼───────┼───────┤
row 2   │ (2,0) │ (2,1) │ (2,2) │ (2,3) │
        └───────┴───────┴───────┴───────┘
```

### Color Format

All colors are RGBA with values in the range **0.0 to 1.0**:

```python
(red, green, blue, alpha)
# Example: semi-transparent red
(1.0, 0.0, 0.0, 0.5)
```

## Pixel Operations

### put()

Set the color of one or more pixels.

```python
layer.put(row: int, col: int, *color: ColorType) -> Layer
```

**Parameters:**

- `row` - Y coordinate
- `col` - Starting X coordinate
- `color` - One or more colors (placed consecutively)

**Examples:**

```python
# Single pixel
layer.put(0, 0, "red")
layer.put(0, 0, (1.0, 0.0, 0.0, 1.0))

# Multiple pixels in a row
layer.put(0, 0, "red", "green", "blue")  # Fills cols 0, 1, 2

# Using Color objects
from uchroma.color import to_color
color = to_color("#ff00ff")
layer.put(2, 5, color)
```

### get()

Get the color of a pixel.

```python
layer.get(row: int, col: int) -> Color
```

**Example:**

```python
color = layer.get(0, 0)
print(color.rgb)   # (1.0, 0.0, 0.0)
print(color.html)  # #ff0000
```

### put_all()

Set all pixels from a 2D list.

```python
layer.put_all(data: list) -> Layer
```

**Example:**

```python
data = [
    ["red", "green", "blue"],  # Row 0
    ["cyan", "magenta", "yellow"],  # Row 1
]
layer.put_all(data)
```

### clear()

Clear the layer (set all pixels to transparent black).

```python
layer.clear() -> Layer
```

## Shape Drawing

All shape methods support anti-aliasing for smooth edges.

### circle()

Draw a circle.

```python
layer.circle(
    row: int,           # Center row (Y)
    col: int,           # Center column (X)
    radius: float,      # Radius
    color: ColorType,   # Color
    fill: bool = False, # Filled or outline
    alpha: float = 1.0  # Opacity
) -> Layer
```

**Examples:**

```python
# Outline circle
layer.circle(3, 11, 3, "red")

# Filled circle
layer.circle(3, 11, 3, "blue", fill=True)

# Semi-transparent filled circle
layer.circle(3, 11, 3, "green", fill=True, alpha=0.5)
```

### ellipse()

Draw an ellipse.

```python
layer.ellipse(
    row: int,           # Center row (Y)
    col: int,           # Center column (X)
    radius_r: float,    # Radius on Y axis
    radius_c: float,    # Radius on X axis
    color: ColorType,   # Color
    fill: bool = False, # Filled or outline
    alpha: float = 1.0  # Opacity
) -> Layer
```

**Examples:**

```python
# Horizontal ellipse
layer.ellipse(3, 11, 2, 5, "purple")

# Vertical filled ellipse
layer.ellipse(3, 11, 5, 2, "orange", fill=True)
```

### line()

Draw an anti-aliased line between two points.

```python
layer.line(
    row1: int,          # Start row
    col1: int,          # Start column
    row2: int,          # End row
    col2: int,          # End column
    color: ColorType,   # Color
    alpha: float = 1.0  # Opacity
) -> Layer
```

**Example:**

```python
# Diagonal line
layer.line(0, 0, 5, 21, "white")

# Horizontal line
layer.line(2, 0, 2, 21, "cyan")
```

## Direct Matrix Access

For maximum performance, access the underlying numpy array directly.

### matrix Property

```python
layer.matrix  # numpy.ndarray of shape (height, width, 4)
```

**Examples:**

```python
# Set a single pixel
layer.matrix[row][col] = (1.0, 0.0, 0.0, 1.0)

# Fill entire layer with one color
layer.matrix[:, :] = (0.0, 0.5, 1.0, 1.0)

# Fill a specific row
layer.matrix[0, :] = (1.0, 1.0, 0.0, 1.0)

# Fill a specific column
layer.matrix[:, 5] = (0.0, 1.0, 0.0, 1.0)

# Fill a rectangular region
layer.matrix[1:4, 5:10] = (1.0, 0.0, 1.0, 1.0)

# Gradient across rows
for row in range(layer.height):
    intensity = row / layer.height
    layer.matrix[row, :] = (intensity, 0.0, 1.0 - intensity, 1.0)
```

### Numpy Operations

Leverage numpy for efficient bulk operations:

```python
import numpy as np

# Fade all colors by 50%
layer.matrix[:, :, :3] *= 0.5

# Set alpha channel only
layer.matrix[:, :, 3] = 0.8

# Invert colors
layer.matrix[:, :, :3] = 1.0 - layer.matrix[:, :, :3]

# Apply a color mask
mask = np.zeros((layer.height, layer.width, 4))
mask[2:4, 8:12] = (1.0, 0.0, 0.0, 1.0)
layer.matrix = np.maximum(layer.matrix, mask)
```

## Layer Properties

### blend_mode

The blend mode used when compositing with other layers.

```python
layer.blend_mode = "screen"  # Default
```

Available modes:

- `screen` - Brightens (default)
- `soft_light` - Subtle overlay
- `lighten_only` - Maximum of both
- `darken_only` - Minimum of both
- `dodge` - Brightening with contrast
- `multiply` - Darkens
- `hard_light` - High contrast
- `addition` - Sum of colors
- `difference` - Absolute difference
- `subtract` - Subtraction
- `grain_extract` - Subtractive with midpoint
- `grain_merge` - Additive with midpoint
- `divide` - Division blend

### opacity

The overall opacity of the layer (0.0 to 1.0).

```python
layer.opacity = 0.75
```

### background_color

The background color used for compositing.

```python
layer.background_color = "black"
layer.background_color = (0.1, 0.0, 0.1, 1.0)
```

## Color Input Formats

All methods accepting colors support multiple formats:

### String Names

```python
layer.put(0, 0, "red")
layer.put(0, 0, "cornflowerblue")
```

### Hex Codes

```python
layer.put(0, 0, "#ff0000")
layer.put(0, 0, "#f00")  # Short form
layer.put(0, 0, "#ff000080")  # With alpha
```

### RGB Tuples

```python
# Floats (0.0-1.0)
layer.put(0, 0, (1.0, 0.0, 0.0))
layer.put(0, 0, (1.0, 0.0, 0.0, 0.5))  # With alpha

# Integers (0-255)
layer.put(0, 0, (255, 0, 0))
```

### Color Objects

```python
from uchroma.color import to_color
from uchroma.colorlib import Color

# Via to_color helper
color = to_color("purple")
layer.put(0, 0, color)

# Direct Color creation
color = Color.NewFromHsv(270, 1.0, 1.0)
layer.put(0, 0, color)
```

## Method Chaining

All mutating methods return `self` for chaining:

```python
layer.clear().put(0, 0, "red").circle(3, 11, 2, "blue", fill=True)
```

## Complete Example

```python
async def draw(self, layer, timestamp) -> bool:
    # Clear previous frame
    layer.clear()

    # Draw a gradient background
    for row in range(layer.height):
        intensity = row / layer.height
        layer.matrix[row, :] = (0.0, 0.0, intensity * 0.3, 1.0)

    # Draw some shapes
    layer.circle(
        layer.height // 2,
        layer.width // 2,
        min(layer.height, layer.width) // 3,
        "cyan",
        fill=True,
        alpha=0.8
    )

    # Draw a moving line
    import math
    t = timestamp * 2
    x = int((math.sin(t) + 1) / 2 * layer.width)
    layer.line(0, x, layer.height - 1, layer.width - x - 1, "white")

    return True
```

## Performance Tips

1. **Use matrix operations** - Direct numpy access is faster than `put()`
2. **Avoid allocations** - Pre-allocate arrays outside the draw loop
3. **Skip unchanged pixels** - Only update what changes
4. **Use fill modes** - `fill=True` for circles is faster than drawing outlines

```python
# Slow: Individual pixel operations
for row in range(height):
    for col in range(width):
        layer.put(row, col, color)

# Fast: Numpy broadcast
layer.matrix[:, :] = (*color.rgb, 1.0)
```

## Next Steps

- [Colors](./colors) - Color parsing, gradients, and schemes
- [Traits](./traits) - Configurable parameters
- [Creating Effects](./creating-effects) - Full renderer tutorial
