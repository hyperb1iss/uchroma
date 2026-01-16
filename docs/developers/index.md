# Developer Guide

Welcome to the uchroma Developer Guide. This documentation covers everything you need to build custom lighting effects, integrate with the D-Bus API, and extend uchroma's functionality.

## Who This Guide Is For

- **Effect Creators** - Build custom lighting animations for your devices
- **Application Developers** - Integrate uchroma into your applications via D-Bus
- **Contributors** - Understand the architecture to contribute to the project

## What You Can Build

### Custom Effects

Create your own lighting effects by implementing a `Renderer` class. Effects can:

- Animate colors across your device's LED matrix
- React to keyboard input for interactive lighting
- Use configurable parameters exposed to the UI
- Blend with other effects using layer compositing

```python
from uchroma.renderer import Renderer, RendererMeta
from traitlets import Float

class PulseEffect(Renderer):
    meta = RendererMeta("Pulse", "Pulsing color", "Your Name", "1.0")
    speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)

    def init(self, frame):
        self._time = 0.0
        return True

    async def draw(self, layer, timestamp):
        import math
        intensity = (math.sin(self._time * self.speed) + 1) / 2
        for row in range(layer.height):
            for col in range(layer.width):
                layer.matrix[row][col] = (intensity, 0.0, intensity, 1.0)
        self._time += 1 / self.fps
        return True
```

### D-Bus Integrations

Control uchroma from any application using the D-Bus API:

```python
from uchroma.client.dbus_client import UChromaClient

client = UChromaClient()
device = client.get_device(0)
device.Brightness = 75.0
device.AddRenderer("uchroma.fxlib.plasma.Plasma", -1, {})
```

### GTK Extensions

Extend the GTK frontend with custom widgets and panels.

## Quick Links

| Topic | Description |
|-------|-------------|
| [Architecture](./architecture) | System overview and component interactions |
| [Creating Effects](./creating-effects) | Step-by-step tutorial for custom renderers |
| [D-Bus Modernization Plan](./dbus-modernization-plan) | Roadmap for 2026 D-Bus alignment |
| [Layer API](./layer-api) | Drawing primitives and pixel operations |
| [Traits](./traits) | Configurable parameters with traitlets |
| [Colors](./colors) | Color handling, gradients, and schemes |
| [Advanced](./advanced) | Input events, Cython, D-Bus API |

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Linux with systemd (for D-Bus)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/uchroma/uchroma.git
cd uchroma

# Install dependencies (including GTK)
make sync

# Run the daemon
make server

# In another terminal, run the GTK frontend
make gtk
```

### Development Commands

```bash
make sync           # Install dependencies
make rebuild        # Rebuild after .pyx changes
make check          # Run lint + format check + typecheck
make fix            # Auto-fix lint + format issues
make test           # Run tests
make server-debug   # Run daemon with debug logging
```

### Project Structure

```
uchroma/
├── renderer.py          # Base Renderer class
├── layer.py             # Layer drawing API
├── traits.py            # Traitlet types
├── color.py             # Color utilities
├── colorlib.py          # ColorAide wrapper
├── blending.py          # Blend modes
├── fxlib/               # Built-in effects
│   ├── plasma.py
│   ├── rainbow.py
│   ├── ripple.py
│   └── ...
├── server/
│   ├── server.py        # Daemon entry point
│   ├── anim.py          # Animation loop
│   ├── frame.py         # Framebuffer
│   ├── dbus.py          # D-Bus interfaces
│   └── data/            # Device configs
├── client/
│   ├── main.py          # CLI entry point
│   └── dbus_client.py   # D-Bus client
└── gtk/                 # GTK frontend
```

## Next Steps

Start with the [Architecture](./architecture) guide to understand how the components fit together, then follow the [Creating Effects](./creating-effects) tutorial to build your first custom effect.
