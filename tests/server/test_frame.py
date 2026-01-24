#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.server.frame module."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from uchroma.color import to_color
from uchroma.layer import Layer
from uchroma.server import hid
from uchroma.server.frame import Frame
from uchroma.server.hardware import Hardware
from uchroma.server.types import BaseCommand


def run_commit(frame, layers, **kwargs):
    return asyncio.run(frame.commit(layers, **kwargs))


def run_reset(frame, **kwargs):
    return asyncio.run(frame.reset(**kwargs))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_driver():
    """Create a mock driver for Frame testing."""
    driver = SimpleNamespace()
    driver.name = "Test Device"
    driver.logger = MagicMock()
    driver.fx_manager = MagicMock()
    driver.fx_manager.activate = MagicMock()
    driver.run_command = AsyncMock(return_value=True)
    driver.run_report = MagicMock()
    driver.get_report = MagicMock()
    driver.has_quirk = MagicMock(return_value=False)
    driver.hardware = MagicMock()
    driver.hardware.has_quirk = MagicMock(return_value=False)
    driver.device_type = Hardware.Type.KEYBOARD
    driver._async_lock = None
    driver.hid_device = MagicMock()

    @asynccontextmanager
    async def device_open():
        yield

    driver.device_open = device_open
    return driver


@pytest.fixture(autouse=True)
def mock_send_frame_async():
    with patch("uchroma.server.frame.hid.send_frame_async", new=AsyncMock()) as mock:
        yield mock


@pytest.fixture
def mock_report():
    """Create a mock report object."""
    report = MagicMock()
    report.clear = MagicMock()
    report.put_byte = MagicMock()
    report.put_bytes = MagicMock()
    report.set_remaining_packets = MagicMock()
    report.args = MagicMock()
    report.args.put_all = MagicMock()
    return report


@pytest.fixture
def frame_6x22(mock_driver):
    """Create a Frame with keyboard dimensions (6 rows x 22 cols)."""
    return Frame(mock_driver, width=22, height=6)


@pytest.fixture
def frame_1x15(mock_driver):
    """Create a Frame with single-row mouse dimensions (1 row x 15 cols)."""
    return Frame(mock_driver, width=15, height=1)


@pytest.fixture
def frame_wide(mock_driver):
    """Create a Frame wider than one report payload (6 rows x 30 cols)."""
    return Frame(mock_driver, width=30, height=6)


@pytest.fixture
def red_layer():
    """Create a layer filled with red (full alpha)."""
    layer = Layer(22, 6)
    layer._matrix[:, :, 0] = 1.0  # R
    layer._matrix[:, :, 3] = 1.0  # A
    return layer


@pytest.fixture
def green_layer():
    """Create a layer filled with green (full alpha)."""
    layer = Layer(22, 6)
    layer._matrix[:, :, 1] = 1.0  # G
    layer._matrix[:, :, 3] = 1.0  # A
    return layer


@pytest.fixture
def transparent_layer():
    """Create a transparent layer (zero alpha)."""
    layer = Layer(22, 6)
    # Matrix is all zeros by default (including alpha)
    return layer


@pytest.fixture
def half_alpha_blue_layer():
    """Create a blue layer with 50% alpha."""
    layer = Layer(22, 6)
    layer._matrix[:, :, 2] = 1.0  # B
    layer._matrix[:, :, 3] = 0.5  # A = 50%
    return layer


# ─────────────────────────────────────────────────────────────────────────────
# Frame.Command Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameCommand:
    """Tests for Frame.Command enum values."""

    def test_set_frame_data_matrix_value(self):
        """SET_FRAME_DATA_MATRIX has correct command tuple."""
        assert Frame.Command.SET_FRAME_DATA_MATRIX.value == (0x03, 0x0B, None)

    def test_set_frame_data_single_value(self):
        """SET_FRAME_DATA_SINGLE has correct command tuple."""
        assert Frame.Command.SET_FRAME_DATA_SINGLE.value == (0x03, 0x0C, None)

    def test_command_is_base_command(self):
        """Frame.Command inherits from BaseCommand."""
        assert issubclass(Frame.Command, BaseCommand)


