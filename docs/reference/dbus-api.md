# D-Bus API Reference

uchroma exposes a D-Bus API for programmatic control of Razer devices. The daemon runs on the
session bus and provides interfaces for device management, LED control, effects, and animations.

## Service Overview

| Item      | Value         |
| --------- | ------------- |
| Bus Type  | Session       |
| Bus Name  | `io.uchroma`  |
| Base Path | `/io/uchroma` |

## Object Paths

| Path                                   | Description                           |
| -------------------------------------- | ------------------------------------- |
| `/io/uchroma`                          | Root service, DeviceManager interface |
| `/io/uchroma/{type}/{vid}_{pid}_{idx}` | Individual device                     |

Device paths follow the pattern:

- `{type}` - Device type: `keyboard`, `mouse`, `mousepad`, `headset`, `keypad`, `laptop`
- `{vid}` - Vendor ID in hex (e.g., `1532`)
- `{pid}` - Product ID in hex (e.g., `026c`)
- `{idx}` - Device index with leading zero (e.g., `01`)

Example: `/io/uchroma/keyboard/1532_026c_01`

---

## io.uchroma.DeviceManager

Root interface for device enumeration.

**Path**: `/io/uchroma`

### Methods

#### GetDevices

Returns a list of all connected device object paths.

```
GetDevices() -> ao
```

**Returns**: Array of object paths

### Signals

#### DevicesChanged

Emitted when a device is added or removed.

```
DevicesChanged(action: s, device: o) -> so
```

**Parameters**:

- `action` - "add" or "remove"
- `device` - Object path of the device

---

## io.uchroma.Device

Primary interface for device properties and control.

### Properties (Read-Only)

| Property          | Type        | Description                               |
| ----------------- | ----------- | ----------------------------------------- |
| `Name`            | `s`         | Device name (e.g., "Huntsman V2 TKL")     |
| `DeviceType`      | `s`         | Type: keyboard, mouse, mousepad, etc.     |
| `DriverVersion`   | `s`         | Driver version string                     |
| `FirmwareVersion` | `s`         | Device firmware version                   |
| `SerialNumber`    | `s`         | Device serial number                      |
| `Manufacturer`    | `s`         | Manufacturer name (Razer)                 |
| `VendorId`        | `u`         | USB vendor ID (0x1532)                    |
| `ProductId`       | `u`         | USB product ID                            |
| `DeviceIndex`     | `u`         | Device index (for multiple same devices)  |
| `HasMatrix`       | `b`         | True if device has addressable LED matrix |
| `Width`           | `i`         | Matrix width (columns)                    |
| `Height`          | `i`         | Matrix height (rows)                      |
| `SysPath`         | `s`         | Linux sysfs path                          |
| `Key`             | `s`         | Unique device key (vid:pid.idx)           |
| `BusPath`         | `o`         | D-Bus object path                         |
| `IsWireless`      | `b`         | True if wireless device                   |
| `IsCharging`      | `b`         | True if charging (wireless only)          |
| `BatteryLevel`    | `d`         | Battery percentage 0.0-100.0              |
| `SupportedLeds`   | `as`        | List of LED zone names                    |
| `Zones`           | `as`        | List of zone identifiers                  |
| `KeyMapping`      | `a{sa(ii)}` | Key name to matrix coordinates            |

### Properties (Read-Write)

| Property     | Type | Description                 |
| ------------ | ---- | --------------------------- |
| `Brightness` | `d`  | Global brightness 0.0-100.0 |
| `Suspended`  | `b`  | True to suspend device      |

### Methods

#### Reset

Reset device to default state.

```
Reset()
```

### Signals

#### PropertiesChanged

Standard D-Bus properties changed signal.

```
PropertiesChanged(interface_name: s, changed_properties: a{sv}, invalidated_properties: as)
```

---

## io.uchroma.LEDManager

Interface for individual LED zone control.

### Properties (Read-Only)

| Property        | Type        | Description                     |
| --------------- | ----------- | ------------------------------- |
| `AvailableLEDs` | `a{sa{sv}}` | Map of LED name to trait values |

### Methods

#### GetLED

Get current state of an LED zone.

```
GetLED(name: s) -> a{sv}
```

**Parameters**:

- `name` - LED zone name (e.g., "backlight", "logo")

**Returns**: Dictionary of trait values

#### SetLED

Set LED zone properties.

```
SetLED(name: s, properties: a{sv}) -> b
```

**Parameters**:

- `name` - LED zone name
- `properties` - Dictionary of property values

**Returns**: True on success

### Signals

#### LEDChanged

Emitted when an LED zone changes.

```
LEDChanged(led: s) -> s
```

---

## io.uchroma.FXManager

Interface for built-in hardware effects.

### Properties (Read-Only)

| Property      | Type        | Description                               |
| ------------- | ----------- | ----------------------------------------- |
| `AvailableFX` | `a{sa{sv}}` | Map of effect name to configurable traits |
| `CurrentFX`   | `(sa{sv})`  | Tuple of (effect_name, trait_values)      |

### Methods

#### SetFX

Activate a built-in effect.

```
SetFX(name: s, args: a{sv}) -> b
```

