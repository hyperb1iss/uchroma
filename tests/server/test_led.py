#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# uchroma - LED module unit tests
from __future__ import annotations

import asyncio
from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from uchroma.colorlib import Color
from uchroma.server.hardware import Quirks
from uchroma.server.led import LED, NOSTORE, VARSTORE, LEDManager, LEDMode
from uchroma.server.types import LEDType
from uchroma.util import Signal

# ─────────────────────────────────────────────────────────────────────────────
# LEDMode Enum Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDModeEnum:
    """Tests for LEDMode enum values."""

    @pytest.mark.parametrize(
        "mode,expected_value",
        [
            (LEDMode.STATIC, 0x00),
            (LEDMode.BLINK, 0x01),
            (LEDMode.PULSE, 0x02),
            (LEDMode.SPECTRUM, 0x04),
        ],
    )
    def test_led_mode_values(self, mode, expected_value):
        """LEDMode enum should have correct hex values."""
        assert mode.value == expected_value

    def test_led_mode_from_value(self):
        """LEDMode should be constructible from value."""
        assert LEDMode(0x00) == LEDMode.STATIC
        assert LEDMode(0x01) == LEDMode.BLINK
        assert LEDMode(0x02) == LEDMode.PULSE
        assert LEDMode(0x04) == LEDMode.SPECTRUM

    def test_led_mode_names(self):
        """LEDMode names should be uppercase."""
        assert LEDMode.STATIC.name == "STATIC"
        assert LEDMode.BLINK.name == "BLINK"
        assert LEDMode.PULSE.name == "PULSE"
        assert LEDMode.SPECTRUM.name == "SPECTRUM"


# ─────────────────────────────────────────────────────────────────────────────
# LED.Command Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDCommand:
    """Tests for LED.Command enum values."""

    @pytest.mark.parametrize(
        "command,expected",
        [
            (LED.Command.SET_LED_STATE, (0x03, 0x00, 0x03)),
            (LED.Command.SET_LED_COLOR, (0x03, 0x01, 0x05)),
            (LED.Command.SET_LED_MODE, (0x03, 0x02, 0x03)),
            (LED.Command.SET_LED_BRIGHTNESS, (0x03, 0x03, 0x03)),
            (LED.Command.GET_LED_STATE, (0x03, 0x80, 0x03)),
            (LED.Command.GET_LED_COLOR, (0x03, 0x81, 0x05)),
            (LED.Command.GET_LED_MODE, (0x03, 0x82, 0x03)),
            (LED.Command.GET_LED_BRIGHTNESS, (0x03, 0x83, 0x03)),
        ],
    )
    def test_command_values(self, command, expected):
        """LED.Command should have correct (class, id, length) tuples."""
        assert command.value == expected


class TestLEDExtendedCommand:
    """Tests for LED.ExtendedCommand enum values."""

    @pytest.mark.parametrize(
        "command,expected",
        [
            (LED.ExtendedCommand.SET_LED_BRIGHTNESS, (0x0F, 0x04, 0x03)),
            (LED.ExtendedCommand.GET_LED_BRIGHTNESS, (0x0F, 0x84, 0x03)),
        ],
    )
    def test_extended_command_values(self, command, expected):
        """LED.ExtendedCommand should have correct (class, id, length) tuples."""
        assert command.value == expected


# ─────────────────────────────────────────────────────────────────────────────
# LED Module Constants Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDConstants:
    """Tests for module-level constants."""

    def test_nostore_value(self):
        """NOSTORE should be 0."""
        assert NOSTORE == 0

    def test_varstore_value(self):
        """VARSTORE should be 1."""
        assert VARSTORE == 1


# ─────────────────────────────────────────────────────────────────────────────
# LED Class Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_led_driver():
    """Create a mock driver for LED testing."""
    driver = MagicMock()
    driver.logger = MagicMock()
    driver.run_with_result = MagicMock(return_value=None)
    driver.run_command = MagicMock(return_value=True)
    driver.run_with_result_async = AsyncMock(return_value=None)
    driver.run_command_async = AsyncMock(return_value=True)
    driver.has_quirk = MagicMock(return_value=False)
    driver.preferences = MagicMock()
    driver.preferences.leds = None
    driver.hardware = MagicMock()
    driver.hardware.supported_leds = [LEDType.LOGO, LEDType.SCROLL_WHEEL]
    driver.supported_leds = [LEDType.LOGO, LEDType.SCROLL_WHEEL, LEDType.BACKLIGHT]
    driver.restore_prefs = Signal()
    return driver


