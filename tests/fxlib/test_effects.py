#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Unit tests for uchroma.fxlib effects."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from uchroma.colorlib import Color

# ─────────────────────────────────────────────────────────────────────────────
# Mock Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_driver():
    """Create a mock driver for renderer testing."""
    driver = MagicMock()
    driver.width = 22
    driver.height = 6
    driver.logger = MagicMock()
    driver.logger.isEnabledFor.return_value = False
    driver.logger.debug = MagicMock()
    return driver


@pytest.fixture
def mock_frame():
    """Create a mock frame for renderer testing."""
    frame = MagicMock()
    frame.width = 22
    frame.height = 6
    return frame


@pytest.fixture
def mock_layer():
    """Create a mock layer for renderer testing."""
    layer = MagicMock()
    layer.width = 22
    layer.height = 6
    layer.matrix = np.zeros((6, 22, 4), dtype=np.float64)
    layer.put = MagicMock()
    layer.put_all = MagicMock()
    return layer


# ─────────────────────────────────────────────────────────────────────────────
# Rainbow Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRainbowRenderer:
    """Tests for Rainbow renderer."""

    @pytest.fixture
    def rainbow(self, mock_driver):
        """Create Rainbow renderer."""
        from uchroma.fxlib.rainbow import Rainbow

        return Rainbow(mock_driver)

    def test_meta(self, rainbow):
        """Rainbow has correct metadata."""
        assert rainbow.meta.display_name == "Rainflow"
        assert "color" in rainbow.meta.description.lower()

    def test_default_speed(self, rainbow):
        """Rainbow has default speed."""
        from uchroma.fxlib.rainbow import DEFAULT_SPEED

        assert rainbow.speed == DEFAULT_SPEED

    def test_default_stagger(self, rainbow):
        """Rainbow has default stagger."""
        assert rainbow.stagger == 4

    def test_init_creates_gradient(self, rainbow, mock_frame):
        """Rainbow.init creates gradient."""
        result = rainbow.init(mock_frame)
        assert result is True
        assert rainbow._gradient is not None

    def test_hue_gradient_creates_colors(self):
        """_hue_gradient creates list of colors."""
        from uchroma.fxlib.rainbow import Rainbow

        gradient = Rainbow._hue_gradient(0, 10)
        assert len(gradient) == 10
        assert all(isinstance(c, Color) for c in gradient)

    def test_draw_returns_true(self, rainbow, mock_frame, mock_layer):
        """Rainbow.draw returns True."""
        rainbow.init(mock_frame)

        async def run_test():
            return await rainbow.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True

    def test_draw_increments_offset(self, rainbow, mock_frame, mock_layer):
        """Rainbow.draw increments offset."""
        rainbow.init(mock_frame)
        initial_offset = rainbow._offset

        async def run_test():
            await rainbow.draw(mock_layer, time.time())
            return rainbow._offset

        new_offset = asyncio.run(run_test())
        assert new_offset == (initial_offset + 1) % len(rainbow._gradient)

    def test_draw_calls_put_all(self, rainbow, mock_frame, mock_layer):
        """Rainbow.draw calls layer.put_all."""
        rainbow.init(mock_frame)

        async def run_test():
            await rainbow.draw(mock_layer, time.time())

        asyncio.run(run_test())
        mock_layer.put_all.assert_called_once()

    def test_draw_no_gradient_returns_false(self, rainbow, mock_layer):
        """Rainbow.draw returns False without gradient."""
        rainbow._gradient = None

        async def run_test():
            return await rainbow.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is False

    def test_speed_change_recreates_gradient(self, rainbow, mock_frame):
        """Changing speed recreates gradient."""
        rainbow.init(mock_frame)
        old_gradient = rainbow._gradient

        rainbow.speed = 10
        assert rainbow._gradient is not old_gradient


