#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.renderer module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uchroma.blending import BlendOp
from uchroma.layer import Layer
from uchroma.renderer import (
    DEFAULT_FPS,
    MAX_FPS,
    NUM_BUFFERS,
    Renderer,
    RendererMeta,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_driver():
    """Create a mock driver for Renderer testing."""
    driver = MagicMock()
    driver.width = 22
    driver.height = 6
    driver.input_manager = None
    return driver


@pytest.fixture
def mock_driver_with_input():
    """Create a mock driver with input manager."""
    driver = MagicMock()
    driver.width = 22
    driver.height = 6
    driver.input_manager = MagicMock()
    return driver


@pytest.fixture
def mock_frame():
    """Create a mock frame for testing."""
    frame = MagicMock()
    frame.width = 22
    frame.height = 6
    return frame


class ConcreteRenderer(Renderer):
    """Concrete implementation for testing."""

    meta = RendererMeta("Test", "Test renderer", "Test Author", "1.0")

    def __init__(self, driver, draw_result=True, **kwargs):
        super().__init__(driver, **kwargs)
        self._draw_result = draw_result
        self._draw_called = False
        self._draw_count = 0

    def init(self, frame) -> bool:
        return True

    async def draw(self, layer: Layer, timestamp: float) -> bool:
        self._draw_called = True
        self._draw_count += 1
        return self._draw_result


@pytest.fixture
def renderer(mock_driver):
    """Create a ConcreteRenderer for testing."""
    return ConcreteRenderer(mock_driver)


@pytest.fixture
def renderer_with_input(mock_driver_with_input):
    """Create a ConcreteRenderer with input support."""
    with patch("uchroma.renderer.InputQueue") as mock_input_queue:
        mock_queue = MagicMock()
        mock_queue.expire_time = 0.0
        mock_input_queue.return_value = mock_queue
        return ConcreteRenderer(mock_driver_with_input)


# ─────────────────────────────────────────────────────────────────────────────
# RendererMeta Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererMeta:
    """Tests for RendererMeta namedtuple."""

    def test_renderer_meta_fields(self):
        """RendererMeta has correct fields."""
        meta = RendererMeta("Name", "Desc", "Author", "1.0")
        assert meta.display_name == "Name"
        assert meta.description == "Desc"
        assert meta.author == "Author"
        assert meta.version == "1.0"

    def test_renderer_meta_is_tuple(self):
        """RendererMeta is a NamedTuple."""
        meta = RendererMeta("A", "B", "C", "D")
        assert isinstance(meta, tuple)
        assert len(meta) == 4

    def test_renderer_meta_immutable(self):
        """RendererMeta is immutable."""
        meta = RendererMeta("A", "B", "C", "D")
        with pytest.raises(AttributeError):
            meta.display_name = "Changed"


# ─────────────────────────────────────────────────────────────────────────────
# Constants Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererConstants:
    """Tests for renderer module constants."""

    def test_max_fps_value(self):
        """MAX_FPS constant value."""
        assert MAX_FPS == 30

    def test_default_fps_value(self):
        """DEFAULT_FPS constant value."""
        assert DEFAULT_FPS == 15

    def test_num_buffers_value(self):
        """NUM_BUFFERS constant value."""
        assert NUM_BUFFERS == 2


# ─────────────────────────────────────────────────────────────────────────────
# Renderer Init Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererInit:
    """Tests for Renderer initialization."""

    def test_init_sets_width_from_driver(self, renderer):
        """Renderer width comes from driver."""
        assert renderer.width == 22

    def test_init_sets_height_from_driver(self, renderer):
        """Renderer height comes from driver."""
        assert renderer.height == 6

    def test_init_running_is_false(self, renderer):
        """Renderer starts not running."""
        assert renderer.running is False

    def test_init_zindex_default(self, renderer):
        """Renderer zindex defaults to -1."""
        assert renderer.zindex == -1

    def test_init_creates_queues(self, renderer):
        """Renderer creates available and active queues."""
        assert hasattr(renderer, "_avail_q")
        assert hasattr(renderer, "_active_q")
        assert renderer._avail_q.maxsize == NUM_BUFFERS
        assert renderer._active_q.maxsize == NUM_BUFFERS

    def test_init_creates_ticker(self, renderer):
        """Renderer creates Ticker with default fps."""
        assert hasattr(renderer, "_tick")
        assert renderer._tick.interval == pytest.approx(1 / DEFAULT_FPS)

    def test_init_no_input_queue_without_input_manager(self, renderer):
        """Renderer has no input queue when driver lacks input_manager."""
        assert renderer._input_queue is None

    def test_init_creates_input_queue_with_input_manager(self, mock_driver_with_input):
        """Renderer creates input queue when driver has input_manager."""
        with patch("uchroma.renderer.InputQueue") as mock_input_queue:
            mock_queue = MagicMock()
            mock_input_queue.return_value = mock_queue
            r = ConcreteRenderer(mock_driver_with_input)
            assert r._input_queue is mock_queue


# ─────────────────────────────────────────────────────────────────────────────
# Renderer Traits Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererTraits:
    """Tests for Renderer traits."""

    def test_fps_default(self, renderer):
        """fps defaults to DEFAULT_FPS."""
        assert renderer.fps == DEFAULT_FPS

    def test_fps_can_be_set(self, renderer):
        """fps trait can be modified."""
        renderer.fps = 20.0
        assert renderer.fps == 20.0

    def test_blend_mode_default(self, renderer):
        """blend_mode defaults to 'screen'."""
        assert renderer.blend_mode == "screen"

    def test_blend_mode_can_be_set(self, renderer):
        """blend_mode trait can be modified."""
        renderer.blend_mode = "multiply"
        assert renderer.blend_mode == "multiply"

    def test_blend_mode_valid_values(self, renderer):
        """blend_mode accepts valid BlendOp modes."""
        for mode in BlendOp.get_modes():
            renderer.blend_mode = mode
            assert renderer.blend_mode == mode

    def test_opacity_default(self, renderer):
        """opacity defaults to 1.0."""
        assert renderer.opacity == 1.0

    def test_opacity_can_be_set(self, renderer):
        """opacity trait can be modified."""
        renderer.opacity = 0.5
        assert renderer.opacity == 0.5

    def test_background_color_default(self, renderer):
        """background_color defaults to black."""
        # ColorTrait defaults to black, not None
        assert renderer.background_color is not None


# ─────────────────────────────────────────────────────────────────────────────
# Renderer Properties Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererProperties:
    """Tests for Renderer properties."""

    def test_has_key_input_false_without_input_queue(self, renderer):
        """has_key_input is False without input queue."""
        assert renderer.has_key_input is False

    def test_has_key_input_true_with_input_queue(self, renderer_with_input):
        """has_key_input is True with input queue."""
        assert renderer_with_input.has_key_input is True

    def test_key_expire_time_zero_without_input(self, renderer):
        """key_expire_time is 0.0 without input queue."""
        assert renderer.key_expire_time == 0.0

    def test_key_expire_time_from_input_queue(self, renderer_with_input):
        """key_expire_time comes from input queue."""
        renderer_with_input._input_queue.expire_time = 5.0
        assert renderer_with_input.key_expire_time == 5.0

    def test_key_expire_time_setter_noop_without_input(self, renderer):
        """Setting key_expire_time is noop without input queue."""
        renderer.key_expire_time = 10.0  # Should not raise
        assert renderer.key_expire_time == 0.0

    def test_key_expire_time_setter_with_input(self, renderer_with_input):
        """Setting key_expire_time updates input queue."""
        renderer_with_input.key_expire_time = 3.0
        assert renderer_with_input._input_queue.expire_time == 3.0

    def test_logger_property(self, renderer):
        """logger property returns the logger instance."""
        assert renderer.logger is renderer._logger


# ─────────────────────────────────────────────────────────────────────────────
# Observer Methods Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererObservers:
    """Tests for Renderer observer methods."""

    def test_fps_changed_updates_ticker(self, renderer):
        """Changing fps updates ticker interval."""
        renderer.fps = 30.0
        assert renderer._tick.interval == pytest.approx(1 / 30.0)

    def test_fps_changed_to_low_value(self, renderer):
        """Changing fps to low value works."""
        renderer.fps = 1.0
        assert renderer._tick.interval == pytest.approx(1.0)

    def test_zindex_changed_updates_logger(self, renderer):
        """Changing zindex updates logger name."""
        old_logger = renderer._logger
        renderer.zindex = 5
        # Logger should be different (new instance with different name)
        assert renderer._logger is not old_logger

    def test_zindex_same_value_no_change(self, renderer):
        """Setting zindex to same positive value doesn't change logger."""
        renderer.zindex = 3
        logger_after_first = renderer._logger
        renderer.zindex = 3  # Same value
        # For positive same values, should skip
        assert renderer._logger is logger_after_first


# ─────────────────────────────────────────────────────────────────────────────
# Init/Finish Method Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererInitFinish:
    """Tests for init and finish methods."""

    def test_base_init_returns_false(self, mock_driver, mock_frame):
        """Base Renderer.init returns False."""

        class BaseRenderer(Renderer):
            async def draw(self, layer, timestamp):
                return False

        r = BaseRenderer(mock_driver)
        assert r.init(mock_frame) is False

    def test_concrete_init_returns_true(self, renderer, mock_frame):
        """ConcreteRenderer.init returns True."""
        assert renderer.init(mock_frame) is True

    def test_finish_method_exists(self, renderer, mock_frame):
        """finish method can be called without error."""
        renderer.finish(mock_frame)  # Should not raise


# ─────────────────────────────────────────────────────────────────────────────
# Queue Management Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererQueueManagement:
    """Tests for queue management methods."""

    def test_free_layer_clears_and_queues(self, renderer):
        """_free_layer clears layer and returns to queue."""
        layer = MagicMock()
        renderer._free_layer(layer)

        layer.lock.assert_called_once_with(False)
        layer.clear.assert_called_once()
        assert renderer._avail_q.qsize() == 1

    def test_flush_clears_queues_when_not_running(self, renderer):
        """_flush clears queues when not running."""
        # Add items to queues
        renderer._avail_q.put_nowait(MagicMock())
        renderer._active_q.put_nowait(MagicMock())

        assert renderer._avail_q.qsize() == 1
        assert renderer._active_q.qsize() == 1

        renderer._flush()

        assert renderer._avail_q.qsize() == 0
        assert renderer._active_q.qsize() == 0

    def test_flush_noop_when_running(self, renderer):
        """_flush is noop when running."""
        renderer._avail_q.put_nowait(MagicMock())
        renderer.running = True

        renderer._flush()

        assert renderer._avail_q.qsize() == 1  # Not flushed


# ─────────────────────────────────────────────────────────────────────────────
# Async Methods Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererAsync:
    """Tests for async methods."""

    def test_stop_sets_running_false(self, renderer):
        """_stop sets running to False."""

        async def run_test():
            renderer.running = True
            await renderer._stop()
            return renderer.running

        result = asyncio.run(run_test())
        assert result is False

    def test_stop_flushes_queues(self, renderer):
        """_stop flushes queues."""

        async def run_test():
            renderer.running = True
            renderer._avail_q.put_nowait(MagicMock())
            await renderer._stop()
            return renderer._avail_q.qsize()

        size = asyncio.run(run_test())
        assert size == 0

    def test_stop_noop_when_not_running(self, renderer):
        """_stop is noop when not running."""

        async def run_test():
            renderer.running = False
            await renderer._stop()  # Should not raise

        asyncio.run(run_test())

    def test_stop_detaches_input_queue(self, renderer_with_input):
        """_stop detaches input queue if present."""

        async def run_test():
            renderer_with_input.running = True
            renderer_with_input._input_queue.detach = AsyncMock()
            await renderer_with_input._stop()
            return renderer_with_input._input_queue.detach.called

        called = asyncio.run(run_test())
        assert called

    def test_run_sets_running_true(self, renderer):
        """_run sets running to True."""

        async def run_test():
            # Add a buffer so it doesn't block forever
            layer = MagicMock()
            renderer._avail_q.put_nowait(layer)

            # Run briefly then stop
            async def stop_after_draw():
                await asyncio.sleep(0.01)
                renderer.running = False

            await asyncio.gather(renderer._run(), stop_after_draw())
            return renderer._draw_called

        result = asyncio.run(run_test())
        assert result

    def test_run_noop_if_already_running(self, renderer):
        """_run returns immediately if already running."""

        async def run_test():
            renderer.running = True
            await renderer._run()  # Should return without doing anything
            return renderer._draw_called

        result = asyncio.run(run_test())
        assert result is False

    def test_run_applies_traits_to_layer(self, renderer):
        """_run applies renderer traits to layer."""

        async def run_test():
            renderer.background_color = "red"
            renderer.blend_mode = "multiply"
            renderer.opacity = 0.5

            layer = MagicMock()
            renderer._avail_q.put_nowait(layer)

            async def stop_after_draw():
                await asyncio.sleep(0.01)
                renderer.running = False

            await asyncio.gather(renderer._run(), stop_after_draw())
            return layer

        layer = asyncio.run(run_test())
        assert layer.blend_mode == "multiply"
        assert layer.opacity == 0.5

    def test_run_locks_and_queues_layer_on_success(self, renderer):
        """_run locks layer and puts in active queue on draw success."""

        async def run_test():
            layer = MagicMock()
            renderer._avail_q.put_nowait(layer)
            renderer._draw_result = True

            async def stop_after_draw():
                await asyncio.sleep(0.01)
                renderer.running = False

            await asyncio.gather(renderer._run(), stop_after_draw())
            return layer, renderer._active_q.qsize()

        layer, qsize = asyncio.run(run_test())
        layer.lock.assert_called_with(True)
        assert qsize == 1

    def test_run_handles_draw_exception(self, mock_driver):
        """_run handles exceptions in draw gracefully."""

        class ErrorRenderer(Renderer):
            meta = RendererMeta("Error", "Raises error", "Test", "1.0")

            async def draw(self, layer, timestamp):
                raise RuntimeError("Draw failed")

        async def run_test():
            renderer = ErrorRenderer(mock_driver)
            layer = MagicMock()
            renderer._avail_q.put_nowait(layer)

            # Should not raise, but should stop
            await renderer._run()
            return renderer.running

        result = asyncio.run(run_test())
        assert result is False

    def test_get_input_events_raises_without_input(self, renderer):
        """get_input_events raises ValueError without input support."""

        async def run_test():
            await renderer.get_input_events()

        with pytest.raises(ValueError, match="not supported"):
            asyncio.run(run_test())

    def test_get_input_events_with_input(self, renderer_with_input):
        """get_input_events returns events from input queue."""

        async def run_test():
            mock_events = [MagicMock(), MagicMock()]
            renderer_with_input._input_queue.attach.return_value = True
            renderer_with_input._input_queue.get_events = AsyncMock(return_value=mock_events)

            events = await renderer_with_input.get_input_events()
            return events, mock_events

        events, mock_events = asyncio.run(run_test())
        assert events == mock_events

    def test_get_input_events_raises_on_attach_failure(self, renderer_with_input):
        """get_input_events raises when attach fails."""

        async def run_test():
            renderer_with_input._input_queue.attach.return_value = False
            await renderer_with_input.get_input_events()

        with pytest.raises(ValueError, match="not supported"):
            asyncio.run(run_test())


# ─────────────────────────────────────────────────────────────────────────────
# Meta Property Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRendererMetaProperty:
    """Tests for Renderer.meta class attribute."""

    def test_default_meta(self, mock_driver):
        """Base Renderer has default meta."""

        class MinimalRenderer(Renderer):
            async def draw(self, layer, timestamp):
                return False

        r = MinimalRenderer(mock_driver)
        assert r.meta.display_name == "_unknown_"

    def test_custom_meta(self, renderer):
        """ConcreteRenderer has custom meta."""
        assert renderer.meta.display_name == "Test"
        assert renderer.meta.author == "Test Author"
