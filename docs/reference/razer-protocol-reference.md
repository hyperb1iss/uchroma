# Razer USB HID Protocol Reference

Comprehensive documentation of the Razer Chroma USB HID protocol, compiled from reverse engineering
efforts by the OpenRazer project, razercfg, and community research.

**Vendor ID**: `0x1532` (Razer Inc.)

---

## 1. Report Structure

All Razer Chroma devices communicate via **90-byte USB HID feature reports**.

### Request Format (PC → Device)

| Offset | Size | Field             | Description                            |
| ------ | ---- | ----------------- | -------------------------------------- |
| 0      | 1    | Status            | Always `0x00` for requests             |
| 1      | 1    | Transaction ID    | Device-specific routing ID             |
| 2-3    | 2    | Remaining Packets | Big-endian, for multi-packet transfers |
| 4      | 1    | Protocol Type     | Always `0x00`                          |
| 5      | 1    | Data Size         | Number of argument bytes               |
| 6      | 1    | Command Class     | Category of command                    |
| 7      | 1    | Command ID        | Specific command within class          |
| 8-87   | 80   | Arguments         | Command parameters                     |
| 88     | 1    | CRC               | XOR checksum of bytes 1-86             |
| 89     | 1    | Reserved          | Always `0x00`                          |

### Response Format (Device → PC)

Same structure, but with status codes in byte 0:

| Status | Name        | Description           |
| ------ | ----------- | --------------------- |
| `0x00` | UNKNOWN     | Pending/unprocessed   |
| `0x01` | BUSY        | Retry needed          |
| `0x02` | OK          | Success               |
| `0x03` | FAIL        | Command failed        |
| `0x04` | TIMEOUT     | No response           |
| `0x05` | UNSUPPORTED | Command not supported |

### CRC Calculation

```python
def calculate_crc(report: bytes) -> int:
    crc = 0
    for i in range(1, 87):  # Bytes 1-86 inclusive
        crc ^= report[i]
    return crc
```

**Note**: Some devices (Blade 2021+) return `CRC=0x00` on success—validation should be skipped for
OK responses.

---

## 2. Transaction IDs

The transaction ID determines device routing and varies by hardware generation:

| Transaction ID | Device Generation  | Examples                                                     |
| -------------- | ------------------ | ------------------------------------------------------------ |
| `0xFF`         | Legacy/Standard    | Most keyboards, original mice                                |
| `0x3F`         | Extended Protocol  | Naga Hex V2, DeathAdder Elite, Mamba Wireless                |
| `0x1F`         | Modern (2021+)     | Blade 2021+, Basilisk Ultimate, Viper V3 Pro                 |
| `0x9F`         | Wireless Keyboards | BlackWidow V3 Pro (wireless), DeathStalker V2 Pro (wireless) |
| `0x80`         | Custom Frame Data  | Some laptops (lid logo)                                      |
| `0x08`         | Special Case       | Naga X                                                       |

### uchroma Quirks Mapping

```python
class Quirks(IntEnum):
    TRANSACTION_CODE_3F = 1
    EXTENDED_FX_CMDS = 2
    TRANSACTION_CODE_1F = 9
    CUSTOM_FRAME_80 = 5
```

---

## 3. Command Classes

### Class 0x00 — Device Info & Control

| ID     | Name                | Size | Description                                |
| ------ | ------------------- | ---- | ------------------------------------------ |
| `0x04` | SET_DEVICE_MODE     | 2    | Set driver mode (0x00=normal, 0x03=driver) |
| `0x05` | SET_POLLING_RATE    | 1    | Set polling rate                           |
| `0x40` | SET_POLLING_RATE_V2 | var  | Extended polling rate (HyperPolling)       |
| `0x41` | PAIRING_STEP        | 3    | Wireless pairing initiation                |
| `0x42` | UNPAIR              | 2    | Wireless unpairing                         |
| `0x46` | PAIRING_SCAN        | 1    | Start pairing scan                         |
| `0x81` | GET_FIRMWARE        | 2    | Query firmware version                     |
| `0x82` | GET_SERIAL          | 22   | Query serial number                        |
| `0x84` | GET_DEVICE_MODE     | 2    | Query current mode                         |
| `0x85` | GET_POLLING_RATE    | 1    | Query polling rate                         |
| `0xBF` | GET_PAIRED_DEVICES  | 31   | Query paired device list                   |
| `0xC0` | GET_POLLING_RATE_V2 | var  | Query extended polling                     |
| `0xC5` | GET_PAIRED_STATUS   | var  | Query paired device status                 |

