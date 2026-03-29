"""
Configuration encryption utilities backed by deterministic local key hierarchy.

Model:
- Master key (keystore/master_key) only wraps/unwarps DEKs
- DEKs (keystore/encrypted_keys/*.json) encrypt/decrypt payload values
- Encrypted payloads use strict versioned format ENC[v2:...]
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from caracal.logging_config import get_logger
from caracal.storage.layout import (
    CaracalLayout,
    append_key_audit_event,
    ensure_layout,
    get_caracal_layout,
)

logger = get_logger(__name__)


_MASTER_KEY_BYTES = 32
_SALT_BYTES = 32
_NONCE_BYTES = 12
_DEK_FILE_VERSION = 1


class MasterKeyError(RuntimeError):
    """Raised when master key access fails or violates strict behavior."""


@dataclass
class RotationSummary:
    """Result from rotating local master key and re-wrapping DEKs."""

    rewrapped_deks: int
    rotated_at: str


class ConfigEncryption:
    """Encrypt/decrypt config values using local DEK envelope encryption."""

    ENCRYPTED_PREFIX = "ENC[v2:"
    ENCRYPTED_SUFFIX = "]"
    DEFAULT_DEK_NAME = "config.default"

    def __init__(
        self,
        layout: Optional[CaracalLayout] = None,
        dek_name: str = DEFAULT_DEK_NAME,
        actor: str = "system",
    ):
        self.layout = layout or get_caracal_layout()
        self.dek_name = dek_name
        self.actor = actor
        ensure_layout(self.layout)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext value under the configured DEK."""
        master_key = self._load_or_init_master_key(allow_bootstrap=True)
        salt = self._load_or_init_salt(allow_bootstrap=True)
        dek = self._load_or_create_dek(master_key=master_key, salt=salt, allow_bootstrap=True)

        nonce = os.urandom(_NONCE_BYTES)
        ciphertext = AESGCM(dek).encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = {
            "v": 2,
            "dek": self.dek_name,
            "n": base64.b64encode(nonce).decode("ascii"),
            "c": base64.b64encode(ciphertext).decode("ascii"),
        }
        encoded_payload = base64.b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        return f"{self.ENCRYPTED_PREFIX}{encoded_payload}{self.ENCRYPTED_SUFFIX}"

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a strict ENC[v2:...] value."""
        if not self.is_encrypted(encrypted):
            raise ValueError(
                f"Value is not encrypted (must start with {self.ENCRYPTED_PREFIX} and end with {self.ENCRYPTED_SUFFIX})"
            )

        encoded_payload = encrypted[len(self.ENCRYPTED_PREFIX):-len(self.ENCRYPTED_SUFFIX)]
        try:
            payload = json.loads(base64.b64decode(encoded_payload).decode("utf-8"))
        except Exception as exc:
            raise ValueError("Encrypted payload is malformed") from exc

        if payload.get("v") != 2:
            raise ValueError("Unsupported encrypted payload version")

        dek_name = str(payload.get("dek") or self.dek_name)
        nonce_b64 = payload.get("n")
        ciphertext_b64 = payload.get("c")
        if not isinstance(nonce_b64, str) or not isinstance(ciphertext_b64, str):
            raise ValueError("Encrypted payload missing nonce or ciphertext")

        master_key = self._load_or_init_master_key(allow_bootstrap=False)
        salt = self._load_or_init_salt(allow_bootstrap=False)
        dek = self._load_or_create_dek(master_key=master_key, salt=salt, allow_bootstrap=False, dek_name=dek_name)

        try:
            nonce = base64.b64decode(nonce_b64)
            ciphertext = base64.b64decode(ciphertext_b64)
            plaintext = AESGCM(dek).decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as exc:
            raise ValueError("Failed to decrypt value") from exc

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        return isinstance(value, str) and value.startswith(cls.ENCRYPTED_PREFIX) and value.endswith(cls.ENCRYPTED_SUFFIX)

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

    def _load_or_init_master_key(self, allow_bootstrap: bool) -> bytes:
        key_path = self.layout.master_key_path
        if key_path.exists():
            raw = base64.b64decode(key_path.read_text(encoding="utf-8").strip())
            if len(raw) != _MASTER_KEY_BYTES:
                raise MasterKeyError("Master key file is invalid")
            append_key_audit_event(
                self.layout,
                event_type="master_key_loaded",
                actor=self.actor,
                operation="read",
                metadata={"path": str(key_path)},
            )
            return raw

        if self._has_any_encrypted_state():
            append_key_audit_event(
                self.layout,
                event_type="master_key_missing",
                actor=self.actor,
                operation="read",
                metadata={"path": str(key_path)},
            )
            raise MasterKeyError(
                "Master key is missing while encrypted key state exists; refusing to regenerate automatically."
            )

        if not allow_bootstrap:
            raise MasterKeyError("Master key is not initialized")

        master_key = os.urandom(_MASTER_KEY_BYTES)
        _atomic_write_text(key_path, base64.b64encode(master_key).decode("ascii"))
        os.chmod(key_path, 0o600)
        append_key_audit_event(
            self.layout,
            event_type="master_key_generated",
            actor=self.actor,
            operation="create",
            metadata={"path": str(key_path)},
        )
        return master_key

    def _load_or_init_salt(self, allow_bootstrap: bool) -> bytes:
        salt_path = self.layout.salt_path
        if salt_path.exists():
            salt = salt_path.read_bytes()
            if len(salt) != _SALT_BYTES:
                raise MasterKeyError("Salt file is invalid")
            return salt

        if not allow_bootstrap:
            raise MasterKeyError("Salt file is missing")

        salt = os.urandom(_SALT_BYTES)
        _atomic_write_bytes(salt_path, salt)
        os.chmod(salt_path, 0o600)
        return salt

    def _dek_file_path(self, dek_name: Optional[str] = None) -> Path:
        name = (dek_name or self.dek_name).replace("/", "_")
        return self.layout.encrypted_keys_dir / f"{name}.json"

    def _load_or_create_dek(
        self,
        master_key: bytes,
        salt: bytes,
        allow_bootstrap: bool,
        dek_name: Optional[str] = None,
    ) -> bytes:
        path = self._dek_file_path(dek_name=dek_name)

        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            wrapped_b64 = payload.get("wrapped_dek")
            nonce_b64 = payload.get("nonce")
            if payload.get("version") != _DEK_FILE_VERSION:
                raise MasterKeyError(f"Unsupported DEK metadata version in {path}")
            if not isinstance(wrapped_b64, str) or not isinstance(nonce_b64, str):
                raise MasterKeyError(f"DEK metadata is invalid in {path}")
            wrapped = base64.b64decode(wrapped_b64)
            nonce = base64.b64decode(nonce_b64)
            return AESGCM(master_key).decrypt(nonce, wrapped, self._wrap_aad(salt, path.stem))

        if not allow_bootstrap:
            raise MasterKeyError(f"DEK metadata is missing for {path.stem}")

        dek = os.urandom(_MASTER_KEY_BYTES)
        nonce = os.urandom(_NONCE_BYTES)
        wrapped = AESGCM(master_key).encrypt(nonce, dek, self._wrap_aad(salt, path.stem))
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "version": _DEK_FILE_VERSION,
            "name": path.stem,
            "wrapped_dek": base64.b64encode(wrapped).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "created_at": now,
            "updated_at": now,
        }
        _atomic_write_text(path, json.dumps(payload, separators=(",", ":"), sort_keys=True))
        os.chmod(path, 0o600)
        return dek

    def _wrap_aad(self, salt: bytes, dek_name: str) -> bytes:
        return salt + b":" + dek_name.encode("utf-8")

    def _has_any_encrypted_state(self) -> bool:
        if self.layout.encrypted_keys_dir.exists():
            return any(self.layout.encrypted_keys_dir.iterdir())
        return False


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(content)
    temp_path.replace(path)


def encrypt_value(value: str) -> str:
    """Encrypt a value with the installation DEK."""
    encryptor = ConfigEncryption(actor="cli")
    return encryptor.encrypt(value)


def decrypt_value(encrypted: str) -> str:
    """Decrypt a value with the installation DEK."""
    encryptor = ConfigEncryption(actor="cli")
    return encryptor.decrypt(encrypted)


def rotate_master_key(actor: str = "cli") -> RotationSummary:
    """Rotate master key and re-wrap all persisted DEKs."""
    layout = get_caracal_layout()
    ensure_layout(layout)

    if not layout.master_key_path.exists():
        append_key_audit_event(
            layout,
            event_type="master_key_missing",
            actor=actor,
            operation="rotate",
            metadata={"path": str(layout.master_key_path)},
        )
        raise MasterKeyError("Cannot rotate master key because it is missing")

    salt = layout.salt_path.read_bytes()
    if len(salt) != _SALT_BYTES:
        raise MasterKeyError("Cannot rotate master key: installation salt is missing or invalid")

    old_master_key = base64.b64decode(layout.master_key_path.read_text(encoding="utf-8").strip())
    if len(old_master_key) != _MASTER_KEY_BYTES:
        raise MasterKeyError("Cannot rotate master key: current key file is invalid")

    new_master_key = os.urandom(_MASTER_KEY_BYTES)
    now = datetime.now(timezone.utc).isoformat()
    rewrapped = 0

    for dek_file in sorted(layout.encrypted_keys_dir.glob("*.json")):
        payload = json.loads(dek_file.read_text(encoding="utf-8"))
        wrapped_b64 = payload.get("wrapped_dek")
        nonce_b64 = payload.get("nonce")
        if not isinstance(wrapped_b64, str) or not isinstance(nonce_b64, str):
            raise MasterKeyError(f"DEK metadata is invalid in {dek_file}")

        old_nonce = base64.b64decode(nonce_b64)
        old_wrapped = base64.b64decode(wrapped_b64)
        dek_plain = AESGCM(old_master_key).decrypt(old_nonce, old_wrapped, salt + b":" + dek_file.stem.encode("utf-8"))

        new_nonce = os.urandom(_NONCE_BYTES)
        new_wrapped = AESGCM(new_master_key).encrypt(
            new_nonce,
            dek_plain,
            salt + b":" + dek_file.stem.encode("utf-8"),
        )

        payload["wrapped_dek"] = base64.b64encode(new_wrapped).decode("ascii")
        payload["nonce"] = base64.b64encode(new_nonce).decode("ascii")
        payload["updated_at"] = now
        _atomic_write_text(dek_file, json.dumps(payload, separators=(",", ":"), sort_keys=True))
        os.chmod(dek_file, 0o600)
        rewrapped += 1

    _atomic_write_text(layout.master_key_path, base64.b64encode(new_master_key).decode("ascii"))
    os.chmod(layout.master_key_path, 0o600)
    append_key_audit_event(
        layout,
        event_type="master_key_rotated",
        actor=actor,
        operation="rotate",
        metadata={"rewrapped_deks": rewrapped},
    )
    return RotationSummary(rewrapped_deks=rewrapped, rotated_at=now)


def get_key_status() -> dict[str, Any]:
    """Return current key material status for CLI diagnostics."""
    layout = get_caracal_layout()
    ensure_layout(layout)
    dek_files = sorted(layout.encrypted_keys_dir.glob("*.json"))
    return {
        "home": str(layout.root),
        "master_key_present": layout.master_key_path.exists(),
        "salt_present": layout.salt_path.exists(),
        "dek_count": len(dek_files),
        "key_audit_log": str(layout.key_audit_log_path),
    }
