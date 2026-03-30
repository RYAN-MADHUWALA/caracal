"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

SDK Secret Resolution — tier-aware, gateway-routed.

SecretsAdapter resolves secret refs based on the org's subscription tier.
Secret values are NEVER logged.

Usage:
    adapter = SecretsAdapter(tier="starter", org_id="org-abc")
    value = adapter.resolve("caracal:prod/openai_key")
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Sentinel to mark that a value must not be logged
_REDACTED = "<redacted>"

_STARTER_TIERS = {"starter"}
_AWS_TIERS = {"growth", "scale", "enterprise"}


class SecretsAdapterError(Exception):
    """Raised when secret resolution fails."""


class SecretsAdapter:
    """
    Tier-aware secret resolver for SDK consumers.

    Delegates to the appropriate backend based on tier:
      Starter  → CaracalVaultBackend (gateway-side resolution)
      Growth+  → AWSSecretsManagerBackend

    Secret values are never included in log output.
    """

    def __init__(self, tier: str, org_id: str, env_id: str = "default") -> None:
        self._tier = tier.lower()
        self._org_id = org_id
        self._env_id = env_id
        self._backend = self._create_backend()
        logger.info(
            "SecretsAdapter initialized (tier=%s, backend=%s)",
            self._tier, self._backend.name,
        )

    def _create_backend(self):
        try:
            from caracalEnterprise.services.gateway.secret_manager import backend_for_tier

            return backend_for_tier(self._tier, self._org_id)
        except ModuleNotFoundError as exc:
            if exc.name != "caracalEnterprise":
                raise

            logger.warning(
                "caracalEnterprise package not available; using SDK local secret backend fallback"
            )
            return _local_backend_for_tier(self._tier, self._org_id)

    def resolve(self, ref: str) -> str:
        """
        Resolve *ref* to a plaintext secret value.

        Raises SecretsAdapterError if the ref cannot be resolved.
        The return value is never logged by this method.
        """
        if not ref:
            raise SecretsAdapterError("Secret ref must not be empty.")
        try:
            value = self._backend.get(ref)
            logger.debug("Resolved secret ref=%r (value: %s)", ref, _REDACTED)
            return value
        except Exception as exc:
            raise SecretsAdapterError(f"Failed to resolve secret ref={ref!r}: {exc}") from exc

    def store(self, ref: str, value: str) -> None:
        """
        Store a secret at *ref*.

        Value is never logged.
        """
        if not ref:
            raise SecretsAdapterError("Secret ref must not be empty.")
        if not value:
            raise SecretsAdapterError("Secret value must not be empty.")
        try:
            self._backend.put(ref, value)
            logger.info("Stored secret ref=%r (value: %s)", ref, _REDACTED)
        except Exception as exc:
            raise SecretsAdapterError(f"Failed to store secret ref={ref!r}: {exc}") from exc

    def delete(self, ref: str) -> None:
        """Remove the secret at *ref*."""
        try:
            self._backend.delete(ref)
            logger.info("Deleted secret ref=%r", ref)
        except Exception as exc:
            raise SecretsAdapterError(f"Failed to delete secret ref={ref!r}: {exc}") from exc

    def list_refs(self) -> list[str]:
        """List all secret refs for the configured org and env."""
        try:
            return self._backend.list_refs(self._org_id, self._env_id)
        except Exception as exc:
            raise SecretsAdapterError(f"Failed to list secrets: {exc}") from exc

    def ref_for(self, name: str) -> str:
        """
        Construct the canonical ref for *name* based on tier.

          Starter  → caracal:{env_id}/{name}
          Growth+  → aws:{org_id}/{env_id}/{name}
        """
        if self._tier in _STARTER_TIERS:
            return f"caracal:{self._env_id}/{name}"
        return f"aws:{self._org_id}/{self._env_id}/{name}"

    @property
    def backend_name(self) -> str:
        return self._backend.name

    @property
    def tier(self) -> str:
        return self._tier


