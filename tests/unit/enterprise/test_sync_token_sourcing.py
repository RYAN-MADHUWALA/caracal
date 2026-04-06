"""Unit tests for enterprise sync token sourcing behavior."""

from __future__ import annotations

import pytest

import caracal.enterprise.license as enterprise_license
import caracal.enterprise.sync as enterprise_sync


@pytest.fixture
def patched_client_factory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(enterprise_sync, "_resolve_api_url", lambda _override=None: "https://enterprise.example")
    monkeypatch.setattr(enterprise_sync, "_get_or_create_client_instance_id", lambda: "client-1")

    def _factory(*, sync_api_key: str | None = "sync-key", license_key: str | None = "license-key"):
        monkeypatch.setattr(enterprise_sync, "load_enterprise_config", lambda: {})
        return enterprise_sync.EnterpriseSyncClient(
            sync_api_key=sync_api_key,
            license_key=license_key,
        )

    return _factory


@pytest.mark.unit
def test_human_session_falls_back_to_sync_key_headers(
    monkeypatch: pytest.MonkeyPatch,
    patched_client_factory,
) -> None:
    monkeypatch.setenv("CARACAL_SESSION_KIND", "human")
    monkeypatch.delenv("CARACAL_AIS_BASE_URL", raising=False)

    client = patched_client_factory(sync_api_key="sync-local")
    headers = client._resolve_enterprise_auth_headers()

    assert headers["X-Caracal-Client-Id"] == "client-1"
    assert headers["X-Sync-Api-Key"] == "sync-local"
    assert "Authorization" not in headers


@pytest.mark.unit
def test_non_human_session_requires_ais_token_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    patched_client_factory,
) -> None:
    monkeypatch.setenv("CARACAL_SESSION_KIND", "automation")
    monkeypatch.delenv("CARACAL_AIS_BASE_URL", raising=False)

    client = patched_client_factory(sync_api_key="sync-local")

    with pytest.raises(RuntimeError, match="AIS token endpoint"):
        client._resolve_enterprise_auth_headers()


@pytest.mark.unit
def test_non_human_session_prefers_ais_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
    patched_client_factory,
) -> None:
    monkeypatch.setenv("CARACAL_SESSION_KIND", "automation")
    monkeypatch.setenv("CARACAL_AIS_BASE_URL", "http://ais.local")
    monkeypatch.setenv("CARACAL_AIS_PRINCIPAL_ID", "principal-1")
    monkeypatch.setenv("CARACAL_AIS_ORGANIZATION_ID", "org-1")
    monkeypatch.setenv("CARACAL_AIS_TENANT_ID", "tenant-1")
    monkeypatch.setattr(enterprise_sync, "_post_json", lambda *_args, **_kwargs: {"access_token": "ais-token"})

    client = patched_client_factory(sync_api_key="sync-local")
    headers = client._resolve_enterprise_auth_headers()

    assert headers["X-Caracal-Client-Id"] == "client-1"
    assert headers["Authorization"] == "Bearer ais-token"
    assert "X-Sync-Api-Key" not in headers


@pytest.mark.unit
def test_human_session_falls_back_when_ais_request_fails(
    monkeypatch: pytest.MonkeyPatch,
    patched_client_factory,
) -> None:
    monkeypatch.setenv("CARACAL_SESSION_KIND", "human")
    monkeypatch.setenv("CARACAL_AIS_BASE_URL", "http://ais.local")
    monkeypatch.setenv("CARACAL_AIS_PRINCIPAL_ID", "principal-1")
    monkeypatch.setenv("CARACAL_AIS_ORGANIZATION_ID", "org-1")
    monkeypatch.setenv("CARACAL_AIS_TENANT_ID", "tenant-1")

    def _raise(*_args, **_kwargs):
        raise ConnectionError("ais unreachable")

    monkeypatch.setattr(enterprise_sync, "_post_json", _raise)

    client = patched_client_factory(sync_api_key="sync-local")
    headers = client._resolve_enterprise_auth_headers()

    assert headers["X-Sync-Api-Key"] == "sync-local"
    assert "Authorization" not in headers


@pytest.mark.unit
def test_non_human_session_requires_identity_triplet_for_ais(
    monkeypatch: pytest.MonkeyPatch,
    patched_client_factory,
) -> None:
    monkeypatch.setenv("CARACAL_SESSION_KIND", "automation")
    monkeypatch.setenv("CARACAL_AIS_BASE_URL", "http://ais.local")
    monkeypatch.delenv("CARACAL_AIS_PRINCIPAL_ID", raising=False)
    monkeypatch.delenv("CARACAL_AIS_ORGANIZATION_ID", raising=False)
    monkeypatch.delenv("CARACAL_AIS_TENANT_ID", raising=False)

    client = patched_client_factory(sync_api_key="sync-local")

    with pytest.raises(RuntimeError, match="principal, organization, and tenant"):
        client._resolve_enterprise_auth_headers()


