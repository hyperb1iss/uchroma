# Advanced Topics

This guide covers advanced features: keyboard-reactive effects, Cython optimization, debug logging,
and the D-Bus API for external integrations.

## Keyboard-Reactive Effects

Effects can respond to keyboard input in real-time. This is how effects like Ripple and Reaction
work.

### Checking Input Support

Not all devices support key events. Check before enabling input features:

```python
class MyReactiveEffect(Renderer):
    def init(self, frame) -> bool:
        if not self.has_key_input:
            self.logger.error("Device does not support key input")
            return False
        return True
```

### Key Expiration

By default, key events are consumed immediately. Set `key_expire_time` to keep events alive for
animations:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Keep events for 0.5 seconds
    self.key_expire_time = 0.5
```

### Getting Events

The `get_input_events()` method is async and yields until events are available:

```python
async def draw(self, layer, timestamp) -> bool:
    # This yields until at least one event is available
    events = await self.get_input_events()

    if not events:
        return False  # Nothing to draw

    for event in events:
        self._process_event(layer, event)

    return True
```

### KeyInputEvent Structure

Each event contains:

| Field         | Type  | Description                            |
| ------------- | ----- | -------------------------------------- |
| `timestamp`   | float | Unix timestamp of key press            |
| `expire_time` | float | When the event expires                 |
| `keycode`     | str   | Key name (e.g., "KEY_A", "KEY_SPACE")  |
| `scancode`    | str   | Hardware scan code                     |
| `keystate`    | int   | Press state                            |
| `coords`      | list  | List of (x, y) coordinates for the key |
| `data`        | dict  | Custom data storage                    |

Computed properties:

| Property           | Description                                 |
| ------------------ | ------------------------------------------- |
| `time_remaining`   | Seconds until expiry                        |
| `percent_complete` | 0.0 (just pressed) to 1.0 (about to expire) |

### Key States

```python
from uchroma.input_queue import InputQueue

# In __init__, configure which states to capture
self._input_queue.keystates = (
    InputQueue.KEY_DOWN |  # Key press
    InputQueue.KEY_UP |    # Key release
    InputQueue.KEY_HOLD    # Key held down
)
```

### Complete Reactive Example

```python
import math

from traitlets import Float
from uchroma.renderer import Renderer, RendererMeta
from uchroma.traits import ColorTrait


class KeyGlow(Renderer):
    """Keys glow when pressed with a fade-out animation."""

    meta = RendererMeta("Key Glow", "Keys glow when pressed", "Author", "1.0")

    color = ColorTrait(default_value="#00ffff").tag(config=True)
    fade_duration = Float(default_value=0.8, min=0.1, max=3.0).tag(config=True)
    glow_radius = Float(default_value=2.0, min=0.5, max=5.0).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fps = 30

    def init(self, frame) -> bool:
        if not self.has_key_input:
            return False
        self.key_expire_time = self.fade_duration
        return True

    @observe("fade_duration")
    def _fade_changed(self, change):
        self.key_expire_time = change.new

    async def draw(self, layer, timestamp) -> bool:
        events = await self.get_input_events()

        if not events:
            return False

        r, g, b = self.color.rgb

        for event in events:
            if event.coords is None:
                continue

            # Intensity fades from 1.0 to 0.0 as event expires
            intensity = event.percent_complete

            # Apply easing for smoother fade
            intensity = intensity * intensity  # Quadratic ease-out

            for coord in event.coords:
                # Draw glow around the key
                layer.circle(
                    coord.y, coord.x,
                    self.glow_radius * (1 + (1 - intensity)),
                    color=(r * intensity, g * intensity, b * intensity, intensity),
                    fill=True
                )

        return True
```

### Storing Data Per Event

Use the `data` dict to store computed values that persist with the event:

```python
async def draw(self, layer, timestamp) -> bool:
    events = await self.get_input_events()

    for event in events:
        # Compute color once on first encounter
        if "my_color" not in event.data:
            event.data["my_color"] = next(self._color_generator)

        color = event.data["my_color"]
        # Use color...
