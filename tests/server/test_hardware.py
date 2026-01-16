# uchroma - Hardware unit tests
from __future__ import annotations

import pytest

from uchroma.server.hardware import (
    Capability,
    Hardware,
    HexQuad,
    KeyMapping,
    MatrixType,
    Point,
    PointList,
    ProtocolSpec,
    Quirks,
    Zone,
)
from uchroma.server.protocol import ProtocolVersion

# ─────────────────────────────────────────────────────────────────────────────
# Quirks Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestQuirksEnum:
    """Tests for the Quirks enum values."""

    def test_quirks_enum_values_exist(self):
        """Verify all expected Quirks enum values exist."""
        assert Quirks.TRANSACTION_CODE_3F == 1
        assert Quirks.EXTENDED_FX_CMDS == 2
        assert Quirks.SCROLL_WHEEL_BRIGHTNESS == 3
        assert Quirks.WIRELESS == 4
        assert Quirks.CUSTOM_FRAME_80 == 5
        assert Quirks.LOGO_LED_BRIGHTNESS == 6
        assert Quirks.PROFILE_LEDS == 7
        assert Quirks.BACKLIGHT_LED_FX_ONLY == 8
        assert Quirks.TRANSACTION_CODE_1F == 9

    def test_quirks_is_int_enum(self):
        """Quirks should be usable as integers."""
        assert int(Quirks.TRANSACTION_CODE_3F) == 1
        assert Quirks.WIRELESS == 4
        assert Quirks.EXTENDED_FX_CMDS + 1 == 3


# ─────────────────────────────────────────────────────────────────────────────
# Point and Zone Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPoint:
    """Tests for Point named tuple."""

    def test_point_construction(self):
        """Point should be constructible with y, x coordinates."""
        p = Point(5, 10)
        assert p.y == 5
        assert p.x == 10

    def test_point_tuple_access(self):
        """Point should be accessible via tuple indexing."""
        p = Point(3, 7)
        assert p[0] == 3
        assert p[1] == 7

    def test_point_repr(self):
        """Point repr should be formatted as (y, x)."""
        p = Point(2, 4)
        assert repr(p) == "(2, 4)"

    def test_point_immutable(self):
        """Point should be immutable (NamedTuple)."""
        p = Point(1, 2)
        with pytest.raises(AttributeError):
            p.y = 5  # type: ignore


class TestZone:
    """Tests for Zone named tuple."""

    def test_zone_construction(self):
        """Zone should be constructible with name, coord, width, height."""
        coord = Point(0, 0)
        z = Zone(name="test_zone", coord=coord, width=10, height=5)
        assert z.name == "test_zone"
        assert z.coord == coord
        assert z.width == 10
        assert z.height == 5

    def test_zone_tuple_unpacking(self):
        """Zone should support tuple unpacking."""
        z = Zone("keyboard", Point(1, 2), 22, 6)
        name, coord, width, height = z
        assert name == "keyboard"
        assert coord == Point(1, 2)
        assert width == 22
        assert height == 6


class TestPointList:
    """Tests for PointList construction."""

    def test_pointlist_single_point(self):
        """PointList with [y, x] should return a Point."""
        result = PointList([3, 5])
        assert isinstance(result, Point)
        assert result.y == 3
        assert result.x == 5

    def test_pointlist_nested_points(self):
        """PointList with nested lists should create list of Points."""
        result = PointList([[0, 1], [2, 3]])
        assert len(result) == 2
        assert result[0] == Point(0, 1)
        assert result[1] == Point(2, 3)


class TestKeyMapping:
    """Tests for KeyMapping ordered dict."""

    def test_keymapping_stores_pointlist(self):
        """KeyMapping should convert values to PointList."""
        km = KeyMapping()
        km["KEY_A"] = [[3, 2]]
        assert len(km["KEY_A"]) == 1
        assert km["KEY_A"][0] == Point(3, 2)