@pytest.mark.unit
def test_resolve_revocation_webhook_target_uses_override_and_cached_sync_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enterprise_license,
        "load_enterprise_config",
        lambda: {"sync_api_key": "sync-key-1"},
    )

    webhook_url, sync_api_key = enterprise_license.resolve_revocation_webhook_target(
        webhook_url_override="https://enterprise.example/custom-revocations",
    )

    assert webhook_url == "https://enterprise.example/custom-revocations"
    assert sync_api_key == "sync-key-1"


@pytest.mark.unit
def test_resolve_revocation_webhook_target_builds_default_sync_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enterprise_license,
        "load_enterprise_config",
        lambda: {
            "enterprise_api_url": "https://enterprise.example",
            "sync_api_key": "sync-key-2",
        },
    )
    monkeypatch.setattr(
        enterprise_license,
        "_resolve_api_url",
        lambda override=None: (override or "https://enterprise.example").rstrip("/"),
    )

    webhook_url, sync_api_key = enterprise_license.resolve_revocation_webhook_target()

    assert webhook_url == "https://enterprise.example/api/sync/revocation-events"
    assert sync_api_key == "sync-key-2"


@pytest.mark.unit
def test_license_validation_fails_closed_when_api_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(enterprise_license, "_resolve_api_url", lambda override=None: "")

    validator = enterprise_license.EnterpriseLicenseValidator()
    result = validator.validate_license("license-key-1")

    assert result.valid is False
    assert "requires a live Enterprise API" in result.message


@pytest.mark.unit
def test_license_validation_fails_closed_when_api_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(enterprise_license, "_resolve_api_url", lambda override=None: "https://enterprise.example")
    monkeypatch.setattr(
        enterprise_license,
        "_candidate_api_urls",
        lambda base_url: [base_url],
    )
    monkeypatch.setattr(enterprise_license, "_get_or_create_client_instance_id", lambda: "client-1")
    monkeypatch.setattr(
        enterprise_license,
        "_post_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionError("offline")),
    )

    validator = enterprise_license.EnterpriseLicenseValidator()
    result = validator.validate_license("license-key-1")

    assert result.valid is False
    assert "requires a live Enterprise API" in result.message


@pytest.mark.unit
def test_license_validation_request_has_no_password_field(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_payload: dict[str, object] = {}

    monkeypatch.setattr(enterprise_license, "_resolve_api_url", lambda override=None: "https://enterprise.example")
    monkeypatch.setattr(enterprise_license, "_candidate_api_urls", lambda base_url: [base_url])
    monkeypatch.setattr(enterprise_license, "_get_or_create_client_instance_id", lambda: "client-1")

    def _capture_post(_url: str, payload: dict, timeout: int = 15) -> dict:
        captured_payload.update(payload)
        return {
            "valid": True,
            "message": "ok",
            "tier": "starter",
            "features": {},
            "enterprise_api_url": "https://enterprise.example",
        }

    monkeypatch.setattr(enterprise_license, "_post_json", _capture_post)
    monkeypatch.setattr(
        enterprise_license.EnterpriseLicenseValidator,
        "_persist_license",
        lambda self, **kwargs: None,
    )

    validator = enterprise_license.EnterpriseLicenseValidator()
    result = validator.validate_license("license-key-1")

    assert result.valid is True
    assert "password" not in captured_payload


@pytest.mark.unit
def test_resolve_api_url_ignores_removed_legacy_gateway_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(enterprise_license, "load_enterprise_config", lambda: {})
    monkeypatch.setattr(enterprise_license, "_load_workspace_dotenv", lambda: {})
    monkeypatch.delenv("CARACAL_ENTERPRISE_URL", raising=False)
    monkeypatch.delenv("CARACAL_ENTERPRISE_DEV_URL", raising=False)
    monkeypatch.delenv("CARACAL_ENTERPRISE_DEFAULT_URL", raising=False)
    monkeypatch.setenv("CARACAL_ENTERPRISE_API_URL", "https://legacy-enterprise.example")
    monkeypatch.setenv("CARACAL_GATEWAY_URL", "https://legacy-gateway.example")

    resolved = enterprise_license._resolve_api_url()

    assert resolved == "https://www.garudexlabs.com"
