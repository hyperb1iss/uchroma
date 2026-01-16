# uchroma

Userspace RGB control for Razer Chroma peripherals. Pure Python daemon with custom animation engine, D-Bus API, CLI client, and GTK4 frontend.

## Quick Reference

```bash
make              # Show all commands
make sync         # Install deps
make rebuild      # Rebuild after .pyx changes
make gtk          # Run GTK frontend
make server       # Run daemon
make check        # Lint + format check + typecheck
make fix          # Auto-fix lint + format
```

## Tooling

**Package manager**: uv (not pip/poetry). All commands use `uv run`.

**Linting**: ruff — configured in `pyproject.toml [tool.ruff]`
- `make lint` / `make lint-fix`
- Line length: 100, target Python 3.10+
- Rules: E, F, I, UP, B, SIM, RUF, C4, PIE, PT, PLC, PLE

**Formatting**: ruff format — `make fmt` / `make fmt-check`

**Type checking**: ty — `make typecheck` or `make tc`
- Configured in `pyproject.toml [tool.ty]`
- Currently warnings-only for gradual adoption

**Cython**: Three `.pyx` modules require rebuild after changes:
- `uchroma/_layer.pyx` — layer pixel operations
- `uchroma/fxlib/_plasma.pyx` — plasma effect hot path
- `uchroma/server/_crc.pyx` — USB report CRC

**Rebuild Cython**: `make rebuild` (runs `uv sync --extra gtk --reinstall-package uchroma`)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    uchromad (daemon)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │DeviceManager│  │AnimationLoop │  │  D-Bus API    │  │
│  │  (hotplug)  │  │ (compositor) │  │(dbus-fast)    │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Renderers → Layers → Frame → USB HID → Hardware       │
└─────────────────────────────────────────────────────────┘
         ↑ D-Bus                    ↑ D-Bus
    ┌────┴────┐                ┌────┴────┐
    │   CLI   │                │   GTK   │
    │ uchroma │                │ frontend│
    └─────────┘                └─────────┘