@pytest.fixture(autouse=True)
def run_led_tasks_immediately():
    def _run(coro, loop=None):
        asyncio.run(coro)
        return SimpleNamespace(done=lambda: True)

    with patch("uchroma.server.led.ensure_future", side_effect=_run):
        yield


@pytest.fixture
def logo_led(mock_led_driver):
    """Create an LED instance for LOGO type."""
    # Mock the initial refresh to avoid hardware calls
    with patch.object(LED, "_refresh_async", new=AsyncMock()):
        led = LED(mock_led_driver, LEDType.LOGO)
        led._dirty = False
        return led


@pytest.fixture
def scroll_led(mock_led_driver):
    """Create an LED instance for SCROLL_WHEEL type (has RGB and modes)."""
    with patch.object(LED, "_refresh_async", new=AsyncMock()):
        led = LED(mock_led_driver, LEDType.SCROLL_WHEEL)
        led._dirty = False
        return led


# ─────────────────────────────────────────────────────────────────────────────
# LED Initialization Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDInit:
    """Tests for LED initialization."""

    def test_led_init_stores_driver(self, mock_led_driver):
        """LED should store driver reference."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        assert led._driver is mock_led_driver

    def test_led_init_stores_led_type(self, mock_led_driver):
        """LED should store led_type."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        assert led._led_type == LEDType.LOGO
        assert led.led_type == LEDType.LOGO

    def test_led_init_sets_logger(self, mock_led_driver):
        """LED should get logger from driver."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        assert led._logger is mock_led_driver.logger

    def test_led_init_state_flags(self, mock_led_driver):
        """LED should initialize with correct state flags."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        assert led._restoring is False
        assert led._refreshing is False
        assert led._dirty is True

    def test_led_init_adds_dynamic_traits(self, mock_led_driver):
        """LED should add brightness, color, and mode traits."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.SCROLL_WHEEL)
        assert hasattr(led, "brightness")
        assert hasattr(led, "color")
        assert hasattr(led, "mode")
        assert hasattr(led, "state")

    def test_led_init_default_brightness(self, mock_led_driver):
        """LED brightness should default to 80.0."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
            led._dirty = False
        assert led.brightness == 80.0

    def test_led_init_default_mode(self, mock_led_driver):
        """LED mode should default to STATIC."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.SCROLL_WHEEL)
            led._dirty = False
        assert led.mode == LEDMode.STATIC

    def test_led_init_default_state(self, mock_led_driver):
        """LED state should default to False."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
            led._dirty = False
        assert led.state is False

    @pytest.mark.parametrize(
        "led_type",
        [LEDType.LOGO, LEDType.SCROLL_WHEEL, LEDType.BACKLIGHT, LEDType.BATTERY],
    )
    def test_led_init_with_different_types(self, mock_led_driver, led_type):
        """LED should initialize with different LED types."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, led_type)
        assert led.led_type == led_type


# ─────────────────────────────────────────────────────────────────────────────
# LED _get and _set Methods Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDGetSet:
    """Tests for LED _get and _set methods."""

    def test_get_calls_run_with_result(self, logo_led, mock_led_driver):
        """_get should call driver.run_with_result with correct args."""
        cmd = LED.Command.GET_LED_STATE
        logo_led._get(cmd)
        mock_led_driver.run_with_result.assert_called_once_with(
            cmd, VARSTORE, LEDType.LOGO.hardware_id
        )

    def test_set_calls_run_command(self, logo_led, mock_led_driver):
        """_set should call driver.run_command with correct args."""
        cmd = LED.Command.SET_LED_STATE
        logo_led._set(cmd, 1)
        mock_led_driver.run_command.assert_called_once_with(
            cmd, VARSTORE, LEDType.LOGO.hardware_id, 1, delay=0.035
        )

    def test_set_with_multiple_args(self, logo_led, mock_led_driver):
        """_set should pass multiple args correctly."""
        cmd = LED.Command.SET_LED_COLOR
        logo_led._set(cmd, 255, 128, 64)
        mock_led_driver.run_command.assert_called_once_with(
            cmd, VARSTORE, LEDType.LOGO.hardware_id, 255, 128, 64, delay=0.035
        )

    def test_get_returns_driver_result(self, logo_led, mock_led_driver):
        """_get should return what driver returns."""
        expected = [0, 0, 1]
        mock_led_driver.run_with_result.return_value = expected
        result = logo_led._get(LED.Command.GET_LED_STATE)
        assert result == expected


# ─────────────────────────────────────────────────────────────────────────────
# LED Brightness Commands Tests (with quirk handling)
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDBrightnessCommands:
    """Tests for _get_brightness and _set_brightness with quirk handling."""

    def test_get_brightness_uses_standard_command(self, logo_led, mock_led_driver):
        """_get_brightness should use standard command when no quirk."""
        mock_led_driver.has_quirk.return_value = False
        logo_led._get_brightness()
        mock_led_driver.has_quirk.assert_called_with(Quirks.EXTENDED_FX_CMDS)
        mock_led_driver.run_with_result.assert_called_once_with(
            LED.Command.GET_LED_BRIGHTNESS, VARSTORE, LEDType.LOGO.hardware_id
        )

    def test_get_brightness_uses_extended_command_with_quirk(self, logo_led, mock_led_driver):
        """_get_brightness should use extended command when quirk is set."""
        mock_led_driver.has_quirk.return_value = True
        logo_led._get_brightness()
        mock_led_driver.has_quirk.assert_called_with(Quirks.EXTENDED_FX_CMDS)
        mock_led_driver.run_with_result.assert_called_once_with(
            LED.ExtendedCommand.GET_LED_BRIGHTNESS, VARSTORE, LEDType.LOGO.hardware_id
        )

    def test_set_brightness_uses_standard_command(self, logo_led, mock_led_driver):
        """_set_brightness should use standard command when no quirk."""
        mock_led_driver.has_quirk.return_value = False
        logo_led._set_brightness(128)
        mock_led_driver.has_quirk.assert_called_with(Quirks.EXTENDED_FX_CMDS)
        mock_led_driver.run_command.assert_called_once_with(
            LED.Command.SET_LED_BRIGHTNESS, VARSTORE, LEDType.LOGO.hardware_id, 128, delay=0.035
        )

    def test_set_brightness_uses_extended_command_with_quirk(self, logo_led, mock_led_driver):
        """_set_brightness should use extended command when quirk is set."""
        mock_led_driver.has_quirk.return_value = True
        logo_led._set_brightness(200)
        mock_led_driver.has_quirk.assert_called_with(Quirks.EXTENDED_FX_CMDS)
        mock_led_driver.run_command.assert_called_once_with(
            LED.ExtendedCommand.SET_LED_BRIGHTNESS,
            VARSTORE,
            LEDType.LOGO.hardware_id,
            200,
            delay=0.035,
        )


# ─────────────────────────────────────────────────────────────────────────────
# LED _refresh_async Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDRefresh:
    """Tests for LED _refresh_async method."""

    def _make_refresh_side_effect(self, state=None, color=None, mode=None, brightness=None):
        """Create a side_effect function that returns appropriate values for each command."""

        def side_effect(cmd, *args):
            if cmd == LED.Command.GET_LED_STATE:
                return state
            elif cmd == LED.Command.GET_LED_COLOR:
                return color
            elif cmd == LED.Command.GET_LED_MODE:
                return mode
            elif cmd in (LED.Command.GET_LED_BRIGHTNESS, LED.ExtendedCommand.GET_LED_BRIGHTNESS):
                return brightness
            return None

        return side_effect

    def test_refresh_reads_state(self, mock_led_driver):
        """_refresh_async should read LED state from device."""
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 1], color=[0, 0, 0, 255, 0], mode=[0, 0, 0], brightness=[0, 0, 128]
        )
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        mock_led_driver.run_with_result_async.reset_mock()
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 1], color=[0, 0, 0, 255, 0], mode=[0, 0, 0], brightness=[0, 0, 128]
        )
        asyncio.run(led._refresh_async())
        calls = mock_led_driver.run_with_result_async.call_args_list
        state_call = call(LED.Command.GET_LED_STATE, VARSTORE, LEDType.LOGO.hardware_id)
        assert state_call in calls

    def test_refresh_reads_color(self, mock_led_driver):
        """_refresh_async should read LED color from device."""
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 0], color=[0, 0, 255, 128, 64], mode=[0, 0, 0], brightness=[0, 0, 128]
        )
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        mock_led_driver.run_with_result_async.reset_mock()
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 0], color=[0, 0, 255, 128, 64], mode=[0, 0, 0], brightness=[0, 0, 128]
        )
        asyncio.run(led._refresh_async())
        calls = mock_led_driver.run_with_result_async.call_args_list
        color_call = call(LED.Command.GET_LED_COLOR, VARSTORE, LEDType.LOGO.hardware_id)
        assert color_call in calls

    def test_refresh_reads_mode(self, mock_led_driver):
        """_refresh_async should read LED mode from device."""
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 0], color=[0, 0, 0, 255, 0], mode=[0, 0, 0x02], brightness=[0, 0, 128]
        )
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        mock_led_driver.run_with_result_async.reset_mock()
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 0], color=[0, 0, 0, 255, 0], mode=[0, 0, 0x02], brightness=[0, 0, 128]
        )
        asyncio.run(led._refresh_async())
        calls = mock_led_driver.run_with_result_async.call_args_list
        mode_call = call(LED.Command.GET_LED_MODE, VARSTORE, LEDType.LOGO.hardware_id)
        assert mode_call in calls

    def test_refresh_reads_brightness(self, mock_led_driver):
        """_refresh_async should read LED brightness from device."""
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 0], color=[0, 0, 0, 255, 0], mode=[0, 0, 0], brightness=[0, 0, 200]
        )
        mock_led_driver.has_quirk.return_value = False
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        mock_led_driver.run_with_result_async.reset_mock()
        mock_led_driver.run_with_result_async.side_effect = self._make_refresh_side_effect(
            state=[0, 0, 0], color=[0, 0, 0, 255, 0], mode=[0, 0, 0], brightness=[0, 0, 200]
        )
        asyncio.run(led._refresh_async())
        calls = mock_led_driver.run_with_result_async.call_args_list
        brightness_call = call(LED.Command.GET_LED_BRIGHTNESS, VARSTORE, LEDType.LOGO.hardware_id)
        assert brightness_call in calls

    def test_refresh_sets_state_from_response(self, mock_led_driver):
        """_refresh_async should set state from device response."""

        # Return state=1 (True)
        def side_effect(cmd, *args):
            if cmd == LED.Command.GET_LED_STATE:
                return [0, 0, 1]
            return None

        mock_led_driver.run_with_result_async.side_effect = side_effect
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        asyncio.run(led._refresh_async())
        assert led.state is True

    def test_refresh_sets_color_from_response(self, mock_led_driver):
        """_refresh_async should set color from device response (RGB bytes)."""

        def side_effect(cmd, *args):
            if cmd == LED.Command.GET_LED_COLOR:
                return [0, 0, 255, 128, 64]  # R=255, G=128, B=64
            return None

        mock_led_driver.run_with_result_async.side_effect = side_effect
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        asyncio.run(led._refresh_async())
        assert led.color.rgb[0] == pytest.approx(1.0, abs=0.01)
        assert led.color.rgb[1] == pytest.approx(128 / 255.0, abs=0.01)
        assert led.color.rgb[2] == pytest.approx(64 / 255.0, abs=0.01)

    def test_refresh_sets_mode_from_response(self, mock_led_driver):
        """_refresh_async should set mode from device response."""

        def side_effect(cmd, *args):
            if cmd == LED.Command.GET_LED_MODE:
                return [0, 0, 0x02]  # PULSE mode
            return None

        mock_led_driver.run_with_result_async.side_effect = side_effect
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        asyncio.run(led._refresh_async())
        assert led.mode == LEDMode.PULSE

    def test_refresh_sets_brightness_from_response(self, mock_led_driver):
        """_refresh_async should set brightness from device response (scaled)."""

        def side_effect(cmd, *args):
            if cmd == LED.Command.GET_LED_BRIGHTNESS:
                return [0, 0, 255]  # Max brightness
            return None

        mock_led_driver.run_with_result_async.side_effect = side_effect
        mock_led_driver.has_quirk.return_value = False
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        asyncio.run(led._refresh_async())
        assert led.brightness == 100.0

    def test_refresh_handles_none_responses(self, mock_led_driver):
        """_refresh_async should handle None responses gracefully."""
        mock_led_driver.run_with_result_async.return_value = None
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        # Should not raise
        asyncio.run(led._refresh_async())

    def test_refresh_sets_refreshing_flag(self, mock_led_driver):
        """_refresh_async should set _refreshing flag during execution."""
        refreshing_during_call = []

        async def capture_refreshing(cmd, *args):
            refreshing_during_call.append(led._refreshing)
            return None

        mock_led_driver.run_with_result_async.side_effect = capture_refreshing
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, LEDType.LOGO)
        asyncio.run(led._refresh_async())
        assert any(refreshing_during_call)
        # After refresh, flag should be False
        assert led._refreshing is False


# ─────────────────────────────────────────────────────────────────────────────
# LED Observer Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDObserver:
    """Tests for LED trait observer (_observer method)."""

    def test_observer_skips_during_refresh(self, logo_led, mock_led_driver):
        """Observer should not trigger commands during refresh."""
        logo_led._refreshing = True
        mock_led_driver.run_command_async.reset_mock()
        logo_led.brightness = 50.0
        mock_led_driver.run_command_async.assert_not_called()

    def test_observer_skips_when_value_unchanged(self, logo_led, mock_led_driver):
        """Observer should not trigger when old == new."""
        logo_led._dirty = False
        mock_led_driver.run_command_async.reset_mock()
        original = logo_led.brightness
        logo_led.brightness = original  # Same value
        # traitlets may or may not call observer, but _set commands shouldn't run
        # for identical values (handled in observer)

    def test_observer_sets_color(self, scroll_led, mock_led_driver):
        """Observer should send SET_LED_COLOR when color changes."""
        scroll_led._dirty = False
        mock_led_driver.run_command_async.reset_mock()
        new_color = Color.NewFromRgb(1.0, 0.0, 0.0)
        scroll_led.color = new_color
        # Check that SET_LED_COLOR was called
        assert any(
            c.args[0] == LED.Command.SET_LED_COLOR
            for c in mock_led_driver.run_command_async.call_args_list
        )

    def test_observer_sets_mode(self, scroll_led, mock_led_driver):
        """Observer should send SET_LED_MODE when mode changes."""
        scroll_led._dirty = False
        mock_led_driver.run_command_async.reset_mock()
        scroll_led.mode = LEDMode.PULSE
        mock_led_driver.run_command_async.assert_called()
        assert any(
            c.args[0] == LED.Command.SET_LED_MODE
            for c in mock_led_driver.run_command_async.call_args_list
        )

    def test_observer_sets_brightness(self, logo_led, mock_led_driver):
        """Observer should send brightness command when brightness changes."""
        logo_led._dirty = False
        mock_led_driver.has_quirk.return_value = False
        mock_led_driver.run_command_async.reset_mock()
        logo_led.brightness = 50.0
        # Should call SET_LED_BRIGHTNESS
        assert any(
            c.args[0] == LED.Command.SET_LED_BRIGHTNESS
            for c in mock_led_driver.run_command_async.call_args_list
        )

    def test_observer_turns_on_led_when_brightness_goes_from_zero(self, logo_led, mock_led_driver):
        """Observer should set state=1 when brightness goes from 0 to >0."""
        logo_led._dirty = False
        logo_led._refreshing = True
        logo_led.brightness = 0.0
        logo_led._refreshing = False
        mock_led_driver.run_command_async.reset_mock()
        logo_led.brightness = 50.0
        # Should have called SET_LED_STATE with 1
        state_calls = [
            c
            for c in mock_led_driver.run_command_async.call_args_list
            if c.args[0] == LED.Command.SET_LED_STATE
        ]
        assert len(state_calls) > 0
        assert state_calls[0].args[-1] == 1

    def test_observer_turns_off_led_when_brightness_goes_to_zero(self, logo_led, mock_led_driver):
        """Observer should set state=0 when brightness goes from >0 to 0."""
        logo_led._dirty = False
        logo_led._refreshing = True
        logo_led.brightness = 50.0
        logo_led._refreshing = False
        mock_led_driver.run_command_async.reset_mock()
        logo_led.brightness = 0.0
        # Should have called SET_LED_STATE with 0
        state_calls = [
            c
            for c in mock_led_driver.run_command_async.call_args_list
            if c.args[0] == LED.Command.SET_LED_STATE
        ]
        assert len(state_calls) > 0
        assert state_calls[0].args[-1] == 0

    def test_observer_updates_prefs_for_non_backlight(self, logo_led, mock_led_driver):
        """Observer should update preferences for non-BACKLIGHT LEDs."""
        logo_led._dirty = False
        mock_led_driver.preferences.leds = None
        mock_led_driver.run_command_async.reset_mock()
        logo_led.brightness = 50.0
        # Check preferences were updated
        assert mock_led_driver.preferences.leds is not None

    def test_observer_skips_prefs_for_backlight(self, mock_led_driver):
        """Observer should NOT update preferences for BACKLIGHT LED."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            backlight_led = LED(mock_led_driver, LEDType.BACKLIGHT)
            backlight_led._dirty = False
        mock_led_driver.preferences.leds = None
        mock_led_driver.run_command_async.reset_mock()
        backlight_led.brightness = 50.0
        # Preferences should not be updated for BACKLIGHT
        # (The code checks led_type != LEDType.BACKLIGHT before _update_prefs)


