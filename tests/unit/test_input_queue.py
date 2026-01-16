#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.input_queue module."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from uchroma.input_queue import InputQueue, KeyInputEvent

# ─────────────────────────────────────────────────────────────────────────────
# KeyInputEvent Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyInputEvent:
    """Tests for KeyInputEvent class."""

    def test_create_event(self):
        """KeyInputEvent can be created with all fields."""
        now = time.time()
        event = KeyInputEvent(
            timestamp=now,
            expire_time=now + 1.0,
            keycode="KEY_A",
            scancode="30",
            keystate=1,
            coords=[[0, 0]],
            data={},
        )
        assert event.keycode == "KEY_A"
        assert event.scancode == "30"
        assert event.keystate == 1
        assert event.coords == [[0, 0]]

    def test_time_remaining_positive(self):
        """time_remaining returns positive when not expired."""
        now = time.time()
        event = KeyInputEvent(
            timestamp=now,
            expire_time=now + 10.0,  # 10 seconds in future
            keycode="KEY_A",
            scancode="30",
            keystate=1,
            coords=None,
            data={},
        )
        assert event.time_remaining > 0
        assert event.time_remaining <= 10.0

    def test_time_remaining_zero_when_expired(self):
        """time_remaining returns 0 when expired."""
        now = time.time()
        event = KeyInputEvent(
            timestamp=now - 2.0,
            expire_time=now - 1.0,  # Already expired
            keycode="KEY_A",
            scancode="30",
            keystate=1,
            coords=None,
            data={},
        )
        assert event.time_remaining == 0.0

    def test_percent_complete_midway(self):
        """percent_complete returns ~0.5 when half expired."""
        now = time.time()
        # Create event that started 0.5s ago, expires in 0.5s
        event = KeyInputEvent(
            timestamp=now - 0.5,
            expire_time=now + 0.5,
            keycode="KEY_A",
            scancode="30",
            keystate=1,
            coords=None,
            data={},
        )
        # Should be around 0.5 (50%)
        assert 0.4 <= event.percent_complete <= 0.6

    def test_percent_complete_clamped(self):
        """percent_complete is clamped to 0-1 range."""
        now = time.time()
        # Expired event
        event = KeyInputEvent(
            timestamp=now - 2.0,
            expire_time=now - 1.0,
            keycode="KEY_A",
            scancode="30",
            keystate=1,
            coords=None,
            data={},
        )
        assert event.percent_complete == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_driver():
    """Create a mock driver for InputQueue testing."""
    driver = MagicMock()
    driver.logger = MagicMock()
    driver.logger.isEnabledFor.return_value = False
    driver.input_manager = MagicMock()
    driver.input_manager.add_callback = MagicMock(return_value=True)
    driver.input_manager.remove_callback = AsyncMock()
    driver.hardware = MagicMock()
    driver.hardware.key_mapping = {"KEY_A": [[0, 1]], "KEY_B": [[0, 2]]}
    return driver


@pytest.fixture
def mock_driver_no_input():
    """Create a mock driver without input manager."""
    driver = MagicMock()
    driver.logger = MagicMock()
    driver.input_manager = None
    driver.hardware = MagicMock()
    driver.hardware.key_mapping = None
    return driver


@pytest.fixture
def input_queue(mock_driver):
    """Create an InputQueue for testing."""
    return InputQueue(mock_driver, expire_time=1.0)


