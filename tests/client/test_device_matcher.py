"""Tests for device matching and selection."""

import pytest

from uchroma.client.device_matcher import DeviceMatcher, parse_device_spec


class TestParseDeviceSpec:
    def test_at_prefix_extracts_name(self):
        result = parse_device_spec("@blackwidow")
        assert result == ("name", "blackwidow")

    def test_numeric_string_is_index(self):
        result = parse_device_spec("0")
        assert result == ("index", 0)

    def test_key_format_detected(self):
        result = parse_device_spec("1532:0226")
        assert result == ("key", "1532:0226")

    def test_key_format_with_index(self):
        result = parse_device_spec("1532:0226.01")
        assert result == ("key", "1532:0226.01")

    def test_dbus_path_detected(self):
        result = parse_device_spec("/io/uchroma/device/0")
        assert result == ("path", "/io/uchroma/device/0")

    def test_bare_name_is_fuzzy(self):
        result = parse_device_spec("black")
        assert result == ("fuzzy", "black")


class TestDeviceMatcher:
    @pytest.fixture
    def devices(self):
        """Mock device list."""
        return [
            {"name": "Razer BlackWidow V3", "key": "1532:0226.00", "type": "keyboard"},
            {"name": "Razer Mamba Elite", "key": "1532:0240.00", "type": "mouse"},
            {"name": "Razer Huntsman", "key": "1532:0227.00", "type": "keyboard"},
        ]

    def test_exact_name_match(self, devices):
        matcher = DeviceMatcher(devices)
        result = matcher.match("name", "Razer BlackWidow V3")
        assert result["key"] == "1532:0226.00"

    def test_fuzzy_match_partial(self, devices):
        matcher = DeviceMatcher(devices)
        result = matcher.match("fuzzy", "black")
        assert result["key"] == "1532:0226.00"

    def test_fuzzy_match_case_insensitive(self, devices):
        matcher = DeviceMatcher(devices)
        result = matcher.match("fuzzy", "MAMBA")
        assert result["key"] == "1532:0240.00"

    def test_index_match(self, devices):
        matcher = DeviceMatcher(devices)
        result = matcher.match("index", 1)
        assert result["name"] == "Razer Mamba Elite"

    def test_key_match_partial(self, devices):
        matcher = DeviceMatcher(devices)
        result = matcher.match("key", "1532:0226")
        assert result["name"] == "Razer BlackWidow V3"

    def test_ambiguous_fuzzy_raises(self, devices):
        matcher = DeviceMatcher(devices)
        # "razer" matches all three
        with pytest.raises(ValueError, match="ambiguous"):
            matcher.match("fuzzy", "razer")

    def test_no_match_raises(self, devices):
        matcher = DeviceMatcher(devices)
        with pytest.raises(ValueError, match="not found"):
            matcher.match("fuzzy", "corsair")

    def test_auto_select_single_device(self):
        devices = [{"name": "BlackWidow", "key": "1532:0226.00", "type": "keyboard"}]
        matcher = DeviceMatcher(devices)
        result = matcher.auto_select()
        assert result["name"] == "BlackWidow"

    def test_auto_select_multiple_raises(self, devices):
        matcher = DeviceMatcher(devices)
        with pytest.raises(ValueError, match="Multiple devices"):
            matcher.auto_select()