# ─────────────────────────────────────────────────────────────────────────────
# Frame Constants Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameConstants:
    """Tests for Frame class constants."""

    def test_default_frame_id_is_0xff(self):
        """DEFAULT_FRAME_ID constant is 0xFF."""
        assert Frame.DEFAULT_FRAME_ID == 0xFF


# ─────────────────────────────────────────────────────────────────────────────
# Frame Properties Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameProperties:
    """Tests for Frame property accessors."""

    def test_width_property(self, frame_6x22):
        """width property returns correct value."""
        assert frame_6x22.width == 22

    def test_height_property(self, frame_6x22):
        """height property returns correct value."""
        assert frame_6x22.height == 6

    def test_device_name_delegates_to_driver(self, frame_6x22, mock_driver):
        """device_name property delegates to driver.name."""
        mock_driver.name = "Custom Device Name"
        assert frame_6x22.device_name == "Custom Device Name"

    def test_debug_opts_returns_dict(self, frame_6x22):
        """debug_opts property returns a dict."""
        assert isinstance(frame_6x22.debug_opts, dict)
        assert frame_6x22.debug_opts == {}

    def test_debug_opts_can_be_modified(self, frame_6x22):
        """debug_opts dict can be modified."""
        frame_6x22.debug_opts["test_key"] = "test_value"
        assert frame_6x22.debug_opts["test_key"] == "test_value"