### Class 0x02 — Key Remapping

| ID     | Name                 | Size | Description                          |
| ------ | -------------------- | ---- | ------------------------------------ |
| `0x0D` | SET_KEY_REMAP        | var  | Key remapping (non-analog keyboards) |
| `0x12` | SET_KEY_REMAP_ANALOG | var  | Key remapping (analog keyboards)     |

### Class 0x03 — Standard LED/Effects

| ID     | Name                   | Size | Description               |
| ------ | ---------------------- | ---- | ------------------------- |
| `0x00` | SET_LED_STATE          | 3    | Enable/disable LED        |
| `0x01` | SET_LED_COLOR          | 5    | Set LED color (RGB)       |
| `0x02` | SET_LED_MODE           | 3    | Set LED effect mode       |
| `0x03` | SET_LED_BRIGHTNESS     | 3    | Set brightness level      |
| `0x0A` | SET_EFFECT             | var  | Apply lighting effect     |
| `0x0B` | SET_FRAME_DATA_MATRIX  | var  | Custom frame (multi-row)  |
| `0x0C` | SET_FRAME_DATA_SINGLE  | var  | Custom frame (single row) |
| `0x10` | SET_DOCK_CHARGE_EFFECT | 1    | Dock charging LED         |
| `0x80` | GET_LED_STATE          | 3    | Query LED state           |
| `0x81` | GET_LED_COLOR          | 5    | Query LED color           |
| `0x82` | GET_LED_MODE           | 3    | Query LED mode            |
| `0x83` | GET_LED_BRIGHTNESS     | 3    | Query brightness          |

### Class 0x04 — DPI / Mouse Settings

| ID     | Name           | Size | Description           |
| ------ | -------------- | ---- | --------------------- |
| `0x05` | SET_DPI_XY     | 7    | Set X/Y DPI values    |
| `0x06` | SET_DPI_STAGES | var  | Set DPI stage presets |
| `0x85` | GET_DPI_XY     | 7    | Query current DPI     |
| `0x86` | GET_DPI_STAGES | var  | Query DPI stages      |

### Class 0x05 — Profile Management

| ID     | Name               | Size | Description                |
| ------ | ------------------ | ---- | -------------------------- |
| `0x02` | SET_PROFILE        | var  | Switch to profile slot     |
| `0x03` | GET_PROFILE        | var  | Query current profile      |
| `0x08` | WRITE_PROFILE_DATA | var  | Write data to profile slot |

Profile slot IDs: `0x00`=no-store, `0x01`=default/white, `0x02`=red, `0x03`=green, `0x04`=blue,
`0x05`=cyan

### Class 0x07 — Power & Battery

| ID     | Name                | Size | Description                    |
| ------ | ------------------- | ---- | ------------------------------ |
| `0x01` | SET_LOW_BATTERY     | 1    | Set low battery threshold      |
| `0x02` | SET_DOCK_BRIGHTNESS | 1    | Set dock LED brightness        |
| `0x03` | SET_IDLE_TIME       | 2    | Set idle timeout (60-900s)     |
| `0x10` | SET_DONGLE_LED      | 1    | Set HyperSpeed dongle LED mode |
| `0x80` | GET_BATTERY_LEVEL   | 2    | Query battery level (0-255)    |
| `0x81` | GET_LOW_BATTERY     | 1    | Query low battery threshold    |
| `0x82` | GET_DOCK_BRIGHTNESS | 1    | Query dock brightness          |
| `0x83` | GET_IDLE_TIME       | 2    | Query idle timeout             |
| `0x84` | GET_CHARGING_STATUS | 2    | Query charging (0=no, 1=yes)   |

### Class 0x0B — Calibration

| ID     | Name                 | Size | Description              |
| ------ | -------------------- | ---- | ------------------------ |
| `0x03` | SET_CALIBRATION      | var  | Surface calibration mode |
| `0x05` | SET_LIFTOFF          | var  | Lift-off distance        |
| `0x09` | START_CALIBRATION    | var  | Begin calibration        |
| `0x0B` | FINALIZE_CALIBRATION | var  | Complete calibration     |
| `0x85` | GET_CALIBRATION      | var  | Query calibration data   |

### Class 0x0D — Laptop Fan/Power (EC Control)

