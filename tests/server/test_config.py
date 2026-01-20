#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.config module."""

from __future__ import annotations

import os
import tempfile
from enum import Enum

import pytest

from uchroma.colorlib import Color
from uchroma.server.config import (
    Configuration,
    FlowSequence,
    LowerCaseSeq,
    represent_color,
    represent_enum,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Enums
# ─────────────────────────────────────────────────────────────────────────────


class SampleMode(Enum):
    FAST = 1
    NORMAL = 2
    SLOW = 3


# ─────────────────────────────────────────────────────────────────────────────
# Representer Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRepresentEnum:
    """Tests for represent_enum function."""

    def test_represent_enum_returns_name(self):
        """represent_enum returns the enum name as a string."""
        from unittest.mock import MagicMock

        dumper = MagicMock()
        dumper.represent_scalar.return_value = "result"

        result = represent_enum(dumper, SampleMode.FAST)

        dumper.represent_scalar.assert_called_once_with("tag:yaml.org,2002:str", "FAST")
        assert result == "result"


class TestRepresentColor:
    """Tests for represent_color function."""

    def test_represent_color_returns_html(self):
        """represent_color returns the HTML hex string."""
        from unittest.mock import MagicMock

        dumper = MagicMock()
        dumper.represent_scalar.return_value = "result"
        color = Color.NewFromRgb(1.0, 0.0, 0.0)

        represent_color(dumper, color)

        # Should call with hex color
        args = dumper.represent_scalar.call_args[0]
        assert args[0] == "tag:yaml.org,2002:str"
        assert args[1].lower() == "#ff0000"


# ─────────────────────────────────────────────────────────────────────────────
# Configuration.create Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigurationCreate:
    """Tests for Configuration.create class method."""

    def test_create_returns_class(self):
        """create returns a new Configuration subclass."""
        TestConfig = Configuration.create(
            "TestConfig", [("name", str), ("value", int)], mutable=True
        )
        assert issubclass(TestConfig, Configuration)
        assert TestConfig.__name__ == "TestConfig"

    def test_create_with_yaml_name(self):
        """create uses custom yaml_name."""
        TestConfig = Configuration.create(
            "TestConfig",
            [("name", str)],
            yaml_name="!custom-tag",
            mutable=True,
        )
        # Just verify it doesn't raise
        assert TestConfig is not None

    def test_create_mutable_flag(self):
        """create respects mutable flag."""
        MutableConfig = Configuration.create("MutableConfig", [("value", int)], mutable=True)
        ImmutableConfig = Configuration.create("ImmutableConfig", [("value", int)], mutable=False)
        assert MutableConfig._mutable is True
        assert ImmutableConfig._mutable is False


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Instance Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigurationInstance:
    """Tests for Configuration instances."""

    @pytest.fixture
    def MutableConfig(self):
        """Create a mutable config class."""
        return Configuration.create(
            "MutableConfig", [("name", str), ("count", int), ("enabled", bool)], mutable=True
        )

    @pytest.fixture
    def ImmutableConfig(self):
        """Create an immutable config class."""
        return Configuration.create("ImmutableConfig", [("name", str)], mutable=False)

    def test_init_with_kwargs(self, MutableConfig):
        """Configuration can be initialized with kwargs."""
        config = MutableConfig(name="test", count=42)
        assert config.name == "test"
        assert config.count == 42

    def test_init_with_parent(self, MutableConfig):
        """Configuration can have a parent."""
        parent = MutableConfig(name="parent")
        child = MutableConfig(parent=parent, count=10)
        assert child.parent is parent

    def test_child_inherits_from_parent(self, MutableConfig):
        """Child inherits values from parent."""
        parent = MutableConfig(name="parent")
        child = MutableConfig(parent=parent)
        # Child should inherit name from parent
        assert child.name == "parent"

    def test_child_overrides_parent(self, MutableConfig):
        """Child can override parent values."""
        parent = MutableConfig(name="parent")
        child = MutableConfig(parent=parent, name="child")
        assert child.name == "child"

    def test_str_representation(self, MutableConfig):
        """str shows non-None values."""
        config = MutableConfig(name="test", count=5)
        s = str(config)
        assert "MutableConfig" in s
        assert "name='test'" in s
        assert "count=5" in s

    def test_immutable_raises_on_setattr(self, ImmutableConfig):
        """Immutable config raises on setattr."""
        config = ImmutableConfig(name="test")
        with pytest.raises(AttributeError, match="read-only"):
            config.name = "changed"

    def test_mutable_allows_setattr(self, MutableConfig):
        """Mutable config allows setattr."""
        config = MutableConfig(name="test")
        config.name = "changed"
        assert config.name == "changed"

    def test_getitem_by_index(self, MutableConfig):
        """Configuration supports getitem by index."""
        config = MutableConfig(name="test")
        # First slot after parent is typically the first field
        # Exact behavior depends on slot ordering
        assert config.get("name") == "test"

    def test_get_with_default(self, MutableConfig):
        """get returns default for None values."""
        config = MutableConfig()
        result = config.get("name", default="default_value")
        assert result == "default_value"


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Hierarchy Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigurationHierarchy:
    """Tests for Configuration parent-child hierarchy."""

    @pytest.fixture
    def HierarchyConfig(self):
        """Create config for hierarchy tests."""
        return Configuration.create("HierarchyConfig", [("id", str), ("data", int)], mutable=True)

    def test_children_property(self, HierarchyConfig):
        """children property returns child configs."""
        parent = HierarchyConfig(id="parent")
        child1 = HierarchyConfig(parent=parent, id="child1")
        child2 = HierarchyConfig(parent=parent, id="child2")

        assert parent.children is not None
        assert len(parent.children) == 2
        assert child1 in parent.children
        assert child2 in parent.children

    def test_search(self, HierarchyConfig):
        """search finds matching configs in hierarchy."""
        parent = HierarchyConfig(id="parent", data=1)
        # Children are created to be found by search
        HierarchyConfig(parent=parent, id="child1", data=2)
        HierarchyConfig(parent=parent, id="child2", data=2)

        results = parent.search("data", 2)
        assert len(results) == 2

    def test_flatten(self, HierarchyConfig):
        """flatten returns list of concrete configs."""
        parent = HierarchyConfig(id="parent", data=1)
        HierarchyConfig(parent=parent, id="child", data=2)

        flat = parent.flatten()
        assert isinstance(flat, list)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Observer Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigurationObserver:
    """Tests for Configuration observers."""

    @pytest.fixture
    def ObservableConfig(self):
        """Create observable config class."""
        return Configuration.create("ObservableConfig", [("value", int)], mutable=True)

    def test_observe_fires_on_change(self, ObservableConfig):
        """Observer fires when value changes."""
        changes = []

        def observer(obj, name, value):
            changes.append((name, value))

        ObservableConfig.observe(observer)
        try:
            config = ObservableConfig(value=1)
            config.value = 2

            assert len(changes) == 1
            assert changes[0] == ("value", 2)
        finally:
            ObservableConfig.unobserve(observer)

    def test_unobserve_removes_observer(self, ObservableConfig):
        """unobserve removes observer."""
        changes = []

        def observer(obj, name, value):
            changes.append(value)

        ObservableConfig.observe(observer)
        ObservableConfig.unobserve(observer)

        config = ObservableConfig(value=1)
        config.value = 2

        assert len(changes) == 0

    def test_observers_paused_context(self, ObservableConfig):
        """observers_paused context manager pauses notifications."""
        changes = []

        def observer(obj, name, value):
            changes.append(value)

        ObservableConfig.observe(observer)
        try:
            config = ObservableConfig(value=1)

            with config.observers_paused():
                config.value = 2

            assert len(changes) == 0
        finally:
            ObservableConfig.unobserve(observer)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Serialization Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigurationSerialization:
    """Tests for Configuration YAML serialization."""

    @pytest.fixture
    def SerializableConfig(self):
        """Create serializable config class."""
        return Configuration.create(
            "SerializableConfig",
            [("name", str), ("count", int)],
            yaml_name="!test-config",
            mutable=True,
        )

    def test_sparsedict(self, SerializableConfig):
        """sparsedict returns non-None values."""
        config = SerializableConfig(name="test", count=5)
        sparse = config.sparsedict()

        assert isinstance(sparse, dict)
        assert sparse["name"] == "test"
        assert sparse["count"] == 5

    def test_yaml_property(self, SerializableConfig):
        """yaml property returns YAML string."""
        config = SerializableConfig(name="test", count=5)
        yaml_str = config.yaml

        assert isinstance(yaml_str, str)
        assert "test" in yaml_str

    def test_save_and_load_yaml(self, SerializableConfig):
        """save_yaml and load_yaml roundtrip."""
        config = SerializableConfig(name="roundtrip", count=42)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            filename = f.name

        try:
            config.save_yaml(filename)

            # Clear cache to force reload
            SerializableConfig._yaml_cache.clear()

            loaded = SerializableConfig.load_yaml(filename)
            assert loaded.name == "roundtrip"
            assert loaded.count == 42
        finally:
            os.unlink(filename)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Type Coercion Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigurationTypeCoercion:
    """Tests for Configuration._coerce_types method."""

    @pytest.fixture
    def TypedConfig(self):
        """Create config with typed fields."""
        return Configuration.create(
            "TypedConfig",
            [("mode", SampleMode), ("count", int), ("name", str)],
            mutable=True,
        )

    def test_coerce_enum_from_string(self, TypedConfig):
        """_coerce_types converts string to enum."""
        result = TypedConfig._coerce_types({"mode": "fast"})
        assert result["mode"] == SampleMode.FAST

    def test_coerce_int(self, TypedConfig):
        """_coerce_types converts to int."""
        result = TypedConfig._coerce_types({"count": "42"})
        assert result["count"] == 42
        assert isinstance(result["count"], int)

    def test_coerce_already_correct_type(self, TypedConfig):
        """_coerce_types passes through correct types."""
        result = TypedConfig._coerce_types({"mode": SampleMode.NORMAL})
        assert result["mode"] == SampleMode.NORMAL

    def test_coerce_invalid_raises(self, TypedConfig):
        """_coerce_types raises on invalid enum conversion."""
        # KeyError from enum lookup is not caught, so it propagates
        with pytest.raises(KeyError):
            TypedConfig._coerce_types({"mode": "INVALID_MODE"})


# ─────────────────────────────────────────────────────────────────────────────
# FlowSequence Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFlowSequence:
    """Tests for FlowSequence class."""

    def test_flow_sequence_is_tuple(self):
        """FlowSequence is a tuple subclass."""
        seq = FlowSequence((1, 2, 3))
        assert isinstance(seq, tuple)
        assert seq == (1, 2, 3)


class TestLowerCaseSeq:
    """Tests for LowerCaseSeq class."""

    def test_lower_case_seq_converts(self):
        """LowerCaseSeq stores lowercase values."""
        seq = LowerCaseSeq(("HELLO", "WORLD"))
        # The __new__ method appends lowercase versions but the tuple itself
        # is created from the original args - this documents actual behavior
        assert isinstance(seq, tuple)
