"""Canonical storage layout for Caracal runtime data."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from caracal.logging_config import get_logger

logger = get_logger(__name__)

_CARACAL_HOME_ENV = "CARACAL_HOME"


class StorageLayoutError(RuntimeError):
    """Raised when storage layout is invalid or cannot be created safely."""


@dataclass(frozen=True)
class CaracalLayout:
    """Resolved storage layout rooted under CARACAL_HOME."""

    root: Path

    @property
    def keystore_dir(self) -> Path:
        return self.root / "keystore"

    @property
    def master_key_path(self) -> Path:
        return self.keystore_dir / "master_key"

    @property
    def salt_path(self) -> Path:
        return self.keystore_dir / "salt.bin"

    @property
    def encrypted_keys_dir(self) -> Path:
        return self.keystore_dir / "encrypted_keys"

    @property
    def workspaces_dir(self) -> Path:
        return self.root / "workspaces"

    @property
    def ledger_dir(self) -> Path:
        return self.root / "ledger"

    @property
    def merkle_dir(self) -> Path:
        return self.ledger_dir / "merkle"

    @property
    def audit_logs_dir(self) -> Path:
        return self.ledger_dir / "audit_logs"

    @property
    def system_dir(self) -> Path:
        return self.root / "system"

    @property
    def metadata_dir(self) -> Path:
        return self.system_dir / "metadata"

    @property
    def history_dir(self) -> Path:
        return self.system_dir / "history"

    @property
    def key_audit_log_path(self) -> Path:
        return self.audit_logs_dir / "key_events.jsonl"


def resolve_caracal_home(require_explicit: bool = False) -> Path:
    """Resolve CARACAL_HOME root.

    Resolution order is deterministic:
    1. CARACAL_HOME
    2. ~/.caracal (only when require_explicit=False)
    """
    home_value = os.getenv(_CARACAL_HOME_ENV)
    if home_value:
        return Path(home_value).expanduser().resolve(strict=False)

    if require_explicit:
        raise StorageLayoutError(
            "CARACAL_HOME is required but not set. Set CARACAL_HOME to an explicit runtime path."
        )

    return (Path.home() / ".caracal").resolve(strict=False)


def get_caracal_layout(home: Optional[Path | str] = None, require_explicit: bool = False) -> CaracalLayout:
    """Return resolved layout for current process."""
    if home is None:
        resolved_home = resolve_caracal_home(require_explicit=require_explicit)
    else:
        resolved_home = Path(home).expanduser().resolve(strict=False)
    return CaracalLayout(root=resolved_home)


def _ensure_dir(path: Path, mode: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError as exc:
        raise StorageLayoutError(f"Failed to set permissions on directory {path}: {exc}") from exc


def _ensure_file_mode(path: Path, mode: int) -> None:
    if not path.exists():
        return

    current_mode = stat.S_IMODE(path.stat().st_mode)
    if current_mode != mode:
        os.chmod(path, mode)


def ensure_layout(layout: CaracalLayout) -> None:
    """Create canonical directory structure and enforce secure defaults."""
    _ensure_dir(layout.root, 0o700)
    _ensure_dir(layout.keystore_dir, 0o700)
    _ensure_dir(layout.encrypted_keys_dir, 0o700)
    _ensure_dir(layout.workspaces_dir, 0o700)
    _ensure_dir(layout.ledger_dir, 0o700)
    _ensure_dir(layout.merkle_dir, 0o700)
    _ensure_dir(layout.audit_logs_dir, 0o700)
    _ensure_dir(layout.system_dir, 0o700)
    _ensure_dir(layout.metadata_dir, 0o700)
    _ensure_dir(layout.history_dir, 0o700)

    _ensure_file_mode(layout.master_key_path, 0o600)
    _ensure_file_mode(layout.salt_path, 0o600)


def append_key_audit_event(
    layout: CaracalLayout,
    event_type: str,
    actor: str,
    operation: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Append key lifecycle event to append-only JSONL audit file."""
    ensure_layout(layout)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "actor": actor,
        "operation": operation,
        "metadata": metadata or {},
    }

    try:
        with layout.key_audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    except OSError as exc:
        raise StorageLayoutError(f"Failed to append key audit event: {exc}") from exc
