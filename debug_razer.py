#!/usr/bin/env python3
"""Debug script to test Razer Blade brightness control."""

import logging
import sys
import hid

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Add uchroma to path
sys.path.insert(0, '/home/bliss/dev/uchroma')

from uchroma.log import Log, LOG_PROTOCOL_TRACE

# Enable protocol trace
Log.enable_color(True)
logger = Log.get('uchroma.test')
logger.setLevel(LOG_PROTOCOL_TRACE)

from uchroma.server.device_manager import UChromaDeviceManager

print("=" * 60)
print("Razer Blade Brightness Control Test")
print("=" * 60)

# List Razer devices
print("\n[1] Scanning for Razer HID devices...")
razer_devices = []
for d in hid.enumerate():
    if d['vendor_id'] == 0x1532:
        razer_devices.append(d)
        print(f"  Found: {d['product_string']} (0x{d['product_id']:04x}) interface {d['interface_number']}")

if not razer_devices:
    print("  No Razer devices found!")
    sys.exit(1)

print("\n[2] Initializing device manager...")
dm = UChromaDeviceManager()

print(f"\n[3] Found {len(dm.devices)} uchroma devices")
for key, dev in dm.devices.items():
    print(f"  - {dev.name} (key={key})")
    print(f"    Type: {dev.device_type}")
    print(f"    Quirks: {dev.hardware.quirks}")

    print(f"\n[4] Testing brightness on {dev.name}...")

    try:
        # Get current brightness
        print("    Getting current brightness...")
        current = dev.brightness
        print(f"    Current brightness: {current}%")

        # Try setting brightness
        print("    Setting brightness to 50%...")
        dev._set_brightness(50.0)

        # Read it back
        print("    Reading brightness back...")
        new_val = dev._get_brightness()
        print(f"    New brightness: {new_val}%")

        # Restore original
        print(f"    Restoring brightness to {current}%...")
        dev._set_brightness(current)

        print(f"\n[SUCCESS] Brightness control is working!")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