```

### Key Components

| Module | Purpose |
|--------|---------|
| `uchroma/server/server.py` | Daemon entry, signal handling, lifecycle |
| `uchroma/server/device_manager.py` | USB hotplug via pyudev, device enumeration |
| `uchroma/server/device_base.py` | Base device class, HID communication |
| `uchroma/server/anim.py` | AnimationLoop, AnimationManager, layer compositing |
| `uchroma/server/frame.py` | Framebuffer, hardware commit, layer composition |
| `uchroma/server/dbus.py` | D-Bus interfaces (dbus-fast) |
| `uchroma/renderer.py` | Base Renderer class with traitlets |
| `uchroma/layer.py` | Layer with drawing primitives (circle, line, etc.) |
| `uchroma/blending.py` | Blend modes (screen, soft_light, dodge, etc.) |
| `uchroma/fxlib/*.py` | Built-in renderers (plasma, rainbow, ripple, reaction) |

## Animation System

**Producer-consumer with double-buffering**:

1. Each `Renderer` runs in its own async task at its configured FPS
2. Renderer draws to a `Layer`, puts it on `_active_q`
3. `AnimationLoop` waits on all renderer queues (FIRST_COMPLETED)
4. Loop composites layers by z-order using blend modes
5. `Frame.commit()` sends RGB data to hardware via USB HID
6. Old buffers returned to renderers via `_avail_q`

**Key constants** (`uchroma/renderer.py`):
- `MAX_FPS = 30` — animation loop cap
- `DEFAULT_FPS = 15` — default renderer FPS
- `NUM_BUFFERS = 2` — double-buffering

**Ticker** (`uchroma/util.py`): Async context manager for frame rate sync. Sleeps for remainder of interval after work completes.

### Creating a Renderer

```python
from uchroma.renderer import Renderer, RendererMeta
from traitlets import Float

class MyEffect(Renderer):
    meta = RendererMeta('My Effect', 'Description', 'Author', 'v1.0')

    # Configurable traits (exposed to D-Bus/UI)
    speed = Float(default_value=1.0, min=0.1, max=5.0).tag(config=True)

    def init(self, frame) -> bool:
        # Setup when effect activates
        return True

    async def draw(self, layer, timestamp) -> bool:
        # Draw frame, return True to display
        layer.put(0, 0, 'red')  # Set pixel
        return True
```

Register in `pyproject.toml`:
```toml
[project.entry-points."uchroma.plugins"]
renderers = "your_module"
```

## Device Configuration

YAML files in `uchroma/server/data/` define hardware:

```yaml
!device-config
manufacturer: Razer
type: KEYBOARD
vendor_id: 0x1532
dimensions: [6, 22]  # [rows, cols] = [height, width]
supported_leds: [backlight, logo]
key_mapping: !!omap
  - KEY_ESC: [[0, 1]]
  - KEY_SPACE: [[5, 5], [5, 6], [5, 7]]  # Multi-cell keys
```

Device types: `KEYBOARD`, `MOUSE`, `MOUSEPAD`, `HEADSET`, `KEYPAD`, `LAPTOP`

## D-Bus Interface

**Bus name**: `io.uchroma`
**Base path**: `/io/uchroma`

Key interfaces:
- `io.uchroma.DeviceManager` — device enumeration
- `io.uchroma.Device` — brightness, effects, properties
- `io.uchroma.AnimationManager` — layer management

Client usage:
```python
from uchroma.client.dbus_client import UChromaClientAsync

client = UChromaClientAsync()
await client.connect()
paths = await client.get_device_paths()
device = await client.get_device(paths[0])
```

## GTK Frontend

**Stack**: GTK4 + libadwaita + Cairo

```
uchroma/gtk/
├── application.py      # Adw.Application, D-Bus service connection
├── window.py           # Main window, layout orchestration
├── widgets/            # Reusable components
│   ├── matrix_preview.py   # Cairo LED matrix visualization
│   ├── effect_card.py      # Effect selection cards
│   ├── layer_row.py        # Layer list items
│   └── brightness_scale.py # Brightness slider
├── panels/             # UI sections
│   ├── mode_toggle.py      # Hardware/Custom mode switch
│   ├── effect_selector.py  # Effect card grid
│   ├── layer_panel.py      # Layer management
│   └── param_inspector.py  # Parameter editor
├── services/
│   └── preview_renderer.py # Local effect preview at 30fps
└── resources/
    └── style.css           # SilkCircuit theme
```

**Run**: `make gtk` or `uv run python -m uchroma.gtk`

## Color Handling

Uses **ColorAide** for color manipulation.

```python
from uchroma.color import to_color
from uchroma.colorlib import Color

c = to_color('red')           # By name
c = to_color('#ff0000')       # Hex
c = to_color((1.0, 0.0, 0.0)) # RGB tuple
c = Color('oklch', [0.7, 0.15, 30])  # Any color space
```

**Alpha handling** (`_layer.pyx`): ColorAide's alpha is a property, not a method. The `color_to_np()` function handles both for compatibility.

## Traitlets

Observable properties for renderer configuration:

```python
from traitlets import Float, Int, observe
from uchroma.traits import ColorTrait, ColorSchemeTrait

class MyRenderer(Renderer):
    speed = Float(default_value=1.0).tag(config=True)
    color = ColorTrait().tag(config=True)

    @observe('speed')
    def _speed_changed(self, change):
        # React to changes
        pass
```

Traits tagged `config=True` are exposed via D-Bus and saved to preferences.

## USB Protocol

Razer devices use USB HID feature reports:

1. Create `RazerReport` with command class/id
2. Pack arguments via `report.args.put()`
3. CRC calculated automatically (`_crc.pyx`)
4. Send via hidapi, enforce inter-command delay
5. Parse response for queries

Transaction IDs vary by device (quirks system handles this).

## Logging

Use the `Log` class from `uchroma.log` — never use print statements for debugging.

```python
from uchroma.log import Log

_logger = Log.get("uchroma.mymodule")

_logger.debug("Debug message")
_logger.info("Info message")
_logger.warning("Warning message")
_logger.error("Error message")
```

**Enable debug logging**: `UCHROMA_LOG_LEVEL=DEBUG`

```bash
UCHROMA_LOG_LEVEL=DEBUG make server
UCHROMA_LOG_LEVEL=DEBUG uv run python -m uchroma.gtk
```

## File Locations

| Path | Purpose |
|------|---------|
| `~/.config/uchroma/` | User preferences |
| `/etc/udev/rules.d/70-uchroma.rules` | Device permissions |
| `/usr/lib/systemd/user/uchromad.service` | Systemd service |

## Common Tasks

**Add a new device**: Create entry in appropriate `uchroma/server/data/*.yaml`

**Add a new effect**: Create `Renderer` subclass in `uchroma/fxlib/`, register in `pyproject.toml`

**Debug daemon**: `UCHROMA_LOG_LEVEL=DEBUG make server` or `make server-debug`

**Test without hardware**: GTK preview renderer works standalone

## Dependencies

Core: numpy, traitlets, dbus-fast, hid, pyudev, coloraide, scikit-image, ruamel.yaml, evdev

GTK: pygobject (optional extra)

Build: cython, setuptools
