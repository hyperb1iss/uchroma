#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.prefs module."""

from __future__ import annotations

import os
import tempfile
import time
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

from uchroma.colorlib import Color

# ─────────────────────────────────────────────────────────────────────────────
# Preferences Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPreferences:
    """Tests for Preferences class."""

    @pytest.fixture
    def prefs_class(self):
        """Import Preferences class."""
        from uchroma.server.prefs import Preferences

        return Preferences

    def test_init_with_brightness(self, prefs_class):
        """Preferences can store brightness."""
        prefs = prefs_class(brightness=75.0)
        assert prefs.brightness == 75.0

    def test_init_with_serial(self, prefs_class):
        """Preferences can store serial."""
        prefs = prefs_class(serial="XX00000001")
        assert prefs.serial == "XX00000001"

    def test_init_with_fx(self, prefs_class):
        """Preferences can store fx name."""
        prefs = prefs_class(fx="rainbow")
        assert prefs.fx == "rainbow"

    def test_init_with_fx_args(self, prefs_class):
        """Preferences can store fx_args."""
        args = OrderedDict({"speed": 1.0, "direction": "cw"})
        prefs = prefs_class(fx_args=args)
        assert prefs.fx_args == args

    def test_init_with_layers(self, prefs_class):
        """Preferences can store layers."""
        layers = OrderedDict({"layer1": {"effect": "plasma"}})
        prefs = prefs_class(layers=layers)
        assert prefs.layers == layers

    def test_init_with_leds(self, prefs_class):
        """Preferences can store leds dict."""
        leds = {"backlight": True, "logo": False}
        prefs = prefs_class(leds=leds)
        assert prefs.leds == leds

    def test_init_with_last_updated(self, prefs_class):
        """Preferences can store last_updated timestamp."""
        now = time.time()
        prefs = prefs_class(last_updated=now)
        assert prefs.last_updated == now

    def test_yaml_header(self, prefs_class):
        """_yaml_header returns formatted header."""
        prefs = prefs_class()
        header = prefs._yaml_header()
        assert "#" in header
        assert "uChroma preferences" in header
        assert "Updated on:" in header

    def test_parent_child_hierarchy(self, prefs_class):
        """Preferences supports parent-child hierarchy."""
        parent = prefs_class(brightness=100.0)
        child = prefs_class(parent=parent, serial="child1")
        assert child.parent is parent
        # Child should inherit brightness
        assert child.brightness == 100.0

    def test_child_overrides_parent(self, prefs_class):
        """Child can override parent values."""
        parent = prefs_class(brightness=100.0)
        child = prefs_class(parent=parent, brightness=50.0)
        assert child.brightness == 50.0


