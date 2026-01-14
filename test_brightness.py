#!/usr/bin/env python3
"""Test extended brightness commands for Blade 2021."""

import sys
sys.path.insert(0, '.')

import logging
from uchroma.log import LOG_PROTOCOL_TRACE

# Enable protocol trace logging
logging.basicConfig(level=LOG_PROTOCOL_TRACE)

from uchroma.server.device_manager import UChromaDeviceManager

print("Discovering devices...")
dm = UChromaDeviceManager()

print(f"\nFound {len(dm.devices)} device(s):")
for key, device in dm.devices.items():
    print(f"  [{key}] {device.name}")
    print(f"      Type: {device.hardware.type}")
    print(f"      Has EXTENDED_FX_CMDS: {device._use_extended if hasattr(device, '_use_extended') else 'N/A'}")

    print("\n  Testing brightness get...")
    try:
        brightness = device.brightness
        print(f"      Current brightness: {brightness}")
    except Exception as e:
        print(f"      ERROR getting brightness: {e}")

    print("\n  Testing brightness set (50%)...")
    try:
        device.brightness = 50.0
        print(f"      Set brightness to 50%")

        # Read it back
        brightness = device.brightness
        print(f"      Readback brightness: {brightness}")
    except Exception as e:
        print(f"      ERROR setting brightness: {e}")

print("\nDone!")
