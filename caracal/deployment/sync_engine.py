"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Hard-cut compatibility surface for legacy sync engine imports.

Legacy sync-state database pathways were removed. This module remains only to
provide explicit fail-closed behavior for pre-hard-cut callers until the sync
CLI/flow surfaces are fully deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from caracal.deployment.exceptions import SyncOperationError


class SyncDirection(str, Enum):
    """Legacy sync direction enumeration retained for compatibility imports."""

    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "both"


@dataclass
class SyncResult:
    """Legacy sync result structure for compatibility."""

    success: bool
    uploaded_count: int = 0
    downloaded_count: int = 0
    conflicts_count: int = 0
    conflicts_resolved: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0
    operations_applied: List[str] = field(default_factory=list)


@dataclass
class SyncStatus:
    """Legacy sync status structure for compatibility."""

    workspace: str
    last_sync: Optional[datetime] = None
    pending_operations: int = 0
    conflicts_count: int = 0
    conflicts: List["Conflict"] = field(default_factory=list)
    sync_enabled: bool = False
    remote_url: Optional[str] = None
    remote_version: Optional[str] = None
    local_version: str = "hardcut"
    consecutive_failures: int = 0
    last_error: Optional[str] = None

    @property
    def last_sync_timestamp(self) -> Optional[datetime]:
        return self.last_sync


@dataclass
class Operation:
    """Legacy operation structure retained for compatibility."""

    id: str
    type: str
    entity_type: str
    entity_id: str
    data: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    last_error: Optional[str] = None


@dataclass
class Conflict:
    """Legacy conflict structure retained for compatibility."""

    id: str
    entity_type: str
    entity_id: str
    local_version: Dict[str, Any]
    remote_version: Dict[str, Any]
    local_timestamp: datetime
    remote_timestamp: datetime
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None


_HARDCUT_REMOVAL_MESSAGE = (
    "Legacy sync engine has been removed in hard-cut mode. "
    "Use enterprise command surfaces instead."
)


class SyncEngine:
    """Compatibility shim that fails closed for removed legacy sync operations."""

    def __init__(self, *args: Any, **kwargs: Any):
        self._init_args = args
        self._init_kwargs = kwargs

    def _raise_removed(self) -> None:
        raise SyncOperationError(_HARDCUT_REMOVAL_MESSAGE)

    def connect(self, workspace: str, enterprise_url: str, token: str) -> None:
        self._raise_removed()

    def disconnect(self, workspace: str) -> None:
        self._raise_removed()

    def sync_now(self, workspace: str, direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> SyncResult:
        self._raise_removed()

    def get_sync_status(self, workspace: str) -> SyncStatus:
        return SyncStatus(
            workspace=workspace,
            sync_enabled=False,
            last_error=_HARDCUT_REMOVAL_MESSAGE,
        )

    def get_conflict_history(self, workspace: str, limit: int = 100) -> List[Conflict]:
        return []

    def enable_auto_sync(
        self,
        workspace: str,
        interval_seconds: Optional[int] = None,
        interval: Optional[int] = None,
    ) -> None:
        self._raise_removed()

    def disable_auto_sync(self, workspace: str) -> None:
        self._raise_removed()
