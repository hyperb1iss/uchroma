#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.anim module."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uchroma.renderer import Renderer, RendererMeta

# ─────────────────────────────────────────────────────────────────────────────
# RendererInfo Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererInfo:
    """Tests for RendererInfo NamedTuple."""

    def test_renderer_info_creation(self):
        """RendererInfo can be created with all fields."""
        from uchroma.server.anim import RendererInfo

        info = RendererInfo(
            module="test.module",
            clazz=Renderer,
            key="test.module.TestRenderer",
            meta=RendererMeta("Test", "Description", "Author", "1.0"),
            traits={"speed": 1.0},
        )
        assert info.module == "test.module"
        assert info.clazz == Renderer
        assert info.key == "test.module.TestRenderer"
        assert info.meta.display_name == "Test"
        assert info.traits == {"speed": 1.0}

    def test_renderer_info_is_tuple(self):
        """RendererInfo is a NamedTuple."""
        from uchroma.server.anim import RendererInfo

        info = RendererInfo("m", Renderer, "k", RendererMeta("N", "", "", ""), {})
        assert isinstance(info, tuple)
        assert len(info) == 5


# ─────────────────────────────────────────────────────────────────────────────
# Mock Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_driver():
    """Create a mock driver for animation testing."""
    driver = MagicMock()
    driver.logger = MagicMock()
    driver.logger.isEnabledFor.return_value = False
    driver.logger.debug = MagicMock()
    driver.logger.info = MagicMock()
    driver.logger.error = MagicMock()
    driver.power_state_changed = MagicMock()
    driver.power_state_changed.connect = MagicMock()
    driver.restore_prefs = MagicMock()
    driver.restore_prefs.connect = MagicMock()
    driver.reset = MagicMock()
    driver.preferences = MagicMock()
    driver.preferences.layers = None
    return driver


@pytest.fixture
def mock_frame():
    """Create a mock frame for animation testing."""
    frame = MagicMock()
    frame._driver = MagicMock()
    frame._driver.logger = MagicMock()
    frame._driver.logger.isEnabledFor.return_value = False
    frame.create_layer = MagicMock(return_value=MagicMock())
    frame.commit = MagicMock()
    return frame