| ID     | Name         | Size | Description      |
| ------ | ------------ | ---- | ---------------- |
| `0x02` | SET_FAN_MODE | var  | Fan control mode |
| `0x82` | GET_FAN_RPM  | var  | Query fan speed  |

### Class 0x0F — Extended Matrix Effects

| ID     | Name                   | Size | Description                 |
| ------ | ---------------------- | ---- | --------------------------- |
| `0x02` | SET_EFFECT_EXTENDED    | var  | Apply extended effect       |
| `0x03` | SET_FRAME_EXTENDED     | var  | Extended custom frame       |
| `0x04` | SET_LED_BRIGHTNESS_EXT | 3    | Set brightness (extended)   |
| `0x80` | GET_EFFECT_EXTENDED    | var  | Query current effect        |
| `0x82` | GET_MATRIX_EFFECT      | var  | Query matrix state          |
| `0x84` | GET_LED_BRIGHTNESS_EXT | 3    | Query brightness (extended) |

---

## 4. Effects

### Standard Effects (Class 0x03, ID 0x0A)

| Effect ID | Name         | Args                                 |
| --------- | ------------ | ------------------------------------ |
| `0x00`    | DISABLE      | —                                    |
| `0x01`    | WAVE         | direction (1=right, 2=left)          |
| `0x02`    | REACTIVE     | speed, R, G, B                       |
| `0x03`    | BREATHE      | mode, [colors...]                    |
| `0x04`    | SPECTRUM     | —                                    |
| `0x05`    | CUSTOM_FRAME | varstore                             |
| `0x06`    | STATIC       | R, G, B                              |
| `0x0A`    | GRADIENT     | —                                    |
| `0x0C`    | SWEEP        | direction, speed, bg_color, fg_color |
| `0x10`    | HIGHLIGHT    | —                                    |
| `0x11`    | MORPH        | mode, speed, color1, color2          |
| `0x12`    | FIRE         | mode, speed, color                   |
| `0x13`    | RIPPLE_SOLID | mode, speed, color                   |
| `0x14`    | RIPPLE       | mode, speed, color                   |
| `0x19`    | STARLIGHT    | mode, speed, [colors...]             |

### Extended Effects (Class 0x0F, ID 0x02)

Used on devices with `EXTENDED_FX_CMDS` quirk:

| Effect ID | Name         | Args                     |
| --------- | ------------ | ------------------------ |
| `0x00`    | DISABLE      | —                        |
| `0x01`    | STATIC       | R, G, B                  |
| `0x02`    | BREATHE      | mode, [colors...]        |
| `0x03`    | SPECTRUM     | —                        |
| `0x04`    | WAVE         | direction                |
| `0x05`    | REACTIVE     | speed, R, G, B           |
| `0x07`    | STARLIGHT    | mode, speed, [colors...] |
| `0x08`    | CUSTOM_FRAME | —                        |

**Format**: `[varstore, LED_type, effect_id, ...params]`

---

## 5. LED Identifiers

| LED Type      | ID     | Capabilities             |
| ------------- | ------ | ------------------------ |
| SCROLL_WHEEL  | `0x01` | RGB, brightness          |
| MISC          | `0x02` | RGB                      |
| BATTERY       | `0x03` | RGB (dock charge color)  |
| LOGO          | `0x04` | RGB, brightness          |
| BACKLIGHT     | `0x05` | RGB, brightness, effects |
| MACRO         | `0x07` | On/off                   |
| GAME          | `0x08` | On/off                   |
| PROFILE_RED   | `0x0E` | On/off                   |
| PROFILE_GREEN | `0x0C` | On/off                   |
| PROFILE_BLUE  | `0x0D` | On/off                   |
| CHARGING      | `0x20` | On/off                   |
| FAST_CHARGING | `0x21` | On/off                   |
| FULLY_CHARGED | `0x22` | On/off                   |

---

## 6. Polling Rates

### Standard Polling Rate Values (Class 0x00, ID 0x05)

| Value  | Rate    |
| ------ | ------- |
| `0x01` | 1000 Hz |
| `0x02` | 500 Hz  |
| `0x08` | 125 Hz  |

### HyperPolling Values (Class 0x00, ID 0x40)

| Value  | Rate                       |
| ------ | -------------------------- |
| `0x02` | 4000 Hz (8000 Hz wireless) |
| `0x04` | 2000 Hz                    |
| `0x08` | 1000 Hz                    |
| `0x10` | 500 Hz                     |
| `0x40` | 125 Hz                     |