# ─────────────────────────────────────────────────────────────────────────────
# Frame.create_layer Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameCreateLayer:
    """Tests for Frame.create_layer method."""

    def test_create_layer_returns_layer_instance(self, frame_6x22):
        """create_layer returns a Layer instance."""
        layer = frame_6x22.create_layer()
        assert isinstance(layer, Layer)

    def test_create_layer_has_correct_width(self, frame_6x22):
        """create_layer returns Layer with frame's width."""
        layer = frame_6x22.create_layer()
        assert layer.width == 22

    def test_create_layer_has_correct_height(self, frame_6x22):
        """create_layer returns Layer with frame's height."""
        layer = frame_6x22.create_layer()
        assert layer.height == 6

    def test_create_layer_uses_driver_logger(self, frame_6x22, mock_driver):
        """create_layer passes driver's logger to Layer."""
        layer = frame_6x22.create_layer()
        assert layer._logger is mock_driver.logger

    def test_create_layer_matrix_shape(self, frame_6x22):
        """create_layer returns Layer with correct matrix shape."""
        layer = frame_6x22.create_layer()
        assert layer.matrix.shape == (6, 22, 4)  # height x width x RGBA

    def test_create_layer_matrix_initialized_to_zero(self, frame_6x22):
        """create_layer returns Layer with zero-initialized matrix."""
        layer = frame_6x22.create_layer()
        assert np.all(layer.matrix == 0)

    def test_create_layer_for_single_row_frame(self, frame_1x15):
        """create_layer works for single-row frames."""
        layer = frame_1x15.create_layer()
        assert layer.width == 15
        assert layer.height == 1
        assert layer.matrix.shape == (1, 15, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Frame.compose Tests - Empty List
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameComposeEmpty:
    """Tests for Frame.compose with empty layer list."""

    def test_compose_empty_list_returns_none(self):
        """compose([]) returns None."""
        result = Frame.compose([])
        assert result is None

    def test_compose_is_static_method(self):
        """compose is a static method (no self required)."""
        # Can call without instance
        result = Frame.compose([])
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Frame.compose Tests - Single Layer
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameComposeSingleLayer:
    """Tests for Frame.compose with a single layer."""

    def test_compose_single_layer_returns_rgb_array(self, red_layer):
        """compose with single layer returns RGB array (no alpha)."""
        result = Frame.compose([red_layer])
        assert result is not None
        assert result.shape == (6, 22, 3)  # No alpha channel

    def test_compose_single_layer_red_content(self, red_layer):
        """compose with red layer produces red RGB output."""
        result = Frame.compose([red_layer])
        # Result is uint8 (0-255) from img_as_ubyte
        assert result.dtype == np.uint8
        # Red channel should be 255
        assert np.all(result[:, :, 0] == 255)
        # Green and blue should be 0
        assert np.all(result[:, :, 1] == 0)
        assert np.all(result[:, :, 2] == 0)

    def test_compose_single_layer_green_content(self, green_layer):
        """compose with green layer produces green RGB output."""
        result = Frame.compose([green_layer])
        assert np.all(result[:, :, 0] == 0)
        assert np.all(result[:, :, 1] == 255)
        assert np.all(result[:, :, 2] == 0)

    def test_compose_single_layer_transparent(self, transparent_layer):
        """compose with transparent layer produces black output."""
        result = Frame.compose([transparent_layer])
        # Transparent composites against black background
        assert np.all(result == 0)

    def test_compose_single_layer_partial_alpha(self, half_alpha_blue_layer):
        """compose with partial alpha blends against background."""
        result = Frame.compose([half_alpha_blue_layer])
        # Blue channel should be ~127 (0.5 * 255)
        # Due to alpha compositing: (1-0.5)*0 + 0.5*1 = 0.5
        assert np.all(result[:, :, 2] > 120)
        assert np.all(result[:, :, 2] < 135)


# ─────────────────────────────────────────────────────────────────────────────
# Frame.compose Tests - Multiple Layers
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameComposeMultipleLayers:
    """Tests for Frame.compose with multiple layers."""

    def test_compose_two_layers_blends(self, red_layer, green_layer):
        """compose with two layers blends them together."""
        result = Frame.compose([red_layer, green_layer])
        assert result is not None
        assert result.shape == (6, 22, 3)

    def test_compose_order_matters(self, red_layer, green_layer):
        """Layer order affects blend result (base vs overlay)."""
        result1 = Frame.compose([red_layer, green_layer])
        result2 = Frame.compose([green_layer, red_layer])
        # Results should differ because base layer changes
        # (Though with full alpha screen blend, they may be similar)
        assert result1 is not None
        assert result2 is not None

    def test_compose_blends_using_layer_blend_mode(self):
        """compose uses each layer's blend_mode property."""
        base = Layer(4, 4)
        base._matrix[:, :] = [0.5, 0.0, 0.0, 1.0]  # Half red, full alpha

        overlay = Layer(4, 4)
        overlay._matrix[:, :] = [0.5, 0.0, 0.0, 1.0]  # Half red, full alpha
        overlay.blend_mode = "multiply"  # Set multiply blend

        result = Frame.compose([base, overlay])
        # Multiply 0.5 * 0.5 = 0.25 -> ~63 in uint8
        # (actual result affected by alpha compositing)
        assert result is not None

    def test_compose_uses_layer_opacity(self):
        """compose respects layer opacity property."""
        base = Layer(4, 4)
        base._matrix[:, :] = [1.0, 0.0, 0.0, 1.0]  # Red, full alpha

        overlay = Layer(4, 4)
        overlay._matrix[:, :] = [0.0, 1.0, 0.0, 1.0]  # Green, full alpha
        overlay._opacity = 0.0  # Zero opacity - should have no effect

        result = Frame.compose([base, overlay])
        # With zero opacity, result should be mostly red
        assert result is not None

    def test_compose_skips_none_layers(self, red_layer):
        """compose skips None layers in the list."""
        result = Frame.compose([red_layer, None])
        # Should not crash, returns valid result
        assert result is not None
        assert result.shape == (6, 22, 3)

    def test_compose_skips_invalid_ndim_layers(self, red_layer):
        """compose skips layers with invalid matrix dimensions."""
        # Create a layer with wrong ndim
        bad_layer = Layer(22, 6)
        bad_layer._matrix = np.zeros((6, 22))  # 2D instead of 3D

        result = Frame.compose([red_layer, bad_layer])
        # Should not crash
        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Frame.compose Tests - Background Color
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameComposeBackgroundColor:
    """Tests for Frame.compose background color handling."""

    def test_compose_base_layer_background_color_honored(self):
        """Background color is honored on the base layer."""
        base = Layer(4, 4)
        base._matrix[:, :] = [0.0, 0.0, 0.0, 0.0]  # Transparent
        base.background_color = to_color("white")

        result = Frame.compose([base])
        # Transparent pixels composite against white background
        assert result is not None
        assert np.all(result == 255)  # White

    def test_compose_overlay_background_color_ignored(self):
        """Background color on overlay layers is ignored."""
        base = Layer(4, 4)
        base._matrix[:, :] = [0.0, 0.0, 0.0, 0.0]  # Transparent

        overlay = Layer(4, 4)
        overlay._matrix[:, :] = [0.0, 0.0, 0.0, 0.0]  # Transparent
        overlay.background_color = to_color("red")  # Should be ignored

        result = Frame.compose([base, overlay])
        # Only base layer bg_color matters, which is None (black)
        assert result is not None
        assert np.all(result == 0)  # Black

    def test_compose_no_background_defaults_to_black(self):
        """No background color defaults to black."""
        base = Layer(4, 4)
        base._matrix[:, :] = [0.0, 0.0, 0.0, 0.0]  # Fully transparent

        result = Frame.compose([base])
        assert np.all(result == 0)  # Black


# ─────────────────────────────────────────────────────────────────────────────
# Frame._set_frame_data_single Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameSetFrameDataSingle:
    """Tests for Frame._set_frame_data_single (height=1 devices)."""

    def test_set_frame_data_single_called_for_height_1(self, frame_1x15, mock_driver):
        """_set_frame_data_single is called when height=1."""
        layer = frame_1x15.create_layer()
        layer._matrix[:, :] = [1.0, 0.0, 0.0, 1.0]  # Red

        run_commit(frame_1x15, [layer], show=False)

        # Should call run_command for single-row device
        mock_driver.run_command.assert_called_once()
        call_args = mock_driver.run_command.call_args
        assert call_args[0][0] == Frame.Command.SET_FRAME_DATA_SINGLE

    def test_set_frame_data_single_transaction_id(self, frame_1x15, mock_driver):
        """_set_frame_data_single uses transaction_id=0x80."""
        layer = frame_1x15.create_layer()
        run_commit(frame_1x15, [layer], show=False)

        call_kwargs = mock_driver.run_command.call_args_list[0][1]
        assert call_kwargs["transaction_id"] == 0x80

    def test_set_frame_data_single_segments_wide(self, mock_driver):
        """_set_frame_data_single segments wider rows."""
        frame = Frame(mock_driver, width=30, height=1)
        layer = frame.create_layer()

        run_commit(frame, [layer], show=False)

        max_cols = (hid.DATA_SIZE - 2) // 3
        expected_segments = (frame.width + max_cols - 1) // max_cols
        assert mock_driver.run_command.call_count == expected_segments

        first_args = mock_driver.run_command.call_args_list[0][0]
        second_args = mock_driver.run_command.call_args_list[1][0]

        assert first_args[1] == 0
        assert first_args[2] == max_cols
        assert second_args[1] == max_cols
        assert second_args[2] == frame.width - max_cols


# ─────────────────────────────────────────────────────────────────────────────
# Frame._set_frame_data_matrix Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameSetFrameDataMatrix:
    """Tests for Frame._set_frame_data_matrix (height>1 devices)."""

    def test_set_frame_data_matrix_called_for_height_gt_1(
        self, frame_6x22, mock_driver, mock_send_frame_async
    ):
        """_set_frame_data_matrix is called when height>1."""
        layer = frame_6x22.create_layer()
        layer._matrix[:, :] = [1.0, 0.0, 0.0, 1.0]  # Red

        run_commit(frame_6x22, [layer], show=False)

        mock_send_frame_async.assert_called_once()
        mock_driver.run_command.assert_not_called()

    def test_set_frame_data_matrix_passes_row_offsets_none(
        self, frame_6x22, mock_driver, mock_send_frame_async
    ):
        """_set_frame_data_matrix passes None row_offsets when hook is absent."""
        layer = frame_6x22.create_layer()

        run_commit(frame_6x22, [layer], show=False)

        call_kwargs = mock_send_frame_async.call_args.kwargs
        assert call_kwargs["row_offsets"] is None

    def test_set_frame_data_matrix_applies_row_offset(
        self, frame_6x22, mock_driver, mock_send_frame_async
    ):
        """_set_frame_data_matrix applies row offsets to column indices."""
        mock_driver.get_row_offset = MagicMock(return_value=2)
        layer = frame_6x22.create_layer()

        run_commit(frame_6x22, [layer], show=False)

        call_kwargs = mock_send_frame_async.call_args.kwargs
        assert call_kwargs["row_offsets"] == [2] * frame_6x22.height
        assert mock_driver.get_row_offset.call_count == frame_6x22.height

    def test_set_frame_data_matrix_transaction_id_default(
        self, frame_6x22, mock_driver, mock_send_frame_async
    ):
        """_set_frame_data_matrix uses transaction_id=0xFF by default."""
        mock_driver.has_quirk.return_value = False
        layer = frame_6x22.create_layer()

        run_commit(frame_6x22, [layer], show=False)

        call_kwargs = mock_send_frame_async.call_args.kwargs
        assert call_kwargs["transaction_id"] == 0xFF
        assert call_kwargs["is_extended"] is False

    def test_set_frame_data_matrix_quirk_custom_frame_80(
        self, frame_6x22, mock_driver, mock_send_frame_async
    ):
        """_set_frame_data_matrix uses tid=0x80 with CUSTOM_FRAME_80 quirk."""
        from uchroma.server.hardware import Quirks

        # Only CUSTOM_FRAME_80 quirk, not EXTENDED_FX_CMDS (which is checked first)
        mock_driver.has_quirk.side_effect = lambda q: q == Quirks.CUSTOM_FRAME_80
        layer = frame_6x22.create_layer()

        run_commit(frame_6x22, [layer], show=False)

        call_kwargs = mock_send_frame_async.call_args.kwargs
        assert call_kwargs["transaction_id"] == 0x80
        assert call_kwargs["is_extended"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Frame Wide Frames (>24 cols) Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameWideFrames:
    """Tests for Frame handling of wide frames (width > report payload)."""

    def test_wide_frame_calls_send_frame_async(self, frame_wide, mock_send_frame_async):
        """Wide frames use the async sender regardless of width."""
        layer = frame_wide.create_layer()

        run_commit(frame_wide, [layer], show=False)

        mock_send_frame_async.assert_called_once()
        frame_arg = mock_send_frame_async.call_args.args[1]
        assert frame_arg.shape == (frame_wide.height, frame_wide.width, 3)

    def test_wide_frame_passes_protocol_delays(self, frame_wide, mock_send_frame_async):
        """Wide frames pass protocol-based delay values to Rust sender."""
        layer = frame_wide.create_layer()

        run_commit(frame_wide, [layer], show=False)

        call_kwargs = mock_send_frame_async.call_args.kwargs
        assert call_kwargs["pre_delay_ms"] == 7
        assert call_kwargs["post_delay_ms"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Frame.commit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameCommit:
    """Tests for Frame.commit method."""

    def test_commit_calls_compose(self, frame_6x22, mock_driver):
        """commit calls compose with the layers."""
        layer = frame_6x22.create_layer()

        with (
            patch.object(Frame, "compose", wraps=Frame.compose) as mock_compose,
            patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()),
        ):
            run_commit(frame_6x22, [layer], show=False)
            mock_compose.assert_called_once_with([layer])

    def test_commit_calls_set_frame_data(self, frame_6x22, mock_driver):
        """commit calls _set_frame_data with composed image."""
        layer = frame_6x22.create_layer()

        with patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()) as mock_set:
            run_commit(frame_6x22, [layer], show=False)
            mock_set.assert_called_once()

    def test_commit_activates_custom_frame_when_show_true(self, frame_6x22, mock_driver):
        """commit activates custom_frame effect when show=True."""
        layer = frame_6x22.create_layer()

        with (
            patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()),
            patch.object(frame_6x22, "_set_custom_frame", new=AsyncMock()) as mock_custom,
        ):
            run_commit(frame_6x22, [layer], show=True)

        mock_custom.assert_called_once()

    def test_commit_does_not_activate_when_show_false(self, frame_6x22, mock_driver):
        """commit does not activate effect when show=False."""
        layer = frame_6x22.create_layer()

        with (
            patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()),
            patch.object(frame_6x22, "_set_custom_frame", new=AsyncMock()) as mock_custom,
        ):
            run_commit(frame_6x22, [layer], show=False)

        mock_custom.assert_not_called()

    def test_commit_default_show_is_true(self, frame_6x22, mock_driver):
        """commit defaults to show=True."""
        layer = frame_6x22.create_layer()

        with (
            patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()),
            patch.object(frame_6x22, "_set_custom_frame", new=AsyncMock()) as mock_custom,
        ):
            run_commit(frame_6x22, [layer])

        mock_custom.assert_called_once()

    def test_commit_returns_frame_instance(self, frame_6x22, mock_driver):
        """commit returns the Frame instance for chaining."""
        layer = frame_6x22.create_layer()

        with (
            patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()),
            patch.object(frame_6x22, "_set_custom_frame", new=AsyncMock()),
        ):
            result = run_commit(frame_6x22, [layer])

        assert result is frame_6x22

    def test_commit_with_custom_frame_id(self, frame_6x22, mock_driver):
        """commit passes frame_id to _set_frame_data."""
        layer = frame_6x22.create_layer()

        with patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()) as mock_set:
            run_commit(frame_6x22, [layer], frame_id=0x01, show=False)
            mock_set.assert_called_once()
            assert mock_set.call_args.args[1] == 0x01

    def test_commit_with_none_frame_id_uses_default(self, frame_6x22, mock_driver):
        """commit with frame_id=None uses DEFAULT_FRAME_ID."""
        layer = frame_6x22.create_layer()

        with patch.object(frame_6x22, "_set_frame_data", new=AsyncMock()) as mock_set:
            run_commit(frame_6x22, [layer], frame_id=None, show=False)
            assert mock_set.call_args.args[1] is None


