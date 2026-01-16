#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.protocol module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from uchroma.server.hardware import Quirks
from uchroma.server.protocol import (
    ProtocolConfig,
    ProtocolVersion,
    get_protocol_from_quirks,
    get_transaction_id,
    uses_extended_fx,
)

# ─────────────────────────────────────────────────────────────────────────────
# ProtocolVersion Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProtocolVersion:
    """Tests for ProtocolVersion enum."""

    def test_legacy_value(self):
        """LEGACY protocol has correct value."""
        assert ProtocolVersion.LEGACY.value == "legacy"

    def test_extended_value(self):
        """EXTENDED protocol has correct value."""
        assert ProtocolVersion.EXTENDED.value == "extended"

    def test_modern_value(self):
        """MODERN protocol has correct value."""
        assert ProtocolVersion.MODERN.value == "modern"

    def test_wireless_kb_value(self):
        """WIRELESS_KB protocol has correct value."""
        assert ProtocolVersion.WIRELESS_KB.value == "wireless_kb"

    def test_special_value(self):
        """SPECIAL protocol has correct value."""
        assert ProtocolVersion.SPECIAL.value == "special"

    def test_headset_v1_value(self):
        """HEADSET_V1 protocol has correct value."""
        assert ProtocolVersion.HEADSET_V1.value == "headset_v1"

    def test_headset_v2_value(self):
        """HEADSET_V2 protocol has correct value."""
        assert ProtocolVersion.HEADSET_V2.value == "headset_v2"


# ─────────────────────────────────────────────────────────────────────────────
# ProtocolConfig Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProtocolConfig:
    """Tests for ProtocolConfig dataclass."""

    def test_legacy_config(self):
        """LEGACY config has correct values."""
        config = ProtocolConfig.LEGACY
        assert config.version == ProtocolVersion.LEGACY
        assert config.transaction_id == 0xFF
        assert config.uses_extended_fx is False

    def test_extended_config(self):
        """EXTENDED config has correct values."""
        config = ProtocolConfig.EXTENDED
        assert config.version == ProtocolVersion.EXTENDED
        assert config.transaction_id == 0x3F
        assert config.uses_extended_fx is True

    def test_modern_config(self):
        """MODERN config has correct values."""
        config = ProtocolConfig.MODERN
        assert config.version == ProtocolVersion.MODERN
        assert config.transaction_id == 0x1F
        assert config.uses_extended_fx is True

    def test_wireless_kb_config(self):
        """WIRELESS_KB config has correct values."""
        config = ProtocolConfig.WIRELESS_KB
        assert config.version == ProtocolVersion.WIRELESS_KB
        assert config.transaction_id == 0x9F
        assert config.uses_extended_fx is True

    def test_special_08_config(self):
        """SPECIAL_08 config has correct values."""
        config = ProtocolConfig.SPECIAL_08
        assert config.version == ProtocolVersion.SPECIAL
        assert config.transaction_id == 0x08
        assert config.uses_extended_fx is True

    def test_default_inter_command_delay(self):
        """Default inter_command_delay is 7ms."""
        config = ProtocolConfig.LEGACY
        assert config.inter_command_delay == 0.007

    def test_config_is_frozen(self):
        """ProtocolConfig is immutable."""
        config = ProtocolConfig.LEGACY
        with pytest.raises(AttributeError):
            config.transaction_id = 0x00


