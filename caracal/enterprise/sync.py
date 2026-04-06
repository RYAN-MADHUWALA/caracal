"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Enterprise Sync Client.

Pushes local Caracal Core data (principals, policies, mandates, ledger
entries) to the Caracal Enterprise dashboard.

Authentication is done via a sync API key that is generated during
license validation.  The key is stored in enterprise runtime metadata
and used automatically for subsequent syncs.

Usage::

    from caracal.enterprise.sync import EnterpriseSyncClient
    from caracal.deployment.enterprise_sync_payload import build_enterprise_sync_payload

    client = EnterpriseSyncClient()        # uses stored config
    payload = build_enterprise_sync_payload(client_instance_id="client-1")
    result = client.upload_payload(payload)
    print(result)

    status = client.get_sync_status()      # check last sync
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from caracal.enterprise.license import (
    _build_client_metadata,
    _get_or_create_client_instance_id,
    _get_json,
    _resolve_api_url,
    load_enterprise_config,
    save_enterprise_config,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _get_json_with_retry(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    max_attempts: int = 3,
    backoff_base: float = 1.5,
) -> Dict[str, Any]:
    """Call _get_json with exponential-backoff retry on transient failures.

    Retries on network errors and HTTP 5xx responses.  HTTPError with a
    4xx status is re-raised immediately (no retry — auth/config issue).
    """
    import time

    attempt = 0
    last_exc: Exception = RuntimeError("No attempts made")
    while attempt < max_attempts:
        try:
            return _get_json(url, headers=headers)
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise  # 4xx — auth/config problem, don't retry
            last_exc = exc
        except (urllib.error.URLError, OSError) as exc:
            last_exc = exc

        attempt += 1
        if attempt < max_attempts:
            wait = backoff_base ** attempt
            logger.debug(
                "Gateway sync attempt %d/%d failed (%s), retrying in %.1fs…",
                attempt,
                max_attempts,
                last_exc,
                wait,
            )
            time.sleep(wait)

    raise last_exc

@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    message: str
    synced_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "synced_counts": self.synced_counts,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Sync Client
# ---------------------------------------------------------------------------

class EnterpriseSyncClient:
    """Client for syncing local Caracal data to Enterprise dashboard.

    Uses the sync API key stored in enterprise runtime metadata (generated
    during license validation) for authentication.

    Gateway configuration pull is exposed as an explicit operation via
    ``pull_gateway_config()`` and is not executed implicitly by ``sync()``.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        sync_api_key: Optional[str] = None,
    ):
        cfg = load_enterprise_config()
        self._api_url = _resolve_api_url(api_url)
        self._sync_api_key = sync_api_key or cfg.get("sync_api_key")
        self._client_instance_id = cfg.get("client_instance_id") or _get_or_create_client_instance_id()

    def _resolve_enterprise_auth_headers(self) -> Dict[str, str]:
        resolved_sync_api_key = str(self._sync_api_key or "").strip()
        if not resolved_sync_api_key:
            raise RuntimeError("Enterprise sync requires a configured sync API key")

        headers: Dict[str, str] = {
            "X-Caracal-Client-Id": self._client_instance_id,
            "X-Sync-Api-Key": resolved_sync_api_key,
        }
        return headers

    @property
    def is_configured(self) -> bool:
        """True if we have enough config to attempt a sync."""
        return bool(self._sync_api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_payload(self, payload: Dict[str, Any]) -> SyncResult:
        """Upload an explicit sync payload to Enterprise."""
        if not self.is_configured:
            return SyncResult(
                success=False,
                message=(
                    "Enterprise sync not configured. "
                    "Run 'caracal flow' → Enterprise → Connect License first."
                ),
            )

        if not self._api_url:
            return SyncResult(
                success=False,
                message=(
                    "Enterprise sync URL is not configured. "
                    "Set CARACAL_ENTERPRISE_URL (or CARACAL_ENTERPRISE_DEV_URL in dev mode)."
                ),
            )

        upload_payload = dict(payload or {})
        upload_payload.setdefault("client_instance_id", self._client_instance_id)
        upload_payload.setdefault("client_metadata", _build_client_metadata())

        try:
            data = json.dumps(upload_payload).encode()
            url = f"{self._api_url}/api/sync/upload"

            headers = self._resolve_enterprise_auth_headers()
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", **headers},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode())
            except urllib.error.URLError as exc:
                return SyncResult(
                    success=False,
                    message=f"Cannot reach Enterprise API at {self._api_url}: {exc.reason}",
                )

            # Update last sync in local config
            cfg = load_enterprise_config()
            cfg["enterprise_api_url"] = self._api_url
            cfg["last_sync"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "counts": result.get("synced_counts", {}),
            }
            save_enterprise_config(cfg)

            errors = result.get("errors", [])

            return SyncResult(
                success=result.get("success", True),
                message=result.get("message", "Sync completed."),
                synced_counts=result.get("synced_counts", {}),
                errors=errors,
            )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode() if exc.fp else ""
            try:
                err = json.loads(body)
                detail = err.get("detail", {})
                if isinstance(detail, dict):
                    msg = detail.get("message", str(detail))
                else:
                    msg = str(detail)
            except json.JSONDecodeError:
                msg = body[:500]
            return SyncResult(success=False, message=f"Sync failed: {msg}")

        except urllib.error.URLError as exc:
            return SyncResult(
                success=False,
                message=f"Cannot reach Enterprise API at {self._api_url}: {exc.reason}",
            )

        except Exception as exc:
            return SyncResult(success=False, message=f"Unexpected sync error: {exc}")

    def pull_gateway_config(self) -> Dict[str, Any]:
        """Pull gateway configuration from the Enterprise API.

        Explicit operation for gateway-connected deployments. The Enterprise
        API's ``/api/gateway/sync-config`` endpoint returns the provisioned
        gateway endpoint, API key, deployment type, and enforcement settings
        for the authenticated organization.

        On success the gateway section of enterprise runtime metadata is updated
        and the gateway feature flags are reloaded.

        Returns:
            Dict with keys ``success``, ``message``, and the full gateway
            config when successful.
        """
        if not self.is_configured:
            return {"success": False, "message": "Enterprise sync not configured."}

        try:
            headers = self._resolve_enterprise_auth_headers()
            url = f"{self._api_url}/api/gateway/sync-config"
            result = _get_json_with_retry(url, headers=headers)

            if not result.get("gateway_configured"):
                return {
                    "success": True,
                    "gateway_configured": False,
                    "message": result.get("message", "No gateway provisioned."),
                }

            # Persist to enterprise runtime metadata gateway section
            cfg = load_enterprise_config()
            cfg["gateway"] = {
                "enabled": True,
                "deployment_type": result.get("deployment_type", "managed"),
                "endpoint": result.get("gateway_endpoint", ""),
                "api_key": result.get("gateway_api_key", ""),
                "fail_closed": result.get("fail_closed", True),
                "use_provider_registry": result.get("use_provider_registry", True),
            }
            cfg["enterprise_api_url"] = self._api_url
            cfg["tier"] = result.get("tier", cfg.get("tier", "starter"))
            save_enterprise_config(cfg)

            # Reload gateway feature flags so the SDK picks up the new config
            try:
                from caracal.core.gateway_features import reset_gateway_features
                reset_gateway_features()
            except ImportError:
                pass

            logger.info(
                "Gateway config synced from Enterprise: %s endpoint=%s",
                result.get("deployment_type"),
                result.get("gateway_endpoint"),
            )

            return {
                "success": True,
                "gateway_configured": True,
                "message": "Gateway configuration synced from Enterprise.",
                **result,
            }

        except Exception as exc:
            logger.warning("Failed to pull gateway config: %s", exc)
            return {
                "success": False,
                "message": f"Failed to pull gateway config: {exc}",
            }

    def get_sync_status(self) -> Dict[str, Any]:
        """Fetch the sync status from the Enterprise API."""
        if not self.is_configured:
            return {"error": "Enterprise sync not configured."}

        try:
            url = f"{self._api_url}/api/sync/status"
            headers = self._resolve_enterprise_auth_headers()
            return _get_json(url, headers=headers)

        except Exception as exc:
            return {"error": f"Cannot fetch sync status: {exc}"}

    def test_connection(self) -> bool:
        """Quick connectivity check to the Enterprise API."""
        if not self.is_configured:
            return False

        for probe_path in ("/health", "/api/health"):
            url = f"{self._api_url}{probe_path}"
            req = urllib.request.Request(
                url,
                headers=self._resolve_enterprise_auth_headers(),
                method="GET",
            )

            try:
                # Any HTTP response means the API is network-reachable.
                with urllib.request.urlopen(req, timeout=5):
                    pass
                return True
            except urllib.error.HTTPError:
                return True
            except Exception:
                continue

        return False
