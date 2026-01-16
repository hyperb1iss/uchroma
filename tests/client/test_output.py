#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for CLI output styling."""

from uchroma.client.output import Output, strip_ansi


class TestStripAnsi:
    def test_strips_color_codes(self):
        colored = "\x1b[38;2;128;255;234mhello\x1b[0m"
        assert strip_ansi(colored) == "hello"

    def test_preserves_plain_text(self):
        assert strip_ansi("hello world") == "hello world"

    def test_strips_multiple_codes(self):
        text = "\x1b[1m\x1b[38;2;255;0;0mbold red\x1b[0m"
        assert strip_ansi(text) == "bold red"


class TestSemanticMethods:
    """Test that semantic methods apply styling correctly."""

    def test_no_color_env_disables_colors(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        out = Output()
        result = out.device("test")
        assert "\x1b[" not in result

    def test_device_applies_styling(self):
        out = Output(force_color=True)
        result = out.device("BlackWidow")
        # Should have ANSI codes
        assert "\x1b[" in result
        assert "BlackWidow" in result

    def test_key_applies_styling(self):
        out = Output(force_color=True)
        result = out.key("brightness")
        assert "\x1b[" in result
        assert "brightness" in result

    def test_value_applies_styling(self):
        out = Output(force_color=True)
        result = out.value("80%")
        assert "\x1b[" in result
        assert "80%" in result

    def test_muted_applies_styling(self):
        out = Output(force_color=True)
        result = out.muted("metadata")
        assert "\x1b[" in result
        assert "metadata" in result

    def test_path_applies_styling(self):
        out = Output(force_color=True)
        result = out.path("/usr/bin/uchroma")
        assert "\x1b[" in result

    def test_header_is_bold(self):
        out = Output(force_color=True)
        result = out.header("Section")
        # Bold escape code
        assert "\x1b[1m" in result


class TestStateMessages:
    """Test success/error/warning formatting."""

    def test_success_has_checkmark(self):
        out = Output(force_color=True)
        result = out.success("done")
        assert "\u2713" in result  # ✓
        assert "done" in result

    def test_error_has_cross(self):
        out = Output(force_color=True)
        result = out.error("fail")
        assert "\u2717" in result  # ✗
        assert "fail" in result

    def test_warning_has_exclamation(self):
        out = Output(force_color=True)
        result = out.warning("caution")
        assert "!" in result
        assert "caution" in result

    def test_active_applies_styling(self):
        out = Output(force_color=True)
        result = out.active("●")
        assert "\x1b[" in result


class TestCompoundFormatters:
    """Test compound formatting methods."""

    def test_device_line_format(self):
        out = Output(force_color=False)
        result = out.device_line("BlackWidow", "keyboard", "1532:0226")
        assert "BlackWidow" in result
        assert "keyboard" in result
        assert "1532:0226" in result

    def test_kv_format(self):
        out = Output(force_color=False)
        result = out.kv("brightness", "80%")
        assert "brightness" in result
        assert "80%" in result
        assert ":" in result

    def test_columns_alignment(self):
        out = Output(force_color=False)
        lines = out.columns([("name", "BlackWidow"), ("type", "keyboard")])
        # Each line should have the pipe separator
        assert all("\u2502" in line for line in lines)
        assert len(lines) == 2

    def test_trait_line(self):
        out = Output(force_color=False)
        result = out.trait_line("speed", "float", "1.0", "min: 0.1, max: 5.0")
        assert "speed" in result
        assert "float" in result
        assert "1.0" in result
        assert "min:" in result

    def test_trait_line_without_value(self):
        out = Output(force_color=False)
        result = out.trait_line("speed", "float")
        assert "speed" in result
        assert "float" in result
        assert "=" not in result

    def test_separator(self):
        out = Output(force_color=False)
        result = out.separator(10)
        assert "\u2500" * 10 in result


class TestColorDetection:
    """Test automatic color detection."""

    def test_force_color_true(self):
        out = Output(force_color=True)
        assert out._color_enabled is True

    def test_force_color_false(self):
        out = Output(force_color=False)
        assert out._color_enabled is False

    def test_no_color_env(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        out = Output()
        assert out._color_enabled is False

    def test_dumb_terminal(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        out = Output()
        assert out._color_enabled is False
