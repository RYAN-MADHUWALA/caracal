from caracal.provider.catalog import (
    PROVIDER_PATTERNS,
    build_provider_record,
    build_resources_from_pattern,
    resolve_auth_headers,
    workspace_to_gateway_payload,
)


def test_build_provider_record_tracks_resources_and_actions():
    resources = build_resources_from_pattern(PROVIDER_PATTERNS["ai"][0])

    record = build_provider_record(
        name="openai-main",
        service_type="ai",
        definition_id="openai.chat.api",
        auth_scheme="bearer",
        base_url="https://api.openai.com",
        resources=resources,
        credential_ref="provider_openai-main_credential",
    )

    assert record["provider_id"] == "openai-main"
    assert record["provider_definition"] == "openai.chat.api"
    assert record["resources"] == ["embeddings", "models", "responses"]
    assert "create" in record["actions"]
    assert record["provider_definition_data"]["resources"]["responses"]["actions"]["create"]["method"] == "POST"


def test_resolve_auth_headers_uses_api_key_header_by_default():
    assert resolve_auth_headers(auth_scheme="api_key", credential_value="secret-token") == {
        "X-API-Key": "secret-token"
    }


def test_resolve_auth_headers_uses_custom_header_name_when_provided():
    assert resolve_auth_headers(
        auth_scheme="header",
        credential_value="abc123",
        auth_metadata={"header_name": "X-Custom-Key"},
    ) == {"X-Custom-Key": "abc123"}


def test_workspace_to_gateway_payload_preserves_contract_shape():
    resources = build_resources_from_pattern(PROVIDER_PATTERNS["application"][0])
    workspace_entry = build_provider_record(
        name="crm-main",
        service_type="application",
        definition_id="crm-main",
        auth_scheme="bearer",
        base_url="https://crm.example.com",
        resources=resources,
        credential_ref="provider_crm-main_credential",
    )

    gateway_payload = workspace_to_gateway_payload(
        "crm-main",
        workspace_entry,
        organization_id="org-123",
    )

    assert gateway_payload["organization_id"] == "org-123"
    assert gateway_payload["credential_storage"] == "gateway_vault"
    assert gateway_payload["provider_definition_data"]["resources"]["records"]["actions"]["create"]["path_prefix"] == "/v1/records"