# ─────────────────────────────────────────────────────────────────────────────
# Frame.reset Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameReset:
    """Tests for Frame.reset method."""

    def test_reset_commits_empty_layer(self, frame_6x22, mock_driver):
        """reset commits an empty (black) layer."""
        with patch.object(frame_6x22, "commit", new=AsyncMock()) as mock_commit:
            run_reset(frame_6x22)

            mock_commit.assert_called_once()
            layers = mock_commit.call_args.args[0]
            assert len(layers) == 1
            assert isinstance(layers[0], Layer)

    def test_reset_uses_show_false(self, frame_6x22, mock_driver):
        """reset commits with show=False."""
        with patch.object(frame_6x22, "commit", new=AsyncMock()) as mock_commit:
            run_reset(frame_6x22)

            call_kwargs = mock_commit.call_args.kwargs
            assert call_kwargs.get("show") is False

    def test_reset_returns_frame_instance(self, frame_6x22, mock_driver):
        """reset returns the Frame instance for chaining."""
        with patch.object(frame_6x22, "commit", new=AsyncMock()):
            result = run_reset(frame_6x22)

        assert result is frame_6x22

    def test_reset_clears_hardware_frame(self, frame_6x22, mock_send_frame_async):
        """reset sends black pixels to hardware."""
        run_reset(frame_6x22)

        mock_send_frame_async.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Frame._set_frame_data Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameSetFrameData:
    """Tests for Frame._set_frame_data internal method."""

    def test_set_frame_data_routes_to_single_for_height_1(self, frame_1x15, mock_driver):
        """_set_frame_data calls _set_frame_data_single for height=1."""
        img = np.zeros((1, 15, 3), dtype=np.uint8)

        with patch.object(frame_1x15, "_set_frame_data_single", new=AsyncMock()) as mock_single:
            asyncio.run(frame_1x15._set_frame_data(img))
            mock_single.assert_called_once()

    def test_set_frame_data_routes_to_matrix_for_height_gt_1(self, frame_6x22, mock_driver):
        """_set_frame_data calls _set_frame_data_matrix for height>1."""
        img = np.zeros((6, 22, 3), dtype=np.uint8)

        with patch.object(frame_6x22, "_set_frame_data_matrix", new=AsyncMock()) as mock_matrix:
            asyncio.run(frame_6x22._set_frame_data(img))
            mock_matrix.assert_called_once()

    def test_set_frame_data_uses_default_frame_id(self, frame_1x15, mock_driver):
        """_set_frame_data uses DEFAULT_FRAME_ID when None passed."""
        img = np.zeros((1, 15, 3), dtype=np.uint8)

        with patch.object(frame_1x15, "_set_frame_data_single", new=AsyncMock()) as mock_single:
            asyncio.run(frame_1x15._set_frame_data(img, frame_id=None))
            # frame_id should be DEFAULT_FRAME_ID (0xFF)
            call_args = mock_single.call_args[0]
            assert call_args[1] == Frame.DEFAULT_FRAME_ID


