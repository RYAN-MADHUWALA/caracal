"""Unit tests for enterprise sync token sourcing behavior."""

from __future__ import annotations

import pytest

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
