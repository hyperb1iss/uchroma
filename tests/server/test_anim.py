#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.anim module."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from types import MappingProxyType
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

    def test_stop_cancels_waiter_when_renderer_not_running(self, mock_frame, mock_renderer):
        """LayerHolder.stop cancels waiter task even when renderer is not running."""
        from uchroma.server.anim import LayerHolder

        mock_renderer.running = False
        holder = LayerHolder(mock_renderer, mock_frame)

        async def run_test():
            holder.waiter = asyncio.create_task(asyncio.sleep(10))
            await holder.stop()
            return holder.waiter.cancelled() and mock_renderer.finish.called

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

    def test_shutdown_awaits_loop_stop(self, animation_manager):
        """AnimationManager.shutdown awaits loop stop."""

        async def run_test():
            loop = MagicMock()
            loop.clear_layers = AsyncMock()
            loop.stop_async = AsyncMock()
            animation_manager._loop = loop

            await animation_manager.shutdown()

            loop.clear_layers.assert_awaited_once()
            loop.stop_async.assert_awaited_once()

        asyncio.run(run_test())

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

    def test_discover_returns_mapping_proxy(self, mock_driver):
        """_discover_renderers returns immutable MappingProxyType."""
        from uchroma.server.anim import AnimationManager

        mock_driver.frame_control = MagicMock()
        with patch("uchroma.server.anim.entry_points") as mock_eps:
            mock_eps.return_value = MagicMock()
            mock_eps.return_value.select = MagicMock(return_value=[])

            # Clear any existing subclasses
            with patch.object(Renderer, "__subclasses__", return_value=[]):
                mgr = AnimationManager(mock_driver)
                assert isinstance(mgr._renderer_info, MappingProxyType)


