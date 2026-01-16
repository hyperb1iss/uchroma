# Reference

Technical reference documentation for uchroma.

## Contents

- **[Supported Devices](devices.md)** - Complete matrix of supported Razer hardware with
  vendor/product IDs, dimensions, and feature support
- **[D-Bus API](dbus-api.md)** - D-Bus interface reference for programmatic control
- **[Razer Protocol Reference](razer-protocol-reference.md)** - Low-level USB HID protocol
  documentation
- **[Razer Device Database](razer-device-database.md)** - Device-specific quirks and configuration

## Quick Links

### Device Configuration

Device hardware definitions are stored in YAML files under `uchroma/server/data/`:

| File            | Device Types                                           |
| --------------- | ------------------------------------------------------ |
| `keyboard.yaml` | Keyboards (BlackWidow, Huntsman, DeathStalker, Ornata) |
| `mouse.yaml`    | Mice (DeathAdder, Basilisk, Viper, Naga, Cobra)        |
| `mousepad.yaml` | Mousepads (Firefly, Goliathus)                         |
| `headset.yaml`  | Headsets (Kraken)                                      |
| `keypad.yaml`   | Keypads (Tartarus)                                     |
| `laptop.yaml`   | Laptops (Blade, Blade Stealth, Blade Pro)              |

### D-Bus Service

| Item        | Value         |
| ----------- | ------------- |
| Bus name    | `io.uchroma`  |
| Base path   | `/io/uchroma` |
| Session bus | Yes           |

### Vendor Information

| Item         | Value    |
| ------------ | -------- |
| Manufacturer | Razer    |
| Vendor ID    | `0x1532` |

## See Also

- [Getting Started](../guide/index.md) - Installation and basic usage
- [Architecture](../developers/architecture.md) - System design overview
- [Effects Development](../developers/creating-effects.md) - Creating custom renderers
