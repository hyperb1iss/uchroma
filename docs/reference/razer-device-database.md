# Razer Device Database

Comprehensive list of Razer Chroma devices with USB Product IDs, capabilities, and protocol
requirements.

**Vendor ID**: `0x1532`

**Coverage audit**: Run `python3 scripts/audit_hardware_db.py` to compare this list to
`uchroma/server/data/*.yaml`.

---

## Keyboards

### BlackWidow Series

| Model                        | PID    | Transaction ID | Matrix | Quirks      |
| ---------------------------- | ------ | -------------- | ------ | ----------- |
| BlackWidow Ultimate 2012     | 0x010D | 0xFF           | 6×22   | —           |
| BlackWidow Ultimate 2013     | 0x010E | 0xFF           | 6×22   | —           |
| BlackWidow Ultimate 2016     | 0x0214 | 0xFF           | 6×22   | —           |
| BlackWidow Chroma            | 0x0203 | 0xFF           | 6×22   | —           |
| BlackWidow Chroma TE         | 0x0209 | 0xFF           | 6×22   | —           |
| BlackWidow Chroma V2         | 0x0221 | 0xFF           | 6×22   | —           |
| BlackWidow X Chroma          | 0x0216 | 0xFF           | 6×22   | —           |
| BlackWidow X Chroma TE       | 0x0217 | 0xFF           | 6×22   | —           |
| BlackWidow X Ultimate        | 0x0223 | 0xFF           | 6×22   | —           |
| BlackWidow Elite             | 0x0228 | 0xFF           | 6×22   | —           |
| BlackWidow V3                | 0x024E | 0xFF           | 6×22   | —           |
| BlackWidow V3 Mini           | 0x0258 | 0x1F           | 5×15   | EXTENDED_FX |
| BlackWidow V3 TKL            | 0x0A24 | 0xFF           | 6×18   | —           |
| BlackWidow V3 Pro (Wired)    | 0x025A | 0x1F           | 6×22   | WIRELESS    |
| BlackWidow V3 Pro (Wireless) | 0x025C | 0x9F           | 6×22   | WIRELESS    |
| BlackWidow V4                | 0x0287 | 0x1F           | 6×22   | EXTENDED_FX |
| BlackWidow V4 X              | 0x028D | 0x1F           | 6×22   | EXTENDED_FX |
| BlackWidow V4 75%            | 0x028E | 0x1F           | 6×16   | EXTENDED_FX |
| BlackWidow V4 Mini           | 0x0283 | 0x1F           | 5×15   | EXTENDED_FX |

### Huntsman Series

| Model                | PID    | Transaction ID | Matrix | Quirks              |
| -------------------- | ------ | -------------- | ------ | ------------------- |
| Huntsman             | 0x0227 | 0xFF           | 6×22   | —                   |
| Huntsman Elite       | 0x0226 | 0xFF           | 6×22   | —                   |
| Huntsman TE          | 0x022C | 0xFF           | 6×18   | —                   |
| Huntsman Mini        | 0x0257 | 0x1F           | 5×15   | EXTENDED_FX         |
| Huntsman Mini Analog | 0x0266 | 0x1F           | 5×15   | EXTENDED_FX         |
| Huntsman V2          | 0x026B | 0x1F           | 6×22   | EXTENDED_FX         |
| Huntsman V2 TKL      | 0x026C | 0x1F           | 6×18   | EXTENDED_FX         |
| Huntsman V2 Analog   | 0x0266 | 0x1F           | 6×22   | EXTENDED_FX, ANALOG |
| Huntsman V3 Pro      | 0x02A6 | 0x1F           | 6×22   | EXTENDED_FX         |
| Huntsman V3 Pro TKL  | 0x02B0 | 0x1F           | 6×18   | EXTENDED_FX         |
| Huntsman V3 Pro Mini | 0x02B1 | 0x1F           | 5×15   | EXTENDED_FX         |

### DeathStalker Series

| Model                          | PID    | Transaction ID | Matrix | Quirks      |
| ------------------------------ | ------ | -------------- | ------ | ----------- |
| DeathStalker Chroma            | 0x0204 | 0xFF           | 1×12   | —           |
| DeathStalker V2                | 0x0295 | 0x1F           | 6×22   | EXTENDED_FX |
| DeathStalker V2 Pro (Wired)    | 0x0296 | 0x1F           | 6×22   | WIRELESS    |
| DeathStalker V2 Pro (Wireless) | 0x0298 | 0x9F           | 6×22   | WIRELESS    |
| DeathStalker V2 Pro TKL        | 0x029C | 0x1F           | 6×18   | WIRELESS    |

