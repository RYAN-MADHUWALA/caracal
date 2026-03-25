"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Sync state management for Caracal deployment architecture.

Provides PostgreSQL-based sync state management with operation queuing,
conflict tracking, and distributed coordination using advisory locks.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from caracal.db.connection import DatabaseConnectionManager
from caracal.db.models import SyncConflict, SyncMetadata, SyncOperation
from caracal.deployment.exceptions import (
    SyncOperationError,
    SyncStateError,
)

logger = structlog.get_logger(__name__)


class SyncStateManager:
    """
    Manages sync state using PostgreSQL.
    
    Provides methods for operation queuing, conflict tracking, and
    sync metadata management with connection pooling and advisory locks.
    """
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        """
        Initialize sync state manager.
        
        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager
        logger.info("sync_state_manager_initialized")
    
    @contextmanager
    def _session(self):
        """Get database session context."""
        with self.db_manager.session_scope() as session:
            yield session
    
    def _acquire_advisory_lock(self, session: Session, lock_id: int, timeout_seconds: int = 10) -> bool:
        """
        Acquire PostgreSQL advisory lock for distributed coordination.
        
        Args:
            session: Database session
            lock_id: Lock identifier (32-bit integer)
            timeout_seconds: Lock acquisition timeout
            
        Returns:
            True if lock acquired, False otherwise
        """
        try:
            # Try to acquire lock with timeout
            result = session.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id}
            ).scalar()
            
            if result:
                logger.debug("advisory_lock_acquired", lock_id=lock_id)
            else:
                logger.warning("advisory_lock_failed", lock_id=lock_id)
            
            return bool(result)
        except Exception as e:
            logger.error("advisory_lock_error", lock_id=lock_id, error=str(e))
            return False
    
    def _release_advisory_lock(self, session: Session, lock_id: int) -> None:
        """
        Release PostgreSQL advisory lock.
        
        Args:
            session: Database session
            lock_id: Lock identifier
        """
        try:
            session.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id}
            )
            logger.debug("advisory_lock_released", lock_id=lock_id)
        except Exception as e:
            logger.warning("advisory_lock_release_error", lock_id=lock_id, error=str(e))
    
    def _get_workspace_lock_id(self, workspace: str) -> int:
        """
        Generate lock ID for workspace.
        
        Uses hash of workspace name to generate consistent lock ID.
        
        Args:
            workspace: Workspace name
            
        Returns:
            32-bit integer lock ID
        """
        # Use hash of workspace name, constrained to 32-bit signed integer range
        return hash(workspace) % (2**31)
    
    # =========================================================================
    # Operation Queue Management
    # =========================================================================
    
    def queue_operation(
        self,
        workspace: str,
        operation_type: str,
        entity_type: str,
        entity_id: str,
        operation_data: Dict[str, Any],
        scheduled_at: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Queue sync operation for later execution.
        
        Args:
            workspace: Workspace name
            operation_type: Operation type (create, update, delete)
            entity_type: Entity type
            entity_id: Entity identifier
            operation_data: Operation data
            scheduled_at: Optional scheduled execution time
            correlation_id: Optional correlation ID for tracking
            metadata: Optional metadata
            
        Returns:
            Operation ID (UUID string)
            
        Raises:
            SyncOperationError: If queuing fails
        """
        try:
            with self._session() as session:
                operation = SyncOperation(
                    operation_id=uuid.uuid4(),
                    workspace=workspace,
                    operation_type=operation_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    operation_data=operation_data,
                    scheduled_at=scheduled_at,
                    correlation_id=correlation_id,
                    operation_metadata=metadata,
                    status="pending"
                )
                
                session.add(operation)
                session.commit()
                
                operation_id = str(operation.operation_id)
                
                logger.info(
                    "operation_queued",
                    workspace=workspace,
                    operation_id=operation_id,
                    operation_type=operation_type,
                    entity_type=entity_type
                )
                
                return operation_id
                
        except Exception as e:
            logger.error(
                "operation_queue_failed",
                workspace=workspace,
                operation_type=operation_type,
                error=str(e)
            )
            raise SyncOperationError(f"Failed to queue operation: {e}") from e
    
    def get_pending_operations(
        self,
        workspace: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending operations for workspace.
        
        Args:
            workspace: Workspace name
            limit: Optional limit on number of operations
            
        Returns:
            List of operation dictionaries
        """
        try:
            with self._session() as session:
                query = select(SyncOperation).where(
                    and_(
                        SyncOperation.workspace == workspace,
                        SyncOperation.status == "pending"
                    )
                ).order_by(SyncOperation.created_at)
                
                if limit:
                    query = query.limit(limit)
                
                operations = session.execute(query).scalars().all()
                
                return [
                    {
                        "operation_id": str(op.operation_id),
                        "operation_type": op.operation_type,
                        "entity_type": op.entity_type,
                        "entity_id": op.entity_id,
                        "operation_data": op.operation_data,
                        "created_at": op.created_at.isoformat(),
                        "retry_count": op.retry_count,
                        "correlation_id": op.correlation_id
                    }
                    for op in operations
                ]
                
        except Exception as e:
            logger.error(
                "get_pending_operations_failed",
                workspace=workspace,
                error=str(e)
            )
            return []
    
    def mark_operation_completed(self, operation_id: str) -> None:
        """
        Mark operation as completed.
        
        Args:
            operation_id: Operation ID
            
        Raises:
            SyncOperationError: If update fails
        """
        try:
            with self._session() as session:
                operation = session.get(SyncOperation, uuid.UUID(operation_id))
                
                if not operation:
                    raise SyncOperationError(f"Operation not found: {operation_id}")
                
                operation.status = "completed"
                operation.completed_at = datetime.utcnow()
                
                session.commit()
                
                logger.info(
                    "operation_completed",
                    operation_id=operation_id,
                    workspace=operation.workspace
                )
                
        except Exception as e:
            logger.error(
                "mark_operation_completed_failed",
                operation_id=operation_id,
                error=str(e)
            )
            raise SyncOperationError(f"Failed to mark operation completed: {e}") from e
    
    def mark_operation_failed(
        self,
        operation_id: str,
        error_message: str,
        increment_retry: bool = True
    ) -> None:
        """
        Mark operation as failed and optionally increment retry count.
        
        Args:
            operation_id: Operation ID
            error_message: Error message
            increment_retry: Whether to increment retry count
            
        Raises:
            SyncOperationError: If update fails
        """
        try:
            with self._session() as session:
                operation = session.get(SyncOperation, uuid.UUID(operation_id))
                
                if not operation:
                    raise SyncOperationError(f"Operation not found: {operation_id}")
                
                operation.last_error = error_message
                operation.last_retry_at = datetime.utcnow()
                
                if increment_retry:
                    operation.retry_count += 1
                
                # Mark as failed if max retries exceeded
                if operation.retry_count >= operation.max_retries:
                    operation.status = "failed"
                else:
                    operation.status = "pending"  # Will be retried
                
                session.commit()
                
                logger.warning(
                    "operation_failed",
                    operation_id=operation_id,
                    workspace=operation.workspace,
                    retry_count=operation.retry_count,
                    status=operation.status
                )
                
        except Exception as e:
            logger.error(
                "mark_operation_failed_error",
                operation_id=operation_id,
                error=str(e)
            )
            raise SyncOperationError(f"Failed to mark operation failed: {e}") from e
    
    def get_operation_count(self, workspace: str, status: Optional[str] = None) -> int:
        """
        Get count of operations for workspace.
        
        Args:
            workspace: Workspace name
            status: Optional status filter
            
        Returns:
            Operation count
        """
        try:
            with self._session() as session:
                query = select(func.count(SyncOperation.operation_id)).where(
                    SyncOperation.workspace == workspace
                )
                
                if status:
                    query = query.where(SyncOperation.status == status)
                
                count = session.execute(query).scalar()
                return count or 0
                
        except Exception as e:
            logger.error(
                "get_operation_count_failed",
                workspace=workspace,
                error=str(e)
            )
            return 0
    
    # =========================================================================
    # Conflict Tracking
    # =========================================================================
    
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record sync conflict.
        
        Args:
            workspace: Workspace name
            entity_type: Entity type
            entity_id: Entity identifier
            local_version: Local version data
            remote_version: Remote version data
            local_timestamp: Local modification timestamp
            remote_timestamp: Remote modification timestamp
            correlation_id: Optional correlation ID
            metadata: Optional metadata
            
        Returns:
            Conflict ID (UUID string)
            
        Raises:
            SyncOperationError: If recording fails
        """
        try:
            with self._session() as session:
                conflict = SyncConflict(
                    conflict_id=uuid.uuid4(),
                    workspace=workspace,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    local_version=local_version,
                    remote_version=remote_version,
                    local_timestamp=local_timestamp,
                    remote_timestamp=remote_timestamp,
                    correlation_id=correlation_id,
                    conflict_metadata=metadata,
                    status="unresolved"
                )
                
                session.add(conflict)
                session.commit()
                
                conflict_id = str(conflict.conflict_id)
                
                logger.warning(
                    "conflict_recorded",
                    workspace=workspace,
                    conflict_id=conflict_id,
                    entity_type=entity_type,
                    entity_id=entity_id
                )
                
                return conflict_id
                
        except Exception as e:
            logger.error(
                "record_conflict_failed",
                workspace=workspace,
                entity_type=entity_type,
                error=str(e)
            )
            raise SyncOperationError(f"Failed to record conflict: {e}") from e
    
    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_strategy: str,
        resolved_version: Dict[str, Any],
        resolved_by: str
    ) -> None:
        """
        Mark conflict as resolved.
        
        Args:
            conflict_id: Conflict ID
            resolution_strategy: Resolution strategy used
            resolved_version: Resolved version data
            resolved_by: Resolver identifier (system or user)
            
        Raises:
            SyncOperationError: If resolution fails
        """
        try:
            with self._session() as session:
                conflict = session.get(SyncConflict, uuid.UUID(conflict_id))
                
                if not conflict:
                    raise SyncOperationError(f"Conflict not found: {conflict_id}")
                
                conflict.resolution_strategy = resolution_strategy
                conflict.resolved_version = resolved_version
                conflict.resolved_at = datetime.utcnow()
                conflict.resolved_by = resolved_by
                conflict.status = "resolved"
                
                session.commit()
                
                logger.info(
                    "conflict_resolved",
                    conflict_id=conflict_id,
                    workspace=conflict.workspace,
                    strategy=resolution_strategy
                )
                
        except Exception as e:
            logger.error(
                "resolve_conflict_failed",
                conflict_id=conflict_id,
                error=str(e)
            )
            raise SyncOperationError(f"Failed to resolve conflict: {e}") from e
    
    def get_unresolved_conflicts(
        self,
        workspace: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get unresolved conflicts for workspace.
        
        Args:
            workspace: Workspace name
            limit: Optional limit on number of conflicts
            
        Returns:
            List of conflict dictionaries
        """
        try:
            with self._session() as session:
                query = select(SyncConflict).where(
                    and_(
                        SyncConflict.workspace == workspace,
                        SyncConflict.status == "unresolved"
                    )
                ).order_by(SyncConflict.detected_at)
                
                if limit:
                    query = query.limit(limit)
                
                conflicts = session.execute(query).scalars().all()
                
                return [
                    {
                        "conflict_id": str(c.conflict_id),
                        "entity_type": c.entity_type,
                        "entity_id": c.entity_id,
                        "local_version": c.local_version,
                        "remote_version": c.remote_version,
                        "local_timestamp": c.local_timestamp.isoformat(),
                        "remote_timestamp": c.remote_timestamp.isoformat(),
                        "detected_at": c.detected_at.isoformat()
                    }
                    for c in conflicts
                ]
                
        except Exception as e:
            logger.error(
                "get_unresolved_conflicts_failed",
                workspace=workspace,
                error=str(e)
            )
            return []
    
    def get_conflict_history(
        self,
        workspace: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get conflict history for workspace.
        
        Args:
            workspace: Workspace name
            limit: Maximum number of conflicts to return
            
        Returns:
            List of conflict dictionaries
        """
        try:
            with self._session() as session:
                query = select(SyncConflict).where(
                    SyncConflict.workspace == workspace
                ).order_by(SyncConflict.detected_at.desc()).limit(limit)
                
                conflicts = session.execute(query).scalars().all()
                
                return [
                    {
                        "conflict_id": str(c.conflict_id),
                        "entity_type": c.entity_type,
                        "entity_id": c.entity_id,
                        "status": c.status,
                        "detected_at": c.detected_at.isoformat(),
                        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                        "resolution_strategy": c.resolution_strategy,
                        "resolved_by": c.resolved_by
                    }
                    for c in conflicts
                ]
                
        except Exception as e:
            logger.error(
                "get_conflict_history_failed",
                workspace=workspace,
                error=str(e)
            )
            return []
    
    # =========================================================================
    # Sync Metadata Management
    # =========================================================================
    
    def get_sync_metadata(self, workspace: str) -> Optional[Dict[str, Any]]:
        """
        Get sync metadata for workspace.
        
        Args:
            workspace: Workspace name
            
        Returns:
            Sync metadata dictionary or None if not found
        """
        try:
            with self._session() as session:
                metadata = session.get(SyncMetadata, workspace)
                
                if not metadata:
                    return None
                
                return {
                    "workspace": metadata.workspace,
                    "remote_url": metadata.remote_url,
                    "remote_version": metadata.remote_version,
                    "sync_enabled": metadata.sync_enabled,
                    "last_sync_at": metadata.last_sync_at.isoformat() if metadata.last_sync_at else None,
                    "last_sync_direction": metadata.last_sync_direction,
                    "last_sync_status": metadata.last_sync_status,
                    "total_operations_synced": metadata.total_operations_synced,
                    "total_conflicts_detected": metadata.total_conflicts_detected,
                    "total_conflicts_resolved": metadata.total_conflicts_resolved,
                    "last_error": metadata.last_error,
                    "consecutive_failures": metadata.consecutive_failures,
                    "auto_sync_enabled": metadata.auto_sync_enabled,
                    "auto_sync_interval_seconds": metadata.auto_sync_interval_seconds
                }
                
        except Exception as e:
            logger.error(
                "get_sync_metadata_failed",
                workspace=workspace,
                error=str(e)
            )
            return None
    
    def update_sync_metadata(
        self,
        workspace: str,
        **updates
    ) -> None:
        """
        Update sync metadata for workspace.
        
        Args:
            workspace: Workspace name
            **updates: Metadata fields to update
            
        Raises:
            SyncStateError: If update fails
        """
        try:
            with self._session() as session:
                metadata = session.get(SyncMetadata, workspace)
                
                if not metadata:
                    # Create new metadata record
                    metadata = SyncMetadata(workspace=workspace)
                    session.add(metadata)
                
                # Update fields
                for key, value in updates.items():
                    if hasattr(metadata, key):
                        setattr(metadata, key, value)
                
                metadata.updated_at = datetime.utcnow()
                
                session.commit()
                
                logger.debug(
                    "sync_metadata_updated",
                    workspace=workspace,
                    updates=list(updates.keys())
                )
                
        except Exception as e:
            logger.error(
                "update_sync_metadata_failed",
                workspace=workspace,
                error=str(e)
            )
            raise SyncStateError(f"Failed to update sync metadata: {e}") from e
    
    def increment_sync_stats(
        self,
        workspace: str,
        operations_synced: int = 0,
        conflicts_detected: int = 0,
        conflicts_resolved: int = 0
    ) -> None:
        """
        Increment sync statistics for workspace.
        
        Args:
            workspace: Workspace name
            operations_synced: Number of operations synced
            conflicts_detected: Number of conflicts detected
            conflicts_resolved: Number of conflicts resolved
        """
        try:
            with self._session() as session:
                metadata = session.get(SyncMetadata, workspace)
                
                if not metadata:
                    metadata = SyncMetadata(workspace=workspace)
                    session.add(metadata)
                
                metadata.total_operations_synced += operations_synced
                metadata.total_conflicts_detected += conflicts_detected
                metadata.total_conflicts_resolved += conflicts_resolved
                metadata.updated_at = datetime.utcnow()
                
                session.commit()
                
                logger.debug(
                    "sync_stats_incremented",
                    workspace=workspace,
                    operations_synced=operations_synced,
                    conflicts_detected=conflicts_detected,
                    conflicts_resolved=conflicts_resolved
                )
                
        except Exception as e:
            logger.error(
                "increment_sync_stats_failed",
                workspace=workspace,
                error=str(e)
            )