**Note**: HyperPolling dongle sends each rate command twice with transaction IDs `0x00` and `0x01`.

---

## 7. Custom Frame Protocol

### Matrix Frame (multi-row keyboards)

**Command**: `0x03, 0x0B`

| Byte | Description                        |
| ---- | ---------------------------------- |
| 0    | Frame ID (usually `0xFF`)          |
| 1    | Row index (0-5 for 6-row keyboard) |
| 2    | Start column                       |
| 3    | End column                         |
| 4+   | RGB data (3 bytes per LED)         |

For keyboards wider than 24 columns, split into two commands.

### Single Row Frame (mousepads, mice)

**Command**: `0x03, 0x0C`

| Byte | Description |
| ---- | ----------- |
| 0    | Start index |
| 1    | End index   |
| 2+   | RGB data    |

---

## 8. Headset Protocol (Kraken Family)

Kraken headsets use a **completely different protocol**:

### Report Structure

- **Output Report ID**: 0x04 (37 bytes)
- **Input Report ID**: 0x05 (33 bytes)
- **Delay**: 25ms between commands

### Command Format

| Byte | Description                                                         |
| ---- | ------------------------------------------------------------------- |
| 0    | Destination (`0x00`=read RAM, `0x20`=read EEPROM, `0x40`=write RAM) |
| 1    | Length                                                              |
| 2-3  | Address (big-endian)                                                |
| 4+   | Arguments                                                           |

### Memory Addresses

**Rainie (Kraken 7.1 v1)**:

- LED Mode: `0x1008`
- Breathing Color: `0x15DE`

**Kylie (Kraken V2/Ultimate)**:

- LED Mode: `0x172D`
- Breathing 1: `0x1741`
- Breathing 2: `0x1745`
- Breathing 3: `0x174D`

### Effect Bits (single byte)

| Bit | Effect         |
| --- | -------------- |
| 0   | LED On         |
| 1   | Breathe Single |
| 2   | Spectrum       |
| 3   | Sync           |
| 4   | Breathe Double |
| 5   | Breathe Triple |

---

## 9. Inter-Command Timing

| Device Type       | Delay |
| ----------------- | ----- |
| Standard          | 7ms   |
| Headsets (Kraken) | 25ms  |
| Naga mice         | 35ms  |
| Wireless (retry)  | 100ms |

---

## 10. Known Quirks

### Device-Specific Issues

| Quirk                | Devices               | Workaround                       |
| -------------------- | --------------------- | -------------------------------- |
| CRC=0x00 on success  | Blade 2021+           | Skip CRC validation on OK status |
| Extended FX only     | Synapse 3 devices     | Use class 0x0F instead of 0x03   |
| No firmware effects  | Newer mice/keyboards  | Software-rendered effects only   |
| Battery always 0     | AA battery mice       | Check `is_wireless` flag         |
| Serial query timeout | Wireless (device off) | Mark device offline              |

### Multi-Packet Transfers

For commands exceeding 80 bytes of arguments:

1. Set `remaining_packets` field to count of additional packets
2. Send packets in sequence
3. Hardware processes on final packet (`remaining_packets=0`)

---

## 11. Reverse Engineering Methodology

### Setup

1. VirtualBox with Windows VM
2. Razer Synapse installed
3. USB passthrough to VM
4. Wireshark with usbmon kernel module

### Capture Commands

```bash
sudo modprobe usbmon
sudo setfacl -m u:$USER:r /dev/usbmon*
wireshark -k -i usbmon0
```

### Filter

```
usb.idVendor == 0x1532 && usb.transfer_type == 0x02
```

Look for "Leftover Capture Data" field containing protocol bytes.

---

## 12. Sources

- [OpenRazer GitHub](https://github.com/openrazer/openrazer)
- [OpenRazer Wiki - Reverse Engineering](https://github.com/openrazer/openrazer/wiki/Reverse-Engineering-USB-Protocol)
- [OpenRazer Wiki - Unknown Commands](https://github.com/openrazer/openrazer/wiki/Unknown-commands)
- [razercfg Project](https://bues.ch/h/razercfg)
- [razer_test (z3ntu)](https://github.com/z3ntu/razer_test)
- [razer-laptop-control](https://github.com/rnd-ash/razer-laptop-control)
- [librazerblade](https://github.com/Meetem/librazerblade)