### Other Keyboards

| Model         | PID    | Transaction ID | Matrix | Quirks      |
| ------------- | ------ | -------------- | ------ | ----------- |
| Ornata Chroma | 0x021E | 0xFF           | 6×22   | —           |
| Ornata V2     | 0x024A | 0xFF           | 6×22   | —           |
| Ornata V3     | 0x0292 | 0x1F           | 6×22   | EXTENDED_FX |
| Ornata V3 TKL | 0x02B3 | 0x1F           | 6×18   | EXTENDED_FX |
| Cynosa Chroma | 0x022A | 0xFF           | 6×22   | —           |
| Cynosa V2     | 0x025E | 0xFF           | 6×22   | —           |
| Cynosa Lite   | 0x023F | 0xFF           | 1×1    | SINGLE_LED  |
| Tartarus V2   | 0x022B | 0xFF           | 4×6    | KEYPAD      |
| Tartarus Pro  | 0x0244 | 0x3F           | 4×6    | KEYPAD      |

---

## Mice

### DeathAdder Series

| Model                        | PID    | Transaction ID | LEDs | Quirks           |
| ---------------------------- | ------ | -------------- | ---- | ---------------- |
| DeathAdder Chroma            | 0x0043 | 0xFF           | 2    | —                |
| DeathAdder Elite             | 0x005C | 0x3F           | 2    | EXTENDED_FX      |
| DeathAdder Essential         | 0x006E | 0xFF           | 1    | SINGLE_LED       |
| DeathAdder Essential (White) | 0x0071 | 0xFF           | 1    | SINGLE_LED       |
| DeathAdder V2                | 0x0084 | 0x3F           | 2    | EXTENDED_FX      |
| DeathAdder V2 Mini           | 0x008C | 0x3F           | 1    | EXTENDED_FX      |
| DeathAdder V2 Pro (Wired)    | 0x007C | 0x3F           | 2    | WIRELESS         |
| DeathAdder V2 Pro (Wireless) | 0x007D | 0x3F           | 2    | WIRELESS         |
| DeathAdder V2 X HyperSpeed   | 0x009C | 0x1F           | 0    | WIRELESS, NO_LED |
| DeathAdder V3                | 0x00B2 | 0x1F           | 0    | NO_LED           |
| DeathAdder V3 Pro (Wired)    | 0x00B6 | 0x1F           | 0    | WIRELESS, NO_LED |
| DeathAdder V3 Pro (Wireless) | 0x00B7 | 0x1F           | 0    | WIRELESS, NO_LED |
| DeathAdder V3 HyperSpeed     | 0x00C3 | 0x1F           | 0    | WIRELESS, NO_LED |
| DeathAdder V4 Pro            | 0x00CE | 0x1F           | 0    | WIRELESS, NO_LED |

### Viper Series

| Model                     | PID    | Transaction ID | LEDs | Quirks           |
| ------------------------- | ------ | -------------- | ---- | ---------------- |
| Viper                     | 0x0078 | 0x3F           | 1    | EXTENDED_FX      |
| Viper Mini                | 0x008A | 0x3F           | 1    | EXTENDED_FX      |
| Viper Ultimate (Wired)    | 0x007A | 0x3F           | 2    | WIRELESS         |
| Viper Ultimate (Wireless) | 0x007B | 0x3F           | 2    | WIRELESS         |
| Viper V2 Pro (Wired)      | 0x00A6 | 0x1F           | 0    | WIRELESS, NO_LED |
| Viper V2 Pro (Wireless)   | 0x00A7 | 0x1F           | 0    | WIRELESS, NO_LED |
| Viper V3 Pro (Wired)      | 0x00C0 | 0x1F           | 0    | WIRELESS, NO_LED |
| Viper V3 Pro (Wireless)   | 0x00C1 | 0x1F           | 0    | WIRELESS, NO_LED |
| Viper V3 HyperSpeed       | 0x00C2 | 0x1F           | 0    | WIRELESS, NO_LED |

### Basilisk Series

