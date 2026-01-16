# uchroma test configuration and shared fixtures
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

from uchroma.color import Color

if TYPE_CHECKING:
    from collections.abc import Generator


# ─────────────────────────────────────────────────────────────────────────────
# Async fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Color fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def red_color():
    """Pure red color."""
    return Color.NewFromRgb(1.0, 0.0, 0.0)


@pytest.fixture
def green_color():
    """Pure green color."""
    return Color.NewFromRgb(0.0, 1.0, 0.0)


@pytest.fixture
def blue_color():
    """Pure blue color."""
    return Color.NewFromRgb(0.0, 0.0, 1.0)


@pytest.fixture
def white_color():
    """Pure white color."""
    return Color.NewFromRgb(1.0, 1.0, 1.0)


@pytest.fixture
def black_color():
    """Pure black color."""
    return Color.NewFromRgb(0.0, 0.0, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Image/Array fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def rgba_zeros() -> np.ndarray:
    """4x4 RGBA image filled with zeros."""
    return np.zeros((4, 4, 4), dtype=np.float64)


@pytest.fixture
def rgba_ones() -> np.ndarray:
    """4x4 RGBA image filled with ones."""
    return np.ones((4, 4, 4), dtype=np.float64)


@pytest.fixture
def rgba_half() -> np.ndarray:
    """4x4 RGBA image filled with 0.5."""
    return np.full((4, 4, 4), 0.5, dtype=np.float64)


@pytest.fixture
def rgb_red() -> np.ndarray:
    """4x4 RGBA image of pure red."""
    img = np.zeros((4, 4, 4), dtype=np.float64)
    img[:, :, 0] = 1.0  # Red channel
    img[:, :, 3] = 1.0  # Alpha channel
    return img


@pytest.fixture
def rgb_green() -> np.ndarray:
    """4x4 RGBA image of pure green."""
    img = np.zeros((4, 4, 4), dtype=np.float64)
    img[:, :, 1] = 1.0  # Green channel
    img[:, :, 3] = 1.0  # Alpha channel
    return img


# ─────────────────────────────────────────────────────────────────────────────
# Mock HID device fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_hid_device():
    """Mock HID device for protocol testing."""
    device = MagicMock()
    device.send_feature_report = MagicMock(return_value=90)
    device.get_feature_report = MagicMock(return_value=bytes(90))
    device.write = MagicMock(return_value=90)
    device.read = MagicMock(return_value=bytes(90))
    device.close = MagicMock()
    device.nonblocking = False
    return device


@pytest.fixture
def mock_device_info():
    """Mock HID device info."""
    return {
        "path": b"/dev/hidraw0",
        "vendor_id": 0x1532,
        "product_id": 0x0227,
        "serial_number": "XX0000000001",
        "release_number": 0x0200,
        "manufacturer_string": "Razer",
        "product_string": "Razer BlackWidow Chroma",
        "usage_page": 0x0001,
        "usage": 0x0006,
        "interface_number": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mock hardware fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_hardware():
    """Mock Hardware object for device testing."""
    hw = MagicMock()
    hw.name = "Test Device"
    hw.type = "keyboard"
    hw.vendor_id = 0x1532
    hw.product_id = 0x0227
    hw.width = 22
    hw.height = 6
    hw.supported_fx = ["static", "wave", "spectrum"]
    hw.supported_leds = ["backlight", "logo"]
    hw.quirks = 0
    hw.has_matrix = True
    hw.has_quirk = MagicMock(return_value=False)
    return hw


@pytest.fixture
def mock_driver(mock_hardware, mock_hid_device):
    """Mock driver (device) for command testing."""
    driver = MagicMock()
    driver.hardware = mock_hardware
    driver.hid = mock_hid_device
    driver.name = "Test Device"
    driver.device_type = "keyboard"
    driver.width = 22
    driver.height = 6
    driver.last_cmd_time = 0.0
    driver.logger = MagicMock()
    driver.device_open = MagicMock()
    driver.has_quirk = MagicMock(return_value=False)
    return driver


# ─────────────────────────────────────────────────────────────────────────────
# Report fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_report_bytes() -> bytes:
    """Sample 90-byte HID report."""
    data = bytearray(90)
    data[0] = 0x00  # Status
    data[1] = 0xFF  # Transaction ID
    data[2] = 0x00  # Remaining packets
    data[3] = 0x00  # Protocol type
    data[4] = 0x00  # Reserved
    data[5] = 0x03  # Data size
    data[6] = 0x03  # Command class
    data[7] = 0x00  # Command ID
    # Data at 8-87
    # CRC at 88
    # Reserved at 89
    return bytes(data)


# ─────────────────────────────────────────────────────────────────────────────
# Pytest configuration
# ─────────────────────────────────────────────────────────────────────────────


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "hardware: marks tests requiring hardware")