**Parameters**:

- `name` - Effect name (e.g., "wave", "spectrum", "static")
- `args` - Effect-specific arguments

**Returns**: True on success

**Available Effects**:

- `disable` - Turn off effects
- `wave` - Scrolling wave pattern
- `reactive` - Key press reactive lighting
- `breathe` - Pulsing/breathing effect
- `spectrum` - Spectrum cycling
- `static` - Solid color
- `starlight` - Twinkling stars (newer devices)
- `rainbow` - Rainbow wave

---

## io.uchroma.AnimationManager

Interface for custom animation/renderer management.

### Properties (Read-Only)

| Property             | Type        | Description                                 |
| -------------------- | ----------- | ------------------------------------------- |
| `AvailableRenderers` | `a{sa{sv}}` | Map of renderer name to metadata and traits |
| `CurrentRenderers`   | `a(so)`     | Array of (renderer_type, layer_path) tuples |
| `AnimationState`     | `s`         | Current state: running, paused, stopped     |

### Methods

#### AddRenderer

Add a renderer layer to the animation stack.

```
AddRenderer(name: s, zindex: i, traits: a{sv}) -> o
```

**Parameters**:

- `name` - Renderer name (e.g., "plasma", "ripple")
- `zindex` - Layer z-index (-1 for auto)
- `traits` - Initial trait values

**Returns**: Object path of the new layer

#### GetLayerInfo

Get information about a specific layer.

```
GetLayerInfo(zindex: i) -> a{sv}
```

**Parameters**:

- `zindex` - Layer z-index

**Returns**: Dictionary with Key, ZIndex, Type, and trait values

#### SetLayerTraits

Update traits on an existing layer.

```
SetLayerTraits(zindex: i, traits: a{sv}) -> b
```

**Parameters**:

- `zindex` - Layer z-index
- `traits` - New trait values

**Returns**: True on success

#### RemoveRenderer

Remove a renderer layer.

```
RemoveRenderer(zindex: i) -> b
```

**Parameters**:

- `zindex` - Layer z-index

**Returns**: True on success

#### GetCurrentFrame

Get the current composited frame data.

```
GetCurrentFrame() -> a{sv}
```

**Returns**: Dictionary with:

- `width` (i) - Frame width
- `height` (i) - Frame height
- `data` (ay) - RGB pixel data
- `seq` (i) - Frame sequence number
- `timestamp` (d) - Frame timestamp

#### StopAnimation

Stop all animations.

```
StopAnimation() -> b
```

#### PauseAnimation

Pause all animations.

```
PauseAnimation() -> b
```

---

## io.uchroma.SystemControl

Interface for laptop system control (Blade models only).

### Properties (Read-Only)

| Property              | Type    | Description                                                     |
| --------------------- | ------- | --------------------------------------------------------------- |
| `FanRPM`              | `ai`    | Current fan RPM(s) [fan1] or [fan1, fan2]                       |
| `FanMode`             | `s`     | Fan mode: "auto" or "manual"                                    |
| `FanLimits`           | `a{sv}` | Fan limits: min_rpm, min_manual_rpm, max_rpm, supports_dual_fan |
| `AvailablePowerModes` | `as`    | List of power mode names                                        |
| `AvailableBoostModes` | `as`    | List of boost mode names                                        |
| `SupportsFanSpeed`    | `b`     | True if fan speed reading supported                             |
| `SupportsBoost`       | `b`     | True if boost control supported                                 |

### Properties (Read-Write)

| Property    | Type | Description                                   |
| ----------- | ---- | --------------------------------------------- |
| `PowerMode` | `s`  | Power mode: balanced, gaming, creator, custom |
| `CPUBoost`  | `s`  | CPU boost: low, medium, high, boost           |
| `GPUBoost`  | `s`  | GPU boost: low, medium, high, boost           |

### Methods

#### SetFanAuto

Set fans to automatic EC control.

```
SetFanAuto() -> b
```

#### SetFanRPM

Set manual fan RPM.

```
SetFanRPM(rpm: i, fan2_rpm: i) -> b
```

**Parameters**:

- `rpm` - Primary fan RPM
- `fan2_rpm` - Secondary fan RPM (-1 to ignore)

---

## Python Client

uchroma provides Python client classes for easy D-Bus interaction.

### Async Client

```python
import asyncio
from uchroma.client.dbus_client import UChromaClientAsync

async def main():
    client = UChromaClientAsync()
    await client.connect()

    # Get all devices
    paths = await client.get_device_paths()
    print(f"Found {len(paths)} devices")

    # Get device by path
    device = await client.get_device(paths[0])
    print(f"Device: {device.Name}")
    print(f"Type: {device.DeviceType}")
    print(f"Matrix: {device.Width}x{device.Height}")

    # Set brightness
    device.Brightness = 75.0

    # Get available renderers
    print(f"Renderers: {list(device.AvailableRenderers.keys())}")

    # Add a renderer
    layer_path = device.AddRenderer("plasma", -1, {})
    print(f"Added layer at: {layer_path}")

    await client.disconnect()

asyncio.run(main())
```

### Sync Client