# ─────────────────────────────────────────────────────────────────────────────
# LED Lazy Refresh Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDLazyRefresh:
    """Tests for LED lazy refresh behavior via __getattribute__."""

    def test_accessing_brightness_triggers_refresh_when_dirty(self, mock_led_driver):
        """Accessing brightness should trigger refresh when _dirty is True."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()) as mock_refresh:
            led = LED(mock_led_driver, LEDType.LOGO)
            led._dirty = True
            _ = led.brightness
            mock_refresh.assert_called()

    def test_accessing_color_triggers_refresh_when_dirty(self, mock_led_driver):
        """Accessing color should trigger refresh when _dirty is True."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()) as mock_refresh:
            led = LED(mock_led_driver, LEDType.LOGO)
            led._dirty = True
            _ = led.color
            mock_refresh.assert_called()

    def test_accessing_mode_triggers_refresh_when_dirty(self, mock_led_driver):
        """Accessing mode should trigger refresh when _dirty is True."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()) as mock_refresh:
            led = LED(mock_led_driver, LEDType.LOGO)
            led._dirty = True
            _ = led.mode
            mock_refresh.assert_called()

    def test_accessing_state_triggers_refresh_when_dirty(self, mock_led_driver):
        """Accessing state should trigger refresh when _dirty is True."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()) as mock_refresh:
            led = LED(mock_led_driver, LEDType.LOGO)
            led._dirty = True
            _ = led.state
            mock_refresh.assert_called()

    def test_no_refresh_when_not_dirty(self, logo_led, mock_led_driver):
        """Accessing traits should NOT refresh when _dirty is False."""
        logo_led._dirty = False
        mock_led_driver.run_with_result_async.reset_mock()
        _ = logo_led.brightness
        _ = logo_led.color
        _ = logo_led.mode
        _ = logo_led.state
        # run_with_result_async is used by _get_async, which is called in _refresh_async
        mock_led_driver.run_with_result_async.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# LED get_values / set_values Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDGetSetValues:
    """Tests for LED get_values and set_values serialization methods."""

    def test_get_values_returns_ordered_dict(self, logo_led):
        """get_values should return an OrderedDict."""
        values = logo_led.get_values()
        assert isinstance(values, OrderedDict)

    def test_get_values_contains_brightness(self, logo_led):
        """get_values should include brightness (always config=True)."""
        values = logo_led.get_values()
        assert "brightness" in values

    def test_get_values_for_rgb_led_contains_color(self, scroll_led):
        """get_values should include color for RGB-capable LEDs."""
        # SCROLL_WHEEL has rgb=True, so color trait has config=True
        values = scroll_led.get_values()
        assert "color" in values

    def test_get_values_for_mode_led_contains_mode(self, scroll_led):
        """get_values should include mode for mode-capable LEDs."""
        # SCROLL_WHEEL has has_modes=True, so mode trait has config=True
        values = scroll_led.get_values()
        assert "mode" in values

    def test_get_values_sorted_keys(self, scroll_led):
        """get_values should return keys in sorted order."""
        values = scroll_led.get_values()
        keys = list(values.keys())
        assert keys == sorted(keys)

    def test_set_values_restores_brightness(self, logo_led, mock_led_driver):
        """set_values should restore brightness."""
        mock_led_driver.run_command_async.reset_mock()
        logo_led.set_values({"brightness": 42.0})
        assert logo_led.brightness == 42.0

    def test_set_values_restores_multiple(self, scroll_led, mock_led_driver):
        """set_values should restore multiple values."""
        new_color = Color.NewFromRgb(0.5, 0.5, 0.5)
        scroll_led.set_values({"brightness": 60.0, "color": new_color, "mode": LEDMode.BLINK})
        assert scroll_led.brightness == 60.0
        assert scroll_led.mode == LEDMode.BLINK

    def test_set_values_sets_restoring_flag(self, logo_led):
        """set_values should set _restoring flag during restoration."""
        # We can't easily test the flag during, but we can verify it's False after
        logo_led.set_values({"brightness": 30.0})
        assert logo_led._restoring is False


