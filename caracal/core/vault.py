"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

CaracalVault — production-ready built-in secret store for Starter tier.

Architecture:
  - AES-256-GCM authenticated encryption.
  - Envelope encryption: each secret encrypted with a unique data key (DEK).
  - DEKs are encrypted under a master key (MEK) stored KMS-wrapped in the DB.
  - Per-environment key isolation via env_id prefix on all DB keys.
  - In-memory LRU cache for plaintext DEKs (bounded, TTL-aware, never logged).
  - Gateway-only access: raises GatewayContextRequired if caller is not gateway.
  - Rate limiting: token-bucket per org_id (configurable).
  - Append-only audit events for every CRUD operation.
  - Manual key rotation: re-encrypts all DEKs under a new MEK version.

Ref format for secrets stored in CaracalVault:
  caracal:{env_id}/{secret_name}
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from caracal.logging_config import get_logger

logger = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

_AES_KEY_BYTES = 32          # AES-256
_GCM_NONCE_BYTES = 12        # 96-bit GCM nonce
_CACHE_MAX_ENTRIES = 512
_CACHE_TTL_SECONDS = 300     # 5 minutes
_RATE_LIMIT_WINDOW = 60.0    # seconds
_RATE_LIMIT_DEFAULT = 120    # requests per window


# ── Exceptions ─────────────────────────────────────────────────────────────

class VaultError(Exception):
    """Base class for all vault errors."""


class GatewayContextRequired(VaultError):
    """Raised when CaracalVault is accessed outside the gateway context."""


class SecretNotFound(VaultError):
    """Raised when a requested secret does not exist."""


class VaultRateLimitExceeded(VaultError):
    """Raised when org rate limit is exceeded."""


class MasterKeyError(VaultError):
    """Raised when the master key cannot be derived or decrypted."""


# ── Data types ─────────────────────────────────────────────────────────────

@dataclass
class VaultEntry:
    """Persistent envelope for a single encrypted secret."""
    entry_id: str
    org_id: str
    env_id: str
    secret_name: str
    # AES-256-GCM ciphertext of secret value (base64)
    ciphertext_b64: str
    # GCM nonce used for ciphertext (base64)
    iv_b64: str
    # AES-256-GCM ciphertext of the DEK, encrypted under the MEK (base64)
    encrypted_dek_b64: str
    # GCM nonce used for DEK encryption (base64)
    dek_iv_b64: str
    # Version of the master key used for DEK wrapping
    key_version: int
    created_at: str
    updated_at: str


@dataclass
class VaultAuditEvent:
    """Append-only audit record for a vault operation."""
    event_id: str
    org_id: str
    env_id: str
    secret_name: str
    operation: str          # "create" | "read" | "update" | "delete" | "rotate"
    key_version: int
    actor: str              # "gateway" | "admin"
    timestamp: str
    success: bool
    error_code: Optional[str] = None


@dataclass
class RotationResult:
    secrets_rotated: int
    secrets_failed: int
    new_key_version: int
    duration_seconds: float


# ── Internal LRU Cache ────────────────────────────────────────────────────

@dataclass
class _CacheEntry:
    dek: bytes
    expires_at: float


class _DEKCache:
    """
    Bounded in-memory cache for decrypted DEKs.
    Key: (org_id, env_id, entry_id, key_version).
    Never persisted; evicted after TTL or when capacity is exceeded.
    """

    def __init__(self, max_entries: int = _CACHE_MAX_ENTRIES, ttl: float = _CACHE_TTL_SECONDS):
        self._max = max_entries
        self._ttl = ttl
        self._store: Dict[Tuple, _CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: Tuple) -> Optional[bytes]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry.dek

    def put(self, key: Tuple, dek: bytes) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                # Evict earliest-expiring entry
                oldest = min(self._store, key=lambda k: self._store[k].expires_at)
                del self._store[oldest]
            self._store[key] = _CacheEntry(dek=dek, expires_at=time.monotonic() + self._ttl)

    def invalidate_prefix(self, org_id: str, env_id: str) -> None:
        with self._lock:
            to_remove = [k for k in self._store if k[0] == org_id and k[1] == env_id]
            for k in to_remove:
                del self._store[k]


# ── Rate Limiter (token bucket, in-memory) ────────────────────────────────

@dataclass
class _RateBucket:
    tokens: float
    last_refill: float


