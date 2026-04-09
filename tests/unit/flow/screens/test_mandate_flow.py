"""Unit tests for TUI mandate flow tool-registry issuance path."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from rich.console import Console

import caracal.flow.screens.mandate_flow as mandate_flow_module
from caracal.flow.screens.mandate_flow import MandateFlow


class _FakePrompt:
    def __init__(self):
        self._uuid_values = iter([
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ])
        self._select_values = iter([
            "all",
            "tool.one",
            "done",
        ])

    def uuid(self, _label, _items):
        return next(self._uuid_values)

    def select(self, _label, choices=None, default=None):
        del choices, default
        return next(self._select_values)

    def number(self, _label, default=None, min_value=None, max_value=None):
        del default, min_value, max_value
        return 3600

    def confirm(self, _label, default=False):
        del default
        return True


@pytest.mark.unit
def test_issue_mandate_derives_scopes_from_registered_tool_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    principal_rows = [
        SimpleNamespace(principal_id=uuid4(), name="issuer"),
        SimpleNamespace(principal_id=uuid4(), name="subject"),
    ]
    registered_tool_rows = [
        SimpleNamespace(tool_id="tool.one", active=True, provider_name="endframe"),
    ]
    policy_rows = [SimpleNamespace(allow_delegation=True, max_network_distance=2)]

    class _Query:
        def __init__(self, rows):
            self._rows = list(rows)

        def all(self):
            return list(self._rows)

        def filter_by(self, **kwargs):
            rows = [
                row for row in self._rows
                if all(getattr(row, key, None) == value for key, value in kwargs.items())
            ]
            return _Query(rows)

        def order_by(self, *_args, **_kwargs):
            return self

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self._rows[0] if self._rows else None

    class _Session:
        def query(self, model):
            if model.__name__ == "Principal":
                return _Query(principal_rows)
            if model.__name__ == "RegisteredTool":
                return _Query(registered_tool_rows)
            if model.__name__ == "AuthorityPolicy":
                return _Query(policy_rows)
            raise AssertionError(f"Unexpected model query: {model}")

    class _Scope:
        def __init__(self, session):
            self._session = session

        def __enter__(self):
            return self._session

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    class _DBManager:
        def __init__(self):
            self._session = _Session()

        def session_scope(self):
            return _Scope(self._session)

        def close(self):
            return None

    fake_db_manager = _DBManager()

    issued_payload: dict[str, object] = {}

    class _FakeMandateManager:
        def __init__(self, db_session):
            self.db_session = db_session

        def issue_mandate(
            self,
            *,
            issuer_id,
            subject_id,
            resource_scope,
            action_scope,
            validity_seconds,
            network_distance,
        ):
            issued_payload["issuer_id"] = issuer_id
            issued_payload["subject_id"] = subject_id
            issued_payload["resource_scope"] = list(resource_scope)
            issued_payload["action_scope"] = list(action_scope)
            issued_payload["validity_seconds"] = validity_seconds
            issued_payload["network_distance"] = network_distance
            return SimpleNamespace(
                mandate_id=uuid4(),
                valid_until=datetime.utcnow() + timedelta(hours=1),
                network_distance=network_distance if network_distance is not None else 2,
            )

    tool_contract = {
        "tool_ids": ["tool.one"],
        "providers": ["endframe"],
        "resource_scope": ["provider:endframe:resource:deployments"],
        "action_scope": ["provider:endframe:action:invoke"],
    }

    resolve_fn = Mock(return_value=tool_contract)
    validate_mock_calls = {}

    def _validate_provider_scopes(**kwargs):
        validate_mock_calls.update(kwargs)

    monkeypatch.setattr("caracal.db.connection.get_db_manager", lambda: fake_db_manager)
    monkeypatch.setattr("caracal.core.mandate.MandateManager", _FakeMandateManager)
    monkeypatch.setattr(mandate_flow_module, "resolve_issue_scopes_from_tool_ids", resolve_fn)
    monkeypatch.setattr(mandate_flow_module, "validate_provider_scopes", _validate_provider_scopes)
    monkeypatch.setattr(MandateFlow, "_resolve_active_workspace_name", staticmethod(lambda: "test-workspace"))

    flow = MandateFlow(console=Console(record=True))
    flow.prompt = _FakePrompt()

    flow.issue_mandate()

    resolve_fn.assert_called_once()
    resolve_kwargs = resolve_fn.call_args.kwargs
    assert resolve_kwargs["tool_ids"] == ["tool.one"]
    assert issued_payload["resource_scope"] == ["provider:endframe:resource:deployments"]
    assert issued_payload["action_scope"] == ["provider:endframe:action:invoke"]
    assert validate_mock_calls["resource_scopes"] == ["provider:endframe:resource:deployments"]
    assert validate_mock_calls["action_scopes"] == ["provider:endframe:action:invoke"]