class _LocalCaracalVaultBackend:
    """Starter-tier fallback backend that talks directly to CaracalVault."""

    def __init__(self, org_id: str) -> None:
        self._org_id = org_id

    @property
    def name(self) -> str:
        return "caracal_vault"

    def _parse_ref(self, ref: str) -> tuple[str, str]:
        clean = ref.removeprefix("caracal:").strip()
        if "/" not in clean:
            raise SecretsAdapterError(
                f"Invalid CaracalVault ref format: {ref!r}. Expected 'caracal:{{env_id}}/{{secret_name}}'."
            )
        return clean.split("/", 1)

    def get(self, ref: str) -> str:
        env_id, name = self._parse_ref(ref)
        from caracal.core.vault import get_vault, gateway_context

        with gateway_context():
            return get_vault().get(self._org_id, env_id, name)

    def put(self, ref: str, value: str) -> None:
        env_id, name = self._parse_ref(ref)
        from caracal.core.vault import get_vault, gateway_context

        with gateway_context():
            get_vault().put(self._org_id, env_id, name, value)

    def delete(self, ref: str) -> None:
        env_id, name = self._parse_ref(ref)
        from caracal.core.vault import get_vault, gateway_context

        with gateway_context():
            get_vault().delete(self._org_id, env_id, name)

    def list_refs(self, org_id: str, env_id: str) -> list[str]:
        from caracal.core.vault import get_vault, gateway_context

        with gateway_context():
            names = get_vault().list_secrets(org_id, env_id)
        return [f"caracal:{env_id}/{name}" for name in names]


class _LocalAWSSecretsManagerBackend:
    """Growth/enterprise fallback backend using boto3 directly."""

    def __init__(self, region: Optional[str] = None) -> None:
        import os

        self._region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    @property
    def name(self) -> str:
        return "aws_secrets_manager"

    def _client(self):
        try:
            import boto3  # type: ignore

            return boto3.client("secretsmanager", region_name=self._region)
        except ImportError as exc:
            raise SecretsAdapterError("boto3 is not installed. Run: pip install boto3") from exc

    def _parse_ref(self, ref: str) -> tuple[str, Optional[str]]:
        clean = ref.removeprefix("aws:").strip()
        if "#" in clean:
            secret_id, key = clean.rsplit("#", 1)
            return secret_id, key
        return clean, None

    def get(self, ref: str) -> str:
        secret_id, key = self._parse_ref(ref)
        try:
            resp = self._client().get_secret_value(SecretId=secret_id)
            raw = resp.get("SecretString") or resp.get("SecretBinary", b"").decode()
            if key:
                import json

                payload = json.loads(raw)
                if key not in payload:
                    raise SecretsAdapterError(f"Key '{key}' not found in AWS secret '{secret_id}'.")
                return payload[key]
            return raw
        except SecretsAdapterError:
            raise
        except Exception as exc:
            raise SecretsAdapterError(f"AWS lookup failed for ref={ref!r}: {exc}") from exc

    def put(self, ref: str, value: str) -> None:
        secret_id, key = self._parse_ref(ref)
        client = self._client()
        try:
            if key:
                import json

                try:
                    existing = json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
                except client.exceptions.ResourceNotFoundException:
                    existing = {}
                existing[key] = value
                payload = json.dumps(existing)
            else:
                payload = value

            try:
                client.put_secret_value(SecretId=secret_id, SecretString=payload)
            except client.exceptions.ResourceNotFoundException:
                client.create_secret(Name=secret_id, SecretString=payload)
        except Exception as exc:
            raise SecretsAdapterError(f"AWS write failed for ref={ref!r}: {exc}") from exc

    def delete(self, ref: str) -> None:
        secret_id, _ = self._parse_ref(ref)
        try:
            self._client().delete_secret(SecretId=secret_id, ForceDeleteWithoutRecovery=False)
        except Exception as exc:
            raise SecretsAdapterError(f"AWS delete failed for ref={ref!r}: {exc}") from exc

    def list_refs(self, org_id: str, env_id: str) -> list[str]:
        try:
            paginator = self._client().get_paginator("list_secrets")
            refs: list[str] = []
            filter_prefix = f"{org_id}/{env_id}/"
            for page in paginator.paginate(Filters=[{"Key": "name", "Values": [filter_prefix]}]):
                for secret in page.get("SecretList", []):
                    refs.append(f"aws:{secret['Name']}")
            return refs
        except Exception as exc:
            raise SecretsAdapterError(f"AWS list failed for org={org_id} env={env_id}: {exc}") from exc


def _local_backend_for_tier(tier: str, org_id: str):
    t = tier.lower()
    if t in _STARTER_TIERS:
        return _LocalCaracalVaultBackend(org_id=org_id)
    if t in _AWS_TIERS:
        return _LocalAWSSecretsManagerBackend()
    raise SecretsAdapterError(
        f"Unsupported tier '{tier}' for secret management. Valid tiers: {sorted(_STARTER_TIERS | _AWS_TIERS)}"
    )
