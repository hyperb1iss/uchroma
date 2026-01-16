# Power Management

System control features for Razer laptops and battery status for wireless devices.

## power

Control power modes, fan speeds, and CPU/GPU boost levels on Razer laptops.

### Synopsis

```
uchroma power [command] [options]
uchroma fan [command] [options]
uchroma boost [command] [options]
```

### Commands

| Command            | Description                                   |
| ------------------ | --------------------------------------------- |
| `status`           | Show current power/fan/boost status (default) |
| `mode [MODE]`      | Get or set power mode                         |
| `fan auto`         | Set fans to automatic control                 |
| `fan manual <RPM>` | Set manual fan speed                          |
| `boost`            | Get or set CPU/GPU boost levels               |

---

## Status Display

Show current system control status.

```bash
$ uchroma power status

 System Control Status:

power-mode                     Power profile management
───────────────────────────────────────────────────────────
current                        Balanced
available                      balanced, gaming, creator, custom

fan                            Cooling fan control
───────────────────────────────────────────────────────────
mode                           Auto
rpm                            ████████░░░░░░░░░░░░ 2400 RPM
range                          0 - 5000 RPM

boost                          CPU/GPU performance boost
───────────────────────────────────────────────────────────
cpu                            Medium
gpu                            Medium
available                      low, medium, high, boost
```

---

## Power Modes

### Query Current Mode

```bash
$ uchroma power mode
Current power mode: Balanced
Available modes: balanced, gaming, creator, custom
```

### Set Power Mode

```bash
$ uchroma power mode gaming
Power mode: Gaming

$ uchroma power mode balanced
Power mode: Balanced
```

### Available Modes

| Mode       | Description                                   |
| ---------- | --------------------------------------------- |
| `balanced` | Default balanced performance and battery life |
| `gaming`   | Maximum performance for gaming                |
| `creator`  | Optimized for creative workloads              |
| `custom`   | User-defined settings                         |

---

## Fan Control

### Automatic Mode

Let the system control fan speeds automatically.

```bash
$ uchroma power fan auto
Fans set to automatic control
```

### Manual Mode

Set a specific fan RPM.

```bash
# Set both fans to 3000 RPM
$ uchroma power fan manual 3000
Fan RPM: 3000

# Set different speeds for dual-fan systems
$ uchroma power fan manual 3000 --fan2 3500
Fan RPM: 3000 / 3500
```

### Options

| Option       | Description                                        |
| ------------ | -------------------------------------------------- |
| `--fan2 RPM` | Set second fan to different RPM (dual-fan laptops) |

### RPM Limits

Fan RPM must be within the device's supported range. Check with `uchroma power status` to see the
valid range (typically 0-5000 RPM).

```bash
$ uchroma power fan manual 6000
Error: RPM must be 0-5000, got 6000
```

---

## Boost Control

Control CPU and GPU performance boost levels.

### Query Current Boost

```bash
$ uchroma power boost
CPU boost: Medium
GPU boost: Medium
Available modes: low, medium, high, boost
```

### Set Boost Levels

```bash
# Set CPU boost
$ uchroma power boost --cpu high
CPU boost: High

# Set GPU boost
$ uchroma power boost --gpu medium
GPU boost: Medium

# Set both
$ uchroma power boost --cpu boost --gpu high
CPU boost: Boost
GPU boost: High
```

### Options

| Option       | Description         |
| ------------ | ------------------- |
| `--cpu MODE` | Set CPU boost level |
| `--gpu MODE` | Set GPU boost level |

### Boost Modes

| Mode     | Description                              |
| -------- | ---------------------------------------- |
| `low`    | Minimal boost, quieter operation         |
| `medium` | Balanced boost                           |
| `high`   | Aggressive boost, may increase fan noise |
| `boost`  | Maximum boost (CPU only on some models)  |

---

## battery

Show battery status for wireless devices.

### Synopsis

```
uchroma battery [options]
uchroma bat [options]
uchroma wireless [options]
```

### Options

| Option    | Short | Description                          |
| --------- | ----- | ------------------------------------ |
| `--all`   | `-a`  | Show all wireless devices            |
| `--quiet` | `-q`  | Only show percentage (for scripting) |

### Examples

**Single device:**

```bash
$ uchroma battery

 Razer DeathAdder V3 Pro

  battery      85% (discharging)
               ████████████████░░░░
```

**All wireless devices:**

```bash
$ uchroma battery --all

 Wireless Device Status:

  Razer DeathAdder V3 Pro    85%
  Razer BlackWidow V3 Pro    62% (charging)
```

**Script-friendly:**

```bash
$ uchroma battery --quiet
85%
```

**Wired device:**

```bash
$ uchroma battery
Device is not wireless
```

### Battery Indicator

The visual battery bar changes color based on level:

- **Green** (>50%): Healthy charge
- **Yellow** (20-50%): Moderate
- **Red** (<20%): Low battery warning

Charging status is indicated with a lightning bolt icon.

---

## Scripting Examples

### Low Battery Warning

```bash
#!/bin/bash
# Warn if any device is below 20%

for device in $(uchroma list --quiet); do
    level=$(uchroma -d "$device" battery --quiet 2>/dev/null)
    if [ -n "$level" ]; then
        level_num=${level%\%}
        if [ "$level_num" -lt 20 ]; then
            notify-send "Low Battery" "$device: $level"
        fi
    fi
done
```

### Gaming Mode Script

```bash
#!/bin/bash
# Set up laptop for gaming

uchroma power mode gaming
uchroma power boost --cpu high --gpu high
uchroma brightness 100
uchroma profile load gaming

echo "Gaming mode enabled"
```

### Quiet Mode Script

```bash
#!/bin/bash
# Minimize fan noise for quiet operation

uchroma power mode balanced
uchroma power boost --cpu low --gpu low
uchroma power fan auto
uchroma brightness 30

echo "Quiet mode enabled"
```

---

## Requirements

- **Power commands**: Require a Razer laptop with system control support
- **Battery command**: Requires a wireless Razer peripheral
- **uchromad**: Must be running to communicate with devices

Use `uchroma dump device` to check if your device supports these features:

```bash
$ uchroma dump device | grep -E "(wireless|system_control)"
    wireless: yes
    system_control: yes
```

---

## Related Commands

- [`watch`](advanced.md#watch) - Live monitoring of fan speeds and battery
- [`profile`](profiles.md) - Save power settings in profiles