# ─────────────────────────────────────────────────────────────────────────────
# get_protocol_from_quirks Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetProtocolFromQuirks:
    """Tests for get_protocol_from_quirks function."""

    @pytest.fixture
    def mock_hardware(self):
        """Create a mock Hardware object."""
        hw = MagicMock()
        hw.has_quirk = MagicMock(return_value=False)
        return hw

    def test_no_quirks_returns_legacy(self, mock_hardware):
        """Device with no quirks uses LEGACY protocol."""
        protocol = get_protocol_from_quirks(mock_hardware)
        assert protocol == ProtocolConfig.LEGACY

    def test_transaction_code_3f_returns_extended(self, mock_hardware):
        """Device with TRANSACTION_CODE_3F uses EXTENDED protocol."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_3F
        protocol = get_protocol_from_quirks(mock_hardware)
        assert protocol == ProtocolConfig.EXTENDED

    def test_transaction_code_1f_returns_modern(self, mock_hardware):
        """Device with TRANSACTION_CODE_1F uses MODERN protocol."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_1F
        protocol = get_protocol_from_quirks(mock_hardware)
        assert protocol == ProtocolConfig.MODERN

    def test_transaction_code_9f_returns_wireless_kb(self, mock_hardware):
        """Device with TRANSACTION_CODE_9F uses WIRELESS_KB protocol."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_9F
        protocol = get_protocol_from_quirks(mock_hardware)
        assert protocol == ProtocolConfig.WIRELESS_KB

    def test_transaction_code_08_returns_special(self, mock_hardware):
        """Device with TRANSACTION_CODE_08 uses SPECIAL_08 protocol."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_08
        protocol = get_protocol_from_quirks(mock_hardware)
        assert protocol == ProtocolConfig.SPECIAL_08

    def test_9f_takes_precedence_over_1f(self, mock_hardware):
        """TRANSACTION_CODE_9F takes precedence over TRANSACTION_CODE_1F."""
        mock_hardware.has_quirk = lambda q: q in (
            Quirks.TRANSACTION_CODE_9F,
            Quirks.TRANSACTION_CODE_1F,
        )
        protocol = get_protocol_from_quirks(mock_hardware)
        assert protocol == ProtocolConfig.WIRELESS_KB


# ─────────────────────────────────────────────────────────────────────────────
# get_transaction_id Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetTransactionId:
    """Tests for get_transaction_id function."""

    @pytest.fixture
    def mock_hardware(self):
        """Create a mock Hardware object."""
        hw = MagicMock()
        hw.has_quirk = MagicMock(return_value=False)
        return hw

    def test_legacy_returns_0xff(self, mock_hardware):
        """Legacy device returns 0xFF transaction ID."""
        tid = get_transaction_id(mock_hardware)
        assert tid == 0xFF

    def test_extended_returns_0x3f(self, mock_hardware):
        """Extended device returns 0x3F transaction ID."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_3F
        tid = get_transaction_id(mock_hardware)
        assert tid == 0x3F

    def test_modern_returns_0x1f(self, mock_hardware):
        """Modern device returns 0x1F transaction ID."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_1F
        tid = get_transaction_id(mock_hardware)
        assert tid == 0x1F

    def test_wireless_returns_0x9f(self, mock_hardware):
        """Wireless keyboard returns 0x9F transaction ID."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_9F
        tid = get_transaction_id(mock_hardware)
        assert tid == 0x9F


# ─────────────────────────────────────────────────────────────────────────────
# uses_extended_fx Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestUsesExtendedFx:
    """Tests for uses_extended_fx function."""

    @pytest.fixture
    def mock_hardware(self):
        """Create a mock Hardware object."""
        hw = MagicMock()
        hw.has_quirk = MagicMock(return_value=False)
        return hw

    def test_legacy_does_not_use_extended(self, mock_hardware):
        """Legacy device does not use extended FX."""
        assert uses_extended_fx(mock_hardware) is False

    def test_extended_uses_extended_fx(self, mock_hardware):
        """Extended protocol uses extended FX."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_3F
        assert uses_extended_fx(mock_hardware) is True

    def test_modern_uses_extended_fx(self, mock_hardware):
        """Modern protocol uses extended FX."""
        mock_hardware.has_quirk = lambda q: q == Quirks.TRANSACTION_CODE_1F
        assert uses_extended_fx(mock_hardware) is True

    def test_extended_fx_quirk_alone_uses_extended(self, mock_hardware):
        """EXTENDED_FX_CMDS quirk alone enables extended FX."""
        mock_hardware.has_quirk = lambda q: q == Quirks.EXTENDED_FX_CMDS
        assert uses_extended_fx(mock_hardware) is True
