"""
Configuration encryption utilities backed by AWS KMS.

Model:
- All encrypted payloads are handled directly by AWS KMS.
- No local master key, salt, or DEK files are used.
- Encrypted payloads use strict versioned format ENC[v3:...].
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from caracal.logging_config import get_logger
from caracal.storage.layout import CaracalLayout, append_key_audit_event, get_caracal_layout

logger = get_logger(__name__)


class MasterKeyError(RuntimeError):
    """Raised when KMS key access fails or violates strict behavior."""


@dataclass
class RotationSummary:
    """Result from requesting master-key rotation at the KMS layer."""

    rewrapped_deks: int
    rotated_at: str


class ConfigEncryption:
    """Encrypt/decrypt config values using AWS KMS."""

    ENCRYPTED_PREFIX = "ENC[v3:"
    ENCRYPTED_SUFFIX = "]"

    def __init__(
        self,
        layout: Optional[CaracalLayout] = None,
        dek_name: str = "config.default",
        actor: str = "system",
    ):
        self.layout = layout or get_caracal_layout()
        self.actor = actor
        self.dek_name = dek_name
        self.key_id = os.getenv("CARACAL_AWS_KMS_KEY_ID") or os.getenv("AWS_KMS_KEY_ID")
        self.region = os.getenv("CARACAL_AWS_REGION") or os.getenv("AWS_REGION")

    def _get_kms_client(self):
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise MasterKeyError("boto3 is required for AWS KMS-backed config encryption") from exc

        if not self.key_id:
            raise MasterKeyError(
                "CARACAL_AWS_KMS_KEY_ID (or AWS_KMS_KEY_ID) must be configured for config encryption"
            )

        session = boto3.session.Session(region_name=self.region) if self.region else boto3.session.Session()
        return session.client("kms")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext value under the configured AWS KMS key."""
        kms = self._get_kms_client()
        context = {
            "caracal:domain": "config",
            "caracal:dek": self.dek_name,
        }
        try:
            result = kms.encrypt(
                KeyId=self.key_id,
                Plaintext=plaintext.encode("utf-8"),
                EncryptionContext=context,
            )
        except Exception as exc:
            raise MasterKeyError(f"Failed to encrypt value with AWS KMS: {exc}") from exc

        payload = {
            "v": 3,
            "backend": "aws_kms",
            "key_id": self.key_id,
            "region": self.region,
            "ctx": context,
            "c": base64.b64encode(result["CiphertextBlob"]).decode("ascii"),
        }
        encoded_payload = base64.b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        return f"{self.ENCRYPTED_PREFIX}{encoded_payload}{self.ENCRYPTED_SUFFIX}"

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a strict ENC[v3:...] value."""
        if not self.is_encrypted(encrypted):
            raise ValueError("Value is not an ENC[...] encrypted payload")

        if not encrypted.startswith(self.ENCRYPTED_PREFIX):
            raise MasterKeyError("Unsupported encrypted payload version; only ENC[v3:...] is allowed")

        encoded_payload = encrypted[len(self.ENCRYPTED_PREFIX):-len(self.ENCRYPTED_SUFFIX)]
        try:
            payload = json.loads(base64.b64decode(encoded_payload).decode("utf-8"))
        except Exception as exc:
            raise ValueError("Encrypted payload is malformed") from exc

        if payload.get("v") != 3 or payload.get("backend") != "aws_kms":
            raise MasterKeyError("Unsupported encrypted payload backend/version")

        ciphertext_b64 = payload.get("c")
        context = payload.get("ctx") or {}
        if not isinstance(ciphertext_b64, str) or not isinstance(context, dict):
            raise ValueError("Encrypted payload missing ciphertext or context")

        kms = self._get_kms_client()
        try:
            result = kms.decrypt(
                CiphertextBlob=base64.b64decode(ciphertext_b64),
                EncryptionContext=context,
            )
        except Exception as exc:
            raise MasterKeyError(f"Failed to decrypt value with AWS KMS: {exc}") from exc

        try:
            return result["Plaintext"].decode("utf-8")
        except Exception as exc:
            raise ValueError("KMS plaintext is invalid UTF-8") from exc

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        return isinstance(value, str) and value.startswith("ENC[v") and value.endswith(cls.ENCRYPTED_SUFFIX)

    def decrypt_config(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        """Recursively decrypt encrypted values in a configuration dictionary."""
        result: dict[str, Any] = {}
        for key, value in config_dict.items():
            if isinstance(value, str) and self.is_encrypted(value):
                result[key] = self.decrypt(value)
            elif isinstance(value, dict):
                result[key] = self.decrypt_config(value)
            elif isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, str) and self.is_encrypted(item):
                        items.append(self.decrypt(item))
                    elif isinstance(item, dict):
                        items.append(self.decrypt_config(item))
                    else:
                        items.append(item)
                result[key] = items
            else:
                result[key] = value
        return result


def encrypt_value(value: str) -> str:
    """Encrypt a value with the configured AWS KMS key."""
    encryptor = ConfigEncryption(actor="cli")
    return encryptor.encrypt(value)


def decrypt_value(encrypted: str) -> str:
    """Decrypt a value with the configured AWS KMS key."""
    encryptor = ConfigEncryption(actor="cli")
    return encryptor.decrypt(encrypted)


def rotate_master_key(actor: str = "cli") -> RotationSummary:
    """Record KMS rotation intent; actual key material rotation is managed by AWS."""
    now = datetime.now(timezone.utc).isoformat()
    layout = get_caracal_layout()
    append_key_audit_event(
        layout,
        event_type="master_key_rotation_requested",
        actor=actor,
        operation="rotate",
        metadata={"backend": "aws_kms"},
    )
    return RotationSummary(rewrapped_deks=0, rotated_at=now)


def get_key_status() -> dict[str, Any]:
    """Return current key status for CLI diagnostics."""
    key_id = os.getenv("CARACAL_AWS_KMS_KEY_ID") or os.getenv("AWS_KMS_KEY_ID")
    region = os.getenv("CARACAL_AWS_REGION") or os.getenv("AWS_REGION")
    return {
        "backend": "aws_kms",
        "kms_key_id": key_id,
        "kms_region": region,
        "configured": bool(key_id),
        "local_master_key_supported": False,
    }
