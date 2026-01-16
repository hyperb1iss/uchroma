#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""Tests for CLI base infrastructure."""

import pytest

from uchroma.client.cli_base import UChromaCLI


class TestParserCreation:
    """Test argument parser setup."""

    def test_has_version_flag(self):
        cli = UChromaCLI()
        # Should have -v/--version
        actions = {tuple(a.option_strings) for a in cli.parser._actions if a.option_strings}
        assert ("-v", "--version") in actions

    def test_has_device_option(self):
        cli = UChromaCLI()
        actions = {tuple(a.option_strings) for a in cli.parser._actions if a.option_strings}
        assert ("-d", "--device") in actions

    def test_has_debug_flag(self):
        cli = UChromaCLI()
        actions = {tuple(a.option_strings) for a in cli.parser._actions if a.option_strings}
        assert ("--debug",) in actions

    def test_has_no_color_flag(self):
        cli = UChromaCLI()
        actions = {tuple(a.option_strings) for a in cli.parser._actions if a.option_strings}
        assert ("--no-color",) in actions


class TestDeviceSpecExtraction:
    """Test @device argument handling."""

    def test_extracts_at_device_from_start(self):
        cli = UChromaCLI()
        spec, remaining = cli._extract_device_spec(["@blackwidow", "brightness", "80"])
        assert spec == "blackwidow"
        assert remaining == ["brightness", "80"]

    def test_extracts_at_device_from_middle(self):
        cli = UChromaCLI()
        spec, remaining = cli._extract_device_spec(["brightness", "@blackwidow", "80"])
        assert spec == "blackwidow"
        assert remaining == ["brightness", "80"]

    def test_returns_none_when_no_at_device(self):
        cli = UChromaCLI()
        spec, remaining = cli._extract_device_spec(["brightness", "80"])
        assert spec is None
        assert remaining == ["brightness", "80"]

    def test_only_extracts_first_at_device(self):
        cli = UChromaCLI()
        spec, remaining = cli._extract_device_spec(["@first", "@second", "cmd"])
        assert spec == "first"
        assert remaining == ["@second", "cmd"]

    def test_handles_empty_args(self):
        cli = UChromaCLI()
        spec, remaining = cli._extract_device_spec([])
        assert spec is None
        assert remaining == []

    def test_at_index_works(self):
        cli = UChromaCLI()
        spec, remaining = cli._extract_device_spec(["@0", "brightness"])
        assert spec == "0"
        assert remaining == ["brightness"]


class TestArgParsing:
    """Test full argument parsing."""

    def _cli_with_test_cmd(self) -> UChromaCLI:
        """Create CLI with a test subcommand registered."""
        cli = UChromaCLI()
        sub = cli.add_subparsers()
        sub.add_parser("brightness", help="Test command")
        return cli

    def test_device_spec_from_at_prefix(self):
        cli = self._cli_with_test_cmd()
        args = cli.parse_args(["@blackwidow", "brightness"])
        assert args.device_spec == "blackwidow"

    def test_device_spec_from_flag(self):
        cli = self._cli_with_test_cmd()
        args = cli.parse_args(["-d", "blackwidow", "brightness"])
        assert args.device_spec == "blackwidow"

    def test_flag_takes_precedence_over_at(self):
        cli = UChromaCLI()
        args = cli.parse_args(["@ignored", "-d", "preferred"])
        assert args.device_spec == "preferred"

    def test_no_device_spec(self):
        cli = self._cli_with_test_cmd()
        args = cli.parse_args(["brightness"])
        assert args.device_spec is None

    def test_debug_flag(self):
        cli = self._cli_with_test_cmd()
        args = cli.parse_args(["--debug", "brightness"])
        assert args.debug is True

    def test_no_color_flag_affects_output(self):
        cli = UChromaCLI()
        cli.parse_args(["--no-color"])
        assert cli.out._color_enabled is False

    def test_help_exits_zero(self):
        cli = UChromaCLI()
        with pytest.raises(SystemExit) as exc:
            cli.parse_args(["--help"])
        assert exc.value.code == 0

    def test_version_exits_zero(self):
        cli = UChromaCLI()
        with pytest.raises(SystemExit) as exc:
            cli.parse_args(["--version"])
        assert exc.value.code == 0


class TestSubparsers:
    """Test subcommand registration."""

    def test_add_subparsers(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        assert subparsers is not None

    def test_subparsers_cached(self):
        cli = UChromaCLI()
        sub1 = cli.add_subparsers()
        sub2 = cli.add_subparsers()
        assert sub1 is sub2

    def test_register_command(self):
        cli = UChromaCLI()
        subparsers = cli.add_subparsers()
        test_parser = subparsers.add_parser("test", help="Test command")
        test_parser.set_defaults(func=lambda args: "executed")

        args = cli.parse_args(["test"])
        assert args.command == "test"
        assert args.func(args) == "executed"


class TestOutputIntegration:
    """Test Output class integration."""

    def test_has_output_instance(self):
        cli = UChromaCLI()
        assert cli.out is not None

    def test_error_method_exits(self):
        cli = UChromaCLI()
        with pytest.raises(SystemExit) as exc:
            cli.error("Something went wrong")
        assert exc.value.code == 1

    def test_print_methods_exist(self, capsys):
        cli = UChromaCLI()
        cli.print_success("It worked")
        captured = capsys.readouterr()
        assert "worked" in captured.out

        cli.print_warning("Be careful")
        captured = capsys.readouterr()
        assert "careful" in captured.out