| Model                        | PID    | Transaction ID | LEDs | Quirks           |
| ---------------------------- | ------ | -------------- | ---- | ---------------- |
| Basilisk                     | 0x0064 | 0x3F           | 2    | EXTENDED_FX      |
| Basilisk Essential           | 0x0065 | 0xFF           | 1    | —                |
| Basilisk V2                  | 0x0085 | 0x3F           | 2    | EXTENDED_FX      |
| Basilisk V3                  | 0x0099 | 0x1F           | 11   | EXTENDED_FX      |
| Basilisk V3 Pro (Wired)      | 0x00AA | 0x1F           | 11   | WIRELESS         |
| Basilisk V3 Pro (Wireless)   | 0x00AB | 0x1F           | 11   | WIRELESS         |
| Basilisk V3 X HyperSpeed     | 0x00B9 | 0x1F           | 0    | WIRELESS, NO_LED |
| Basilisk Ultimate (Wired)    | 0x0086 | 0x1F           | 14   | WIRELESS         |
| Basilisk Ultimate (Wireless) | 0x0088 | 0x1F           | 14   | WIRELESS         |
| Basilisk X HyperSpeed        | 0x0083 | 0x1F           | 0    | WIRELESS, NO_LED |

### Naga Series

| Model                  | PID    | Transaction ID | LEDs | Quirks           |
| ---------------------- | ------ | -------------- | ---- | ---------------- |
| Naga Epic Chroma       | 0x003E | 0xFF           | 3    | —                |
| Naga Hex V2            | 0x0050 | 0x3F           | 2    | EXTENDED_FX      |
| Naga Trinity           | 0x0067 | 0x3F           | 3    | EXTENDED_FX      |
| Naga Left-Handed       | 0x008D | 0x3F           | 2    | EXTENDED_FX      |
| Naga Pro (Wired)       | 0x008F | 0x3F           | 3    | WIRELESS         |
| Naga Pro (Wireless)    | 0x0090 | 0x3F           | 3    | WIRELESS         |
| Naga V2 HyperSpeed     | 0x00B4 | 0x1F           | 0    | WIRELESS, NO_LED |
| Naga V2 Pro (Wired)    | 0x00C4 | 0x1F           | 2    | WIRELESS         |
| Naga V2 Pro (Wireless) | 0x00C5 | 0x1F           | 2    | WIRELESS         |
| Naga X                 | 0x0096 | 0x08           | 2    | SPECIAL_TID      |

### Other Mice

| Model                     | PID    | Transaction ID | LEDs | Quirks      |
| ------------------------- | ------ | -------------- | ---- | ----------- |
| Mamba Chroma              | 0x0044 | 0xFF           | 2    | —           |
| Mamba Elite               | 0x006C | 0x3F           | 20   | EXTENDED_FX |
| Mamba Wireless (Wired)    | 0x0072 | 0x3F           | 2    | WIRELESS    |
| Mamba Wireless (Wireless) | 0x0073 | 0x3F           | 2    | WIRELESS    |
| Cobra                     | 0x00AF | 0x1F           | 1    | EXTENDED_FX |
| Cobra Pro (Wired)         | 0x00B0 | 0x1F           | 10   | WIRELESS    |
| Cobra Pro (Wireless)      | 0x00B1 | 0x1F           | 10   | WIRELESS    |
| Orochi V2                 | 0x0094 | 0x1F           | 1    | WIRELESS    |
| Atheris                   | 0x0062 | 0x3F           | 2    | WIRELESS    |
| Pro Click                 | 0x0089 | 0x3F           | 0    | NO_LED      |
| Pro Click V2              | 0x00BD | 0x1F           | 0    | NO_LED      |

---

## Laptops

### Razer Blade Series