# ─────────────────────────────────────────────────────────────────────────────
# AnimationLoop Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAnimationLoop:
    """Tests for AnimationLoop class."""

    def test_init(self, mock_frame):
        """AnimationLoop initializes with frame."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        assert loop._frame is mock_frame
        assert loop.running is False
        assert loop.layers == []

    def test_init_with_blend_mode(self, mock_frame):
        """AnimationLoop stores default blend mode."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame, default_blend_mode="screen")
        assert loop._default_blend_mode == "screen"

    def test_layers_default_empty(self, mock_frame):
        """AnimationLoop starts with empty layers list."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        assert loop.layers == []
        assert len(loop.layers) == 0

    def test_running_default_false(self, mock_frame):
        """AnimationLoop starts not running."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        assert loop.running is False

    def test_start_no_layers(self, mock_frame):
        """AnimationLoop.start returns False with no layers."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        result = loop.start()
        assert result is False

    def test_start_already_running(self, mock_frame):
        """AnimationLoop.start returns False if already running."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        loop.running = True
        result = loop.start()
        assert result is False

    def test_pause_sets_event(self, mock_frame):
        """AnimationLoop.pause controls pause event."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        # Default is not paused (event is set)
        assert loop._pause_event.is_set()

        # Pause
        loop.pause(True)
        assert not loop._pause_event.is_set()

        # Unpause
        loop.pause(False)
        assert loop._pause_event.is_set()

    def test_stop_when_not_running(self, mock_frame):
        """AnimationLoop.stop returns False when not running."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        result = loop.stop()
        assert result is False

    def test_dequeue_nowait_not_running(self, mock_frame):
        """_dequeue_nowait returns False when not running."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        result = loop._dequeue_nowait(0)
        assert result is False

    def test_dequeue_nowait_index_out_of_range(self, mock_frame):
        """_dequeue_nowait returns False for out-of-range index."""
        from uchroma.server.anim import AnimationLoop

        loop = AnimationLoop(mock_frame)
        loop.running = True
        result = loop._dequeue_nowait(10)  # No layers
        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# LayerHolder Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLayerHolder:
    """Tests for LayerHolder class."""

    @pytest.fixture
    def mock_renderer(self):
        """Create a mock renderer."""
        renderer = MagicMock(spec=Renderer)
        renderer.running = False
        renderer.zindex = 0
        renderer._flush = MagicMock()
        renderer._free_layer = MagicMock()
        renderer.observe = MagicMock()
        renderer.finish = MagicMock()
        renderer._run = AsyncMock()
        renderer._stop = AsyncMock()
        return renderer

    def test_init(self, mock_frame, mock_renderer):
        """LayerHolder initializes with renderer and frame."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(mock_renderer, mock_frame)
        assert holder._renderer is mock_renderer
        assert holder._frame is mock_frame
        assert holder.waiter is None
        assert holder.active_buf is None
        assert holder.task is None

    def test_init_with_blend_mode(self, mock_frame, mock_renderer):
        """LayerHolder stores blend mode."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(mock_renderer, mock_frame, blend_mode="multiply")
        assert holder._blend_mode == "multiply"

    def test_type_string(self, mock_frame, mock_renderer):
        """LayerHolder.type_string returns module.class format."""
        from uchroma.server.anim import LayerHolder

        mock_renderer.__class__.__module__ = "test.module"
        mock_renderer.__class__.__name__ = "TestRenderer"

        holder = LayerHolder(mock_renderer, mock_frame)
        assert holder.type_string == "test.module.TestRenderer"

    def test_zindex_property(self, mock_frame, mock_renderer):
        """LayerHolder.zindex returns renderer zindex."""
        from uchroma.server.anim import LayerHolder

        mock_renderer.zindex = 5
        holder = LayerHolder(mock_renderer, mock_frame)
        assert holder.zindex == 5

    def test_renderer_property(self, mock_frame, mock_renderer):
        """LayerHolder.renderer returns renderer."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(mock_renderer, mock_frame)
        assert holder.renderer is mock_renderer

    def test_start_creates_task(self, mock_frame, mock_renderer):
        """LayerHolder.start creates task when not running."""
        from uchroma.server.anim import LayerHolder

        mock_renderer.running = False
        holder = LayerHolder(mock_renderer, mock_frame)

        with patch("uchroma.server.anim.ensure_future") as mock_ensure:
            mock_ensure.return_value = MagicMock()
            holder.start()
            mock_ensure.assert_called_once()

    def test_start_no_op_when_running(self, mock_frame, mock_renderer):
        """LayerHolder.start is no-op when already running."""
        from uchroma.server.anim import LayerHolder

        mock_renderer.running = True
        holder = LayerHolder(mock_renderer, mock_frame)

        with patch("uchroma.server.anim.ensure_future") as mock_ensure:
            holder.start()
            mock_ensure.assert_not_called()

    def test_stop_async(self, mock_frame, mock_renderer):
        """LayerHolder.stop stops renderer."""
        from uchroma.server.anim import LayerHolder

        mock_renderer.running = True
        holder = LayerHolder(mock_renderer, mock_frame)

        async def run_test():
            await holder.stop()
            return mock_renderer._stop.called

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# AnimationManager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAnimationManager:
    """Tests for AnimationManager class."""

    @pytest.fixture
    def mock_frame_control(self):
        """Mock frame control for AnimationManager."""
        frame = MagicMock()
        frame._driver = MagicMock()
        frame._driver.logger = MagicMock()
        frame._driver.logger.isEnabledFor.return_value = False
        frame.create_layer = MagicMock(return_value=MagicMock())
        return frame

    @pytest.fixture
    def animation_manager(self, mock_driver, mock_frame_control):
        """Create AnimationManager for testing."""
        from uchroma.server.anim import AnimationManager

        mock_driver.frame_control = mock_frame_control
        with patch.object(AnimationManager, "_discover_renderers", return_value=OrderedDict()):
            mgr = AnimationManager(mock_driver)
        return mgr

    def test_init(self, mock_driver):
        """AnimationManager initializes with driver."""
        from uchroma.server.anim import AnimationManager

        mock_driver.frame_control = MagicMock()
        with patch.object(AnimationManager, "_discover_renderers", return_value=OrderedDict()):
            mgr = AnimationManager(mock_driver)

        assert mgr._driver is mock_driver
        assert mgr._loop is None
        assert mgr.paused is False

    def test_running_false_when_no_loop(self, animation_manager):
        """AnimationManager.running is False with no loop."""
        assert animation_manager.running is False

    def test_running_false_when_loop_not_running(self, animation_manager, mock_frame):
        """AnimationManager.running is False when loop not running."""
        from uchroma.server.anim import AnimationLoop

        animation_manager._loop = AnimationLoop(mock_frame)
        assert animation_manager.running is False

    def test_renderer_info_property(self, animation_manager):
        """AnimationManager.renderer_info returns discovered renderers."""
        assert animation_manager.renderer_info == OrderedDict()

    def test_stop_no_loop(self, animation_manager):
        """AnimationManager.stop returns False with no loop."""
        result = animation_manager.stop()
        assert result is False

    def test_pause_no_loop(self, animation_manager):
        """AnimationManager.pause handles missing loop."""
        result = animation_manager.pause()
        assert result is False  # paused is False

    def test_pause_toggle(self, animation_manager, mock_frame):
        """AnimationManager.pause toggles paused state."""
        from uchroma.server.anim import AnimationLoop

        animation_manager._loop = AnimationLoop(mock_frame)
        animation_manager._loop.pause = MagicMock()

        # Toggle on
        animation_manager.pause(True)
        assert animation_manager.paused is True

        # Toggle off
        animation_manager.pause(False)
        assert animation_manager.paused is False

    def test_remove_renderer_no_loop(self, animation_manager):
        """AnimationManager.remove_renderer returns False with no loop."""
        result = animation_manager.remove_renderer(0)
        assert result is False

    def test_remove_renderer_invalid_zindex(self, animation_manager, mock_frame):
        """AnimationManager.remove_renderer returns False for invalid zindex."""
        from uchroma.server.anim import AnimationLoop

        animation_manager._loop = AnimationLoop(mock_frame)

        result = animation_manager.remove_renderer(None)
        assert result is False

        result = animation_manager.remove_renderer(-1)
        assert result is False

    def test_shutdown_no_loop(self, animation_manager):
        """AnimationManager.shutdown handles missing loop."""

        async def run_test():
            await animation_manager.shutdown()
            return animation_manager._shutting_down

        result = asyncio.run(run_test())
        assert result is True

    def test_create_loop(self, animation_manager, mock_frame):
        """AnimationManager._create_loop creates AnimationLoop."""
        animation_manager._driver.frame_control = mock_frame

        assert animation_manager._loop is None
        animation_manager._create_loop()
        assert animation_manager._loop is not None

    def test_create_loop_idempotent(self, animation_manager, mock_frame):
        """AnimationManager._create_loop doesn't recreate loop."""
        animation_manager._driver.frame_control = mock_frame

        animation_manager._create_loop()
        loop1 = animation_manager._loop

        animation_manager._create_loop()
        loop2 = animation_manager._loop

        assert loop1 is loop2

    def test_power_state_changed_pauses(self, animation_manager, mock_frame):
        """AnimationManager._power_state_changed pauses on suspend."""
        from uchroma.server.anim import AnimationLoop

        animation_manager._loop = AnimationLoop(mock_frame)
        animation_manager._loop.running = True
        animation_manager._loop.pause = MagicMock()

        animation_manager._power_state_changed(100.0, True)  # suspended=True
        assert animation_manager.paused is True

    def test_update_prefs_no_loop(self, animation_manager):
        """AnimationManager._update_prefs handles missing loop."""
        animation_manager._update_prefs()  # Should not raise

    def test_update_prefs_shutting_down(self, animation_manager, mock_frame):
        """AnimationManager._update_prefs skips during shutdown."""
        from uchroma.server.anim import AnimationLoop

        animation_manager._loop = AnimationLoop(mock_frame)
        animation_manager._shutting_down = True
        animation_manager._update_prefs()  # Should not raise

    def test_restore_prefs_empty(self, animation_manager):
        """AnimationManager._restore_prefs handles empty prefs."""
        prefs = MagicMock()
        prefs.layers = None
        animation_manager._restore_prefs(prefs)  # Should not raise

    def test_restore_prefs_with_layers(self, animation_manager):
        """AnimationManager._restore_prefs adds renderers from prefs."""
        prefs = MagicMock()
        prefs.layers = OrderedDict({"test.Renderer": {"speed": 1.0}})

        with patch.object(animation_manager, "add_renderer") as mock_add:
            animation_manager._restore_prefs(prefs)
            mock_add.assert_called_once_with("test.Renderer", {"speed": 1.0})


# ─────────────────────────────────────────────────────────────────────────────
# Discover Renderers Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDiscoverRenderers:
    """Tests for renderer discovery."""

    def test_discover_returns_ordered_dict(self, mock_driver):
        """_discover_renderers returns OrderedDict."""
        from uchroma.server.anim import AnimationManager

        mock_driver.frame_control = MagicMock()
        with patch("uchroma.server.anim.entry_points") as mock_eps:
            mock_eps.return_value = MagicMock()
            mock_eps.return_value.select = MagicMock(return_value=[])

            # Clear any existing subclasses
            with patch.object(Renderer, "__subclasses__", return_value=[]):
                mgr = AnimationManager(mock_driver)
                assert isinstance(mgr._renderer_info, (OrderedDict, dict))