```

## Cython Optimization

Performance-critical code can be implemented in Cython for significant speedups.

### Cython Modules in uchroma

| File                        | Purpose                            |
| --------------------------- | ---------------------------------- |
| `uchroma/_layer.pyx`        | Pixel operations, color conversion |
| `uchroma/fxlib/_plasma.pyx` | Plasma effect calculations         |
| `uchroma/server/_crc.pyx`   | USB report CRC                     |

### Rebuilding After Changes

After modifying `.pyx` files:

```bash
make rebuild
```

This runs `uv sync --extra gtk --reinstall-package uchroma`.

### Example: Optimized Effect Core

Create `uchroma/fxlib/_myeffect.pyx`:

```python
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

import numpy as np
cimport numpy as np


def draw_pattern(int width, int height, np.ndarray[np.float64_t, ndim=3] matrix,
                 double time, list gradient):
    """
    Draw an optimized pattern directly into the matrix.

    Args:
        width: Layer width
        height: Layer height
        matrix: The layer's backing array (height x width x 4)
        time: Animation time
        gradient: List of Color objects
    """
    cdef int row, col, idx
    cdef int grad_len = len(gradient)
    cdef double r, g, b

    for row in range(height):
        for col in range(width):
            # Compute gradient index
            idx = int((col + row + time * 10) % grad_len)

            # Get color RGB
            color = gradient[idx]
            r, g, b = color.rgb

            # Write directly to matrix
            matrix[row, col, 0] = r
            matrix[row, col, 1] = g
            matrix[row, col, 2] = b
            matrix[row, col, 3] = 1.0
```

Use in your renderer:

```python
from ._myeffect import draw_pattern

class MyFastEffect(Renderer):
    async def draw(self, layer, timestamp) -> bool:
        draw_pattern(
            layer.width, layer.height,
            layer.matrix,
            self._time,
            self._gradient
        )
        self._time += 1 / self.fps
        return True
```

## Debug Logging

### Using the Logger

Every renderer has a logger instance:

```python
class MyEffect(Renderer):
    async def draw(self, layer, timestamp) -> bool:
        self.logger.debug("Drawing frame at t=%.3f", timestamp)
        self.logger.info("Effect started with speed=%s", self.speed)
        self.logger.warning("Gradient is empty!")
        self.logger.error("Failed to process event: %s", event)
        return True
```

### Enabling Debug Output

Set the `UCHROMA_LOG_LEVEL` environment variable:

```bash
# Full debug output
UCHROMA_LOG_LEVEL=DEBUG make server

# Or with the daemon directly
UCHROMA_LOG_LEVEL=DEBUG uv run uchromad

# For GTK frontend
UCHROMA_LOG_LEVEL=DEBUG uv run python -m uchroma.gtk
```

### Creating Module Loggers

For non-renderer code:

```python
from uchroma.log import Log

_logger = Log.get("uchroma.mymodule")

def my_function():
    _logger.debug("Doing something")
```

### Trace Logging

For very verbose output (protocol-level):

```python
from uchroma.log import LOG_TRACE, LOG_PROTOCOL_TRACE

if self.logger.isEnabledFor(LOG_TRACE):
    self.logger.debug("Detailed trace: %s", data)
```

## D-Bus API

The D-Bus API allows external applications to control uchroma.

### Bus Information

- **Bus Name:** `io.uchroma`
- **Base Path:** `/io/uchroma`

### Available Interfaces

| Interface                     | Path                      | Purpose            |
| ----------------------------- | ------------------------- | ------------------ |
| `io.uchroma.DeviceManager`    | `/io/uchroma`             | Device enumeration |
| `io.uchroma.Device`           | `/io/uchroma/{type}/{id}` | Device properties  |
| `io.uchroma.AnimationManager` | `/io/uchroma/{type}/{id}` | Layer management   |
| `io.uchroma.FXManager`        | `/io/uchroma/{type}/{id}` | Built-in effects   |
| `io.uchroma.LEDManager`       | `/io/uchroma/{type}/{id}` | LED control        |
| `io.uchroma.SystemControl`    | `/io/uchroma/{type}/{id}` | Laptop features    |

### Python Client

```python
from uchroma.client.dbus_client import UChromaClient, UChromaClientAsync
import asyncio

# Synchronous usage
client = UChromaClient()
paths = client.get_device_paths()
device = client.get_device(0)  # By index
device = client.get_device("1532:026c")  # By USB ID

print(f"Device: {device.Name}")
print(f"Brightness: {device.Brightness}")

