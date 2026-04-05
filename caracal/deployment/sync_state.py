"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Hard-cut compatibility surface for legacy sync-state manager imports.

Legacy sync-state ORM tables were removed. This module remains as an explicit
fail-closed compatibility shim until sync-era callers are deleted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from caracal.deployment.exceptions import SyncStateError


_HARDCUT_REMOVAL_MESSAGE = (
    "Legacy sync-state management has been removed in hard-cut mode. "
    "Use enterprise command surfaces instead."
)


class SyncStateManager:
    """Compatibility shim that fails closed for removed legacy sync-state APIs."""

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    def _raise_removed(self) -> None:
        raise SyncStateError(_HARDCUT_REMOVAL_MESSAGE)

    def queue_operation(
        self,
        workspace: str,
        operation_type: str,
        entity_type: str,
        entity_id: str,
        operation_data: Dict[str, Any],
        scheduled_at: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._raise_removed()

    def get_pending_operations(self, workspace: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return []

    def mark_operation_processing(self, operation_id: str) -> bool:
        self._raise_removed()

    def mark_operation_completed(self, operation_id: str) -> bool:
        self._raise_removed()

    def mark_operation_failed(self, operation_id: str, error: str, max_retries: int = 5) -> bool:
        self._raise_removed()

    def get_operation_statistics(self, workspace: str, status: Optional[str] = None) -> Dict[str, int]:
        return {"total": 0, "pending": 0, "processing": 0, "completed": 0, "failed": 0}

    def record_conflict(
        self,
        workspace: str,
        entity_type: str,
        entity_id: str,
        local_version: Dict[str, Any],
        remote_version: Dict[str, Any],
        local_timestamp: datetime,
        remote_timestamp: datetime,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._raise_removed()

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_strategy: str,
        resolved_version: Dict[str, Any],
        resolved_by: str = "system",
    ) -> bool:
        self._raise_removed()

    def get_unresolved_conflicts(self, workspace: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return []

    def get_conflict_history(self, workspace: str, limit: int = 100) -> List[Dict[str, Any]]:
        return []

    def get_sync_metadata(self, workspace: str) -> Optional[Dict[str, Any]]:
        return None

    def update_sync_metadata(
        self,
        workspace: str,
        sync_enabled: Optional[bool] = None,
        remote_url: Optional[str] = None,
        remote_version: Optional[str] = None,
        last_sync_at: Optional[datetime] = None,
        last_sync_direction: Optional[str] = None,
        last_sync_status: Optional[str] = None,
        auto_sync_enabled: Optional[bool] = None,
        auto_sync_interval_seconds: Optional[int] = None,
        next_auto_sync_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        self._raise_removed()

    def cleanup_old_operations(
        self,
        workspace: str,
        older_than_days: int = 30,
        status_filter: Optional[List[str]] = None,
    ) -> int:
        return 0