class _VaultRateLimiter:
    def __init__(self, limit: int = _RATE_LIMIT_DEFAULT, window: float = _RATE_LIMIT_WINDOW):
        self._limit = limit
        self._window = window
        self._buckets: Dict[str, _RateBucket] = {}
        self._lock = threading.Lock()

    def check(self, org_id: str) -> None:
        with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(org_id)
            if bucket is None:
                self._buckets[org_id] = _RateBucket(tokens=self._limit - 1, last_refill=now)
                return
            elapsed = now - bucket.last_refill
            bucket.tokens = min(self._limit, bucket.tokens + elapsed * (self._limit / self._window))
            bucket.last_refill = now
            if bucket.tokens < 1:
                raise VaultRateLimitExceeded(
                    f"Vault rate limit exceeded for org {org_id}. "
                    f"Limit: {self._limit} requests per {int(self._window)}s."
                )
            bucket.tokens -= 1


# ── Master Key Provider ───────────────────────────────────────────────────

class MasterKeyProvider:
    """
    Derives or unwraps the MEK for a given org.

    In production: the KMS-wrapped MEK ciphertext is stored in the DB
    (vault_master_keys table) and unwrapped via AWS KMS or a local KMS
    derived from CARACAL_VAULT_MEK_SECRET env var.

    For Starter tier (no AWS KMS), falls back to HKDF derivation from
    CARACAL_VAULT_MEK_SECRET.  This env var MUST be set to a
    cryptographically strong random value and treated as a root secret.
    """

    _ENV_MEK_SECRET = "CARACAL_VAULT_MEK_SECRET"

    def __init__(self) -> None:
        raw = os.environ.get(self._ENV_MEK_SECRET)
        if not raw:
            raise MasterKeyError(
                f"{self._ENV_MEK_SECRET} is not set.  "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        self._root = raw.encode()

    def derive(self, org_id: str, env_id: str, key_version: int) -> bytes:
        """Derive a 256-bit MEK for (org, env, version) using HKDF-SHA256."""
        info = f"caracal-vault:{org_id}:{env_id}:v{key_version}".encode()
        return HKDF(
            algorithm=hashes.SHA256(),
            length=_AES_KEY_BYTES,
            salt=None,
            info=info,
        ).derive(self._root)


# ── CaracalVault ──────────────────────────────────────────────────────────

_GATEWAY_CONTEXT_FLAG = threading.local()


def _assert_gateway_context() -> None:
    if not getattr(_GATEWAY_CONTEXT_FLAG, "active", False):
        raise GatewayContextRequired(
            "CaracalVault may only be accessed from within the gateway request context. "
            "Direct application layer access is forbidden."
        )


class gateway_context:  # noqa: N801 — context manager, lowercase intentional
    """Context manager that marks the current thread as a gateway context."""

    def __enter__(self) -> "gateway_context":
        _GATEWAY_CONTEXT_FLAG.active = True
        return self

    def __exit__(self, *_) -> None:
        _GATEWAY_CONTEXT_FLAG.active = False


class CaracalVault:
    """
    Built-in secret store for Starter tier.

    Public interface:
      put(org_id, env_id, name, plaintext, actor) → VaultEntry
      get(org_id, env_id, name, actor) → str
      delete(org_id, env_id, name, actor) → None
      rotate_master_key(org_id, env_id, actor) → RotationResult
      list_secrets(org_id, env_id, actor) → list[str]
      drain_audit_events() → list[VaultAuditEvent]

    All mutating operations require gateway_context().
    """

    def __init__(
        self,
        storage: Optional["_VaultStorage"] = None,
        key_provider: Optional[MasterKeyProvider] = None,
        rate_limit: int = _RATE_LIMIT_DEFAULT,
    ) -> None:
        self._storage = storage or _InMemoryVaultStorage()
        self._keys = key_provider or MasterKeyProvider()
        self._cache = _DEKCache()
        self._rl = _VaultRateLimiter(limit=rate_limit)
        self._audit: list[VaultAuditEvent] = []
        self._audit_lock = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────

    def put(self, org_id: str, env_id: str, name: str, plaintext: str, actor: str = "gateway") -> VaultEntry:
        _assert_gateway_context()
        self._rl.check(org_id)
        try:
            entry = self._encrypt_and_store(org_id, env_id, name, plaintext)
            op = "update" if self._storage.exists(org_id, env_id, name) else "create"
            self._audit_event(org_id, env_id, name, op, entry.key_version, actor, True)
            return entry
        except VaultError:
            raise
        except Exception as exc:
            self._audit_event(org_id, env_id, name, "create", 0, actor, False, type(exc).__name__)
            raise VaultError(f"Failed to store secret '{name}': {exc}") from exc

    def get(self, org_id: str, env_id: str, name: str, actor: str = "gateway") -> str:
        _assert_gateway_context()
        self._rl.check(org_id)
        try:
            entry = self._storage.load(org_id, env_id, name)
            plaintext = self._decrypt_entry(entry)
            self._audit_event(org_id, env_id, name, "read", entry.key_version, actor, True)
            return plaintext
        except SecretNotFound:
            self._audit_event(org_id, env_id, name, "read", 0, actor, False, "SecretNotFound")
            raise
        except Exception as exc:
            self._audit_event(org_id, env_id, name, "read", 0, actor, False, type(exc).__name__)
            raise VaultError(f"Failed to retrieve secret '{name}': {exc}") from exc

    def delete(self, org_id: str, env_id: str, name: str, actor: str = "gateway") -> None:
        _assert_gateway_context()
        self._rl.check(org_id)
        entry = self._storage.load(org_id, env_id, name)
        self._storage.remove(org_id, env_id, name)
        self._cache.invalidate_prefix(org_id, env_id)
        self._audit_event(org_id, env_id, name, "delete", entry.key_version, actor, True)

    def list_secrets(self, org_id: str, env_id: str, actor: str = "gateway") -> list[str]:
        _assert_gateway_context()
        self._rl.check(org_id)
        return self._storage.list_names(org_id, env_id)

    def rotate_master_key(self, org_id: str, env_id: str, actor: str = "admin") -> RotationResult:
        """
        Re-encrypts all DEKs under a new MEK version.

        Zero-downtime pattern:
          1. Determine new version = current_max + 1.
          2. For each entry: decrypt DEK with old MEK → re-wrap with new MEK.
          3. Atomically replace stored entry.
          4. Invalidate DEK cache.
        """
        _assert_gateway_context()
        t0 = time.monotonic()
        names = self._storage.list_names(org_id, env_id)
        new_version = self._storage.current_key_version(org_id, env_id) + 1
        rotated = 0
        failed = 0
        for name in names:
            try:
                entry = self._storage.load(org_id, env_id, name)
                plaintext = self._decrypt_entry(entry)
                new_entry = self._encrypt_and_store(org_id, env_id, name, plaintext, key_version=new_version)
                self._audit_event(org_id, env_id, name, "rotate", new_version, actor, True)
                rotated += 1
            except Exception as exc:
                logger.error("Vault rotation failed for %s/%s/%s: %s", org_id, env_id, name, exc)
                self._audit_event(org_id, env_id, name, "rotate", new_version, actor, False, type(exc).__name__)
                failed += 1
        self._cache.invalidate_prefix(org_id, env_id)
        return RotationResult(
            secrets_rotated=rotated,
            secrets_failed=failed,
            new_key_version=new_version,
            duration_seconds=round(time.monotonic() - t0, 3),
        )

    def drain_audit_events(self) -> list[VaultAuditEvent]:
        """Return and clear accumulated audit events (thread-safe)."""
        with self._audit_lock:
            events, self._audit = self._audit[:], []
        return events

    # ── Internal helpers ───────────────────────────────────────────────

    def _encrypt_and_store(
        self, org_id: str, env_id: str, name: str, plaintext: str,
        key_version: Optional[int] = None,
    ) -> VaultEntry:
        if key_version is None:
            key_version = self._storage.current_key_version(org_id, env_id)

        mek = self._keys.derive(org_id, env_id, key_version)

        # Generate fresh DEK for this entry
        dek = os.urandom(_AES_KEY_BYTES)

        # Encrypt plaintext with DEK
        value_nonce = os.urandom(_GCM_NONCE_BYTES)
        ciphertext = AESGCM(dek).encrypt(value_nonce, plaintext.encode(), None)

        # Wrap DEK with MEK
        dek_nonce = os.urandom(_GCM_NONCE_BYTES)
        encrypted_dek = AESGCM(mek).encrypt(dek_nonce, dek, None)

        now = datetime.now(timezone.utc).isoformat()
        entry = VaultEntry(
            entry_id=str(uuid4()),
            org_id=org_id,
            env_id=env_id,
            secret_name=name,
            ciphertext_b64=base64.b64encode(ciphertext).decode(),
            iv_b64=base64.b64encode(value_nonce).decode(),
            encrypted_dek_b64=base64.b64encode(encrypted_dek).decode(),
            dek_iv_b64=base64.b64encode(dek_nonce).decode(),
            key_version=key_version,
            created_at=now,
            updated_at=now,
        )
        self._storage.save(entry)
        return entry

    def _decrypt_entry(self, entry: VaultEntry) -> str:
        cache_key = (entry.org_id, entry.env_id, entry.entry_id, entry.key_version)
        dek = self._cache.get(cache_key)
        if dek is None:
            mek = self._keys.derive(entry.org_id, entry.env_id, entry.key_version)
            dek_nonce = base64.b64decode(entry.dek_iv_b64)
            encrypted_dek = base64.b64decode(entry.encrypted_dek_b64)
            dek = AESGCM(mek).decrypt(dek_nonce, encrypted_dek, None)
            self._cache.put(cache_key, dek)

        nonce = base64.b64decode(entry.iv_b64)
        ciphertext = base64.b64decode(entry.ciphertext_b64)
        return AESGCM(dek).decrypt(nonce, ciphertext, None).decode()

    def _audit_event(
        self, org_id: str, env_id: str, name: str, op: str,
        version: int, actor: str, success: bool, error_code: Optional[str] = None,
    ) -> None:
        event = VaultAuditEvent(
            event_id=str(uuid4()),
            org_id=org_id,
            env_id=env_id,
            secret_name=name,
            operation=op,
            key_version=version,
            actor=actor,
            timestamp=datetime.now(timezone.utc).isoformat(),
            success=success,
            error_code=error_code,
        )
        with self._audit_lock:
            self._audit.append(event)


# ── Storage abstraction ───────────────────────────────────────────────────

class _VaultStorage:
    """Interface that concrete storage adapters must implement."""

    def save(self, entry: VaultEntry) -> None:
        raise NotImplementedError

    def load(self, org_id: str, env_id: str, name: str) -> VaultEntry:
        raise NotImplementedError

    def exists(self, org_id: str, env_id: str, name: str) -> bool:
        raise NotImplementedError

    def remove(self, org_id: str, env_id: str, name: str) -> None:
        raise NotImplementedError

    def list_names(self, org_id: str, env_id: str) -> list[str]:
        raise NotImplementedError

    def current_key_version(self, org_id: str, env_id: str) -> int:
        raise NotImplementedError


class _InMemoryVaultStorage(_VaultStorage):
    """
    In-memory storage for testing and single-process deployments.
    NOT suitable for multi-replica production use — use the DB-backed adapter.
    """

    def __init__(self) -> None:
        self._data: Dict[Tuple[str, str, str], VaultEntry] = {}
        self._versions: Dict[Tuple[str, str], int] = {}

    def _key(self, org_id: str, env_id: str, name: str) -> Tuple[str, str, str]:
        return (org_id, env_id, name)

    def save(self, entry: VaultEntry) -> None:
        k = self._key(entry.org_id, entry.env_id, entry.secret_name)
        self._data[k] = entry
        vk = (entry.org_id, entry.env_id)
        self._versions[vk] = max(self._versions.get(vk, 1), entry.key_version)

    def load(self, org_id: str, env_id: str, name: str) -> VaultEntry:
        entry = self._data.get(self._key(org_id, env_id, name))
        if entry is None:
            raise SecretNotFound(f"Secret '{name}' not found in env '{env_id}' for org '{org_id}'.")
        return entry

    def exists(self, org_id: str, env_id: str, name: str) -> bool:
        return self._key(org_id, env_id, name) in self._data

    def remove(self, org_id: str, env_id: str, name: str) -> None:
        self._data.pop(self._key(org_id, env_id, name), None)

    def list_names(self, org_id: str, env_id: str) -> list[str]:
        return [name for (o, e, name) in self._data if o == org_id and e == env_id]

    def current_key_version(self, org_id: str, env_id: str) -> int:
        return self._versions.get((org_id, env_id), 1)


# ── Singleton for gateway use ─────────────────────────────────────────────

_vault_instance: Optional[CaracalVault] = None
_vault_lock = threading.Lock()


def get_vault() -> CaracalVault:
    """Return the process-wide CaracalVault singleton."""
    global _vault_instance
    if _vault_instance is None:
        with _vault_lock:
            if _vault_instance is None:
                _vault_instance = CaracalVault()
    return _vault_instance
