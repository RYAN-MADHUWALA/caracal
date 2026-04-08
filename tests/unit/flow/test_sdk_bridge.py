import pytest

pytest.importorskip("aiohttp")

from caracal.flow import sdk_bridge


class _FakeClient:
    captured_kwargs: dict = {}

    def __init__(self, **kwargs):
        _FakeClient.captured_kwargs = dict(kwargs)
        self.context = object()
        self._default_scope = object()

    def close(self) -> None:
        return None


def test_sdk_bridge_uses_canonical_client_init_with_legacy_config_path(monkeypatch) -> None:
    monkeypatch.setattr(sdk_bridge, "CaracalClient", _FakeClient)
    monkeypatch.setenv("CARACAL_API_KEY", "env-api-key")
    monkeypatch.setenv("CARACAL_API_PORT", "9010")

    bridge = sdk_bridge.SDKBridge(config_path="/tmp/legacy-config.yaml")

    assert _FakeClient.captured_kwargs == {
        "api_key": "env-api-key",
        "base_url": "http://localhost:9010",
    }
    assert bridge.current_scope is None


def test_sdk_bridge_explicit_params_override_environment(monkeypatch) -> None:
    monkeypatch.setattr(sdk_bridge, "CaracalClient", _FakeClient)
    monkeypatch.setenv("CARACAL_API_KEY", "env-api-key")
    monkeypatch.setenv("CARACAL_API_URL", "http://env.example")

    bridge = sdk_bridge.SDKBridge(
        api_key="explicit-key",
        base_url="https://api.example",
    )

    assert _FakeClient.captured_kwargs == {
        "api_key": "explicit-key",
        "base_url": "https://api.example",
    }
    assert bridge.current_scope is None