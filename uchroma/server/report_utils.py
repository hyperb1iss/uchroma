#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Utilities for building Razer HID reports.
"""

import struct
from enum import Enum

import numpy as np

from uchroma.colorlib import Color
from uchroma.server import hid


def put_arg(report: hid.RazerReport, arg, packing: str | None = None) -> None:
    """Put a Python argument into a Rust RazerReport.

    Handles type conversion for Color, Enum, numpy arrays, bytes, and ints.
    """
    if packing is not None:
        data = struct.pack(packing, arg)
        report.put_bytes(data)
    elif isinstance(arg, Color):
        rgb = arg.intTuple[:3]  # RGB only, no alpha
        report.put_rgb(rgb[0], rgb[1], rgb[2])
    elif isinstance(arg, Enum):
        if hasattr(arg, "opcode"):
            val = arg.opcode
        else:
            val = arg.value
        if isinstance(val, int):
            report.put_byte(val)
        else:
            report.put_bytes(bytes(val) if not isinstance(val, bytes) else val)
    elif isinstance(arg, np.ndarray):
        report.put_bytes(bytes(arg.flatten().astype(np.uint8)))
    elif isinstance(arg, (bytearray, bytes)):
        report.put_bytes(bytes(arg))
    elif isinstance(arg, int):
        report.put_byte(arg)
    else:
        # Try to pack as single byte
        report.put_byte(int(arg))