@pytest.fixture
def input_queue_no_expire(mock_driver):
    """Create an InputQueue without expiration."""
    return InputQueue(mock_driver, expire_time=None)


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue Init Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueInit:
    """Tests for InputQueue initialization."""

    def test_init_with_expire_time(self, mock_driver):
        """InputQueue initializes with expire_time."""
        queue = InputQueue(mock_driver, expire_time=2.0)
        assert queue.expire_time == 2.0

    def test_init_without_expire_time(self, mock_driver):
        """InputQueue initializes without expire_time."""
        queue = InputQueue(mock_driver, expire_time=None)
        assert queue.expire_time == 0

    def test_init_default_keystate(self, input_queue):
        """InputQueue defaults to KEY_DOWN only."""
        assert input_queue.keystates == InputQueue.KEY_DOWN

    def test_init_not_attached(self, input_queue):
        """InputQueue starts not attached."""
        assert input_queue._attached is False


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue Constants Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueConstants:
    """Tests for InputQueue constants."""

    def test_key_up_constant(self):
        """KEY_UP constant is defined."""
        assert InputQueue.KEY_UP == 1

    def test_key_down_constant(self):
        """KEY_DOWN constant is defined."""
        assert InputQueue.KEY_DOWN == 2

    def test_key_hold_constant(self):
        """KEY_HOLD constant is defined."""
        assert InputQueue.KEY_HOLD == 4


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue Attach/Detach Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueAttach:
    """Tests for InputQueue attach/detach."""

    def test_attach_success(self, input_queue, mock_driver):
        """attach returns True on success."""
        result = input_queue.attach()
        assert result is True
        assert input_queue._attached is True
        mock_driver.input_manager.add_callback.assert_called_once()

    def test_attach_already_attached(self, input_queue):
        """attach returns True if already attached."""
        input_queue.attach()
        result = input_queue.attach()  # Second call
        assert result is True

    def test_attach_no_input_manager(self, mock_driver_no_input):
        """attach raises ValueError without input manager."""
        queue = InputQueue(mock_driver_no_input)
        with pytest.raises(ValueError, match="not supported"):
            queue.attach()

    def test_attach_callback_fails(self, input_queue, mock_driver):
        """attach returns False if callback registration fails."""
        mock_driver.input_manager.add_callback.return_value = False
        result = input_queue.attach()
        assert result is False

    def test_detach(self, input_queue, mock_driver):
        """detach removes callback and sets attached False."""

        async def run_test():
            input_queue.attach()
            await input_queue.detach()
            return input_queue._attached

        attached = asyncio.run(run_test())
        assert attached is False
        mock_driver.input_manager.remove_callback.assert_called_once()

    def test_detach_when_not_attached(self, input_queue):
        """detach is noop when not attached."""

        async def run_test():
            await input_queue.detach()  # Should not raise

        asyncio.run(run_test())


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue Keystates Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueKeystates:
    """Tests for InputQueue keystates property."""

    def test_keystates_getter(self, input_queue):
        """keystates getter returns current value."""
        assert input_queue.keystates == InputQueue.KEY_DOWN

    def test_keystates_setter(self, input_queue):
        """keystates setter updates value."""
        input_queue.keystates = InputQueue.KEY_UP | InputQueue.KEY_DOWN
        assert input_queue.keystates == InputQueue.KEY_UP | InputQueue.KEY_DOWN

    def test_keystates_all(self, input_queue):
        """keystates can be set to all types."""
        all_states = InputQueue.KEY_UP | InputQueue.KEY_DOWN | InputQueue.KEY_HOLD
        input_queue.keystates = all_states
        assert input_queue.keystates == all_states


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue Expire Time Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueExpireTime:
    """Tests for InputQueue expire_time property."""

    def test_expire_time_getter(self, input_queue):
        """expire_time getter returns current value."""
        assert input_queue.expire_time == 1.0

    def test_expire_time_setter(self, input_queue):
        """expire_time setter updates value."""
        input_queue.expire_time = 5.0
        assert input_queue.expire_time == 5.0


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue get_events_nowait Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueGetEventsNowait:
    """Tests for InputQueue.get_events_nowait method."""

    def test_get_events_nowait_empty(self, input_queue):
        """get_events_nowait returns empty list when no events."""
        result = input_queue.get_events_nowait()
        assert result == []

    def test_get_events_nowait_returns_copy(self, input_queue):
        """get_events_nowait returns a copy of the events list."""
        result1 = input_queue.get_events_nowait()
        result2 = input_queue.get_events_nowait()
        assert result1 is not result2


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue get_events Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueGetEvents:
    """Tests for InputQueue.get_events method."""

    def test_get_events_not_attached(self, input_queue, mock_driver):
        """get_events returns None if not attached."""

        async def run_test():
            return await input_queue.get_events()

        result = asyncio.run(run_test())
        assert result is None
        mock_driver.logger.error.assert_called()

    def test_get_events_no_expire_time(self, input_queue_no_expire):
        """get_events returns single event when no expire_time."""

        async def run_test():
            input_queue_no_expire.attach()
            # Simulate putting an event
            input_queue_no_expire._q.put_nowait("test_event")
            return await input_queue_no_expire.get_events()

        result = asyncio.run(run_test())
        assert result == "test_event"


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue _expire Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueExpire:
    """Tests for InputQueue._expire method."""

    def test_expire_removes_old_events(self, input_queue):
        """_expire removes expired events."""
        now = time.time()
        # Add expired event
        old_event = KeyInputEvent(
            timestamp=now - 2.0,
            expire_time=now - 1.0,  # Expired 1 second ago
            keycode="KEY_A",
            scancode="30",
            keystate=1,
            coords=None,
            data={},
        )
        # Add fresh event
        new_event = KeyInputEvent(
            timestamp=now,
            expire_time=now + 10.0,
            keycode="KEY_B",
            scancode="31",
            keystate=1,
            coords=None,
            data={},
        )
        input_queue._events = [old_event, new_event]

        input_queue._expire()

        assert len(input_queue._events) == 1
        assert input_queue._events[0].keycode == "KEY_B"

    def test_expire_noop_when_no_expire_time(self, input_queue):
        """_expire does nothing when expire_time is None."""
        input_queue._expire_time = None
        input_queue._events = ["should_stay"]

        input_queue._expire()

        assert input_queue._events == ["should_stay"]