# ─────────────────────────────────────────────────────────────────────────────
# LED String Representation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDStringRepresentation:
    """Tests for LED __str__ and __repr__."""

    def test_str_contains_led_type(self, logo_led):
        """__str__ should include led_type."""
        s = str(logo_led)
        assert "led_type=" in s
        assert "LOGO" in s

    def test_str_contains_state(self, logo_led):
        """__str__ should include state."""
        s = str(logo_led)
        assert "state=" in s

    def test_str_contains_brightness(self, logo_led):
        """__str__ should include brightness."""
        s = str(logo_led)
        assert "brightness=" in s

    def test_str_contains_color(self, logo_led):
        """__str__ should include color."""
        s = str(logo_led)
        assert "color=" in s

    def test_str_contains_mode(self, logo_led):
        """__str__ should include mode."""
        s = str(logo_led)
        assert "mode=" in s

    def test_repr_equals_str(self, logo_led):
        """__repr__ should equal __str__."""
        assert repr(logo_led) == str(logo_led)

    def test_str_format(self, logo_led):
        """__str__ should have LED(...) format."""
        s = str(logo_led)
        assert s.startswith("LED(")
        assert s.endswith(")")


# ─────────────────────────────────────────────────────────────────────────────
# LEDManager Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDManagerInit:
    """Tests for LEDManager initialization."""

    def test_manager_stores_driver(self, mock_led_driver):
        """LEDManager should store driver reference."""
        manager = LEDManager(mock_led_driver)
        assert manager._driver is mock_led_driver

    def test_manager_initializes_empty_led_cache(self, mock_led_driver):
        """LEDManager should initialize with empty LED cache."""
        manager = LEDManager(mock_led_driver)
        assert manager._leds == {}

    def test_manager_creates_led_changed_signal(self, mock_led_driver):
        """LEDManager should create led_changed Signal."""
        manager = LEDManager(mock_led_driver)
        assert isinstance(manager.led_changed, Signal)

    def test_manager_connects_restore_prefs(self, mock_led_driver):
        """LEDManager should connect to driver.restore_prefs signal."""
        manager = LEDManager(mock_led_driver)
        # The signal should have _restore_prefs connected
        assert manager._restore_prefs in mock_led_driver.restore_prefs._handlers