# ─────────────────────────────────────────────────────────────────────────────
# LayerHolder Trait Change Propagation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLayerHolderTraitPropagation:
    """Tests for LayerHolder trait change signal propagation."""

    @pytest.fixture
    def real_renderer(self, mock_frame):
        """Create a real renderer instance for trait testing."""
        from traitlets import Float

        from uchroma.renderer import Renderer, RendererMeta

        class TestRenderer(Renderer):
            meta = RendererMeta("Test", "Test renderer", "Test", "1.0")
            speed = Float(default_value=1.0).tag(config=True)

            def init(self, frame):
                return True

            async def draw(self, layer, timestamp):
                return True

        # Create a mock driver with required attributes
        mock_driver = MagicMock()
        mock_driver.width = 10
        mock_driver.height = 5
        mock_driver.input_manager = None

        return TestRenderer(mock_driver)

    def test_traits_changed_ignored_before_start(self, mock_frame, real_renderer):
        """Trait changes are ignored before layer.start() is called."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(real_renderer, mock_frame)
        signal_received = []

        def on_traits_changed(*args):
            signal_received.append(args)

        holder.traits_changed.connect(on_traits_changed)

        # Change a trait before starting
        real_renderer.speed = 2.0

        # Signal should NOT have fired (not started yet)
        assert len(signal_received) == 0

    def test_traits_changed_fires_after_start(self, mock_frame, real_renderer):
        """Trait changes fire signal after layer.start() is called."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(real_renderer, mock_frame)
        signal_received = []

        def on_traits_changed(*args):
            signal_received.append(args)

        holder.traits_changed.connect(on_traits_changed)

        # Start the layer (but don't actually run the async task)
        holder._started = True

        # Change a trait after starting
        real_renderer.speed = 3.0

        # Signal should have fired
        assert len(signal_received) > 0
        # Check the signal contains expected data
        _zindex, _trait_values, change_name, _old_value = signal_received[-1]
        assert change_name == "speed"

    def test_started_flag_set_on_start(self, mock_frame, real_renderer):
        """_started flag is set when start() is called."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(real_renderer, mock_frame)
        assert holder._started is False

        with patch("uchroma.server.anim.ensure_future"):
            holder.start()

        assert holder._started is True

    def test_trait_values_returns_config_traits_only(self, mock_frame, real_renderer):
        """trait_values property returns only config=True traits."""
        from uchroma.server.anim import LayerHolder

        holder = LayerHolder(real_renderer, mock_frame)

        # Set values
        real_renderer.speed = 2.5
        real_renderer.running = True  # Not config=True
        real_renderer.zindex = 5  # Not config=True

        trait_values = holder.trait_values

        # Should include config traits
        assert "speed" in trait_values
        # Should NOT include runtime state
        assert "running" not in trait_values
        assert "zindex" not in trait_values


# ─────────────────────────────────────────────────────────────────────────────
# End-to-End Preference Persistence Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPreferencePersistence:
    """Tests for end-to-end trait change to preference persistence."""

    @pytest.fixture
    def mock_frame_with_driver(self):
        """Create a mock frame with a real-ish driver for prefs testing."""
        frame = MagicMock()
        frame._driver = MagicMock()
        frame._driver.logger = MagicMock()
        frame._driver.logger.isEnabledFor.return_value = False
        frame._driver.logger.debug = MagicMock()
        frame._driver.logger.info = MagicMock()
        frame.create_layer = MagicMock(return_value=MagicMock())
        frame.commit = MagicMock()
        return frame

    def test_update_prefs_saves_layer_traits(self, mock_driver, mock_frame_with_driver):
        """_update_prefs saves layer trait values to preferences."""
        from uchroma.server.anim import AnimationLoop, AnimationManager, LayerHolder

        # Setup
        mock_driver.frame_control = mock_frame_with_driver
        mock_driver.preferences = MagicMock()
        mock_driver.preferences.layers = None

        with patch.object(AnimationManager, "_discover_renderers", return_value=OrderedDict()):
            mgr = AnimationManager(mock_driver)

        # Create a loop with a mock layer
        mgr._loop = AnimationLoop(mock_frame_with_driver)

        mock_holder = MagicMock(spec=LayerHolder)
        mock_holder.type_string = "test.TestRenderer"
        mock_holder.trait_values = {"speed": 2.0, "opacity": 0.5}

        # Patch start() to avoid triggering async code when layers change
        with patch.object(mgr._loop, "start"):
            mgr._loop.layers = [mock_holder]

        # Call _update_prefs
        mgr._update_prefs()

        # Verify preferences were set
        assert mock_driver.preferences.layers is not None
        assert "test.TestRenderer" in mock_driver.preferences.layers
        assert mock_driver.preferences.layers["test.TestRenderer"]["speed"] == 2.0

    def test_loop_layers_changed_triggers_update_prefs(self, mock_driver, mock_frame_with_driver):
        """_loop_layers_changed triggers _update_prefs on modify."""
        from uchroma.server.anim import AnimationManager

        mock_driver.frame_control = mock_frame_with_driver
        mock_driver.preferences = MagicMock()

        with patch.object(AnimationManager, "_discover_renderers", return_value=OrderedDict()):
            mgr = AnimationManager(mock_driver)

        with patch.object(mgr, "_update_prefs") as mock_update:
            # Simulate a "modify" event (trait change)
            mgr._loop_layers_changed("modify", 0, {"speed": 2.0}, "speed", 1.0)
            mock_update.assert_called_once()

    def test_loop_layers_changed_skips_on_error(self, mock_driver, mock_frame_with_driver):
        """_loop_layers_changed skips _update_prefs when error=True."""
        from uchroma.server.anim import AnimationManager

        mock_driver.frame_control = mock_frame_with_driver

        with patch.object(AnimationManager, "_discover_renderers", return_value=OrderedDict()):
            mgr = AnimationManager(mock_driver)

        with patch.object(mgr, "_update_prefs") as mock_update:
            # Simulate event with error flag
            mgr._loop_layers_changed("modify", 0, {}, "speed", 1.0, error=True)
            mock_update.assert_not_called()
