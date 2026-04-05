"""Unit tests for AIS runtime lifecycle wiring in runtime entrypoints."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from caracal.identity.attestation_nonce import AttestationNonceConsumedError
from caracal.runtime import entrypoints


@dataclass
class _FakeAisProcess:
    poll_values: list[int | None]

    def __post_init__(self) -> None:
        self._index = 0

    def poll(self) -> int | None:
        if self._index >= len(self.poll_values):
            return self.poll_values[-1] if self.poll_values else None
        value = self.poll_values[self._index]
        self._index += 1
        return value


@dataclass
class _FakeMcpProcess:
    poll_values: list[int | None]

    def __post_init__(self) -> None:
        self._index = 0

    def poll(self) -> int | None:
        if self._index >= len(self.poll_values):
            return self.poll_values[-1] if self.poll_values else 0
        value = self.poll_values[self._index]
        self._index += 1
        return value


@pytest.mark.unit
def test_consume_ais_startup_attestation_requires_nonce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(entrypoints.AIS_STARTUP_NONCE_ENV, raising=False)

    with pytest.raises(RuntimeError, match=entrypoints.AIS_STARTUP_NONCE_ENV):
        entrypoints._consume_ais_startup_attestation(
            nonce_manager_factory=lambda: object(),
        )


@pytest.mark.unit
def test_consume_ais_startup_attestation_rejects_consumed_nonce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Manager:
        def consume_nonce(self, nonce: str, *, expected_principal_id: str | None = None) -> str:
            raise AttestationNonceConsumedError("missing")

    monkeypatch.setenv(entrypoints.AIS_STARTUP_NONCE_ENV, "nonce-1")

    with pytest.raises(RuntimeError, match="invalid or already consumed"):
        entrypoints._consume_ais_startup_attestation(
            nonce_manager_factory=lambda: _Manager(),
        )


@pytest.mark.unit
def test_consume_ais_startup_attestation_passes_expected_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str | None] = {}

    class _Manager:
        def consume_nonce(self, nonce: str, *, expected_principal_id: str | None = None) -> str:
            seen["nonce"] = nonce
            seen["expected"] = expected_principal_id
            return "principal-1"

    monkeypatch.setenv(entrypoints.AIS_STARTUP_NONCE_ENV, "nonce-2")
    monkeypatch.setenv(entrypoints.AIS_STARTUP_PRINCIPAL_ENV, "principal-1")

    principal_id = entrypoints._consume_ais_startup_attestation(
        nonce_manager_factory=lambda: _Manager(),
    )

    assert principal_id == "principal-1"
    assert seen == {"nonce": "nonce-2", "expected": "principal-1"}


@pytest.mark.unit
def test_run_local_caracal_routes_runtime_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entrypoints, "_run_runtime_mcp", lambda: 17)

    with pytest.raises(SystemExit) as exc_info:
        entrypoints._run_local_caracal(("runtime-mcp",))

    assert int(exc_info.value.code) == 17


@pytest.mark.unit
def test_run_local_caracal_routes_ais_serve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entrypoints, "_run_ais_server", lambda: 9)

    with pytest.raises(SystemExit) as exc_info:
        entrypoints._run_local_caracal(("ais-serve",))

    assert int(exc_info.value.code) == 9


@pytest.mark.unit
def test_wait_for_ais_healthy_returns_true_after_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    checks = iter([False, True])

    monkeypatch.setattr(entrypoints, "_check_ais_health", lambda *_args, **_kwargs: next(checks))
    monkeypatch.setattr(entrypoints.time, "sleep", lambda *_args, **_kwargs: None)

    assert entrypoints._wait_for_ais_healthy(object(), timeout_seconds=2, probe_timeout_seconds=0.1)


@pytest.mark.unit
def test_run_runtime_mcp_restarts_ais_when_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    ais_processes = [
        _FakeAisProcess([None, None, None]),
        _FakeAisProcess([None, None]),
    ]
    mcp_process = _FakeMcpProcess([None, 0])
    started: list[_FakeAisProcess] = []
    terminated: list[object] = []
    health_checks = iter([False])

    monkeypatch.setattr(entrypoints, "assert_runtime_hardcut", lambda **_kwargs: None)
    monkeypatch.setattr(entrypoints, "_create_ais_server_config", lambda: object())
    monkeypatch.setattr(entrypoints, "_wait_for_ais_healthy", lambda *_args, **_kwargs: True)

    def _start_ais() -> _FakeAisProcess:
        process = ais_processes[len(started)]
        started.append(process)
        return process

    monkeypatch.setattr(entrypoints, "_start_ais_subprocess", _start_ais)
    monkeypatch.setattr(entrypoints.subprocess, "Popen", lambda *_args, **_kwargs: mcp_process)
    monkeypatch.setattr(
        entrypoints,
        "_check_ais_health",
        lambda *_args, **_kwargs: next(health_checks, True),
    )
    monkeypatch.setattr(entrypoints, "_terminate_subprocess", lambda process: terminated.append(process))
    monkeypatch.setattr(entrypoints.time, "sleep", lambda *_args, **_kwargs: None)

    exit_code = entrypoints._run_runtime_mcp()

    assert exit_code == 0
    assert len(started) == 2
    assert ais_processes[0] in terminated
    assert ais_processes[1] in terminated
