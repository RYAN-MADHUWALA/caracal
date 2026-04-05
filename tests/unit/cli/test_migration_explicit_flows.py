"""Unit tests for explicit hard-cut migration CLI commands."""

from __future__ import annotations

from click.testing import CliRunner
import pytest

import caracal.cli.migration as migration_cli
from caracal.cli.migration import migrate_group


@pytest.mark.unit
def test_oss_to_enterprise_command_uses_selected_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {}

    class _FakeManager:
        def migrate_credentials_oss_to_enterprise(self, **kwargs):
            calls.update(kwargs)
            return {
                "workspaces": ["alpha"],
                "credentials_selected": 2,
                "dry_run": False,
                "decisions": [],
            }

    monkeypatch.setattr(
        migration_cli,
        "_enforce_explicit_hardcut_migration_policy",
        lambda: None,
    )
    monkeypatch.setattr(migration_cli, "MigrationManager", lambda: _FakeManager())

    runner = CliRunner()
    result = runner.invoke(
        migrate_group,
        [
            "oss-to-enterprise",
            "--gateway-url",
            "https://enterprise.example.com",
            "--migrate-credential",
            "cred_one",
            "--migrate-credential",
            "cred_two",
        ],
    )

    assert result.exit_code == 0
    assert calls["include_credentials"] == ["cred_one", "cred_two"]


@pytest.mark.unit
def test_enterprise_to_oss_command_parses_import_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {}

    class _FakeManager:
        def migrate_credentials_enterprise_to_oss(self, **kwargs):
            calls.update(kwargs)
            return {
                "workspaces": ["alpha"],
                "credentials_selected": 1,
                "credentials_imported": 1,
                "license_deactivated": False,
                "dry_run": False,
                "decisions": [],
            }

    monkeypatch.setattr(
        migration_cli,
        "_enforce_explicit_hardcut_migration_policy",
        lambda: None,
    )
    monkeypatch.setattr(migration_cli, "MigrationManager", lambda: _FakeManager())

    runner = CliRunner()
    result = runner.invoke(
        migrate_group,
        [
            "enterprise-to-oss",
            "--migrate-credential",
            "provider_api_key",
            "--import-credential",
            "provider_api_key=secret-123",
        ],
    )

    assert result.exit_code == 0
    assert calls["include_credentials"] == ["provider_api_key"]
    assert calls["exported_credentials"] == {"provider_api_key": "secret-123"}
