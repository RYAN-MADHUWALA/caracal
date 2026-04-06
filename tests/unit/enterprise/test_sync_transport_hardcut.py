"""Static guards for explicit sync and gateway transport behavior."""

from __future__ import annotations

from pathlib import Path


_CARACAL_ROOT = Path(__file__).resolve().parents[3]


def test_enterprise_sync_modules_have_no_candidate_url_fallbacks() -> None:
    license_payload = (_CARACAL_ROOT / "caracal" / "enterprise" / "license.py").read_text(encoding="utf-8")
    sync_payload = (_CARACAL_ROOT / "caracal" / "enterprise" / "sync.py").read_text(encoding="utf-8")
    gateway_payload = (_CARACAL_ROOT / "caracal" / "flow" / "screens" / "gateway_flow.py").read_text(encoding="utf-8")

    assert "_candidate_api_urls" not in license_payload
    assert "_candidate_api_urls" not in sync_payload
    assert "_candidate_api_urls" not in gateway_payload


def test_sync_status_and_gateway_flow_have_no_hidden_transport_fallback_state() -> None:
    sync_payload = (_CARACAL_ROOT / "caracal" / "enterprise" / "sync.py").read_text(encoding="utf-8")
    gateway_payload = (_CARACAL_ROOT / "caracal" / "flow" / "screens" / "gateway_flow.py").read_text(encoding="utf-8")

    assert '"source": "cache"' not in sync_payload
    assert "_persist_resolved_gateway_endpoint" not in gateway_payload
