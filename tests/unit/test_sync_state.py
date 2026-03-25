"""
Copyright (C) 2026 Garudex Labs.  All Rights Reserved.
Caracal, a product of Garudex Labs

Unit tests for sync state management.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from caracal.deployment.sync_state import SyncStateManager
from caracal.deployment.exceptions import SyncOperationError, SyncStateError


class TestSyncStateManager:
    """Test suite for SyncStateManager."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        manager.session_scope = MagicMock()
        return manager
    
    @pytest.fixture
    def sync_state_manager(self, mock_db_manager):
        """Create SyncStateManager instance."""
        return SyncStateManager(mock_db_manager)
    
    def test_initialization(self, sync_state_manager, mock_db_manager):
        """Test SyncStateManager initialization."""
        assert sync_state_manager.db_manager == mock_db_manager
    
    def test_get_workspace_lock_id(self, sync_state_manager):
        """Test workspace lock ID generation."""
        workspace = "test-workspace"
        lock_id = sync_state_manager._get_workspace_lock_id(workspace)
        
        # Lock ID should be consistent for same workspace
        assert lock_id == sync_state_manager._get_workspace_lock_id(workspace)
        
        # Lock ID should be within 32-bit signed integer range
        assert -(2**31) <= lock_id < 2**31
    
    def test_get_workspace_lock_id_different_workspaces(self, sync_state_manager):
        """Test that different workspaces get different lock IDs."""
        lock_id1 = sync_state_manager._get_workspace_lock_id("workspace1")
        lock_id2 = sync_state_manager._get_workspace_lock_id("workspace2")
        
        # Different workspaces should (likely) have different lock IDs
        # Note: Hash collisions are possible but unlikely
        assert lock_id1 != lock_id2


class TestOperationQueue:
    """Test suite for operation queue functionality."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        return manager
    
    @pytest.fixture
    def sync_state_manager(self, mock_db_manager):
        """Create SyncStateManager instance."""
        return SyncStateManager(mock_db_manager)
    
    def test_queue_operation_basic(self, sync_state_manager):
        """Test basic operation queuing."""
        # This is a minimal test - full integration tests would use real database
        workspace = "test-workspace"
        operation_type = "create"
        entity_type = "mandate"
        entity_id = "mandate-123"
        operation_data = {"action": "create_mandate"}
        
        # Mock the session context
        mock_session = MagicMock()
        sync_state_manager.db_manager.session_scope = MagicMock()
        sync_state_manager.db_manager.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        sync_state_manager.db_manager.session_scope.return_value.__exit__ = MagicMock(return_value=False)
        
        # Call queue_operation
        operation_id = sync_state_manager.queue_operation(
            workspace=workspace,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_data=operation_data
        )
        
        # Verify operation_id is a valid UUID string
        assert isinstance(operation_id, str)
        uuid.UUID(operation_id)  # Should not raise
        
        # Verify session.add was called
        assert mock_session.add.called
        
        # Verify session.commit was called
        assert mock_session.commit.called


class TestConflictTracking:
    """Test suite for conflict tracking functionality."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        return manager
    
    @pytest.fixture
    def sync_state_manager(self, mock_db_manager):
        """Create SyncStateManager instance."""
        return SyncStateManager(mock_db_manager)
    
    def test_record_conflict_basic(self, sync_state_manager):
        """Test basic conflict recording."""
        workspace = "test-workspace"
        entity_type = "mandate"
        entity_id = "mandate-123"
        local_version = {"version": 1, "data": "local"}
        remote_version = {"version": 2, "data": "remote"}
        local_timestamp = datetime.utcnow()
        remote_timestamp = datetime.utcnow()
        
        # Mock the session context
        mock_session = MagicMock()
        sync_state_manager.db_manager.session_scope = MagicMock()
        sync_state_manager.db_manager.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        sync_state_manager.db_manager.session_scope.return_value.__exit__ = MagicMock(return_value=False)
        
        # Call record_conflict
        conflict_id = sync_state_manager.record_conflict(
            workspace=workspace,
            entity_type=entity_type,
            entity_id=entity_id,
            local_version=local_version,
            remote_version=remote_version,
            local_timestamp=local_timestamp,
            remote_timestamp=remote_timestamp
        )
        
        # Verify conflict_id is a valid UUID string
        assert isinstance(conflict_id, str)
        uuid.UUID(conflict_id)  # Should not raise
        
        # Verify session.add was called
        assert mock_session.add.called
        
        # Verify session.commit was called
        assert mock_session.commit.called


class TestSyncMetadata:
    """Test suite for sync metadata management."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        return manager
    
    @pytest.fixture
    def sync_state_manager(self, mock_db_manager):
        """Create SyncStateManager instance."""
        return SyncStateManager(mock_db_manager)
    
    def test_get_sync_metadata_not_found(self, sync_state_manager):
        """Test getting sync metadata when not found."""
        workspace = "test-workspace"
        
        # Mock the session context
        mock_session = MagicMock()
        mock_session.get.return_value = None
        sync_state_manager.db_manager.session_scope = MagicMock()
        sync_state_manager.db_manager.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        sync_state_manager.db_manager.session_scope.return_value.__exit__ = MagicMock(return_value=False)
        
        # Call get_sync_metadata
        result = sync_state_manager.get_sync_metadata(workspace)
        
        # Should return None when not found
        assert result is None