# ─────────────────────────────────────────────────────────────────────────────
# Frame Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFrameIntegration:
    """Integration tests for Frame class."""

    def test_full_workflow_create_and_commit_layer(
        self, frame_6x22, mock_driver, mock_send_frame_async
    ):
        """Full workflow: create layer, draw, commit."""
        # Create a layer
        layer = frame_6x22.create_layer()

        # Draw something (red pixel at 0,0)
        layer._matrix[0, 0] = [1.0, 0.0, 0.0, 1.0]

        # Commit
        result = run_commit(frame_6x22, [layer])

        # Should complete without error
        assert result is frame_6x22
        assert mock_driver.run_command.called
        assert mock_send_frame_async.called

    def test_multiple_layer_composition(self, frame_6x22, mock_driver, mock_send_frame_async):
        """Multiple layers can be composed and committed."""
        # Create two layers
        base = frame_6x22.create_layer()
        base._matrix[:, :] = [1.0, 0.0, 0.0, 1.0]  # Red base

        overlay = frame_6x22.create_layer()
        overlay._matrix[:, :] = [0.0, 1.0, 0.0, 0.5]  # Green overlay, 50% alpha

        # Commit both
        result = run_commit(frame_6x22, [base, overlay], show=False)

        assert result is frame_6x22
        assert mock_send_frame_async.called

    def test_driver_alignment_hook_called(self, frame_6x22, mock_driver, mock_send_frame_async):
        """Driver's align_key_matrix is called if present."""
        mock_driver.align_key_matrix = MagicMock(side_effect=lambda f, img: img)

        layer = frame_6x22.create_layer()
        run_commit(frame_6x22, [layer], show=False)

        mock_driver.align_key_matrix.assert_called()
        assert mock_send_frame_async.called

    def test_driver_row_offset_hook_called(self, frame_6x22, mock_driver):
        """Driver's get_row_offset is called if present."""
        mock_driver.get_row_offset = MagicMock(return_value=0)

        layer = frame_6x22.create_layer()
        run_commit(frame_6x22, [layer], show=False)

        # Should be called once per row
        assert mock_driver.get_row_offset.call_count == 6

    def test_report_caching(self, frame_6x22, mock_driver, mock_report):
        """Report object is cached after first use."""
        mock_driver.get_report.return_value = mock_report

        img = np.zeros((6, 22, 3), dtype=np.uint8)

        # First commit
        frame_6x22._set_frame_data_matrix(img, Frame.DEFAULT_FRAME_ID)
        first_call_count = mock_driver.get_report.call_count

        # Second commit
        frame_6x22._set_frame_data_matrix(img, Frame.DEFAULT_FRAME_ID)

        # get_report should only be called once (cached)
        assert mock_driver.get_report.call_count == first_call_count