# ─────────────────────────────────────────────────────────────────────────────
# Plasma Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPlasmaRenderer:
    """Tests for Plasma renderer."""

    @pytest.fixture
    def plasma(self, mock_driver):
        """Create Plasma renderer."""
        from uchroma.fxlib.plasma import Plasma

        return Plasma(mock_driver)

    def test_meta(self, plasma):
        """Plasma has correct metadata."""
        assert plasma.meta.display_name == "Plasma"
        assert "plasma" in plasma.meta.description.lower()

    def test_default_gradient_length(self, plasma):
        """Plasma has default gradient length."""
        assert plasma.gradient_length == 360

    def test_init_returns_true(self, plasma, mock_frame):
        """Plasma.init returns True."""
        result = plasma.init(mock_frame)
        assert result is True

    def test_init_creates_gradient(self, plasma, mock_frame):
        """Plasma.init creates gradient."""
        plasma.init(mock_frame)
        assert plasma._gradient is not None

    def test_init_sets_start_time(self, plasma, mock_frame):
        """Plasma.init sets start time."""
        before = time.time()
        plasma.init(mock_frame)
        after = time.time()
        assert before <= plasma._start_time <= after

    def test_draw_returns_true(self, plasma, mock_frame, mock_layer):
        """Plasma.draw returns True."""
        plasma.init(mock_frame)

        async def run_test():
            return await plasma.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Aurora Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAuroraRenderer:
    """Tests for Aurora renderer."""

    @pytest.fixture
    def aurora(self, mock_driver):
        """Create Aurora renderer."""
        from uchroma.fxlib.aurora import Aurora

        return Aurora(mock_driver)

    def test_meta(self, aurora):
        """Aurora has correct metadata."""
        assert aurora.meta.display_name == "Aurora"

    def test_init_returns_true(self, aurora, mock_frame):
        """Aurora.init returns True."""
        result = aurora.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, aurora, mock_frame, mock_layer):
        """Aurora.draw returns True."""
        aurora.init(mock_frame)

        async def run_test():
            return await aurora.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Ocean Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestOceanRenderer:
    """Tests for Ocean renderer."""

    @pytest.fixture
    def ocean(self, mock_driver):
        """Create Ocean renderer."""
        from uchroma.fxlib.ocean import Ocean

        return Ocean(mock_driver)

    def test_meta(self, ocean):
        """Ocean has correct metadata."""
        assert ocean.meta.display_name == "Ocean"

    def test_init_returns_true(self, ocean, mock_frame):
        """Ocean.init returns True."""
        result = ocean.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, ocean, mock_frame, mock_layer):
        """Ocean.draw returns True."""
        ocean.init(mock_frame)

        async def run_test():
            return await ocean.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Copper Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCopperBarsRenderer:
    """Tests for CopperBars renderer."""

    @pytest.fixture
    def copper(self, mock_driver):
        """Create CopperBars renderer."""
        from uchroma.fxlib.copper import CopperBars

        return CopperBars(mock_driver)

    def test_meta(self, copper):
        """CopperBars has correct metadata."""
        assert copper.meta.display_name == "Copper Bars"

    def test_init_returns_true(self, copper, mock_frame):
        """Copper.init returns True."""
        result = copper.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, copper, mock_frame, mock_layer):
        """Copper.draw returns True."""
        copper.init(mock_frame)

        async def run_test():
            return await copper.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Nebula Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestNebulaRenderer:
    """Tests for Nebula renderer."""

    @pytest.fixture
    def nebula(self, mock_driver):
        """Create Nebula renderer."""
        from uchroma.fxlib.nebula import Nebula

        return Nebula(mock_driver)

    def test_meta(self, nebula):
        """Nebula has correct metadata."""
        assert nebula.meta.display_name == "Nebula"

    def test_init_returns_true(self, nebula, mock_frame):
        """Nebula.init returns True."""
        result = nebula.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, nebula, mock_frame, mock_layer):
        """Nebula.draw returns True."""
        nebula.init(mock_frame)

        async def run_test():
            return await nebula.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Vortex Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestVortexRenderer:
    """Tests for Vortex renderer."""

    @pytest.fixture
    def vortex(self, mock_driver):
        """Create Vortex renderer."""
        from uchroma.fxlib.vortex import Vortex

        return Vortex(mock_driver)

    def test_meta(self, vortex):
        """Vortex has correct metadata."""
        assert vortex.meta.display_name == "Vortex"

    def test_init_returns_true(self, vortex, mock_frame):
        """Vortex.init returns True."""
        result = vortex.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, vortex, mock_frame, mock_layer):
        """Vortex.draw returns True."""
        vortex.init(mock_frame)

        async def run_test():
            return await vortex.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Kaleidoscope Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestKaleidoscopeRenderer:
    """Tests for Kaleidoscope renderer."""

    @pytest.fixture
    def kaleidoscope(self, mock_driver):
        """Create Kaleidoscope renderer."""
        from uchroma.fxlib.kaleidoscope import Kaleidoscope

        return Kaleidoscope(mock_driver)

    def test_meta(self, kaleidoscope):
        """Kaleidoscope has correct metadata."""
        assert kaleidoscope.meta.display_name == "Kaleidoscope"

    def test_init_returns_true(self, kaleidoscope, mock_frame):
        """Kaleidoscope.init returns True."""
        result = kaleidoscope.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, kaleidoscope, mock_frame, mock_layer):
        """Kaleidoscope.draw returns True."""
        kaleidoscope.init(mock_frame)

        async def run_test():
            return await kaleidoscope.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Metaballs Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMetaballsRenderer:
    """Tests for Metaballs renderer."""

    @pytest.fixture
    def metaballs(self, mock_driver):
        """Create Metaballs renderer."""
        from uchroma.fxlib.metaballs import Metaballs

        return Metaballs(mock_driver)

    def test_meta(self, metaballs):
        """Metaballs has correct metadata."""
        assert metaballs.meta.display_name == "Metaballs"

    def test_init_returns_true(self, metaballs, mock_frame):
        """Metaballs.init returns True."""
        result = metaballs.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, metaballs, mock_frame, mock_layer):
        """Metaballs.draw returns True."""
        metaballs.init(mock_frame)

        async def run_test():
            return await metaballs.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Embers Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEmbersRenderer:
    """Tests for Embers renderer."""

    @pytest.fixture
    def embers(self, mock_driver):
        """Create Embers renderer."""
        from uchroma.fxlib.embers import Embers

        return Embers(mock_driver)

    def test_meta(self, embers):
        """Embers has correct metadata."""
        assert embers.meta.display_name == "Embers"

    def test_init_returns_true(self, embers, mock_frame):
        """Embers.init returns True."""
        result = embers.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, embers, mock_frame, mock_layer):
        """Embers.draw returns True."""
        embers.init(mock_frame)

        async def run_test():
            return await embers.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Comets Effect Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCometsRenderer:
    """Tests for Comets renderer."""

    @pytest.fixture
    def comets(self, mock_driver):
        """Create Comets renderer."""
        from uchroma.fxlib.comets import Comets

        return Comets(mock_driver)

    def test_meta(self, comets):
        """Comets has correct metadata."""
        assert comets.meta.display_name == "Comets"

    def test_init_returns_true(self, comets, mock_frame):
        """Comets.init returns True."""
        result = comets.init(mock_frame)
        assert result is True

    def test_draw_returns_true(self, comets, mock_frame, mock_layer):
        """Comets.draw returns True."""
        comets.init(mock_frame)

        async def run_test():
            return await comets.draw(mock_layer, time.time())

        result = asyncio.run(run_test())
        assert result is True
