"""Unit tests for host/container runtime entrypoints."""

from __future__ import annotations

import argparse
from pathlib import Path

from caracal.runtime import entrypoints


class _Result:
    def __init__(self, code: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


def test_host_help_lists_orchestrator_commands(capsys):
    code = entrypoints._run_host_orchestrator(())

    assert code == 0
    output = capsys.readouterr().out
    assert "up" in output
    assert "down" in output
    assert "cli" in output
    assert "flow" in output
    assert "logs" in output
    assert "reset" in output
    assert "purge" in output


def test_caracal_entrypoint_uses_host_orchestrator(monkeypatch):
    monkeypatch.setattr(entrypoints, "_in_container_runtime", lambda: False)
    monkeypatch.setattr(entrypoints.sys, "argv", ["caracal", "up"])
    monkeypatch.setattr(entrypoints, "_run_host_orchestrator", lambda args: 7)

    try:
        entrypoints.caracal_entrypoint()
        assert False, "Expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 7


def test_caracal_entrypoint_uses_local_cli_in_container(monkeypatch):
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(entrypoints, "_in_container_runtime", lambda: True)
    monkeypatch.setattr(entrypoints.sys, "argv", ["caracal", "principal", "list"])
    monkeypatch.setattr(entrypoints, "_run_local_caracal", lambda args: calls.append(tuple(args)))

    entrypoints.caracal_entrypoint()
    assert calls == [("principal", "list")]


def test_run_local_caracal_uses_restricted_runtime(monkeypatch):
    calls: list[list[str]] = []

    def _fake_run(args):
        calls.append(list(args))
        return 0

    monkeypatch.setattr(
        "caracal.runtime.restricted_shell.run_restricted_command",
        _fake_run,
    )

    try:
        entrypoints._run_local_caracal(("workspace", "list"))
        assert False, "Expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 0

    assert calls == [["workspace", "list"]]


def test_host_up_starts_full_stack(monkeypatch):
    commands: list[list[str]] = []

    monkeypatch.setattr(entrypoints, "_resolve_compose_file", lambda compose_file=None: Path("/tmp/compose.yml"))
    monkeypatch.setattr(entrypoints, "_compose_cmd", lambda _: ["docker", "compose", "-f", "/tmp/compose.yml"])

    def _fake_run(cmd, check=False):
        commands.append(list(cmd))
        return _Result(0)

    monkeypatch.setattr(entrypoints.subprocess, "run", _fake_run)

    namespace = argparse.Namespace(compose_file=None, no_pull=True)
    code = entrypoints._host_up(namespace)

    assert code == 0
    assert commands == [["docker", "compose", "-f", "/tmp/compose.yml", "up", "-d", "postgres", "redis", "mcp"]]


def test_host_up_skips_mcp_pull_for_local_build(monkeypatch):
    commands: list[list[str]] = []

    monkeypatch.setattr(entrypoints, "_resolve_compose_file", lambda compose_file=None: Path("/tmp/compose.yml"))
    monkeypatch.setattr(entrypoints, "_compose_cmd", lambda _: ["docker", "compose", "-f", "/tmp/compose.yml"])
    monkeypatch.setattr(entrypoints, "_service_uses_local_build", lambda *_args, **_kwargs: True)

    def _fake_run(cmd, check=False):
        commands.append(list(cmd))
        return _Result(0)

    monkeypatch.setattr(entrypoints.subprocess, "run", _fake_run)

    namespace = argparse.Namespace(compose_file=None, no_pull=False)
    code = entrypoints._host_up(namespace)

    assert code == 0
    assert commands == [
        ["docker", "compose", "-f", "/tmp/compose.yml", "pull", "postgres", "redis"],
        ["docker", "compose", "-f", "/tmp/compose.yml", "up", "-d", "postgres", "redis", "mcp"],
    ]


def test_host_cli_opens_restricted_cli_in_running_container(monkeypatch):
    commands: list[list[str]] = []

    monkeypatch.setattr(entrypoints, "_resolve_compose_file", lambda compose_file=None: Path("/tmp/compose.yml"))
    monkeypatch.setattr(entrypoints, "_compose_cmd", lambda _: ["docker", "compose", "-f", "/tmp/compose.yml"])
    monkeypatch.setattr(entrypoints, "_host_up", lambda ns: 0)

    def _fake_run(cmd, check=False):
        commands.append(list(cmd))
        return _Result(0)

    monkeypatch.setattr(entrypoints.subprocess, "run", _fake_run)

    namespace = argparse.Namespace(compose_file=None)
    code = entrypoints._host_cli(namespace)

    assert code == 0
    assert commands == [["docker", "compose", "-f", "/tmp/compose.yml", "exec", "-u", "caracal", "mcp", "caracal"]]


def test_host_flow_runs_inside_runtime_container(monkeypatch):
    commands: list[list[str]] = []

    monkeypatch.setattr(entrypoints, "_resolve_compose_file", lambda compose_file=None: Path("/tmp/compose.yml"))
    monkeypatch.setattr(entrypoints, "_compose_cmd", lambda _: ["docker", "compose", "-f", "/tmp/compose.yml"])
    monkeypatch.setattr(entrypoints, "_host_up", lambda ns: 0)

    def _fake_run(cmd, check=False):
        commands.append(list(cmd))
        return _Result(0)

    monkeypatch.setattr(entrypoints.subprocess, "run", _fake_run)

    namespace = argparse.Namespace(compose_file=None)
    code = entrypoints._host_flow(namespace)

    assert code == 0
    assert commands == [[
        "docker",
        "compose",
        "-f",
        "/tmp/compose.yml",
        "exec",
        "-u",
        "caracal",
        "-e",
        "TERM=xterm-256color",
        "-e",
        "COLORTERM=truecolor",
        "mcp",
        "python",
        "-m",
        "caracal.flow.main",
    ]]


def test_host_cli_rejects_passthrough_arguments(capsys):
    code = entrypoints._run_host_orchestrator(("cli", "--", "--help"))

    assert code == 2
    error_output = capsys.readouterr().err
    assert "unrecognized arguments" in error_output


def test_emit_compose_teardown_output_filters_network_warning_from_stderr(capsys):
    network_in_use = entrypoints._emit_compose_teardown_output(
        stdout="",
        stderr=" Network caracal-runtime Removing \n Network caracal-runtime Resource is still in use \n",
    )

    captured = capsys.readouterr()
    assert network_in_use is True
    assert "Network caracal-runtime Removing" in captured.err
    assert "Resource is still in use" not in captured.err
    assert "Resource is still in use" not in captured.out


def test_list_network_container_names_parses_docker_inspect(monkeypatch):
    monkeypatch.setattr(entrypoints.shutil, "which", lambda cmd: "/usr/bin/docker" if cmd == "docker" else None)

    def _fake_run(cmd, check=False, capture_output=False, text=False):
        assert cmd == [
            "/usr/bin/docker",
            "network",
            "inspect",
            "caracal-runtime",
            "--format",
            "{{json .Containers}}",
        ]
        assert check is False
        assert capture_output is True
        assert text is True
        return _Result(
            0,
            stdout='{"abc":{"Name":"caracal-gateway-dev"},"def":{"Name":"caracal-mcp"}}',
        )

    monkeypatch.setattr(entrypoints.subprocess, "run", _fake_run)

    assert entrypoints._list_network_container_names("caracal-runtime") == [
        "caracal-gateway-dev",
        "caracal-mcp",
    ]


def test_finalize_teardown_result_removes_caracal_managed_blockers(monkeypatch, capsys):
    monkeypatch.setattr(
        entrypoints,
        "_reconcile_shared_runtime_network",
        lambda network_name: (["caracal-gateway-dev"], [], True),
    )

    code = entrypoints._finalize_teardown_result(0, True)

    captured = capsys.readouterr()
    assert code == 0
    assert "caracal-gateway-dev" in captured.out
    assert "Removed shared Docker network 'caracal-runtime'." in captured.out


def test_finalize_teardown_result_fails_when_non_caracal_blockers_remain(capsys):
    def _fake_reconcile(network_name):
        return [], ["someone-elses-container"], False

    from caracal.runtime import entrypoints as runtime_entrypoints

    original = runtime_entrypoints._reconcile_shared_runtime_network
    runtime_entrypoints._reconcile_shared_runtime_network = _fake_reconcile
    try:
        code = runtime_entrypoints._finalize_teardown_result(0, True)
    finally:
        runtime_entrypoints._reconcile_shared_runtime_network = original

    captured = capsys.readouterr()
    assert code == 1
    assert "someone-elses-container" in captured.err


def test_host_logs_reports_when_no_runtime_logs(monkeypatch, capsys):
    monkeypatch.setattr(entrypoints, "_resolve_compose_file", lambda compose_file=None: Path("/tmp/compose.yml"))
    monkeypatch.setattr(entrypoints, "_compose_cmd", lambda _: ["docker", "compose", "-f", "/tmp/compose.yml"])

    def _fake_run(cmd, check=False, capture_output=False, text=False):
        assert cmd == [
            "docker",
            "compose",
            "-f",
            "/tmp/compose.yml",
            "logs",
            "mcp",
            "postgres",
            "redis",
        ]
        assert check is False
        assert capture_output is True
        assert text is True
        return _Result(0, stdout="", stderr="")

    monkeypatch.setattr(entrypoints.subprocess, "run", _fake_run)

    namespace = argparse.Namespace(compose_file=None, follow=False, services=["mcp", "postgres", "redis"])
    code = entrypoints._host_logs(namespace)

    captured = capsys.readouterr()
    assert code == 0
    assert "No runtime logs are available." in captured.out


def test_host_purge_requires_force_in_noninteractive_mode(monkeypatch, capsys):
    class _Stdin:
        @staticmethod
        def isatty():
            return False

    monkeypatch.setattr(entrypoints.sys, "stdin", _Stdin())

    namespace = argparse.Namespace(force=False, compose_file=None)
    code = entrypoints._host_purge(namespace)

    captured = capsys.readouterr()
    assert code == 2
    assert "--force" in captured.err


def test_host_purge_removes_caracal_resources(monkeypatch, capsys):
    monkeypatch.setattr(entrypoints, "_confirm_purge", lambda force: True)
    monkeypatch.setattr(entrypoints, "_resolve_compose_file", lambda compose_file=None: Path("/tmp/compose.yml"))
    monkeypatch.setattr(entrypoints, "_list_caracal_container_names", lambda: ["caracal-mcp"])
    monkeypatch.setattr(entrypoints, "_list_caracal_volume_names", lambda: ["caracal_caracal_state"])
    monkeypatch.setattr(entrypoints, "_list_caracal_network_names", lambda: ["caracal-runtime"])
    monkeypatch.setattr(
        entrypoints,
        "_list_caracal_image_refs",
        lambda compose_file=None: ["caracal-runtime:latest"],
    )
    monkeypatch.setattr(
        entrypoints,
        "_list_caracal_purge_paths",
        lambda: [Path("/tmp/.caracal"), Path("/tmp/.caracal-completion.bash")],
    )

    removals: list[tuple[str, str]] = []
    monkeypatch.setattr(entrypoints, "_remove_container", lambda name: removals.append(("container", name)) or True)
    monkeypatch.setattr(entrypoints, "_remove_volume", lambda name: removals.append(("volume", name)) or True)
    monkeypatch.setattr(entrypoints, "_remove_network", lambda name: removals.append(("network", name)) or True)
    monkeypatch.setattr(entrypoints, "_remove_image", lambda ref: removals.append(("image", ref)) or True)
    monkeypatch.setattr(entrypoints, "_delete_path", lambda path: removals.append(("path", str(path))) or True)
    monkeypatch.setattr(entrypoints, "_purge_keyring_credentials", lambda: True)

    namespace = argparse.Namespace(force=True, compose_file=None)
    code = entrypoints._host_purge(namespace)

    captured = capsys.readouterr()
    assert code == 0
    assert ("container", "caracal-mcp") in removals
    assert ("volume", "caracal_caracal_state") in removals
    assert ("network", "caracal-runtime") in removals
    assert ("image", "caracal-runtime:latest") in removals
    assert ("path", "/tmp/.caracal") in removals
    assert "Removed keyring entries: caracal/encryption_key" in captured.out
    assert "Caracal purge completed." in captured.out


def test_host_purge_reports_failures(monkeypatch, capsys):
    monkeypatch.setattr(entrypoints, "_confirm_purge", lambda force: True)
    monkeypatch.setattr(entrypoints, "_list_caracal_container_names", lambda: ["caracal-mcp"])
    monkeypatch.setattr(entrypoints, "_list_caracal_volume_names", lambda: [])
    monkeypatch.setattr(entrypoints, "_list_caracal_network_names", lambda: [])
    monkeypatch.setattr(entrypoints, "_list_caracal_image_refs", lambda compose_file=None: [])
    monkeypatch.setattr(entrypoints, "_list_caracal_purge_paths", lambda: [])
    monkeypatch.setattr(entrypoints, "_remove_container", lambda name: False)
    monkeypatch.setattr(entrypoints, "_purge_keyring_credentials", lambda: False)

    namespace = argparse.Namespace(force=True, compose_file=None)
    code = entrypoints._host_purge(namespace)

    captured = capsys.readouterr()
    assert code == 1
    assert "container:caracal-mcp" in captured.err