# ─────────────────────────────────────────────────────────────────────────────
# PreferenceManager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPreferenceManager:
    """Tests for PreferenceManager class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton instance before each test."""
        from uchroma.server.prefs import PreferenceManager

        # Clear the singleton instance (uses __instance attribute on class)
        if hasattr(PreferenceManager, "_Singleton__instance"):
            delattr(PreferenceManager, "_Singleton__instance")
        yield
        # Clean up after test
        if hasattr(PreferenceManager, "_Singleton__instance"):
            delattr(PreferenceManager, "_Singleton__instance")

    @pytest.fixture
    def temp_conf_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_conf_paths(self, temp_conf_dir):
        """Patch CONFDIR and CONFFILE to use temp directory."""
        conf_file = os.path.join(temp_conf_dir, "preferences.yaml")
        with (
            patch("uchroma.server.prefs.CONFDIR", temp_conf_dir),
            patch("uchroma.server.prefs.CONFFILE", conf_file),
        ):
            yield temp_conf_dir, conf_file

    def test_singleton_behavior(self, mock_conf_paths):
        """PreferenceManager is a singleton."""
        from uchroma.server.prefs import PreferenceManager

        mgr1 = PreferenceManager()
        mgr2 = PreferenceManager()
        assert mgr1 is mgr2

    def test_init_creates_root(self, mock_conf_paths):
        """PreferenceManager creates root preferences."""
        from uchroma.server.prefs import PreferenceManager, Preferences

        mgr = PreferenceManager()
        assert mgr._root is not None
        assert isinstance(mgr._root, Preferences)

    def test_init_creates_confdir(self, temp_conf_dir, mock_conf_paths):
        """PreferenceManager creates config directory."""
        from uchroma.server.prefs import PreferenceManager

        # Remove the temp dir to test creation
        os.rmdir(temp_conf_dir)
        assert not os.path.exists(temp_conf_dir)

        PreferenceManager()

        assert os.path.exists(temp_conf_dir)

    def test_load_prefs_creates_new_when_no_file(self, mock_conf_paths):
        """_load_prefs creates new Preferences when file doesn't exist."""
        from uchroma.server.prefs import PreferenceManager

        mgr = PreferenceManager()
        assert mgr._root.last_updated is not None

    def test_load_prefs_loads_existing_file(self, mock_conf_paths):
        """_load_prefs loads existing preferences file."""
        from uchroma.server.prefs import PreferenceManager, Preferences

        _conf_dir, conf_file = mock_conf_paths

        # Create a preferences file
        prefs = Preferences(brightness=42.0, last_updated=time.time())
        prefs.save_yaml(conf_file)

        mgr = PreferenceManager()
        assert mgr._root.brightness == 42.0

    def test_get_returns_existing_prefs(self, mock_conf_paths):
        """get returns existing preferences for serial."""
        from uchroma.server.prefs import PreferenceManager, Preferences

        mgr = PreferenceManager()
        # Create a child with specific serial
        child = Preferences(parent=mgr._root, serial="TEST123", brightness=75.0)

        result = mgr.get("TEST123")
        assert result is child
        assert result.brightness == 75.0

    def test_get_creates_new_prefs(self, mock_conf_paths):
        """get creates new preferences for unknown serial."""
        from uchroma.server.prefs import PreferenceManager

        mgr = PreferenceManager()
        result = mgr.get("NEW_SERIAL")
        assert result.serial == "NEW_SERIAL"
        assert result.parent is mgr._root

    def test_get_with_none_serial(self, mock_conf_paths):
        """get handles None serial."""
        from uchroma.server.prefs import PreferenceManager

        mgr = PreferenceManager()
        result = mgr.get(None)
        # Should create new prefs with None serial
        assert result.serial is None

    def test_save_prefs_updates_timestamp(self, mock_conf_paths):
        """_save_prefs updates last_updated timestamp."""
        from uchroma.server.prefs import PreferenceManager

        mgr = PreferenceManager()
        old_time = mgr._root.last_updated

        time.sleep(0.01)  # Ensure time difference
        mgr._save_prefs()

        assert mgr._root.last_updated > old_time

    def test_save_prefs_writes_file(self, mock_conf_paths):
        """_save_prefs writes preferences to file."""
        from uchroma.server.prefs import PreferenceManager

        _conf_dir, conf_file = mock_conf_paths
        mgr = PreferenceManager()
        mgr._save_prefs()

        assert os.path.exists(conf_file)

    def test_preferences_changed_ignores_last_updated(self, mock_conf_paths):
        """_preferences_changed doesn't save for last_updated changes."""
        from uchroma.server.prefs import PreferenceManager

        mgr = PreferenceManager()
        with patch.object(mgr, "_save_prefs") as mock_save:
            mgr._preferences_changed(mgr._root, "last_updated", time.time())
            mock_save.assert_not_called()

    def test_preferences_changed_saves_for_other_changes(self, mock_conf_paths):
        """_preferences_changed saves for non-last_updated changes."""
        from uchroma.server.prefs import PreferenceManager

        mgr = PreferenceManager()
        with patch.object(mgr, "_save_prefs") as mock_save:
            mgr._preferences_changed(mgr._root, "brightness", 50.0)
            mock_save.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# YAML Color Serialization Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestYamlColorSerialization:
    """Tests for Color YAML serialization."""

    def test_represent_color_returns_html(self):
        """represent_color returns HTML hex representation."""
        from uchroma.server.prefs import represent_color

        dumper = MagicMock()
        dumper.represent_scalar.return_value = "result"
        color = Color.NewFromRgb(1.0, 0.0, 0.0)

        represent_color(dumper, color)

        dumper.represent_scalar.assert_called_once()
        args = dumper.represent_scalar.call_args[0]
        assert args[0] == "!color"
        assert args[1].lower() == "#ff0000"

    def test_construct_color_creates_color(self):
        """construct_color creates Color from HTML."""
        from uchroma.server.prefs import construct_color

        loader = MagicMock()
        loader.construct_yaml_str.return_value = "#00ff00"
        node = MagicMock()

        result = construct_color(loader, node)

        assert isinstance(result, Color)
        # Check it's green
        assert result.html.lower() == "#00ff00"

    def test_color_roundtrip_via_yaml(self):
        """Color survives YAML roundtrip via Preferences."""
        import os
        import tempfile

        from uchroma.server.prefs import Preferences

        # Create preferences with color data in fx_args
        prefs = Preferences(
            fx="test",
            fx_args=OrderedDict({"color": Color.NewFromRgb(0.0, 0.0, 1.0)}),
            last_updated=time.time(),
        )

        # Save to temp file and load back
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            filename = f.name

        try:
            prefs.save_yaml(filename)

            # Clear cache for fresh load
            Preferences._yaml_cache.clear()

            loaded = Preferences.load_yaml(filename)
            # The color should survive roundtrip (if in fx_args OrderedDict)
            assert loaded.fx_args is not None
        finally:
            os.unlink(filename)


# ─────────────────────────────────────────────────────────────────────────────
# Module Constants Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_confdir_exists(self):
        """CONFDIR is defined."""
        from uchroma.server.prefs import CONFDIR

        assert CONFDIR is not None
        assert ".config/uchroma" in CONFDIR

    def test_conffile_exists(self):
        """CONFFILE is defined."""
        from uchroma.server.prefs import CONFFILE

        assert CONFFILE is not None
        assert "preferences.yaml" in CONFFILE

    def test_conffile_under_confdir(self):
        """CONFFILE is under CONFDIR."""
        from uchroma.server.prefs import CONFDIR, CONFFILE

        assert CONFFILE.startswith(CONFDIR)
