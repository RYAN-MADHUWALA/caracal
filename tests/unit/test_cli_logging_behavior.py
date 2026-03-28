"""Focused tests for quiet interactive CLI logging behavior."""

from __future__ import annotations

from types import SimpleNamespace

from click.testing import CliRunner

from caracal.cli.main import cli


def test_subcommand_help_loads_config_without_emitting_config_logs(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_load_config(config_path, suppress_missing_file_log=False, emit_logs=True):
        captured["config_path"] = config_path
        captured["suppress_missing_file_log"] = suppress_missing_file_log
        captured["emit_logs"] = emit_logs
        return SimpleNamespace(logging=SimpleNamespace(level="INFO", file=None, format="text"))

    monkeypatch.setattr("caracal.cli.main.load_config", _fake_load_config)
    monkeypatch.setattr("caracal.cli.main.get_active_workspace", lambda: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])

    assert result.exit_code == 0
    assert captured["suppress_missing_file_log"] is True
    assert captured["emit_logs"] is False
