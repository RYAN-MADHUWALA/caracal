"""Unit tests for the restricted in-container CLI shell."""

from __future__ import annotations

from prompt_toolkit.document import Document

from caracal.runtime import restricted_shell


def test_parse_restricted_input_strips_caracal_prefix():
    parsed = restricted_shell.parse_restricted_input("caracal workspace list")

    assert parsed.message is None
    assert parsed.args == ["workspace", "list"]


def test_parse_restricted_input_suggests_root_command_typo():
    parsed = restricted_shell.parse_restricted_input("carcal workspace list")

    assert parsed.is_error is True
    assert parsed.message == "Command not found: carcal. Did you mean 'caracal'?"


def test_parse_restricted_input_maps_help_to_real_cli_help():
    parsed = restricted_shell.parse_restricted_input("caracal help")

    assert parsed.message is None
    assert parsed.args == ["--help"]


def test_parse_restricted_tokens_maps_direct_help_to_real_cli_help():
    parsed = restricted_shell.parse_restricted_tokens(["help"])

    assert parsed.message is None
    assert parsed.args == ["--help"]


def test_parse_restricted_input_maps_subcommand_help_to_click_help():
    parsed = restricted_shell.parse_restricted_input("caracal help workspace")

    assert parsed.message is None
    assert parsed.args == ["workspace", "--help"]


def test_parse_restricted_input_maps_trailing_help_to_click_help():
    parsed = restricted_shell.parse_restricted_input("workspace list help")

    assert parsed.message is None
    assert parsed.args == ["workspace", "list", "--help"]


def test_parse_restricted_input_supports_clear_builtin():
    parsed = restricted_shell.parse_restricted_input("clear")

    assert parsed.action == "clear"


def test_run_restricted_command_without_args_opens_repl(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(restricted_shell, "run_restricted_repl", lambda: calls.append("repl") or 0)

    code = restricted_shell.run_restricted_command([])

    assert code == 0
    assert calls == ["repl"]


def test_run_restricted_command_executes_cli_args(monkeypatch):
    calls: list[list[str]] = []

    monkeypatch.setattr(restricted_shell, "_run_cli_command", lambda args: calls.append(list(args)) or 0)

    code = restricted_shell.run_restricted_command(["workspace", "list"])

    assert code == 0
    assert calls == [["workspace", "list"]]


def test_render_banner_shows_guidance(capsys):
    restricted_shell._render_banner()

    captured = capsys.readouterr()
    assert "Caracal CLI" in captured.out
    assert "Authority-scoped command session" in captured.out
    assert "help" in captured.out
    assert "clear" in captured.out
    assert "exit" in captured.out


def test_completer_suggests_real_next_tokens_after_root_command():
    from caracal.cli.main import cli

    completer = restricted_shell.CaracalCompleter(cli)
    completions = list(completer.get_completions(Document("caracal "), None))
    texts = [completion.text for completion in completions]

    assert "--help" in texts
    assert "--version" in texts
    assert "workspace" in texts
    assert "principal" in texts
    assert "help" not in texts
    assert "clear" not in texts


def test_completer_suggests_subcommands_for_groups():
    from caracal.cli.main import cli

    completer = restricted_shell.CaracalCompleter(cli)
    completions = list(completer.get_completions(Document("workspace "), None))
    texts = [completion.text for completion in completions]

    assert "list" in texts
    assert "create" in texts
    assert "--help" in texts
