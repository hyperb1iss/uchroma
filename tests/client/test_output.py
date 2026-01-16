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


class TestOutputColors:
    def test_no_color_env_disables_colors(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        out = Output()
        result = out.cyan("test")
        assert "\x1b[" not in result

    def test_colors_enabled_by_default_on_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        out = Output(force_color=True)
        result = out.cyan("test")
        assert "\x1b[38;2;128;255;234m" in result

    def test_success_uses_green(self):
        out = Output(force_color=True)
        result = out.success("done")
        assert "\x1b[38;2;80;250;123m" in result

    def test_error_uses_red(self):
        out = Output(force_color=True)
        result = out.error("fail")
        assert "\x1b[38;2;255;99;99m" in result


class TestOutputFormatting:
    def test_device_line_format(self):
        out = Output(force_color=False)
        result = out.device_line("BlackWidow", "keyboard", "1532:0226")
        assert "BlackWidow" in result
        assert "keyboard" in result

    def test_columns_alignment(self):
        out = Output(force_color=False)
        lines = out.columns([("name", "BlackWidow"), ("type", "keyboard")])
        # Each line should be aligned
        assert all("\u2502" in line for line in lines)

    def test_trait_line(self):
        out = Output(force_color=False)
        result = out.trait_line("speed", "float", "1.0", "min: 0.1, max: 5.0")
        assert "speed" in result
        assert "float" in result