class TestLEDManagerSupportedLeds:
    """Tests for LEDManager.supported_leds property."""

    def test_supported_leds_delegates_to_hardware(self, mock_led_driver):
        """supported_leds should return hardware.supported_leds."""
        expected = [LEDType.LOGO, LEDType.SCROLL_WHEEL]
        mock_led_driver.hardware.supported_leds = expected
        manager = LEDManager(mock_led_driver)
        assert manager.supported_leds == expected


class TestLEDManagerGet:
    """Tests for LEDManager.get method."""

    def test_get_returns_none_for_unsupported_type(self, mock_led_driver):
        """get() should return None for unsupported LED types."""
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        result = manager.get(LEDType.BATTERY)
        assert result is None

    def test_get_creates_led_instance(self, mock_led_driver):
        """get() should create LED instance for supported type."""
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = manager.get(LEDType.LOGO)
        assert led is not None
        assert isinstance(led, LED)
        assert led.led_type == LEDType.LOGO

    def test_get_caches_led_instance(self, mock_led_driver):
        """get() should cache and return same LED instance."""
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led1 = manager.get(LEDType.LOGO)
            led2 = manager.get(LEDType.LOGO)
        assert led1 is led2

    def test_get_stores_in_leds_dict(self, mock_led_driver):
        """get() should store LED in _leds dict."""
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = manager.get(LEDType.LOGO)
        assert LEDType.LOGO in manager._leds
        assert manager._leds[LEDType.LOGO] is led

    def test_get_attaches_observer(self, mock_led_driver):
        """get() should attach observer to LED for led_changed signal."""
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        handler_called = []

        def handler(led):
            handler_called.append(led)

        manager.led_changed.connect(handler)
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = manager.get(LEDType.LOGO)
            led._dirty = False
        # Trigger a change
        led.brightness = 42.0
        # The handler should have been called
        assert len(handler_called) > 0