# ─────────────────────────────────────────────────────────────────────────────
# InputQueue _input_callback Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInputQueueInputCallback:
    """Tests for InputQueue._input_callback method."""

    def test_input_callback_filters_key_up(self, input_queue):
        """_input_callback filters KEY_UP when not enabled."""

        async def run_test():
            mock_ev = MagicMock()
            mock_ev.keystate = mock_ev.key_up = 0  # KEY_UP
            mock_ev.key_down = 1
            mock_ev.key_hold = 2

            await input_queue._input_callback(mock_ev)
            return input_queue._q.qsize()

        size = asyncio.run(run_test())
        assert size == 0  # Should have filtered it

    def test_input_callback_accepts_key_down(self, input_queue):
        """_input_callback accepts KEY_DOWN when enabled."""

        async def run_test():
            mock_ev = MagicMock()
            mock_ev.keystate = mock_ev.key_down = 1  # KEY_DOWN
            mock_ev.key_up = 0
            mock_ev.key_hold = 2
            mock_ev.keycode = "KEY_A"
            mock_ev.scancode = "30"
            mock_ev.event = MagicMock()
            mock_ev.event.timestamp.return_value = time.time()

            await input_queue._input_callback(mock_ev)
            return input_queue._q.qsize()

        size = asyncio.run(run_test())
        assert size == 1

    def test_input_callback_with_key_mapping(self, input_queue):
        """_input_callback looks up key coords in mapping."""

        async def run_test():
            mock_ev = MagicMock()
            mock_ev.keystate = mock_ev.key_down = 1
            mock_ev.key_up = 0
            mock_ev.key_hold = 2
            mock_ev.keycode = "KEY_A"  # Has mapping
            mock_ev.scancode = "30"
            mock_ev.event = MagicMock()
            mock_ev.event.timestamp.return_value = time.time()

            await input_queue._input_callback(mock_ev)
            return input_queue._events[-1] if input_queue._events else None

        event = asyncio.run(run_test())
        assert event is not None
        assert event.coords == [[0, 1]]

    def test_input_callback_replaces_same_key(self, input_queue):
        """_input_callback replaces existing event for same key."""

        async def run_test():
            # Add first event
            mock_ev1 = MagicMock()
            mock_ev1.keystate = mock_ev1.key_down = 1
            mock_ev1.key_up = 0
            mock_ev1.key_hold = 2
            mock_ev1.keycode = "KEY_A"
            mock_ev1.scancode = "30"
            mock_ev1.event = MagicMock()
            mock_ev1.event.timestamp.return_value = time.time()

            await input_queue._input_callback(mock_ev1)
            assert len(input_queue._events) == 1

            # Add second event for same key
            mock_ev2 = MagicMock()
            mock_ev2.keystate = mock_ev2.key_down = 1
            mock_ev2.key_up = 0
            mock_ev2.key_hold = 2
            mock_ev2.keycode = "KEY_A"  # Same key
            mock_ev2.scancode = "30"
            mock_ev2.event = MagicMock()
            mock_ev2.event.timestamp.return_value = time.time() + 0.1

            await input_queue._input_callback(mock_ev2)
            return len(input_queue._events)

        count = asyncio.run(run_test())
        assert count == 1  # Should still be 1, replaced