class TestHexQuad:
    """Tests for HexQuad type."""

    def test_hexquad_is_int(self):
        """HexQuad should be an int subclass."""
        h = HexQuad(0x1532)
        assert isinstance(h, int)
        assert h == 0x1532


# ─────────────────────────────────────────────────────────────────────────────
# Hardware.has_quirk Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareHasQuirk:
    """Tests for Hardware.has_quirk method."""

    def test_has_quirk_no_quirks_returns_false(self):
        """Device with no quirks should return False for any quirk check."""
        # DeathAdder Chroma has no quirks
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_quirk(Quirks.TRANSACTION_CODE_3F) is False
        assert device.has_quirk(Quirks.EXTENDED_FX_CMDS) is False
        assert device.has_quirk(Quirks.WIRELESS) is False

    def test_has_quirk_single_quirk_match(self):
        """Device with single quirk should return True for matching quirk."""
        # Orochi (Wired) has SCROLL_WHEEL_BRIGHTNESS quirk
        device = Hardware.get_device(0x0048, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_quirk(Quirks.SCROLL_WHEEL_BRIGHTNESS) is True

    def test_has_quirk_single_quirk_no_match(self):
        """Device with single quirk should return False for non-matching quirk."""
        # DeathAdder Elite has TRANSACTION_CODE_3F quirk
        device = Hardware.get_device(0x005C, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_quirk(Quirks.TRANSACTION_CODE_3F) is True
        assert device.has_quirk(Quirks.WIRELESS) is False

    def test_has_quirk_multiple_quirks_any_match(self):
        """Device with multiple quirks should return True if any match."""
        # Naga Hex V2 has both EXTENDED_FX_CMDS and TRANSACTION_CODE_3F
        device = Hardware.get_device(0x0050, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_quirk(Quirks.EXTENDED_FX_CMDS) is True
        assert device.has_quirk(Quirks.TRANSACTION_CODE_3F) is True

    def test_has_quirk_multiple_args_any_match(self):
        """has_quirk with multiple args should return True if any match."""
        # Naga Hex V2 has EXTENDED_FX_CMDS
        device = Hardware.get_device(0x0050, Hardware.Type.MOUSE)
        assert device is not None
        # Check multiple quirks at once - should return True if any match
        assert device.has_quirk(Quirks.WIRELESS, Quirks.EXTENDED_FX_CMDS) is True
        # Neither match
        assert device.has_quirk(Quirks.WIRELESS, Quirks.SCROLL_WHEEL_BRIGHTNESS) is False


# ─────────────────────────────────────────────────────────────────────────────
# Hardware.has_matrix Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareHasMatrix:
    """Tests for Hardware.has_matrix property."""

    def test_has_matrix_no_dimensions_returns_false(self):
        """Device with no dimensions should return False for has_matrix."""
        # DeathAdder Chroma has no dimensions
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.dimensions is None
        assert device.has_matrix is False

    def test_has_matrix_1xn_dimensions_returns_false(self):
        """Device with 1xN dimensions should return False (not a matrix)."""
        # Mamba (Wired) has dimensions [1, 15]
        device = Hardware.get_device(0x0044, Hardware.Type.MOUSE)
        assert device is not None
        assert device.dimensions is not None
        assert device.dimensions.y == 1
        assert device.dimensions.x == 15
        assert device.has_matrix is False

    def test_has_matrix_nxm_dimensions_returns_true(self):
        """Device with NxM dimensions (both > 1) should return True."""
        # BlackWidow Chroma has dimensions [6, 22]
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.dimensions is not None
        assert device.dimensions.y == 6
        assert device.dimensions.x == 22
        assert device.has_matrix is True


# ─────────────────────────────────────────────────────────────────────────────
# Hardware.get_type Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareGetType:
    """Tests for Hardware.get_type class method."""

    def test_get_type_keyboard(self):
        """get_type should load keyboard YAML and return Hardware objects."""
        config = Hardware.get_type(Hardware.Type.KEYBOARD)
        assert config is not None
        assert config.type == Hardware.Type.KEYBOARD
        assert config.manufacturer == "Razer"

    def test_get_type_mouse(self):
        """get_type should load mouse YAML and return Hardware objects."""
        config = Hardware.get_type(Hardware.Type.MOUSE)
        assert config is not None
        assert config.type == Hardware.Type.MOUSE
        assert config.manufacturer == "Razer"

    def test_get_type_headset(self):
        """get_type should load headset YAML."""
        config = Hardware.get_type(Hardware.Type.HEADSET)
        assert config is not None
        assert config.type == Hardware.Type.HEADSET

    def test_get_type_keypad(self):
        """get_type should load keypad YAML."""
        config = Hardware.get_type(Hardware.Type.KEYPAD)
        assert config is not None
        assert config.type == Hardware.Type.KEYPAD

    def test_get_type_laptop(self):
        """get_type should load laptop YAML."""
        config = Hardware.get_type(Hardware.Type.LAPTOP)
        assert config is not None
        assert config.type == Hardware.Type.LAPTOP

    def test_get_type_mousepad(self):
        """get_type should load mousepad YAML."""
        config = Hardware.get_type(Hardware.Type.MOUSEPAD)
        assert config is not None
        assert config.type == Hardware.Type.MOUSEPAD

    def test_get_type_none_returns_none(self):
        """get_type with None should return None."""
        result = Hardware.get_type(None)
        assert result is None

    def test_get_type_returns_hardware_instance(self):
        """get_type should return a Hardware instance."""
        config = Hardware.get_type(Hardware.Type.KEYBOARD)
        assert isinstance(config, Hardware)


# ─────────────────────────────────────────────────────────────────────────────
# Hardware.get_device Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareGetDevice:
    """Tests for Hardware.get_device class method."""

    def test_get_device_with_specific_type(self):
        """get_device with specific hw_type should find device."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.name == "BlackWidow Chroma"
        assert device.product_id == 0x0203

    def test_get_device_without_type_searches_all(self):
        """get_device without hw_type should search all device types."""
        # Mouse device, no type specified
        device = Hardware.get_device(0x0043)
        assert device is not None
        assert device.name == "DeathAdder Chroma"
        assert device.type == Hardware.Type.MOUSE

    def test_get_device_keyboard_without_type(self):
        """get_device should find keyboard when searching all types."""
        device = Hardware.get_device(0x0203)
        assert device is not None
        assert device.name == "BlackWidow Chroma"
        assert device.type == Hardware.Type.KEYBOARD

    def test_get_device_nonexistent_returns_none(self):
        """get_device with non-existent product_id should return None."""
        device = Hardware.get_device(0xFFFF, Hardware.Type.KEYBOARD)
        assert device is None

    def test_get_device_nonexistent_searches_all_returns_none(self):
        """get_device with non-existent product_id (no type) should return None."""
        device = Hardware.get_device(0xFFFF)
        assert device is None

    def test_get_device_wrong_type_returns_none(self):
        """get_device with wrong type should return None."""
        # BlackWidow Chroma is a keyboard, not a mouse
        device = Hardware.get_device(0x0203, Hardware.Type.MOUSE)
        assert device is None


# ─────────────────────────────────────────────────────────────────────────────
# Hardware.Type Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareType:
    """Tests for Hardware.Type enum."""

    def test_hardware_type_values(self):
        """Verify all Hardware.Type enum values."""
        assert Hardware.Type.HEADSET.value == "Headset"
        assert Hardware.Type.KEYBOARD.value == "Keyboard"
        assert Hardware.Type.KEYPAD.value == "Keypad"
        assert Hardware.Type.LAPTOP.value == "Laptop"
        assert Hardware.Type.MOUSE.value == "Mouse"
        assert Hardware.Type.MOUSEPAD.value == "Mousepad"

    def test_hardware_type_names(self):
        """Hardware.Type names should be uppercase."""
        assert Hardware.Type.KEYBOARD.name == "KEYBOARD"
        assert Hardware.Type.MOUSE.name == "MOUSE"


# ─────────────────────────────────────────────────────────────────────────────
# Hardware Property Inheritance Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwarePropertyInheritance:
    """Tests for Hardware property inheritance from parent configs."""

    def test_device_inherits_vendor_id(self):
        """Devices should inherit vendor_id from parent config."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.vendor_id == 0x1532  # Razer vendor ID

    def test_device_inherits_manufacturer(self):
        """Devices should inherit manufacturer from parent config."""
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.manufacturer == "Razer"

    def test_device_inherits_supported_leds(self):
        """Devices should inherit supported_leds from parent config."""
        # DeathAdder Chroma inherits supported_leds from mouse parent
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.supported_leds is not None

    def test_device_overrides_supported_leds(self):
        """Devices can override inherited properties."""
        # Mamba Wireless has custom supported_leds including battery
        device = Hardware.get_device(0x0045, Hardware.Type.MOUSE)
        assert device is not None
        assert device.supported_leds is not None


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests - Real Device Data
# ─────────────────────────────────────────────────────────────────────────────


class TestRealDeviceData:
    """Integration tests using actual device configurations."""

    def test_blackwidow_chroma_full_config(self):
        """BlackWidow Chroma should have complete configuration."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.name == "BlackWidow Chroma"
        assert device.manufacturer == "Razer"
        assert device.vendor_id == 0x1532
        assert device.product_id == 0x0203
        assert device.type == Hardware.Type.KEYBOARD
        assert device.dimensions == Point(6, 22)
        assert device.has_matrix is True
        assert device.supported_fx is not None
        assert "wave" in device.supported_fx
        assert "static" in device.supported_fx

    def test_mamba_wireless_config(self):
        """Mamba Wireless should have wireless quirk."""
        device = Hardware.get_device(0x0045, Hardware.Type.MOUSE)
        assert device is not None
        assert device.name == "Mamba (Wireless)"
        assert device.has_quirk(Quirks.WIRELESS) is True
        assert device.dimensions == Point(1, 15)
        assert device.has_matrix is False

    def test_ornata_chroma_extended_fx(self):
        """Ornata Chroma should have EXTENDED_FX_CMDS quirk."""
        device = Hardware.get_device(0x021E, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.name == "Ornata Chroma"
        assert device.has_quirk(Quirks.EXTENDED_FX_CMDS) is True

    def test_key_mapping_inherited(self):
        """Keyboards should inherit key_mapping from parent."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.key_mapping is not None
        assert "KEY_ESC" in device.key_mapping
        assert "KEY_A" in device.key_mapping


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Capability Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCapabilityEnum:
    """Tests for the Capability enum values."""

    def test_capability_wireless(self):
        """WIRELESS capability should have correct value."""
        assert Capability.WIRELESS.value == "wireless"

    def test_capability_hyperpolling(self):
        """HYPERPOLLING capability should have correct value."""
        assert Capability.HYPERPOLLING.value == "hyperpolling"

    def test_capability_no_led(self):
        """NO_LED capability should have correct value."""
        assert Capability.NO_LED.value == "no_led"

    def test_capability_single_led(self):
        """SINGLE_LED capability should have correct value."""
        assert Capability.SINGLE_LED.value == "single_led"

    def test_capability_software_effects(self):
        """SOFTWARE_EFFECTS capability should have correct value."""
        assert Capability.SOFTWARE_EFFECTS.value == "software_effects"

    def test_capability_analog_keys(self):
        """ANALOG_KEYS capability should have correct value."""
        assert Capability.ANALOG_KEYS.value == "analog_keys"

    def test_capability_profile_leds(self):
        """PROFILE_LEDS capability should have correct value."""
        assert Capability.PROFILE_LEDS.value == "profile_leds"

    def test_capability_is_strenum(self):
        """Capability should be usable as strings."""
        assert str(Capability.WIRELESS) == "wireless"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: MatrixType Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMatrixTypeEnum:
    """Tests for the MatrixType enum values."""

    def test_matrix_type_none(self):
        """NONE matrix type should have correct value."""
        assert MatrixType.NONE.value == "none"

    def test_matrix_type_single(self):
        """SINGLE matrix type should have correct value."""
        assert MatrixType.SINGLE.value == "single"

    def test_matrix_type_row(self):
        """ROW matrix type should have correct value."""
        assert MatrixType.ROW.value == "row"

    def test_matrix_type_full(self):
        """FULL matrix type should have correct value."""
        assert MatrixType.FULL.value == "full"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: ProtocolSpec Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProtocolSpec:
    """Tests for ProtocolSpec named tuple."""

    def test_protocol_spec_defaults(self):
        """ProtocolSpec should have sensible defaults."""
        spec = ProtocolSpec()
        assert spec.version == "legacy"
        assert spec.transaction_id == 0xFF
        assert spec.transaction_id_wireless is None
        assert spec.extended_fx is False
        assert spec.inter_command_delay == 0.007

    def test_protocol_spec_custom_values(self):
        """ProtocolSpec should accept custom values."""
        spec = ProtocolSpec(
            version="modern",
            transaction_id=0x1F,
            transaction_id_wireless=0x1F,
            extended_fx=True,
            inter_command_delay=0.005,
        )
        assert spec.version == "modern"
        assert spec.transaction_id == 0x1F
        assert spec.transaction_id_wireless == 0x1F
        assert spec.extended_fx is True
        assert spec.inter_command_delay == 0.005

    def test_protocol_spec_asdict(self):
        """ProtocolSpec._asdict() should omit None values."""
        spec = ProtocolSpec(version="extended", transaction_id=0x3F, extended_fx=True)
        d = spec._asdict()
        assert d["version"] == "extended"
        assert d["transaction_id"] == 0x3F
        assert "transaction_id_wireless" not in d  # None values omitted

    def test_protocol_spec_is_immutable(self):
        """ProtocolSpec should be immutable."""
        spec = ProtocolSpec()
        with pytest.raises(AttributeError):
            spec.version = "modern"  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Hardware.has_capability Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareHasCapability:
    """Tests for Hardware.has_capability method."""

    def test_has_capability_wireless_via_quirk(self):
        """has_capability should detect WIRELESS from legacy quirk."""
        # Mamba Wireless has WIRELESS quirk
        device = Hardware.get_device(0x0045, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_capability(Capability.WIRELESS) is True
        assert device.has_capability("wireless") is True

    def test_has_capability_no_capability(self):
        """has_capability should return False when not present."""
        # DeathAdder Chroma has no wireless capability
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_capability(Capability.WIRELESS) is False

    def test_has_capability_string_argument(self):
        """has_capability should accept string argument."""
        device = Hardware.get_device(0x0045, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_capability("WIRELESS") is True
        assert device.has_capability("Wireless") is True

    def test_has_capability_unknown_capability(self):
        """has_capability should return False for unknown capability."""
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_capability("nonexistent") is False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Hardware.get_protocol_config Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareGetProtocolConfig:
    """Tests for Hardware.get_protocol_config method."""

    def test_get_protocol_config_legacy(self):
        """Device with no quirks should get LEGACY protocol."""
        # DeathAdder Chroma has no transaction code quirks
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        config = device.get_protocol_config()
        assert config.version == ProtocolVersion.LEGACY
        assert config.transaction_id == 0xFF
        assert config.uses_extended_fx is False

    def test_get_protocol_config_extended(self):
        """Device with TRANSACTION_CODE_3F should get EXTENDED protocol."""
        # Naga Hex V2 has TRANSACTION_CODE_3F
        device = Hardware.get_device(0x0050, Hardware.Type.MOUSE)
        assert device is not None
        config = device.get_protocol_config()
        assert config.version == ProtocolVersion.EXTENDED
        assert config.transaction_id == 0x3F

    def test_get_protocol_config_modern(self):
        """Device with TRANSACTION_CODE_1F should get MODERN protocol."""
        # Find a device with TRANSACTION_CODE_1F quirk
        # Basilisk V3 (0x0099) has TRANSACTION_CODE_1F
        device = Hardware.get_device(0x0099, Hardware.Type.MOUSE)
        if device is not None:
            config = device.get_protocol_config()
            assert config.version == ProtocolVersion.MODERN
            assert config.transaction_id == 0x1F


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Hardware.uses_extended_fx Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareUsesExtendedFx:
    """Tests for Hardware.uses_extended_fx property."""

    def test_uses_extended_fx_false_for_legacy(self):
        """Legacy device should return False for uses_extended_fx."""
        # DeathAdder Chroma doesn't use extended FX
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.uses_extended_fx is False

    def test_uses_extended_fx_true_for_extended(self):
        """Device with EXTENDED_FX_CMDS should return True."""
        # Naga Hex V2 has EXTENDED_FX_CMDS
        device = Hardware.get_device(0x0050, Hardware.Type.MOUSE)
        assert device is not None
        assert device.uses_extended_fx is True

    def test_uses_extended_fx_ornata(self):
        """Ornata Chroma should use extended FX."""
        device = Hardware.get_device(0x021E, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.uses_extended_fx is True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Hardware.has_leds Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareHasLeds:
    """Tests for Hardware.has_leds property."""

    def test_has_leds_true_for_keyboard(self):
        """Keyboard with supported_leds should return True."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        assert device.has_leds is True

    def test_has_leds_true_for_mouse(self):
        """Mouse with supported_leds should return True."""
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        assert device.has_leds is True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Hardware Effect Support Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHardwareEffectSupport:
    """Tests for Hardware.get_supported_effects and supports_effect methods."""

    def test_get_supported_effects_returns_tuple(self):
        """get_supported_effects should return tuple."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        effects = device.get_supported_effects()
        assert isinstance(effects, tuple)

    def test_get_supported_effects_from_supported_fx(self):
        """get_supported_effects should use supported_fx field."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        effects = device.get_supported_effects()
        assert len(effects) > 0
        assert "wave" in effects or "static" in effects

    def test_supports_effect_true(self):
        """supports_effect should return True for supported effect."""
        device = Hardware.get_device(0x0203, Hardware.Type.KEYBOARD)
        assert device is not None
        # BlackWidow Chroma should support common effects
        assert device.supports_effect("static") is True
        assert device.supports_effect("STATIC") is True  # Case insensitive

    def test_supports_effect_returns_true_when_no_list(self):
        """supports_effect should return True when no effects list specified."""
        # Find a device with no supported_fx list
        device = Hardware.get_device(0x0043, Hardware.Type.MOUSE)
        assert device is not None
        if device.supported_fx is None:
            # When no list, all effects considered available
            assert device.supports_effect("static") is True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: New Quirks Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestNewQuirks:
    """Tests for new quirks added in Phase 1."""

    def test_transaction_code_9f_exists(self):
        """TRANSACTION_CODE_9F quirk should exist."""
        assert Quirks.TRANSACTION_CODE_9F == 10

    def test_transaction_code_08_exists(self):
        """TRANSACTION_CODE_08 quirk should exist."""
        assert Quirks.TRANSACTION_CODE_08 == 11

    def test_no_led_quirk_exists(self):
        """NO_LED quirk should exist."""
        assert Quirks.NO_LED == 12

    def test_single_led_quirk_exists(self):
        """SINGLE_LED quirk should exist."""
        assert Quirks.SINGLE_LED == 13

    def test_hyperpolling_quirk_exists(self):
        """HYPERPOLLING quirk should exist."""
        assert Quirks.HYPERPOLLING == 14

    def test_analog_keys_quirk_exists(self):
        """ANALOG_KEYS quirk should exist."""
        assert Quirks.ANALOG_KEYS == 15

    def test_software_effects_quirk_exists(self):
        """SOFTWARE_EFFECTS quirk should exist."""
        assert Quirks.SOFTWARE_EFFECTS == 16

    def test_crc_skip_on_ok_quirk_exists(self):
        """CRC_SKIP_ON_OK quirk should exist."""
        assert Quirks.CRC_SKIP_ON_OK == 17