```python
from uchroma.client.dbus_client import UChromaClient

client = UChromaClient()

# Get devices
paths = client.get_device_paths()
device = client.get_device(paths[0])

# Device lookup by key or index
device = client.get_device("1532:026c")      # By vendor:product
device = client.get_device("1532:026c.01")   # By full key
device = client.get_device(0)                 # By index

# Access properties
print(device.Name)
print(device.Brightness)
device.Brightness = 50.0

# FX control
device.SetFX("spectrum", {})
device.SetFX("static", {"color": "#ff0000"})

# LED control
leds = device.AvailableLEDs
device.SetLED("logo", {"brightness": 100.0})

# Animation control
device.AddRenderer("ripple", 0, {"color": "#00ff00"})
device.SetLayerTraits(0, {"speed": 2.0})
device.RemoveRenderer(0)
```

### DeviceProxy Properties

The `DeviceProxy` class provides convenient property access:

```python
# Device info
device.Name              # str
device.Key               # str (e.g., "1532:026c.01")
device.DeviceType        # str
device.DeviceIndex       # int
device.SerialNumber      # str
device.FirmwareVersion   # str
device.Manufacturer      # str
device.VendorId          # int
device.ProductId         # int
device.HasMatrix         # bool
device.Width             # int
device.Height            # int
device.SupportedLeds     # list[str]
device.BusPath           # str

# Wireless
device.IsWireless        # bool
device.IsCharging        # bool
device.BatteryLevel      # float

# Read/write
device.Brightness        # float (0.0-100.0)
device.Suspended         # bool

# FX
device.AvailableFX       # dict
device.CurrentFX         # tuple

# Animation
device.AvailableRenderers  # dict
device.CurrentRenderers    # list

# LEDs
device.AvailableLEDs     # dict

# System (laptops)
device.HasSystemControl  # bool
device.FanRPM            # list[int]
device.FanMode           # str
device.FanLimits         # dict
device.PowerMode         # str
device.CPUBoost          # str
device.GPUBoost          # str
```

---

## Command Line Examples

### Using dbus-send

```bash
# List devices
dbus-send --session --print-reply \
  --dest=io.uchroma /io/uchroma \
  io.uchroma.DeviceManager.GetDevices

# Get device name
dbus-send --session --print-reply \
  --dest=io.uchroma /io/uchroma/keyboard/1532_026c_01 \
  org.freedesktop.DBus.Properties.Get \
  string:"io.uchroma.Device" string:"Name"

# Set brightness
dbus-send --session --print-reply \
  --dest=io.uchroma /io/uchroma/keyboard/1532_026c_01 \
  org.freedesktop.DBus.Properties.Set \
  string:"io.uchroma.Device" string:"Brightness" \
  variant:double:75.0
```

### Using busctl

```bash
# Introspect service
busctl --user introspect io.uchroma /io/uchroma

# List devices
busctl --user call io.uchroma /io/uchroma \
  io.uchroma.DeviceManager GetDevices

# Get all properties
busctl --user introspect io.uchroma /io/uchroma/keyboard/1532_026c_01
```

### Using gdbus

```bash
# List devices
gdbus call --session --dest io.uchroma --object-path /io/uchroma \
  --method io.uchroma.DeviceManager.GetDevices

# Set effect
gdbus call --session --dest io.uchroma \
  --object-path /io/uchroma/keyboard/1532_026c_01 \
  --method io.uchroma.FXManager.SetFX "spectrum" "{}"
```

---

## D-Bus Type Signatures

| Signature   | Type                  | Example                  |
| ----------- | --------------------- | ------------------------ |
| `s`         | string                | "Huntsman V2"            |
| `b`         | boolean               | true/false               |
| `i`         | int32                 | 42                       |
| `u`         | uint32                | 0x1532                   |
| `d`         | double                | 75.0                     |
| `o`         | object path           | /io/uchroma/keyboard/... |
| `as`        | array of strings      | ["backlight", "logo"]    |
| `ao`        | array of object paths | ["/io/uchroma/..."]      |
| `ai`        | array of int32        | [3500, 3600]             |
| `ay`        | array of bytes        | RGB data                 |
| `a{sv}`     | dict string->variant  | {"name": "value"}        |
| `a{sa{sv}}` | dict string->dict     | nested config            |
| `(so)`      | struct (string, path) | ("plasma", "/path")      |
| `a(so)`     | array of structs      | layers list              |
| `a(ii)`     | array of int pairs    | coordinates              |
| `a{sa(ii)}` | key mapping           | {"KEY_A": [(3, 2)]}      |

---

## Error Handling

The D-Bus API uses standard D-Bus error reporting. Common errors:

- `org.freedesktop.DBus.Error.ServiceUnknown` - Daemon not running
- `org.freedesktop.DBus.Error.UnknownObject` - Invalid device path
- `org.freedesktop.DBus.Error.UnknownMethod` - Method not supported
- `org.freedesktop.DBus.Error.InvalidArgs` - Invalid arguments

Always verify the daemon is running before making calls:

```bash
# Check if service is available
dbus-send --session --print-reply \
  --dest=org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus.NameHasOwner string:"io.uchroma"
```