| Model                | PID    | Transaction ID | Matrix | Quirks          |
| -------------------- | ------ | -------------- | ------ | --------------- |
| Blade (2016)         | 0x020F | 0xFF           | 6×16   | —               |
| Blade Stealth (2016) | 0x0220 | 0xFF           | 6×16   | —               |
| Blade Stealth (2017) | 0x022D | 0xFF           | 6×16   | —               |
| Blade Stealth (2019) | 0x0239 | 0x1F           | 6×16   | —               |
| Blade Stealth (2020) | 0x0252 | 0x1F           | 6×16   | CUSTOM_FRAME_80 |
| Blade Pro (2017)     | 0x0225 | 0xFF           | 6×25   | —               |
| Blade Pro (2019)     | 0x0233 | 0x1F           | 6×16   | —               |
| Blade 14 (2021)      | 0x026D | 0x1F           | 6×16   | —               |
| Blade 14 (2022)      | 0x027A | 0x1F           | 6×16   | —               |
| Blade 14 (2023)      | 0x029D | 0x1F           | 6×16   | —               |
| Blade 14 (2024)      | 0x02A4 | 0x1F           | 6×16   | —               |
| Blade 14 (2025)      | 0x02C5 | 0x1F           | 6×16   | —               |
| Blade 15 (2018)      | 0x0234 | 0x1F           | 6×16   | —               |
| Blade 15 (2019)      | 0x0240 | 0x1F           | 6×16   | —               |
| Blade 15 (2020)      | 0x0253 | 0x1F           | 6×16   | CUSTOM_FRAME_80 |
| Blade 15 (2021)      | 0x026F | 0x1F           | 6×16   | CUSTOM_FRAME_80 |
| Blade 15 (2022)      | 0x027B | 0x1F           | 6×16   | —               |
| Blade 16 (2023)      | 0x029E | 0x1F           | 6×16   | —               |
| Blade 16 (2024)      | 0x02B4 | 0x1F           | 6×16   | —               |
| Blade 16 (2025)      | 0x02C6 | 0x1F           | 6×16   | —               |
| Blade 17 (2021)      | 0x0270 | 0x1F           | 6×16   | —               |
| Blade 17 (2022)      | 0x027C | 0x1F           | 6×16   | —               |
| Blade 18 (2023)      | 0x029F | 0x1F           | 6×16   | —               |
| Blade 18 (2024)      | 0x02B5 | 0x1F           | 6×16   | —               |
| Blade 18 (2025)      | 0x02C7 | 0x1F           | 6×16   | —               |

---

## Mousepads

| Model              | PID    | Transaction ID | Matrix | Quirks      |
| ------------------ | ------ | -------------- | ------ | ----------- |
| Firefly            | 0x0C00 | 0x3F           | 1×15   | EXTENDED_FX |
| Firefly V2         | 0x0C04 | 0x3F           | 1×15   | EXTENDED_FX |
| Firefly V2 Pro     | 0x0C08 | 0x1F           | 1×15   | EXTENDED_FX |
| Firefly Hyperflux  | 0x0068 | 0x3F           | 1×15   | EXTENDED_FX |
| Goliathus Chroma   | 0x0C01 | 0x3F           | 1×15   | EXTENDED_FX |
| Goliathus Extended | 0x0C02 | 0x3F           | 1×15   | EXTENDED_FX |
| Goliathus 3XL      | 0x0C06 | 0x3F           | 1×15   | EXTENDED_FX |
| Strider Chroma     | 0x0C05 | 0x3F           | 1×15   | EXTENDED_FX |

---

## Headsets

| Model                    | PID      | Protocol   | LEDs | Notes                             |
| ------------------------ | -------- | ---------- | ---- | --------------------------------- |
| Kraken 7.1 (Rainie)      | 0x0504   | Headset v1 | 2    | Static, spectrum, 1-color breathe |
| Kraken 7.1 V2 (Kylie)    | 0x0510   | Headset v2 | 2    | + 3-color breathe                 |
| Kraken Ultimate          | 0x0527   | Headset v2 | 2    | Same as V2                        |
| Kraken Kitty Edition     | 0x0F19   | Accessory  | 4    | Ears have separate zones          |
| Kraken Kitty V2          | 0x0560   | Accessory  | 4    | —                                 |
| Kraken V4                | 0x0517   | Unknown    | —    | TBD                               |
| Kraken V4 Pro            | 0x0516   | Unknown    | —    | OLED hub                          |
| Nari Ultimate            | 0x051A   | Unknown    | 2    | Haptic feedback                   |
| Nari                     | 0x051C/D | Unknown    | 2    | Wireless + wired PIDs             |
| Nari Essential           | 0x051E/F | Unknown    | 2    | Budget model                      |
| BlackShark V2 Pro (2020) | 0x0528   | Unknown    | —    | Not supported                     |
| BlackShark V2 Pro (2023) | 0x0555   | Unknown    | —    | Not supported                     |
| Barracuda Pro            | 0x0557   | Unknown    | —    | ANC                               |