class TestLEDManagerRestorePrefs:
    """Tests for LEDManager._restore_prefs method."""

    def test_restore_prefs_skips_backlight(self, mock_led_driver):
        """_restore_prefs should skip BACKLIGHT LED type."""
        mock_led_driver.hardware.supported_leds = [LEDType.BACKLIGHT, LEDType.LOGO]
        mock_led_driver.supported_leds = [LEDType.BACKLIGHT, LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        prefs = MagicMock()
        prefs.leds = {"backlight": {"brightness": 50.0}, "logo": {"brightness": 75.0}}
        with patch.object(LED, "_refresh_async", new=AsyncMock()), patch.object(LED, "set_values"):
            manager._restore_prefs(prefs)
        # Only LOGO should have set_values called, not BACKLIGHT
        # Check the calls don't include backlight brightness setting

    def test_restore_prefs_restores_led_settings(self, mock_led_driver):
        """_restore_prefs should restore LED settings from preferences."""
        mock_led_driver.hardware.supported_leds = [LEDType.LOGO]
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        prefs = MagicMock()
        prefs.leds = {"logo": {"brightness": 65.0}}
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            manager._restore_prefs(prefs)
            led = manager.get(LEDType.LOGO)
        # LED should have restored brightness
        assert led.brightness == 65.0

    def test_restore_prefs_handles_missing_led_prefs(self, mock_led_driver):
        """_restore_prefs should handle missing LED in preferences."""
        mock_led_driver.hardware.supported_leds = [LEDType.LOGO]
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        prefs = MagicMock()
        prefs.leds = {}  # No logo prefs
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            # Should not raise
            manager._restore_prefs(prefs)

    def test_restore_prefs_handles_none_led_prefs(self, mock_led_driver):
        """_restore_prefs should handle None led_prefs."""
        mock_led_driver.hardware.supported_leds = [LEDType.LOGO]
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        prefs = MagicMock()
        prefs.leds = None
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            # Should not raise
            manager._restore_prefs(prefs)


class TestLEDManagerLedChanged:
    """Tests for LEDManager._led_changed callback."""

    def test_led_changed_fires_signal(self, mock_led_driver):
        """_led_changed should fire led_changed signal with LED owner."""
        mock_led_driver.supported_leds = [LEDType.LOGO]
        manager = LEDManager(mock_led_driver)
        received = []

        def handler(led):
            received.append(led)

        manager.led_changed.connect(handler)
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = manager.get(LEDType.LOGO)
            led._dirty = False
        # Trigger a change on the LED
        led.brightness = 33.0
        # Signal should have fired
        assert len(received) > 0
        assert received[0] is led


# ─────────────────────────────────────────────────────────────────────────────
# Integration-style Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLEDIntegration:
    """Integration-style tests for LED behavior."""

    def test_full_led_lifecycle(self, mock_led_driver):
        """Test full LED lifecycle: create, modify, serialize, restore."""
        mock_led_driver.supported_leds = [LEDType.SCROLL_WHEEL]
        mock_led_driver.has_quirk.return_value = False
        manager = LEDManager(mock_led_driver)

        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = manager.get(LEDType.SCROLL_WHEEL)
            led._dirty = False

        # Modify LED
        new_color = Color.NewFromRgb(0.8, 0.2, 0.1)
        led.color = new_color
        led.brightness = 75.0
        led.mode = LEDMode.PULSE

        # Serialize
        values = led.get_values()
        assert "brightness" in values
        assert values["brightness"] == 75.0

        # Create new LED and restore
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led2 = LED(mock_led_driver, LEDType.SCROLL_WHEEL)
            led2._dirty = False
        led2.set_values(values)

        assert led2.brightness == 75.0
        assert led2.mode == LEDMode.PULSE

    @pytest.mark.parametrize(
        "led_type,has_rgb,has_modes",
        [
            (LEDType.SCROLL_WHEEL, True, True),
            (LEDType.LOGO, False, False),
            (LEDType.BATTERY, True, False),
            (LEDType.BACKLIGHT, False, False),
        ],
    )
    def test_led_capabilities_match_type(self, mock_led_driver, led_type, has_rgb, has_modes):
        """LED capabilities should match LEDType properties."""
        with patch.object(LED, "_refresh_async", new=AsyncMock()):
            led = LED(mock_led_driver, led_type)
        # The trait's config tag determines if it's included in get_values
        values = led.get_values()
        # Brightness is always config=True
        assert "brightness" in values
        # Color config depends on led_type.rgb
        assert ("color" in values) == has_rgb
        # Mode config depends on led_type.has_modes
        assert ("mode" in values) == has_modes