# Set brightness
device.Brightness = 75.0

# List available renderers
for name, info in device.AvailableRenderers.items():
    print(f"  {name}: {info['meta']}")

# Add a renderer
path = device.AddRenderer("uchroma.fxlib.plasma.Plasma", -1, {
    "speed": 2.0,
    "preset": "Neon"
})

# Modify active layer
device.SetLayerTraits(0, {"speed": 3.0})

# Remove layer
device.RemoveRenderer(0)
```

### Async Client

```python
async def main():
    client = UChromaClientAsync()
    await client.connect()

    try:
        for path in await client.get_device_paths():
            device = await client.get_device(path)
            print(f"Device: {device.Name}")
    finally:
        await client.disconnect()

asyncio.run(main())
```

### D-Bus Introspection

Use standard D-Bus tools to explore the API:

```bash
# List devices
busctl --user call io.uchroma /io/uchroma \
    io.uchroma.DeviceManager GetDevices

# Introspect a device
busctl --user introspect io.uchroma \
    /io/uchroma/keyboard/1532_026c_00

# Get property
busctl --user get-property io.uchroma \
    /io/uchroma/keyboard/1532_026c_00 \
    io.uchroma.Device Brightness

# Set property
busctl --user set-property io.uchroma \
    /io/uchroma/keyboard/1532_026c_00 \
    io.uchroma.Device Brightness d 75.0
```

### D-Bus Signals

Subscribe to property changes:

```python
# The device emits PropertiesChanged signals
# Use dbus-fast or pydbus to subscribe
```

## Device Configuration

Devices are defined in YAML files at `uchroma/server/data/`:

```yaml
!device-config
name: 'Razer BlackWidow V3'
manufacturer: Razer
type: KEYBOARD
vendor_id: 0x1532
product_id: 0x026c
dimensions: [6, 22] # [rows, cols] = [height, width]
supported_leds: [backlight, logo, macro]
key_mapping: !!omap
  - KEY_ESC: [[0, 1]]
  - KEY_F1: [[0, 3]]
  - KEY_SPACE: [[5, 5], [5, 6], [5, 7]] # Multi-cell keys
```

### Device Types

```python
from uchroma.server.types import DeviceType

DeviceType.KEYBOARD
DeviceType.MOUSE
DeviceType.MOUSEPAD
DeviceType.HEADSET
DeviceType.KEYPAD
DeviceType.LAPTOP
```

## Testing Without Hardware

### GTK Preview

The GTK frontend includes a preview renderer that works without hardware:

```bash
make gtk
```

The preview displays locally-rendered effects at 30fps.

### Mock Device

For development, create a mock device configuration with test dimensions.

## Performance Profiling

### Frame Time Logging

```python
import time

class ProfiledEffect(Renderer):
    async def draw(self, layer, timestamp) -> bool:
        start = time.perf_counter()

        # Your drawing code here

        elapsed = time.perf_counter() - start
        if elapsed > 0.02:  # > 20ms
            self.logger.warning("Slow frame: %.3fms", elapsed * 1000)

        return True
```

### Memory Usage

```python
import sys

def log_memory():
    import gc
    gc.collect()
    # Log object counts, etc.
```

## Blend Modes Reference

| Mode            | Formula        | Use Case             |
| --------------- | -------------- | -------------------- | --- | -------------- |
| `screen`        | 1 - (1-a)(1-b) | Default, brightens   |
| `soft_light`    | Complex        | Subtle overlay       |
| `lighten_only`  | max(a, b)      | Keep brightest       |
| `darken_only`   | min(a, b)      | Keep darkest         |
| `dodge`         | a / (1-b)      | High contrast bright |
| `multiply`      | a \* b         | Darken, shadows      |
| `hard_light`    | Varies         | Strong contrast      |
| `addition`      | a + b          | Additive light       |
| `difference`    |                | a - b                |     | Invert overlap |
| `subtract`      | a - b          | Remove color         |
| `grain_extract` | a - b + 0.5    | Texture extraction   |
| `grain_merge`   | a + b - 0.5    | Texture addition     |
| `divide`        | a / b          | Color division       |

## Next Steps

- [Creating Effects](./creating-effects) - Full renderer tutorial
- [Architecture](./architecture) - System internals
- [Layer API](./layer-api) - Drawing reference