---

## Accessories

### Charging Docks

| Model             | PID    | Transaction ID | Quirks       |
| ----------------- | ------ | -------------- | ------------ |
| Mouse Dock        | 0x007E | 0x3F           | EXTENDED_FX  |
| Mouse Dock Chroma | 0x007C | 0x3F           | EXTENDED_FX  |
| Mouse Dock Pro    | 0x00A4 | 0x1F           | HYPERPOLLING |

### Stands & Stations

| Model                     | PID    | Transaction ID | Quirks      |
| ------------------------- | ------ | -------------- | ----------- |
| Base Station Chroma       | 0x0F08 | 0x3F           | EXTENDED_FX |
| Base Station V2 Chroma    | 0x0F20 | 0x1F           | EXTENDED_FX |
| Laptop Stand Chroma       | 0x0F0D | 0x1F           | EXTENDED_FX |
| Laptop Stand Chroma V2    | 0x0F2C | 0x1F           | EXTENDED_FX |
| Thunderbolt 4 Dock Chroma | 0x0F2D | 0x1F           | EXTENDED_FX |

### Controllers & Other

| Model                  | PID    | Transaction ID | Quirks         |
| ---------------------- | ------ | -------------- | -------------- |
| Chroma Mug Holder      | 0x0F07 | 0x3F           | Limited run    |
| Chroma HDK             | 0x0F09 | 0x3F           | ARGB headers   |
| ARGB Controller        | 0x0F0E | 0x3F           | 6 ARGB headers |
| Core X Chroma          | 0x0216 | 0xFF           | eGPU enclosure |
| Mouse Bungee V3 Chroma | 0x0F1D | 0x1F           | —              |
| Charging Pad Chroma    | 0x0F26 | 0x1F           | Qi charger     |

---

## Keypads

| Model            | PID    | Transaction ID | Matrix | Quirks |
| ---------------- | ------ | -------------- | ------ | ------ |
| Orbweaver Chroma | 0x0207 | 0xFF           | 4×5    | —      |
| Tartarus         | 0x0201 | 0xFF           | 4×5    | —      |
| Tartarus Chroma  | 0x0208 | 0xFF           | 4×5    | —      |
| Tartarus V2      | 0x022B | 0xFF           | 4×6    | —      |
| Tartarus Pro     | 0x0244 | 0x3F           | 4×6    | ANALOG |

---

## Speakers

| Model        | PID    | Transaction ID | LEDs | Notes              |
| ------------ | ------ | -------------- | ---- | ------------------ |
| Nommo Chroma | 0x0517 | 0x3F           | 2    | RGB only via USB   |
| Nommo Pro    | 0x0518 | 0x3F           | 2    | RGB only via USB   |
| Leviathan V2 | 0x0532 | Unknown        | —    | Different protocol |

---

## HyperPolling Dongles

| Model                        | PID    | Notes                   |
| ---------------------------- | ------ | ----------------------- |
| HyperPolling Wireless Dongle | 0x00B3 | Supports 8000Hz polling |

**Pairing Command**: Class `0x00`, ID `0x41` with mouse PID

- Viper V2 Pro: `0xA6`
- DeathAdder V3 Pro: `0xB7`

---

## Quirks Legend

| Quirk           | Description                                 |
| --------------- | ------------------------------------------- |
| EXTENDED_FX     | Uses class 0x0F for effects instead of 0x03 |
| WIRELESS        | Has battery/charging commands               |
| NO_LED          | No RGB lighting                             |
| SINGLE_LED      | Single LED zone only                        |
| CUSTOM_FRAME_80 | Uses transaction ID 0x80 for custom frames  |
| HYPERPOLLING    | Supports 4000/8000Hz polling rates          |
| ANALOG          | Analog key actuation support                |
| SPECIAL_TID     | Uses non-standard transaction ID            |

---

## Sources

- [OpenRazer Supported Devices](https://openrazer.github.io/)
- [USB ID Database](https://the-sz.com/products/usbid/index.php?v=0x1532)
- [Device Hunt](https://devicehunt.com/view/type/usb/vendor/1532)
- [OpenRazer Driver Source](https://github.com/openrazer/openrazer/tree/master/driver)
