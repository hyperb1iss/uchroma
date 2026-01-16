# Installation

## Requirements

- **Linux** with udev and systemd
- **Python 3.10+**
- Razer Chroma peripheral (keyboards, mice, mousepads, headsets, keypads, laptops)

## Linux Installation

OS packages are the recommended way to install UChroma. They include udev rules, systemd service
files, and all dependencies.

### Arch Linux (AUR)

```bash
# Using yay
yay -S uchroma

# Using paru
paru -S uchroma
```

### Ubuntu / Debian

```bash
# Add the PPA
sudo add-apt-repository ppa:hyperbliss/uchroma
sudo apt update

# Install
sudo apt install uchroma
```

### Fedora

```bash
# Enable COPR repository
sudo dnf copr enable hyperbliss/uchroma

# Install
sudo dnf install uchroma
```

## Post-Install Setup

### Add User to plugdev Group

Your user needs access to USB HID devices:

```bash
sudo usermod -aG plugdev $USER
```

**Log out and back in** for the group change to take effect.

### Enable the Daemon

UChroma runs as a user service:

```bash
systemctl --user enable --now uchromad
```

### Verify Installation

Check that your devices are detected:

```bash
uchroma devices
```

Expected output:

```
[0]: Razer BlackWidow V3 (PM2142XXXXXX / v1.0)
```

If you see your device, you're ready. Proceed to the [Quick Start](quick-start.md).

### Troubleshooting

**Device not detected?**

1. Ensure you logged out and back in after adding yourself to `plugdev`
2. Try unplugging and replugging your device
3. Check the daemon status: `systemctl --user status uchromad`
4. Check logs: `journalctl --user -u uchromad -f`

## Development Setup

::: info For Contributors Only This section is for developers who want to work on UChroma itself.
End users should use the OS packages above. :::

### Clone and Install

```bash
git clone https://github.com/hyperbliss/uchroma.git
cd uchroma

# Install dependencies (including GTK frontend)
uv sync --extra gtk
```

### Run from Source

```bash
# Run the daemon
uv run uchromad

# Run the CLI
uv run uchroma devices

# Run the GTK frontend
uv run python -m uchroma.gtk
```

### Rebuild Cython Modules

After modifying `.pyx` files, rebuild the Cython extensions:

```bash
make rebuild
```

### Useful Make Targets

```bash
make              # Show all commands
make sync         # Install dependencies
make rebuild      # Rebuild Cython extensions
make server       # Run daemon
make gtk          # Run GTK frontend
make check        # Lint + format + typecheck
```
