# Hardware Layer Refactor Plan & Worklog

**Created:** 2026-01-15
**Status:** Planning
**Author:** Nova (with Bliss)

---

## Executive Summary

This document outlines a comprehensive refactoring of uchroma's hardware abstraction layer, implementing the architectural recommendations from the protocol research. The goal is to create a cleaner, more maintainable, and extensible system for supporting Razer devices across all protocol generations.

**Key Objectives:**
1. Protocol version abstraction to replace ad-hoc quirks
2. Centralized command registry with protocol-aware dispatching
3. Extended YAML schema for hardware definitions
4. Comprehensive test suite for the hardware layer
5. Improved keyboard layout system
6. Better wireless device support

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Phase 1: Foundation (Non-Breaking)](#2-phase-1-foundation)
3. [Phase 2: Protocol Abstraction](#3-phase-2-protocol-abstraction)
4. [Phase 3: Command Registry](#4-phase-3-command-registry)
5. [Phase 4: Hardware Definition Schema](#5-phase-4-hardware-definition-schema)
6. [Phase 5: Keyboard Layout System](#6-phase-5-keyboard-layout-system)
7. [Phase 6: Test Infrastructure](#7-phase-6-test-infrastructure)
8. [Phase 7: Extended Device Support](#8-phase-7-extended-device-support)
9. [Phase 8: System Control (Laptop EC)](#8-phase-8-system-control-laptop-ec)
10. [Migration Strategy](#9-migration-strategy)
11. [Worklog](#10-worklog)

---

## 1. Current State Analysis

### 1.1 Protocol Handling

**Location:** `uchroma/server/device_base.py:279-298`

Current transaction ID selection uses quirks:

```python
if transaction_id is None:
    if self.has_quirk(Quirks.TRANSACTION_CODE_3F):
        transaction_id = 0x3F
    elif self.has_quirk(Quirks.TRANSACTION_CODE_1F):
        transaction_id = 0x1F
    else:
        transaction_id = 0xFF
```

**Problems:**
- Missing `0x9F` (wireless keyboards) - devices exist in the database but aren't supported
- Missing `0x08` (Naga X special case)
- No protocol version concept - just individual quirks
- Effect IDs differ between standard (0x03) and extended (0x0F) commands

### 1.2 Quirks System

**Location:** `uchroma/server/hardware.py:30-60`

Current quirks:
- `TRANSACTION_CODE_3F` (1)
- `EXTENDED_FX_CMDS` (2)
- `SCROLL_WHEEL_BRIGHTNESS` (3)
- `WIRELESS` (4)
- `CUSTOM_FRAME_80` (5)
- `LOGO_LED_BRIGHTNESS` (6)
- `PROFILE_LEDS` (7)
- `BACKLIGHT_LED_FX_ONLY` (8)
- `TRANSACTION_CODE_1F` (9)

**Missing quirks (from research):**
- `NO_LED` - Device has no RGB LEDs
- `SINGLE_LED` - Only one LED zone
- `HYPERPOLLING` - Supports 4000/8000Hz
- `ANALOG_KEYS` - Analog key actuation
- `HEADSET_PROTOCOL` - Uses headset memory protocol
- `SOFTWARE_EFFECTS` - Firmware lacks effects (needs software rendering)
- `TRANSACTION_CODE_9F` - Wireless keyboards

### 1.3 Effect Handling

**Location:** `uchroma/server/standard_fx.py`

Two separate enums exist:
- `FX` (standard effects, class 0x03)
- `ExtendedFX` (extended effects, class 0x0F)

Effect IDs differ between protocols:

| Effect | Standard (0x03) | Extended (0x0F) |
|--------|-----------------|-----------------|
| DISABLE | 0x00 | 0x00 |
| STATIC | 0x06 | 0x01 |
| SPECTRUM | 0x04 | 0x03 |
| WAVE | 0x01 | 0x04 |
| BREATHE | 0x03 | 0x02 |
| REACTIVE | 0x02 | 0x05 |
| STARLIGHT | 0x19 | 0x07 |
| CUSTOM_FRAME | 0x05 | 0x08 |

### 1.4 Keyboard Layout System

**Pain Points:**

1. **Manual mapping creation** - Currently done by hand using `key_mapping` YAML
2. **Fixup system complexity** - `key_fixup_mapping` with copy/delete/insert operations
3. **Row offsets** - `key_row_offsets` for per-row alignment
4. **Different layouts per locale** - US vs UK vs ISO not handled
5. **No validation** - Can have invalid mappings that fail silently

**Current structure:**
```yaml
key_mapping: !!omap
- KEY_ESC: [[0, 1]]
- KEY_SPACE: [[5, 5], [5, 6], [5, 7], [5, 8], [5, 9]]  # Multi-cell keys
key_fixup_mapping: !!omap
- copy:
  - [[5, 10], [5,9]]    # Source, destination
```

### 1.5 Device Database Gaps

**From `docs/razer-device-database.md` vs `uchroma/server/data/*.yaml`:**

**Missing devices (examples):**
- BlackWidow V4 series (0x0287, 0x028D, 0x028E, 0x0283)
- Huntsman V3 Pro series (0x02A6, 0x02B0, 0x02B1)
- DeathStalker V2 series (0x0295, 0x0296, 0x0298)
- Many modern mice with NO_LED (Viper V3, DeathAdder V3)
- Firefly V2 Pro and other mousepads
- Base Station V2 and other accessories

### 1.6 Test Coverage

**Current state:** No test files exist for the hardware layer.

**Needs:**
- Unit tests for report packing/unpacking
- Unit tests for CRC calculation
- Unit tests for effect mapping
- Integration tests with mock HID device
- YAML schema validation tests
- Keyboard layout validation tests

---

## 2. Phase 1: Foundation (Non-Breaking)

### 2.1 Add Missing Quirks

**File:** `uchroma/server/hardware.py`

```python
class Quirks(IntEnum):
    """Various quirks found across hardware models."""

    # Transaction codes
    TRANSACTION_CODE_3F = 1
    TRANSACTION_CODE_1F = 9
    TRANSACTION_CODE_9F = 10  # NEW: Wireless keyboards
    TRANSACTION_CODE_08 = 11  # NEW: Naga X

    # Command sets
    EXTENDED_FX_CMDS = 2

    # Brightness control
    SCROLL_WHEEL_BRIGHTNESS = 3
    LOGO_LED_BRIGHTNESS = 6

    # Device features
    WIRELESS = 4
    CUSTOM_FRAME_80 = 5
    PROFILE_LEDS = 7
    BACKLIGHT_LED_FX_ONLY = 8

    # NEW quirks
    NO_LED = 12              # Device has no RGB LEDs
    SINGLE_LED = 13          # Only one LED zone
    HYPERPOLLING = 14        # Supports 4000/8000Hz polling
    ANALOG_KEYS = 15         # Analog key actuation support
    SOFTWARE_EFFECTS = 16    # Needs software-rendered effects
    CRC_SKIP_ON_OK = 17      # Skip CRC validation on OK responses
```

**Task:** [ ] Add new quirks to hardware.py

### 2.2 Update Transaction ID Logic

**File:** `uchroma/server/device_base.py:get_report()`

```python
def get_report(self, ..., transaction_id: int | None = None, ...):
    if transaction_id is None:
        if self.has_quirk(Quirks.TRANSACTION_CODE_3F):
            transaction_id = 0x3F
        elif self.has_quirk(Quirks.TRANSACTION_CODE_1F):
            transaction_id = 0x1F
        elif self.has_quirk(Quirks.TRANSACTION_CODE_9F):
            transaction_id = 0x9F
        elif self.has_quirk(Quirks.TRANSACTION_CODE_08):
            transaction_id = 0x08
        else:
            transaction_id = 0xFF
```

**Task:** [ ] Update get_report() with new transaction codes

### 2.3 Update Device YAML Files

Add missing devices with appropriate quirks. Example additions:

**File:** `uchroma/server/data/keyboard.yaml`

```yaml
# BlackWidow V4 series
- !device-config
  name: BlackWidow V4
  product_id: 0x0287
  dimensions: [6, 22]
  quirks: [TRANSACTION_CODE_1F, EXTENDED_FX_CMDS]

- !device-config
  name: BlackWidow V4 75%
  product_id: 0x028E
  dimensions: [6, 16]
  quirks: [TRANSACTION_CODE_1F, EXTENDED_FX_CMDS]
```

**File:** `uchroma/server/data/mouse.yaml`

```yaml
# Viper V3 Pro (no LEDs)
- !device-config
  name: Viper V3 Pro (Wired)
  product_id: 0x00C0
  quirks: [TRANSACTION_CODE_1F, WIRELESS, NO_LED]

- !device-config
  name: Viper V3 Pro (Wireless)
  product_id: 0x00C1
  quirks: [TRANSACTION_CODE_1F, WIRELESS, NO_LED]
```

**Tasks:**
- [ ] Add BlackWidow V4 series to keyboard.yaml
- [ ] Add Huntsman V3 Pro series to keyboard.yaml
- [ ] Add DeathStalker V2 series to keyboard.yaml
- [ ] Add missing wireless keyboard entries with 0x9F
- [ ] Add modern mice with NO_LED quirk
- [ ] Add missing mousepads to mousepad.yaml
- [ ] Add missing accessories (docks, stands)

---

## 3. Phase 2: Protocol Abstraction

### 3.1 Protocol Version Enum

**New file:** `uchroma/server/protocol.py`

```python
from enum import Enum, auto
from dataclasses import dataclass
from typing import ClassVar


class ProtocolVersion(Enum):
    """Protocol versions based on transaction ID and command structure."""

    LEGACY = "legacy"           # 0xFF, standard commands (class 0x03)
    EXTENDED = "extended"       # 0x3F, extended FX commands (class 0x0F)
    MODERN = "modern"           # 0x1F, latest devices
    WIRELESS_KB = "wireless_kb" # 0x9F, wireless keyboards
    HEADSET_V1 = "headset_v1"   # Rainie protocol (memory read/write)
    HEADSET_V2 = "headset_v2"   # Kylie protocol (memory read/write)
    SPECIAL = "special"         # Device-specific (e.g., Naga X with 0x08)


@dataclass(frozen=True)
class ProtocolConfig:
    """Protocol configuration for a device."""

    version: ProtocolVersion
    transaction_id: int
    uses_extended_fx: bool = False
    inter_command_delay: float = 0.007
    crc_skip_on_ok: bool = False

    # Predefined configurations
    LEGACY: ClassVar["ProtocolConfig"]
    EXTENDED: ClassVar["ProtocolConfig"]
    MODERN: ClassVar["ProtocolConfig"]
    WIRELESS_KB: ClassVar["ProtocolConfig"]


# Static configurations
ProtocolConfig.LEGACY = ProtocolConfig(
    version=ProtocolVersion.LEGACY,
    transaction_id=0xFF,
    uses_extended_fx=False,
)

ProtocolConfig.EXTENDED = ProtocolConfig(
    version=ProtocolVersion.EXTENDED,
    transaction_id=0x3F,
    uses_extended_fx=True,
)

ProtocolConfig.MODERN = ProtocolConfig(
    version=ProtocolVersion.MODERN,
    transaction_id=0x1F,
    uses_extended_fx=True,
)

ProtocolConfig.WIRELESS_KB = ProtocolConfig(
    version=ProtocolVersion.WIRELESS_KB,
    transaction_id=0x9F,
    uses_extended_fx=True,
)


def get_protocol_from_quirks(hardware) -> ProtocolConfig:
    """Determine protocol configuration from hardware quirks (backwards compat)."""
    from .hardware import Quirks

    if hardware.has_quirk(Quirks.TRANSACTION_CODE_9F):
        return ProtocolConfig.WIRELESS_KB
    elif hardware.has_quirk(Quirks.TRANSACTION_CODE_1F):
        return ProtocolConfig.MODERN
    elif hardware.has_quirk(Quirks.TRANSACTION_CODE_3F):
        return ProtocolConfig.EXTENDED
    else:
        return ProtocolConfig.LEGACY
```

**Tasks:**
- [ ] Create protocol.py with ProtocolVersion and ProtocolConfig
- [ ] Add get_protocol_from_quirks() for backwards compatibility
- [ ] Update device_base.py to use ProtocolConfig

### 3.2 Integrate Protocol into Device

**File:** `uchroma/server/device_base.py`

```python
from .protocol import ProtocolConfig, get_protocol_from_quirks

class BaseUChromaDevice:
    def __init__(self, ...):
        # ... existing init ...
        self._protocol = get_protocol_from_quirks(self._hardware)

    @property
    def protocol(self) -> ProtocolConfig:
        """Protocol configuration for this device."""
        return self._protocol

    def get_report(self, ..., transaction_id: int | None = None, ...):
        if transaction_id is None:
            transaction_id = self._protocol.transaction_id
        # ... rest of method
```

**Tasks:**
- [ ] Add protocol property to BaseUChromaDevice
- [ ] Update get_report() to use protocol.transaction_id
- [ ] Update run_report() to use protocol.inter_command_delay

---

## 4. Phase 3: Command Registry

### 4.1 Centralized Command Definitions

**New file:** `uchroma/server/commands.py`

```python
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


@dataclass(frozen=True)
class CommandDef:
    """Definition of a hardware command."""

    command_class: int
    command_id: int
    data_size: Optional[int]
    name: str
    description: str = ""
    protocols: Tuple[str, ...] = ("legacy", "extended", "modern")

    @property
    def value(self) -> Tuple[int, int, Optional[int]]:
        """Return tuple for compatibility with BaseCommand."""
        return (self.command_class, self.command_id, self.data_size)


class Commands:
    """Centralized command registry."""

    # Class 0x00 - Device Info & Control
    GET_FIRMWARE = CommandDef(0x00, 0x81, 0x02, "GET_FIRMWARE",
                              "Query firmware version")
    GET_SERIAL = CommandDef(0x00, 0x82, 0x16, "GET_SERIAL",
                            "Query serial number")
    SET_DEVICE_MODE = CommandDef(0x00, 0x04, 0x02, "SET_DEVICE_MODE",
                                 "Set driver mode (0x00=normal, 0x03=driver)")
    SET_POLLING_RATE = CommandDef(0x00, 0x05, 0x01, "SET_POLLING_RATE",
                                  "Set polling rate")
    SET_POLLING_RATE_V2 = CommandDef(0x00, 0x40, None, "SET_POLLING_RATE_V2",
                                     "Extended polling rate (HyperPolling)",
                                     protocols=("modern",))
    GET_POLLING_RATE = CommandDef(0x00, 0x85, 0x01, "GET_POLLING_RATE",
                                  "Query polling rate")

    # Class 0x03 - Standard LED/Effects
    SET_LED_STATE = CommandDef(0x03, 0x00, 0x03, "SET_LED_STATE",
                               "Enable/disable LED")
    SET_LED_COLOR = CommandDef(0x03, 0x01, 0x05, "SET_LED_COLOR",
                               "Set LED color (RGB)")
    SET_LED_BRIGHTNESS = CommandDef(0x03, 0x03, 0x03, "SET_LED_BRIGHTNESS",
                                    "Set brightness level")
    SET_EFFECT = CommandDef(0x03, 0x0A, None, "SET_EFFECT",
                            "Apply lighting effect",
                            protocols=("legacy",))
    SET_FRAME_MATRIX = CommandDef(0x03, 0x0B, None, "SET_FRAME_MATRIX",
                                  "Custom frame (multi-row)")
    SET_FRAME_SINGLE = CommandDef(0x03, 0x0C, None, "SET_FRAME_SINGLE",
                                  "Custom frame (single row)")
    GET_LED_BRIGHTNESS = CommandDef(0x03, 0x83, 0x03, "GET_LED_BRIGHTNESS",
                                    "Query brightness")

    # Class 0x07 - Power & Battery
    GET_BATTERY = CommandDef(0x07, 0x80, 0x02, "GET_BATTERY",
                             "Query battery level (0-255)",
                             protocols=("extended", "modern"))
    GET_CHARGING = CommandDef(0x07, 0x84, 0x02, "GET_CHARGING",
                              "Query charging status",
                              protocols=("extended", "modern"))
    SET_IDLE_TIME = CommandDef(0x07, 0x03, 0x02, "SET_IDLE_TIME",
                               "Set idle timeout (60-900s)",
                               protocols=("extended", "modern"))
    GET_IDLE_TIME = CommandDef(0x07, 0x83, 0x02, "GET_IDLE_TIME",
                               "Query idle timeout",
                               protocols=("extended", "modern"))

    # Class 0x0F - Extended Matrix Effects
    SET_EFFECT_EXTENDED = CommandDef(0x0F, 0x02, None, "SET_EFFECT_EXTENDED",
                                     "Apply extended effect",
                                     protocols=("extended", "modern"))
    SET_FRAME_EXTENDED = CommandDef(0x0F, 0x03, None, "SET_FRAME_EXTENDED",
                                    "Extended custom frame",
                                    protocols=("extended", "modern"))
    SET_BRIGHTNESS_EXTENDED = CommandDef(0x0F, 0x04, 0x03, "SET_BRIGHTNESS_EXTENDED",
                                         "Set brightness (extended)",
                                         protocols=("extended", "modern"))
    GET_BRIGHTNESS_EXTENDED = CommandDef(0x0F, 0x84, 0x03, "GET_BRIGHTNESS_EXTENDED",
                                         "Query brightness (extended)",
                                         protocols=("extended", "modern"))
```

**Tasks:**
- [ ] Create commands.py with CommandDef and Commands registry
- [ ] Add all known commands from protocol reference
- [ ] Add protocol compatibility info to each command

### 4.2 Effect Mapping

**New file:** `uchroma/server/effects.py`

```python
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class EffectDef:
    """Definition of a lighting effect."""

    name: str
    legacy_id: Optional[int]
    extended_id: Optional[int]
    description: str = ""
    max_colors: int = 0
    has_speed: bool = False
    has_direction: bool = False


class Effects:
    """Effect registry with protocol-aware mapping."""

    DISABLE = EffectDef("disable", legacy_id=0x00, extended_id=0x00,
                        description="Disable all effects")
    STATIC = EffectDef("static", legacy_id=0x06, extended_id=0x01,
                       description="Static color", max_colors=1)
    SPECTRUM = EffectDef("spectrum", legacy_id=0x04, extended_id=0x03,
                         description="Cycle through all colors")
    WAVE = EffectDef("wave", legacy_id=0x01, extended_id=0x04,
                     description="Wave animation", has_direction=True)
    BREATHE = EffectDef("breathe", legacy_id=0x03, extended_id=0x02,
                        description="Breathing colors", max_colors=2)
    REACTIVE = EffectDef("reactive", legacy_id=0x02, extended_id=0x05,
                         description="React to keypresses",
                         max_colors=1, has_speed=True)
    STARLIGHT = EffectDef("starlight", legacy_id=0x19, extended_id=0x07,
                          description="Sparkling effect",
                          max_colors=2, has_speed=True)
    CUSTOM_FRAME = EffectDef("custom_frame", legacy_id=0x05, extended_id=0x08,
                             description="Display custom frame")

    # Legacy-only effects
    GRADIENT = EffectDef("gradient", legacy_id=0x0A, extended_id=None)
    SWEEP = EffectDef("sweep", legacy_id=0x0C, extended_id=None)
    MORPH = EffectDef("morph", legacy_id=0x11, extended_id=None)
    FIRE = EffectDef("fire", legacy_id=0x12, extended_id=None)
    RIPPLE_SOLID = EffectDef("ripple_solid", legacy_id=0x13, extended_id=None)
    RIPPLE = EffectDef("ripple", legacy_id=0x14, extended_id=None)

    @classmethod
    def get_id(cls, effect_name: str, uses_extended: bool) -> Optional[int]:
        """Get effect ID for the given protocol."""
        effect = getattr(cls, effect_name.upper(), None)
        if effect is None:
            return None
        return effect.extended_id if uses_extended else effect.legacy_id

    @classmethod
    def supports_protocol(cls, effect_name: str, uses_extended: bool) -> bool:
        """Check if effect is supported on given protocol."""
        effect_id = cls.get_id(effect_name, uses_extended)
        return effect_id is not None
```

**Tasks:**
- [ ] Create effects.py with EffectDef and Effects registry
- [ ] Update StandardFX to use Effects.get_id()
- [ ] Add protocol support checking

---

## 5. Phase 4: Hardware Definition Schema

### 5.1 Extended YAML Schema

The new schema adds protocol metadata directly to device definitions:

```yaml
!device-config
# Identity
name: "Razer Viper V3 Pro"
manufacturer: Razer
type: MOUSE

# USB
vendor_id: 0x1532
product_id: 0x00C0
product_id_wireless: 0x00C1  # Optional paired wireless PID

# Protocol (replaces most quirks)
protocol:
  version: modern              # legacy | extended | modern | wireless_kb
  transaction_id: 0x1F
  transaction_id_wireless: 0x1F
  extended_fx: true
  inter_command_delay: 0.007   # seconds

# Matrix
dimensions: [1, 1]             # [height, width]
matrix_type: none              # none | single | row | full

# Capabilities (replaces some quirks)
capabilities:
  - wireless                   # Battery/charging support
  - hyperpolling               # 4000/8000Hz polling
  - no_led                     # No RGB LEDs

# Effects (what the device supports)
hardware_effects:
  - disable
  - static
  - spectrum
  - breathe

# LEDs
supported_leds: []             # Empty = no LEDs
```

### 5.2 Schema Migration Strategy

1. Keep existing quirks working (backwards compat)
2. Add new `protocol` and `capabilities` fields to YAML loader
3. Generate ProtocolConfig from either new fields OR legacy quirks
4. Eventually deprecate quirk-based transaction codes

**Tasks:**
- [ ] Extend Hardware class to parse new protocol fields
- [ ] Add capabilities list parsing
- [ ] Create migration script to convert old YAML to new format
- [ ] Update YAML loader to handle both formats

---

## 6. Phase 5: Keyboard Layout System

### 6.1 Current Problems

The current system has several pain points:

1. **Manual coordinate mapping** - Every key needs `[[row, col]]` or `[[row, col1], [row, col2]]`
2. **Locale-blind** - No concept of US/UK/ISO/JIS layouts
3. **Fixup complexity** - Copy/insert/delete operations are confusing
4. **No tooling** - The "funny cli" mentioned needs resurrection/improvement

### 6.2 Proposed Improvements

#### 6.2.1 Layout Templates

Create base layout templates that most devices can inherit:

**New file:** `uchroma/server/data/layouts/ansi_full.yaml`

```yaml
# ANSI Full-size keyboard layout template
# 6 rows x 22 columns
!keyboard-layout
name: ANSI Full
rows: 6
cols: 22
locale: US

# Row 0: Function row
row_0:
  ESC: [0, 1]
  F1: [0, 3]
  F2: [0, 4]
  # ...

# Row 1: Number row
row_1:
  GRAVE: [1, 1]
  1: [1, 2]
  # ...
```

**Device can reference:**
```yaml
!device-config
name: BlackWidow Chroma
layout: ansi_full  # Reference to template
layout_overrides:  # Device-specific adjustments
  SPACE: [[5, 5], [5, 6], [5, 7], [5, 8], [5, 9]]  # Wider spacebar
```

#### 6.2.2 Layout Validation Tool

**New file:** `uchroma/tools/layout_validator.py`

```python
def validate_layout(layout: KeyMapping, dimensions: tuple) -> list[str]:
    """Validate keyboard layout for consistency."""
    errors = []
    height, width = dimensions

    for key, coords in layout.items():
        for row, col in coords:
            if row < 0 or row >= height:
                errors.append(f"{key}: row {row} out of range (0-{height-1})")
            if col < 0 or col >= width:
                errors.append(f"{key}: col {col} out of range (0-{width-1})")

    # Check for overlapping coordinates
    all_coords = []
    for key, coords in layout.items():
        for coord in coords:
            if coord in all_coords:
                errors.append(f"{key}: coordinate {coord} already used")
            all_coords.append(coord)

    return errors
```

#### 6.2.3 Interactive Layout Builder

Resurrect and improve the CLI tool for creating layouts:

**New file:** `uchroma/tools/layout_builder.py`

Features:
- Interactive terminal UI showing matrix grid
- Press key to assign current matrix position
- Visual feedback of assigned keys
- Export to YAML format
- Import existing layout for editing

```python
class LayoutBuilder:
    """Interactive keyboard layout builder."""

    def __init__(self, dimensions: tuple[int, int]):
        self.height, self.width = dimensions
        self.mapping = {}
        self.current_pos = (0, 0)

    def run_interactive(self):
        """Run interactive TUI for layout building."""
        # TODO: Implement with curses or similar
        pass

    def export_yaml(self, path: str):
        """Export current mapping to YAML."""
        pass
```

#### 6.2.4 Locale Variants

Support different regional layouts:

```yaml
!device-config
name: BlackWidow Chroma
layout: ansi_full
locale_variants:
  UK:
    # ISO layout differences
    ENTER: [[3, 13], [3, 14], [2, 14]]  # Big Enter key
    BACKSLASH: [[4, 2]]  # Different position
  DE:
    # German layout
    Z: [[4, 4]]  # Swapped with Y
    Y: [[2, 7]]
```

**Tasks:**
- [ ] Create layout template system
- [ ] Implement layout validation tool
- [ ] Create/resurrect interactive layout builder
- [ ] Add locale variant support
- [ ] Document layout creation process

---

## 7. Phase 6: Test Infrastructure

### 7.1 Test Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_protocol.py         # Protocol version tests
├── test_commands.py         # Command registry tests
├── test_effects.py          # Effect mapping tests
├── test_report.py           # Report packing/unpacking
├── test_crc.py              # CRC calculation
├── test_hardware.py         # Hardware config loading
├── test_layout.py           # Keyboard layout validation
├── test_yaml_schema.py      # YAML schema validation
├── integration/
│   ├── test_mock_device.py  # Mock HID device tests
│   └── test_device_flow.py  # End-to-end device flows
└── fixtures/
    ├── mock_hid.py          # Mock HID device implementation
    └── sample_devices.yaml  # Test device configurations
```

### 7.2 Mock HID Device

**File:** `tests/fixtures/mock_hid.py`

```python
from dataclasses import dataclass, field
from typing import Callable, Optional
import numpy as np


@dataclass
class MockHIDDevice:
    """Mock HID device for testing."""

    vendor_id: int = 0x1532
    product_id: int = 0x0203
    responses: dict = field(default_factory=dict)

    sent_reports: list = field(default_factory=list)

    def send_feature_report(self, data: bytes, report_id: bytes = b"\x00"):
        """Record sent report and prepare response."""
        self.sent_reports.append((report_id, data))

    def get_feature_report(self, report_id: bytes, size: int) -> bytes:
        """Return mock response for the last sent command."""
        if not self.sent_reports:
            return self._error_response(0x04)  # TIMEOUT

        _, request = self.sent_reports[-1]
        cmd_class = request[5]
        cmd_id = request[6]

        key = (cmd_class, cmd_id)
        if key in self.responses:
            return self.responses[key]

        # Default: return OK with empty data
        return self._ok_response()

    def _ok_response(self, data: bytes = b"") -> bytes:
        """Generate OK response."""
        resp = bytearray(90)
        resp[0] = 0x02  # Status OK
        resp[1] = 0xFF  # Transaction ID
        resp[4] = len(data)
        resp[8:8+len(data)] = data
        # Calculate CRC
        crc = 0
        for i in range(1, 87):
            crc ^= resp[i]
        resp[88] = crc
        return bytes(resp)

    def _error_response(self, status: int) -> bytes:
        """Generate error response."""
        resp = bytearray(90)
        resp[0] = status
        return bytes(resp)


def create_mock_device(product_id: int = 0x0203, **responses) -> MockHIDDevice:
    """Factory for creating mock devices with preset responses."""
    device = MockHIDDevice(product_id=product_id)
    device.responses.update(responses)
    return device
```

### 7.3 Core Unit Tests

**File:** `tests/test_report.py`

```python
import pytest
import numpy as np
from uchroma.server.report import RazerReport, Status


class MockDriver:
    """Minimal driver mock for report testing."""

    def __init__(self):
        self.logger = logging.getLogger("test")
        self.hid = MockHIDDevice()
        self.last_cmd_time = None

    def device_open(self):
        return contextlib.nullcontext()


class TestRazerReport:
    def test_pack_request_basic(self):
        """Test basic request packing."""
        driver = MockDriver()
        report = RazerReport(
            driver,
            command_class=0x00,
            command_id=0x81,
            data_size=0x02,
            transaction_id=0xFF,
        )

        packed = report._pack_request()

        assert len(packed) == 90
        assert packed[0] == 0x00  # Status (always 0x00 for requests)
        assert packed[1] == 0xFF  # Transaction ID
        # packed[2:4] = Remaining packets (big-endian)
        assert packed[4] == 0x00  # Protocol type
        assert packed[5] == 0x02  # Data size
        assert packed[6] == 0x00  # Command class
        assert packed[7] == 0x81  # Command ID

    def test_pack_request_with_args(self):
        """Test request packing with arguments."""
        driver = MockDriver()
        report = RazerReport(driver, 0x03, 0x0A, None)
        report.args.put(0x06)  # Static effect
        report.args.put(0xFF)  # Red
        report.args.put(0x00)  # Green
        report.args.put(0x00)  # Blue

        packed = report._pack_request()

        assert packed[8] == 0x06
        assert packed[9] == 0xFF
        assert packed[10] == 0x00
        assert packed[11] == 0x00

    def test_crc_calculation(self):
        """Test CRC is calculated correctly."""
        driver = MockDriver()
        report = RazerReport(driver, 0x00, 0x81, 0x02, transaction_id=0xFF)

        packed = report._pack_request()

        # Verify CRC
        crc = 0
        for i in range(1, 87):
            crc ^= packed[i]
        assert packed[88] == crc

    def test_unpack_response_ok(self):
        """Test unpacking successful response."""
        driver = MockDriver()
        report = RazerReport(driver, 0x00, 0x81, 0x02)

        # Create mock response
        response = bytearray(90)
        response[0] = 0x02  # Status OK
        response[4] = 0x02  # Data size
        response[8] = 0x01  # Firmware major
        response[9] = 0x23  # Firmware minor

        result = report._unpack_response(bytes(response))

        assert result is True
        assert report.status == Status.OK
        assert report.result == b"\x01\x23"


class TestCRC:
    def test_fast_crc_matches_python(self):
        """Verify Cython CRC matches pure Python implementation."""
        from uchroma.server._crc import fast_crc

        test_data = bytes(range(90))

        # Python reference implementation
        expected = 0
        for i in range(1, 87):
            expected ^= test_data[i]

        assert fast_crc(test_data) == expected
```

**File:** `tests/test_effects.py`

```python
import pytest
from uchroma.server.effects import Effects


class TestEffects:
    def test_get_id_legacy(self):
        """Test getting legacy effect IDs."""
        assert Effects.get_id("static", uses_extended=False) == 0x06
        assert Effects.get_id("spectrum", uses_extended=False) == 0x04
        assert Effects.get_id("wave", uses_extended=False) == 0x01

    def test_get_id_extended(self):
        """Test getting extended effect IDs."""
        assert Effects.get_id("static", uses_extended=True) == 0x01
        assert Effects.get_id("spectrum", uses_extended=True) == 0x03
        assert Effects.get_id("wave", uses_extended=True) == 0x04

    def test_legacy_only_effects(self):
        """Test effects that only exist in legacy protocol."""
        assert Effects.get_id("fire", uses_extended=False) == 0x12
        assert Effects.get_id("fire", uses_extended=True) is None
        assert Effects.supports_protocol("fire", uses_extended=False) is True
        assert Effects.supports_protocol("fire", uses_extended=True) is False
```

**File:** `tests/test_hardware.py`

```python
import pytest
from uchroma.server.hardware import Hardware, Quirks


class TestHardware:
    def test_load_keyboard_yaml(self):
        """Test loading keyboard configuration."""
        config = Hardware.get_type(Hardware.Type.KEYBOARD)
        assert config is not None

        # Find BlackWidow Chroma
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.name == "BlackWidow Chroma"
        assert device.dimensions == (6, 22)

    def test_quirk_detection(self):
        """Test quirk checking."""
        device = Hardware.get_device(0x0050)  # Naga Hex V2
        assert device is not None
        assert device.has_quirk(Quirks.TRANSACTION_CODE_3F)
        assert device.has_quirk(Quirks.EXTENDED_FX_CMDS)

    def test_has_matrix(self):
        """Test matrix detection."""
        keyboard = Hardware.get_device(0x0203)  # BlackWidow Chroma
        assert keyboard.has_matrix is True

        mouse = Hardware.get_device(0x0043)  # DeathAdder Chroma
        assert mouse.has_matrix is False


class TestYAMLSchema:
    def test_all_devices_have_product_id(self):
        """Ensure all devices have a product_id."""
        for hw_type in Hardware.Type:
            config = Hardware.get_type(hw_type)
            if config is None:
                continue

            def check_device(device):
                if device.product_id is None and device.children:
                    for child in device.children:
                        check_device(child)
                elif device.product_id is not None:
                    assert device.product_id > 0

            check_device(config)

    def test_dimensions_are_valid(self):
        """Ensure dimensions are valid when present."""
        for hw_type in Hardware.Type:
            config = Hardware.get_type(hw_type)
            if config is None:
                continue

            def check_device(device):
                if device.dimensions is not None:
                    height, width = device.dimensions
                    assert height > 0, f"{device.name}: height must be positive"
                    assert width > 0, f"{device.name}: width must be positive"

                if device.children:
                    for child in device.children:
                        check_device(child)

            check_device(config)
```

### 7.4 Integration Tests

**File:** `tests/integration/test_mock_device.py`

```python
import pytest
from tests.fixtures.mock_hid import MockHIDDevice, create_mock_device


class TestMockDeviceIntegration:
    def test_firmware_query(self, mock_blackwidow):
        """Test firmware version query flow."""
        from uchroma.server.device_base import BaseUChromaDevice

        # Set up expected response
        mock_blackwidow.responses[(0x00, 0x81)] = mock_blackwidow._ok_response(b"\x01\x23")

        # Create device instance
        # device = ... (needs hardware fixture)

        # Query firmware
        # result = device.run_with_result(BaseUChromaDevice.Command.GET_FIRMWARE_VERSION)
        # assert result == b"\x01\x23"

    def test_effect_application(self, mock_blackwidow):
        """Test applying an effect."""
        pass


@pytest.fixture
def mock_blackwidow():
    """Create a mock BlackWidow Chroma device."""
    return create_mock_device(product_id=0x0203)
```

### 7.5 Test Configuration

**File:** `tests/conftest.py`

```python
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def hardware_configs():
    """Load all hardware configurations."""
    from uchroma.server.hardware import Hardware

    configs = {}
    for hw_type in Hardware.Type:
        configs[hw_type] = Hardware.get_type(hw_type)
    return configs
```

**Tasks:**
- [ ] Create tests directory structure
- [ ] Implement MockHIDDevice
- [ ] Write test_report.py
- [ ] Write test_crc.py
- [ ] Write test_effects.py
- [ ] Write test_hardware.py
- [ ] Write test_layout.py
- [ ] Write integration tests
- [ ] Add pytest to dev dependencies
- [ ] Create Makefile target for tests

---

## 8. Phase 7: Extended Device Support

### 8.1 Wireless Mixin

**File:** `uchroma/server/wireless.py`

```python
from .commands import Commands


class WirelessMixin:
    """Mixin for wireless device capabilities."""

    @property
    def is_wireless(self) -> bool:
        """Check if device has wireless capabilities."""
        from .hardware import Quirks
        return self.has_quirk(Quirks.WIRELESS)

    @property
    def battery_level(self) -> float:
        """Get battery level as percentage (0-100)."""
        if not self.is_wireless:
            return -1.0

        result = self.run_with_result(Commands.GET_BATTERY)
        if result is None or len(result) < 2:
            return -1.0

        # Battery is returned as 0-255, convert to percentage
        return (result[1] / 255.0) * 100.0

    @property
    def is_charging(self) -> bool:
        """Check if device is currently charging."""
        if not self.is_wireless:
            return False

        result = self.run_with_result(Commands.GET_CHARGING)
        if result is None or len(result) < 2:
            return False

        return result[1] == 0x01

    @property
    def idle_timeout(self) -> int:
        """Get idle timeout in seconds."""
        result = self.run_with_result(Commands.GET_IDLE_TIME)
        if result is None or len(result) < 2:
            return 0

        return (result[0] << 8) | result[1]

    @idle_timeout.setter
    def idle_timeout(self, seconds: int):
        """Set idle timeout (60-900 seconds)."""
        seconds = max(60, min(900, seconds))
        high = (seconds >> 8) & 0xFF
        low = seconds & 0xFF
        self.run_command(Commands.SET_IDLE_TIME, high, low)
```

### 8.2 HyperPolling Support

**File:** `uchroma/server/polling.py`

```python
from enum import Enum
from .commands import Commands


class PollingRate(Enum):
    """Standard polling rates."""
    HZ_125 = (0x08, 125)
    HZ_500 = (0x02, 500)
    HZ_1000 = (0x01, 1000)

    def __init__(self, code: int, rate: int):
        self.code = code
        self.rate = rate


class HyperPollingRate(Enum):
    """HyperPolling rates (requires HyperPolling dongle)."""
    HZ_125 = (0x40, 125)
    HZ_500 = (0x10, 500)
    HZ_1000 = (0x08, 1000)
    HZ_2000 = (0x04, 2000)
    HZ_4000 = (0x02, 4000)
    HZ_8000 = (0x02, 8000)  # Wireless mode with dongle

    def __init__(self, code: int, rate: int):
        self.code = code
        self.rate = rate


class PollingMixin:
    """Mixin for polling rate control."""

    @property
    def supports_hyperpolling(self) -> bool:
        """Check if device supports HyperPolling."""
        from .hardware import Quirks
        return self.has_quirk(Quirks.HYPERPOLLING)

    @property
    def polling_rate(self) -> int:
        """Get current polling rate in Hz."""
        result = self.run_with_result(Commands.GET_POLLING_RATE)
        if result is None:
            return 0

        code = result[0]
        for rate in PollingRate:
            if rate.code == code:
                return rate.rate
        return 0

    @polling_rate.setter
    def polling_rate(self, rate: int):
        """Set polling rate in Hz."""
        for pr in PollingRate:
            if pr.rate == rate:
                self.run_command(Commands.SET_POLLING_RATE, pr.code)
                return
        raise ValueError(f"Invalid polling rate: {rate}")
```

### 8.3 Capability Detection

**File:** `uchroma/server/capabilities.py`

```python
from dataclasses import dataclass, field
from typing import Set


@dataclass
class DeviceCapabilities:
    """Runtime capability detection for devices."""

    device: "BaseUChromaDevice"
    _tested_effects: dict = field(default_factory=dict)

    def has_hardware_effect(self, effect_name: str) -> bool:
        """Test if device supports a hardware effect."""
        if effect_name in self._tested_effects:
            return self._tested_effects[effect_name]

        # Check if effect is in supported_fx list
        if self.device.hardware.supported_fx:
            result = effect_name.lower() in [fx.lower() for fx in self.device.hardware.supported_fx]
            self._tested_effects[effect_name] = result
            return result

        # Default to trying it
        return True

    @property
    def requires_software_effects(self) -> bool:
        """True if device needs software-rendered effects."""
        from .hardware import Quirks
        return self.device.has_quirk(Quirks.SOFTWARE_EFFECTS)

    @property
    def has_matrix(self) -> bool:
        """True if device has an addressable LED matrix."""
        return self.device.has_matrix

    @property
    def has_leds(self) -> bool:
        """True if device has any RGB LEDs."""
        from .hardware import Quirks
        if self.device.has_quirk(Quirks.NO_LED):
            return False
        return bool(self.device.hardware.supported_leds)

    @property
    def supported_effects(self) -> Set[str]:
        """Get set of supported effects."""
        if self.device.hardware.supported_fx:
            return set(self.device.hardware.supported_fx)
        return set()
```

**Tasks:**
- [ ] Create wireless.py with WirelessMixin
- [ ] Create polling.py with PollingMixin
- [ ] Create capabilities.py with DeviceCapabilities
- [ ] Integrate mixins into device classes
- [ ] Add capability checking to FX manager

---

## 8. Phase 8: System Control (Laptop EC)

This phase adds fan control, power mode switching, and system monitoring for Razer Blade laptops. This is **experimental** and requires hardware testing.

### 8.1 Overview

Razer Blade laptops have an Embedded Controller (EC) that manages:
- Fan speed (automatic and manual control)
- Power modes (Balanced, Gaming, Creator)
- CPU/GPU TDP limits
- Thermal management

**Reference implementations:**
- [razer-laptop-control](https://github.com/rnd-ash/razer-laptop-control) (archived)
- [razer-laptop-control-no-dkms](https://github.com/Razer-Linux/razer-laptop-control-no-dkms)
- [librazerblade](https://github.com/Meetem/librazerblade)

### 8.2 EC Command Protocol

**Command Class 0x0D — Laptop EC Control**

| Command ID | Name | Data Size | Description |
|------------|------|-----------|-------------|
| `0x02` | SET_FAN_MODE | var | Set fan control mode/RPM |
| `0x82` | GET_FAN_RPM | var | Query current fan speed |
| `0x0B` | SET_POWER_MODE | 0x02 | Set power profile |
| `0x8B` | GET_POWER_MODE | 0x02 | Query power profile |
| `0x0D` | SET_BOOST | var | CPU/GPU boost control |
| `0x8D` | GET_BOOST | var | Query boost state |

**Note:** Command IDs are partially researched. Hardware testing required.

### 8.3 Power Modes

```python
from enum import IntEnum


class PowerMode(IntEnum):
    """Laptop power profiles."""

    BALANCED = 0      # 35W CPU TDP, quiet fans
    GAMING = 1        # 55W CPU TDP, aggressive cooling
    CREATOR = 2       # Higher GPU TDP, select models only
    CUSTOM = 4        # Manual fan control active


class BoostMode(IntEnum):
    """CPU/GPU boost settings."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    BOOST = 3         # Maximum performance
```

### 8.4 Fan Control Implementation

**File:** `uchroma/server/system_control.py`

```python
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple

from .commands import CommandDef
from .types import BaseCommand


# EC Control Commands (Class 0x0D)
class ECCommand(BaseCommand):
    """Embedded Controller commands for Blade laptops."""

    SET_FAN_MODE = (0x0D, 0x02, None)
    GET_FAN_RPM = (0x0D, 0x82, None)
    SET_POWER_MODE = (0x0D, 0x0B, 0x02)
    GET_POWER_MODE = (0x0D, 0x8B, 0x02)
    SET_BOOST = (0x0D, 0x0D, None)
    GET_BOOST = (0x0D, 0x8D, None)


@dataclass
class FanLimits:
    """Fan RPM limits for a specific model."""

    min_rpm: int = 0         # 0 = automatic
    min_manual_rpm: int = 3500
    max_rpm: int = 5000
    supports_dual_fan: bool = False


# Model-specific fan limits
FAN_LIMITS = {
    "Blade 15": FanLimits(max_rpm=5000),
    "Blade 17": FanLimits(max_rpm=5300, supports_dual_fan=True),
    "Blade 14": FanLimits(max_rpm=5000),
    "Blade Stealth": FanLimits(max_rpm=4500),
    "default": FanLimits(max_rpm=5000),
}


class SystemControlMixin:
    """Mixin for laptop system control (fan, power modes)."""

    @property
    def supports_system_control(self) -> bool:
        """Check if device supports EC control."""
        from .hardware import Hardware
        return self._hardware.type == Hardware.Type.LAPTOP

    @property
    def fan_limits(self) -> FanLimits:
        """Get fan limits for this model."""
        for model_prefix, limits in FAN_LIMITS.items():
            if self._hardware.name and model_prefix in self._hardware.name:
                return limits
        return FAN_LIMITS["default"]

    # ─────────────────────────────────────────────────────────────────────
    # Fan Control
    # ─────────────────────────────────────────────────────────────────────

    @property
    def fan_rpm(self) -> Tuple[int, Optional[int]]:
        """
        Get current fan RPM.

        Returns:
            Tuple of (fan1_rpm, fan2_rpm) - fan2 is None if single fan
        """
        if not self.supports_system_control:
            return (0, None)

        result = self.run_with_result(ECCommand.GET_FAN_RPM)
        if result is None or len(result) < 2:
            return (0, None)

        fan1 = (result[0] << 8) | result[1]

        fan2 = None
        if self.fan_limits.supports_dual_fan and len(result) >= 4:
            fan2 = (result[2] << 8) | result[3]

        return (fan1, fan2)

    @property
    def fan_mode(self) -> str:
        """Get current fan mode: 'auto' or 'manual'."""
        # Implementation depends on how GET_FAN_RPM encodes mode
        return "auto"  # TODO: Determine from hardware response

    def set_fan_auto(self) -> bool:
        """Set fans to automatic control."""
        if not self.supports_system_control:
            return False

        return self.run_command(ECCommand.SET_FAN_MODE, 0x00)

    def set_fan_rpm(self, rpm: int, fan2_rpm: Optional[int] = None) -> bool:
        """
        Set manual fan RPM.

        Args:
            rpm: Target RPM for fan 1 (or both fans if fan2_rpm not specified)
            fan2_rpm: Optional separate RPM for fan 2

        Returns:
            True if successful

        Raises:
            ValueError: If RPM is outside safe limits
        """
        if not self.supports_system_control:
            return False

        limits = self.fan_limits

        # Validate RPM
        if rpm != 0:  # 0 = auto
            if rpm < limits.min_manual_rpm:
                raise ValueError(
                    f"RPM {rpm} below minimum {limits.min_manual_rpm}. "
                    f"Use set_fan_auto() for automatic control."
                )
            if rpm > limits.max_rpm:
                raise ValueError(f"RPM {rpm} exceeds maximum {limits.max_rpm}")

        # Pack RPM as big-endian 16-bit
        args = [(rpm >> 8) & 0xFF, rpm & 0xFF]

        if fan2_rpm is not None and limits.supports_dual_fan:
            if fan2_rpm < limits.min_manual_rpm or fan2_rpm > limits.max_rpm:
                raise ValueError(f"Fan 2 RPM {fan2_rpm} outside limits")
            args.extend([(fan2_rpm >> 8) & 0xFF, fan2_rpm & 0xFF])

        return self.run_command(ECCommand.SET_FAN_MODE, *args)

    # ─────────────────────────────────────────────────────────────────────
    # Power Modes
    # ─────────────────────────────────────────────────────────────────────

    @property
    def power_mode(self) -> PowerMode:
        """Get current power mode."""
        if not self.supports_system_control:
            return PowerMode.BALANCED

        result = self.run_with_result(ECCommand.GET_POWER_MODE)
        if result is None or len(result) < 1:
            return PowerMode.BALANCED

        try:
            return PowerMode(result[0])
        except ValueError:
            return PowerMode.BALANCED

    @power_mode.setter
    def power_mode(self, mode: PowerMode):
        """Set power mode."""
        if not self.supports_system_control:
            return

        self.run_command(ECCommand.SET_POWER_MODE, int(mode), 0x00)

    def set_gaming_mode(self) -> bool:
        """Enable gaming mode (55W CPU TDP, aggressive cooling)."""
        self.power_mode = PowerMode.GAMING
        return True

    def set_balanced_mode(self) -> bool:
        """Enable balanced mode (35W CPU TDP, quiet operation)."""
        self.power_mode = PowerMode.BALANCED
        return True

    def set_creator_mode(self) -> bool:
        """Enable creator mode (higher GPU TDP)."""
        self.power_mode = PowerMode.CREATOR
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Boost Control
    # ─────────────────────────────────────────────────────────────────────

    @property
    def cpu_boost(self) -> BoostMode:
        """Get CPU boost mode."""
        result = self.run_with_result(ECCommand.GET_BOOST)
        if result is None:
            return BoostMode.MEDIUM
        # TODO: Parse response
        return BoostMode.MEDIUM

    @cpu_boost.setter
    def cpu_boost(self, mode: BoostMode):
        """Set CPU boost mode."""
        self.run_command(ECCommand.SET_BOOST, 0x01, int(mode))  # 0x01 = CPU

    @property
    def gpu_boost(self) -> BoostMode:
        """Get GPU boost mode."""
        result = self.run_with_result(ECCommand.GET_BOOST)
        if result is None:
            return BoostMode.MEDIUM
        # TODO: Parse response
        return BoostMode.MEDIUM

    @gpu_boost.setter
    def gpu_boost(self, mode: BoostMode):
        """Set GPU boost mode."""
        self.run_command(ECCommand.SET_BOOST, 0x02, int(mode))  # 0x02 = GPU
```

### 8.5 Temperature Monitoring via hwmon

For temperature data, we integrate with Linux hwmon instead of EC commands:

**File:** `uchroma/server/thermal.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import re


@dataclass
class ThermalZone:
    """A thermal sensor zone."""

    name: str
    path: Path
    temp_input: Path

    def read_temp(self) -> float:
        """Read temperature in Celsius."""
        try:
            raw = self.temp_input.read_text().strip()
            # hwmon reports in millidegrees
            return int(raw) / 1000.0
        except (OSError, ValueError):
            return 0.0


class ThermalMonitor:
    """
    Monitor system temperatures via Linux hwmon.

    Works with:
    - coretemp (Intel CPU)
    - k10temp (AMD CPU)
    - nvidia (NVIDIA GPU via nvidia-smi or hwmon)
    - amdgpu (AMD GPU)
    """

    HWMON_PATH = Path("/sys/class/hwmon")

    def __init__(self):
        self._zones: Dict[str, ThermalZone] = {}
        self._discover_zones()

    def _discover_zones(self):
        """Discover available thermal zones."""
        if not self.HWMON_PATH.exists():
            return

        for hwmon_dir in self.HWMON_PATH.iterdir():
            name_file = hwmon_dir / "name"
            if not name_file.exists():
                continue

            name = name_file.read_text().strip()

            # Find temp inputs
            for temp_input in hwmon_dir.glob("temp*_input"):
                label_file = temp_input.with_name(
                    temp_input.name.replace("_input", "_label")
                )
                if label_file.exists():
                    label = label_file.read_text().strip()
                else:
                    # Use index from filename
                    match = re.search(r"temp(\d+)", temp_input.name)
                    label = f"Temp {match.group(1)}" if match else "Unknown"

                zone_name = f"{name}/{label}"
                self._zones[zone_name] = ThermalZone(
                    name=zone_name,
                    path=hwmon_dir,
                    temp_input=temp_input,
                )

    @property
    def zones(self) -> List[str]:
        """List available thermal zones."""
        return list(self._zones.keys())

    def read_temp(self, zone: str) -> float:
        """Read temperature from a specific zone."""
        if zone not in self._zones:
            return 0.0
        return self._zones[zone].read_temp()

    def read_all(self) -> Dict[str, float]:
        """Read all temperatures."""
        return {name: zone.read_temp() for name, zone in self._zones.items()}

    @property
    def cpu_temp(self) -> float:
        """Get CPU package temperature."""
        # Try common CPU sensor names
        for pattern in ["coretemp/Package", "k10temp/Tctl", "k10temp/Tdie"]:
            for zone_name in self._zones:
                if pattern in zone_name:
                    return self._zones[zone_name].read_temp()
        return 0.0

    @property
    def gpu_temp(self) -> float:
        """Get GPU temperature."""
        # Try common GPU sensor names
        for pattern in ["amdgpu/edge", "nvidia/GPU"]:
            for zone_name in self._zones:
                if pattern in zone_name:
                    return self._zones[zone_name].read_temp()

        # Fallback: try nvidia-smi
        return self._nvidia_smi_temp()

    def _nvidia_smi_temp(self) -> float:
        """Get NVIDIA GPU temp via nvidia-smi."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        return 0.0
```

### 8.6 D-Bus Interface

**Add to:** `uchroma/server/dbus.py`

```python
class SystemControlInterface:
    """D-Bus interface for laptop system control."""

    # ─────────────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────────────

    @dbus_property(access=PropertyAccess.READ)
    def FanRPM(self) -> "ai":
        """Current fan RPM(s)."""
        rpm1, rpm2 = self._device.fan_rpm
        return [rpm1] if rpm2 is None else [rpm1, rpm2]

    @dbus_property(access=PropertyAccess.READ)
    def FanMode(self) -> "s":
        """Current fan mode: 'auto' or 'manual'."""
        return self._device.fan_mode

    @dbus_property(access=PropertyAccess.READWRITE)
    def PowerMode(self) -> "s":
        """Power mode: 'balanced', 'gaming', or 'creator'."""
        return self._device.power_mode.name.lower()

    @PowerMode.setter
    def PowerMode(self, mode: "s"):
        from .system_control import PowerMode as PM
        self._device.power_mode = PM[mode.upper()]

    @dbus_property(access=PropertyAccess.READ)
    def CpuTemp(self) -> "d":
        """CPU temperature in Celsius."""
        return self._thermal.cpu_temp

    @dbus_property(access=PropertyAccess.READ)
    def GpuTemp(self) -> "d":
        """GPU temperature in Celsius."""
        return self._thermal.gpu_temp

    # ─────────────────────────────────────────────────────────────────────
    # Methods
    # ─────────────────────────────────────────────────────────────────────

    @method()
    def SetFanAuto(self) -> "b":
        """Set fans to automatic control."""
        return self._device.set_fan_auto()

    @method()
    def SetFanRPM(self, rpm: "i", rpm2: "i") -> "b":
        """
        Set manual fan RPM.

        Args:
            rpm: Fan 1 RPM (0 for auto)
            rpm2: Fan 2 RPM (-1 to match fan 1)
        """
        fan2 = None if rpm2 < 0 else rpm2
        try:
            return self._device.set_fan_rpm(rpm, fan2)
        except ValueError as e:
            # Log error, return False
            return False

    @method()
    def GetTemperatures(self) -> "a{sd}":
        """Get all available temperatures."""
        return self._thermal.read_all()
```

### 8.7 GTK System Control Panel

**File:** `uchroma/gtk/panels/system_panel.py`

```python
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


class SystemControlPanel(Gtk.Box):
    """Panel for laptop fan and power control."""

    def __init__(self, device_proxy):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._proxy = device_proxy
        self._update_timeout = None

        self._build_ui()
        self._start_updates()

    def _build_ui(self):
        # ─────────────────────────────────────────────────────────────────
        # Power Mode Section
        # ─────────────────────────────────────────────────────────────────
        power_group = Adw.PreferencesGroup(title="Power Mode")
        self.append(power_group)

        self._power_row = Adw.ComboRow(
            title="Performance Profile",
            subtitle="Affects CPU/GPU power limits and fan behavior",
        )
        model = Gtk.StringList.new(["Balanced", "Gaming", "Creator"])
        self._power_row.set_model(model)
        self._power_row.connect("notify::selected", self._on_power_mode_changed)
        power_group.add(self._power_row)

        # ─────────────────────────────────────────────────────────────────
        # Fan Control Section
        # ─────────────────────────────────────────────────────────────────
        fan_group = Adw.PreferencesGroup(title="Fan Control")
        self.append(fan_group)

        # Fan mode toggle
        self._fan_auto_row = Adw.SwitchRow(
            title="Automatic Fan Control",
            subtitle="Let the system manage fan speed",
        )
        self._fan_auto_row.connect("notify::active", self._on_fan_auto_toggled)
        fan_group.add(self._fan_auto_row)

        # Fan 1 RPM slider
        self._fan1_row = Adw.ActionRow(title="Fan 1 Speed")
        self._fan1_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 3500, 5000, 100
        )
        self._fan1_scale.set_hexpand(True)
        self._fan1_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._fan1_scale.connect("value-changed", self._on_fan_rpm_changed)
        self._fan1_row.add_suffix(self._fan1_scale)
        fan_group.add(self._fan1_row)

        # Current RPM display
        self._rpm_label = Gtk.Label(label="Current: -- RPM")
        self._rpm_label.add_css_class("dim-label")
        fan_group.add(self._rpm_label)

        # ─────────────────────────────────────────────────────────────────
        # Thermal Section
        # ─────────────────────────────────────────────────────────────────
        thermal_group = Adw.PreferencesGroup(title="Temperatures")
        self.append(thermal_group)

        self._cpu_temp_row = Adw.ActionRow(
            title="CPU",
            subtitle="Package temperature",
        )
        self._cpu_temp_label = Gtk.Label(label="--°C")
        self._cpu_temp_row.add_suffix(self._cpu_temp_label)
        thermal_group.add(self._cpu_temp_row)

        self._gpu_temp_row = Adw.ActionRow(
            title="GPU",
            subtitle="Graphics temperature",
        )
        self._gpu_temp_label = Gtk.Label(label="--°C")
        self._gpu_temp_row.add_suffix(self._gpu_temp_label)
        thermal_group.add(self._gpu_temp_row)

    def _start_updates(self):
        """Start periodic temperature/RPM updates."""
        self._update_timeout = GLib.timeout_add(1000, self._update_readings)

    def _update_readings(self) -> bool:
        """Update temperature and fan readings."""
        try:
            # Update temps
            cpu_temp = self._proxy.CpuTemp
            gpu_temp = self._proxy.GpuTemp
            self._cpu_temp_label.set_text(f"{cpu_temp:.0f}°C")
            self._gpu_temp_label.set_text(f"{gpu_temp:.0f}°C")

            # Update fan RPM
            rpm = self._proxy.FanRPM
            if len(rpm) == 1:
                self._rpm_label.set_text(f"Current: {rpm[0]} RPM")
            else:
                self._rpm_label.set_text(f"Current: {rpm[0]} / {rpm[1]} RPM")

        except Exception:
            pass

        return True  # Continue updates

    def _on_power_mode_changed(self, row, _pspec):
        """Handle power mode selection."""
        modes = ["balanced", "gaming", "creator"]
        self._proxy.PowerMode = modes[row.get_selected()]

    def _on_fan_auto_toggled(self, row, _pspec):
        """Handle auto fan toggle."""
        if row.get_active():
            self._proxy.SetFanAuto()
            self._fan1_scale.set_sensitive(False)
        else:
            self._fan1_scale.set_sensitive(True)

    def _on_fan_rpm_changed(self, scale):
        """Handle manual fan RPM change."""
        if not self._fan_auto_row.get_active():
            rpm = int(scale.get_value())
            self._proxy.SetFanRPM(rpm, -1)

    def cleanup(self):
        """Stop updates when panel is destroyed."""
        if self._update_timeout:
            GLib.source_remove(self._update_timeout)
            self._update_timeout = None
```

### 8.8 Safety Considerations

**IMPORTANT:** EC commands can affect system stability. Safeguards:

1. **Minimum RPM enforcement** - Never allow fans below 3500 RPM in manual mode
2. **Thermal failsafe** - If temp > 90°C, force fans to auto mode
3. **Graceful degradation** - If EC commands fail, log and continue
4. **User warnings** - Show confirmation dialogs for aggressive settings

```python
# Safety constants
THERMAL_CRITICAL = 95.0   # Force max fans
THERMAL_WARNING = 85.0    # Show warning
MIN_SAFE_RPM = 3500       # Absolute minimum manual RPM

def check_thermal_safety(device, thermal_monitor) -> bool:
    """Check if system is thermally safe."""
    cpu = thermal_monitor.cpu_temp
    gpu = thermal_monitor.gpu_temp

    if cpu > THERMAL_CRITICAL or gpu > THERMAL_CRITICAL:
        device.set_fan_auto()  # Force automatic cooling
        return False

    return True
```

### 8.9 CLI Commands

**Add to:** `uchroma/client/cmd.py`

```python
@cli.group()
def system():
    """Laptop system control commands."""
    pass


@system.command()
@click.option("--rpm", type=int, help="Set manual RPM (0 for auto)")
def fan(rpm):
    """Control fan speed."""
    if rpm is None:
        # Show current
        rpm1, rpm2 = device.fan_rpm
        click.echo(f"Fan 1: {rpm1} RPM")
        if rpm2:
            click.echo(f"Fan 2: {rpm2} RPM")
        click.echo(f"Mode: {device.fan_mode}")
    elif rpm == 0:
        device.set_fan_auto()
        click.echo("Fan set to automatic")
    else:
        device.set_fan_rpm(rpm)
        click.echo(f"Fan set to {rpm} RPM")


@system.command()
@click.argument("mode", type=click.Choice(["balanced", "gaming", "creator"]))
def power(mode):
    """Set power mode."""
    from uchroma.server.system_control import PowerMode
    device.power_mode = PowerMode[mode.upper()]
    click.echo(f"Power mode set to {mode}")


@system.command()
def temps():
    """Show system temperatures."""
    from uchroma.server.thermal import ThermalMonitor
    thermal = ThermalMonitor()
    for zone, temp in thermal.read_all().items():
        click.echo(f"{zone}: {temp:.1f}°C")
```

### 8.10 Hardware Testing Checklist

Before enabling EC control, test on actual hardware:

- [ ] Query GET_FAN_RPM returns valid data
- [ ] Query GET_POWER_MODE returns expected value
- [ ] SET_FAN_MODE with 0x00 enables auto mode
- [ ] SET_FAN_MODE with RPM value changes speed
- [ ] SET_POWER_MODE changes observable behavior
- [ ] System remains stable under load with manual fan
- [ ] Thermal failsafe triggers correctly
- [ ] Resume from suspend restores settings

**Testing commands:**
```bash
# With a test script
uv run python -c "
from uchroma.server.hardware import Hardware
from uchroma.server.system_control import ECCommand

# Get device, run query
# result = device.run_with_result(ECCommand.GET_FAN_RPM)
# print(result.hex() if result else 'No response')
"
```

**Tasks:**
- [ ] Research EC protocol on actual Blade hardware
- [ ] Create system_control.py with fan/power control
- [ ] Add hwmon integration for temperature monitoring
- [ ] Create D-Bus interface for system control
- [ ] Add GTK system control panel
- [ ] Write tests for system control
- [ ] Document safety limits and warnings

---

## 9. Migration Strategy

### 9.1 Phase Order

1. **Phase 1** (Non-Breaking) - Can be done immediately
   - Add new quirks
   - Update transaction ID logic
   - Add missing devices to YAML

2. **Phase 6** (Tests) - Should come early
   - Create test infrastructure
   - Write tests for existing functionality
   - This helps validate other phases

3. **Phase 2** (Protocol Abstraction) - Foundation for other phases
   - Create protocol.py
   - Integrate with device_base.py
   - Maintains backwards compatibility

4. **Phase 3** (Command Registry) - Builds on protocol abstraction
   - Create commands.py
   - Create effects.py
   - Update StandardFX to use new system

5. **Phase 4** (Hardware Schema) - Can be done incrementally
   - Extend YAML parser
   - Add new fields to existing devices
   - Migration script for full conversion

6. **Phase 5** (Layout System) - Independent work
   - Can be done in parallel with other phases
   - Create layout templates
   - Build validation tools

7. **Phase 7** (Extended Support) - After core refactoring
   - Add wireless mixin
   - Add polling support
   - Add capability detection

8. **Phase 8** (System Control) - Requires hardware testing
   - Fan control via EC commands
   - Power mode switching
   - Temperature monitoring via hwmon
   - **Note:** Needs actual Blade hardware to validate EC protocol

### 9.2 Backwards Compatibility

- All quirks-based code continues to work
- New protocol system falls back to quirks if new fields missing
- YAML files can be migrated incrementally
- Existing device classes don't need immediate changes

### 9.3 Risk Mitigation

- **Tests first**: Write tests for existing behavior before refactoring
- **Feature flags**: New protocol system can be disabled if issues arise
- **Gradual rollout**: Migrate one device type at a time
- **Validation**: Schema validation catches YAML errors early

---

## 10. Worklog

### Format
```
[DATE] [STATUS] [PHASE] Description
STATUS: TODO | IN_PROGRESS | DONE | BLOCKED
```

### Entries

```
[2026-01-16] [DONE] [1] Add missing quirks to hardware.py
[2026-01-16] [DONE] [1] Update get_report() with new transaction codes
[2026-01-16] [DONE] [1] Add BlackWidow V4 series to keyboard.yaml
[2026-01-16] [DONE] [1] Add Huntsman V3 Pro series to keyboard.yaml
[2026-01-16] [DONE] [1] Add DeathStalker V2 series to keyboard.yaml
[2026-01-16] [DONE] [1] Add wireless keyboard entries with 0x9F
[2026-01-15] [TODO] [1] Add modern mice with NO_LED quirk
[2026-01-15] [TODO] [1] Add missing mousepads to mousepad.yaml
[2026-01-15] [TODO] [1] Add missing accessories

[2026-01-15] [TODO] [2] Create protocol.py with ProtocolVersion
[2026-01-15] [TODO] [2] Add get_protocol_from_quirks()
[2026-01-15] [TODO] [2] Update device_base.py to use ProtocolConfig

[2026-01-15] [TODO] [3] Create commands.py with CommandDef
[2026-01-15] [TODO] [3] Add all commands from protocol reference
[2026-01-15] [TODO] [3] Create effects.py with EffectDef
[2026-01-15] [TODO] [3] Update StandardFX to use Effects.get_id()

[2026-01-15] [TODO] [4] Extend Hardware class for new protocol fields
[2026-01-15] [TODO] [4] Add capabilities list parsing
[2026-01-15] [TODO] [4] Create migration script for YAML

[2026-01-15] [TODO] [5] Create layout template system
[2026-01-15] [TODO] [5] Implement layout validation tool
[2026-01-15] [TODO] [5] Create interactive layout builder
[2026-01-15] [TODO] [5] Add locale variant support
[2026-01-15] [TODO] [5] Document layout creation process

[2026-01-15] [TODO] [6] Create tests directory structure
[2026-01-15] [TODO] [6] Implement MockHIDDevice
[2026-01-15] [TODO] [6] Write test_report.py
[2026-01-15] [TODO] [6] Write test_crc.py
[2026-01-15] [TODO] [6] Write test_effects.py
[2026-01-15] [TODO] [6] Write test_hardware.py
[2026-01-15] [TODO] [6] Write test_layout.py
[2026-01-15] [TODO] [6] Write integration tests
[2026-01-15] [TODO] [6] Create Makefile target for tests

[2026-01-15] [TODO] [7] Create wireless.py with WirelessMixin
[2026-01-15] [TODO] [7] Create polling.py with PollingMixin
[2026-01-15] [TODO] [7] Create capabilities.py
[2026-01-15] [TODO] [7] Integrate mixins into device classes

[2026-01-16] [TODO] [8] Research EC protocol on actual Blade hardware
[2026-01-16] [TODO] [8] Create system_control.py with fan/power control
[2026-01-16] [TODO] [8] Add hwmon integration for temperature monitoring
[2026-01-16] [TODO] [8] Create D-Bus interface for system control
[2026-01-16] [TODO] [8] Add GTK system control panel
[2026-01-16] [TODO] [8] Write tests for system control
[2026-01-16] [TODO] [8] Document safety limits and warnings
```

---

## Appendix A: Device Database Summary

### Devices Needing Addition

| Category | Model | PID | Transaction ID | Notes |
|----------|-------|-----|----------------|-------|
| Keyboard | BlackWidow V4 | 0x0287 | 0x1F | EXTENDED_FX |
| Keyboard | BlackWidow V4 X | 0x028D | 0x1F | EXTENDED_FX |
| Keyboard | BlackWidow V4 75% | 0x028E | 0x1F | EXTENDED_FX |
| Keyboard | Huntsman V3 Pro | 0x02A6 | 0x1F | EXTENDED_FX |
| Keyboard | DeathStalker V2 | 0x0295 | 0x1F | EXTENDED_FX |
| Keyboard | DeathStalker V2 Pro (W) | 0x0298 | 0x9F | WIRELESS |
| Mouse | Viper V3 Pro (Wired) | 0x00C0 | 0x1F | NO_LED |
| Mouse | Viper V3 Pro (Wireless) | 0x00C1 | 0x1F | NO_LED |
| Mouse | DeathAdder V3 | 0x00B2 | 0x1F | NO_LED |
| Mouse | Basilisk V3 | 0x0099 | 0x1F | 11 LEDs |
| Mousepad | Firefly V2 Pro | 0x0C08 | 0x1F | EXTENDED_FX |
| Accessory | Base Station V2 | 0x0F20 | 0x1F | EXTENDED_FX |

---

## Appendix B: Protocol Quick Reference

### Transaction IDs

| ID | Protocol | Devices |
|----|----------|---------|
| 0xFF | Legacy | Most keyboards, original mice |
| 0x3F | Extended | Naga Hex V2, DeathAdder Elite, Mamba Wireless |
| 0x1F | Modern | Blade 2021+, Basilisk Ultimate, Viper V3 Pro |
| 0x9F | Wireless KB | BlackWidow V3 Pro (wireless), DeathStalker V2 Pro |
| 0x08 | Special | Naga X |

### Effect ID Mapping

| Effect | Legacy (0x03) | Extended (0x0F) |
|--------|---------------|-----------------|
| Disable | 0x00 | 0x00 |
| Wave | 0x01 | 0x04 |
| Reactive | 0x02 | 0x05 |
| Breathe | 0x03 | 0x02 |
| Spectrum | 0x04 | 0x03 |
| Custom | 0x05 | 0x08 |
| Static | 0x06 | 0x01 |
| Starlight | 0x19 | 0x07 |

---

## Appendix C: EC Protocol Quick Reference (Laptops)

### Command Class 0x0D — EC Control

| Command | ID | Direction | Description |
|---------|-----|-----------|-------------|
| SET_FAN_MODE | 0x02 | Write | Set fan mode/RPM |
| GET_FAN_RPM | 0x82 | Read | Query fan speed |
| SET_POWER_MODE | 0x0B | Write | Set power profile |
| GET_POWER_MODE | 0x8B | Read | Query power profile |
| SET_BOOST | 0x0D | Write | CPU/GPU boost control |
| GET_BOOST | 0x8D | Read | Query boost state |

### Power Modes

| Mode | Value | CPU TDP | Fan Behavior |
|------|-------|---------|--------------|
| Balanced | 0x00 | 35W | Quiet, conservative |
| Gaming | 0x01 | 55W | Aggressive, sustained boost |
| Creator | 0x02 | 35W | Higher GPU TDP |
| Custom | 0x04 | Varies | Manual fan control |

### Fan Limits by Model

| Model | Min Manual RPM | Max RPM | Dual Fan |
|-------|----------------|---------|----------|
| Blade 15 | 3500 | 5000 | No |
| Blade 17 | 3500 | 5300 | Yes |
| Blade 14 | 3500 | 5000 | No |
| Blade Stealth | 3500 | 4500 | No |

### Safety Thresholds

| Threshold | Temperature | Action |
|-----------|-------------|--------|
| Warning | 85°C | Show UI warning |
| Critical | 95°C | Force auto fan mode |

---

## Appendix D: Related Projects

| Project | Description | Status |
|---------|-------------|--------|
| [razer-laptop-control](https://github.com/rnd-ash/razer-laptop-control) | Original fan/power driver | Archived (2022) |
| [razer-laptop-control-no-dkms](https://github.com/Razer-Linux/razer-laptop-control-no-dkms) | Maintained fork | Active |
| [librazerblade](https://github.com/Meetem/librazerblade) | C/C++ library for Blade control | Active |
| [OpenRazer](https://github.com/openrazer/openrazer) | Linux driver for Razer peripherals | Active |

---

*End of Document*
