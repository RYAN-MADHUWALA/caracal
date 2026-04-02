"""
Unit tests for deployment sync engine.

This module tests the SyncEngine class and sync operations.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from uuid import uuid4

from caracal.deployment.sync_engine import (
    SyncEngine,
    SyncDirection,
    SyncResult,
    SyncStatus,
    Operation,
    Conflict,
)
from caracal.deployment.config_manager import ConflictStrategy
from caracal.deployment.exceptions import (
    WorkspaceNotFoundError,
    SyncConnectionError,
    SyncOperationError,
    SyncStateError,
    VersionIncompatibleError,
)
from caracal.db.models import SyncMetadata, SyncOperation, SyncConflict


@pytest.mark.unit
class TestSyncDirection:
    """Test suite for SyncDirection enum."""
    
    def test_sync_direction_values(self):
        """Test SyncDirection enum values."""
        assert SyncDirection.PUSH.value == "push"
        assert SyncDirection.PULL.value == "pull"
        assert SyncDirection.BIDIRECTIONAL.value == "both"


@pytest.mark.unit
class TestSyncResult:
    """Test suite for SyncResult dataclass."""
    
    def test_sync_result_creation(self):
        """Test SyncResult creation."""
        result = SyncResult(
            success=True,
            uploaded_count=5,
            downloaded_count=3,
            conflicts_count=1,
            conflicts_resolved=1,
            errors=[],
            duration_ms=1500,
            operations_applied=["op1", "op2"]
        )
        
        assert result.success is True
        assert result.uploaded_count == 5
        assert result.downloaded_count == 3
        assert result.conflicts_count == 1
        assert result.conflicts_resolved == 1
        assert result.duration_ms == 1500
        assert len(result.operations_applied) == 2


@pytest.mark.unit
class TestSyncStatus:
    """Test suite for SyncStatus dataclass."""
    
    def test_sync_status_creation(self):
        """Test SyncStatus creation."""
        last_sync = datetime.utcnow()
        status = SyncStatus(
            workspace="test-workspace",
            last_sync=last_sync,
            pending_operations=5,
            sync_enabled=True,
            remote_url="https://example.com",
            remote_version="0.3.0",
            local_version="0.3.0",
            consecutive_failures=0,
            last_error=None
        )
        
        assert status.workspace == "test-workspace"
        assert status.last_sync == last_sync
        assert status.pending_operations == 5
        assert status.sync_enabled is True


@pytest.mark.unit
class TestSyncEngine:
    """Test suite for SyncEngine class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_db_manager = Mock()
        self.mock_config_manager = Mock()
        self.mock_session = Mock()
        
        # Configure mock db_manager
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.engine = SyncEngine(
            db_manager=self.mock_db_manager,
            config_manager=self.mock_config_manager
        )
    
    def test_sync_engine_initialization(self):
        """Test SyncEngine initialization."""
        assert self.engine.db_manager == self.mock_db_manager
        assert self.engine.config_manager == self.mock_config_manager
        assert isinstance(self.engine._auto_sync_tasks, dict)
    
    def test_get_db_session_without_manager(self):
        """Test _get_db_session raises error without db_manager."""
        engine = SyncEngine(db_manager=None, config_manager=self.mock_config_manager)
        
        with pytest.raises(SyncStateError):
            engine._get_db_session()
    
    def test_connect_success(self):
        """Test successful sync connection."""
        workspace = "test-workspace"
        enterprise_url = "https://enterprise.example.com"
        token = "test-token"
        
        # Mock workspace config
        mock_config = Mock()
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock database query
        mock_sync_meta = Mock(spec=SyncMetadata)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_sync_meta
        
        # Execute
        self.engine.connect(workspace, enterprise_url, token)
        
        # Verify
        self.mock_config_manager.get_workspace_config.assert_called_once_with(workspace)
        self.mock_config_manager.set_workspace_config.assert_called_once()
        self.mock_config_manager.store_secret.assert_called_once()
        self.mock_session.commit.assert_called()
    
    def test_connect_workspace_not_found(self):
        """Test connect raises error for non-existent workspace."""
        self.mock_config_manager.get_workspace_config.side_effect = WorkspaceNotFoundError("Not found")
        
        with pytest.raises(WorkspaceNotFoundError):
            self.engine.connect("nonexistent", "https://example.com", "token")
    
    def test_disconnect_success(self):
        """Test successful sync disconnection."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock database query
        mock_sync_meta = Mock(spec=SyncMetadata)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_sync_meta
        
        # Execute
        self.engine.disconnect(workspace)
        
        # Verify
        assert mock_config.sync_enabled is False
        assert mock_config.sync_url is None
        self.mock_session.commit.assert_called()
    
    def test_sync_now_not_enabled(self):
        """Test sync_now raises error when sync not enabled."""
        workspace = "test-workspace"
        
        # Mock workspace config with sync disabled
        mock_config = Mock()
        mock_config.sync_enabled = False
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        with pytest.raises(SyncOperationError):
            self.engine.sync_now(workspace)
    
    def test_sync_now_no_sync_url(self):
        """Test sync_now raises error when sync URL not configured."""
        workspace = "test-workspace"
        
        # Mock workspace config with no URL
        mock_config = Mock()
        mock_config.sync_enabled = True
        mock_config.sync_url = None
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        with pytest.raises(SyncOperationError):
            self.engine.sync_now(workspace)
    
    def test_queue_operation_success(self):
        """Test successful operation queuing."""
        workspace = "test-workspace"
        operation_type = "create"
        entity_type = "secret"
        entity_id = "secret-123"
        data = {"key": "value"}
        
        # Mock workspace config
        mock_config = Mock()
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Execute
        operation_id = self.engine.queue_operation(
            workspace, operation_type, entity_type, entity_id, data
        )
        
        # Verify
        assert operation_id is not None
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_queue_operation_workspace_not_found(self):
        """Test queue_operation raises error for non-existent workspace."""
        self.mock_config_manager.get_workspace_config.side_effect = WorkspaceNotFoundError("Not found")
        
        with pytest.raises(WorkspaceNotFoundError):
            self.engine.queue_operation("nonexistent", "create", "secret", "id", {})
    
    def test_enable_auto_sync_success(self):
        """Test successful auto-sync enablement."""
        workspace = "test-workspace"
        interval = 300
        
        # Mock workspace config
        mock_config = Mock()
        mock_config.sync_enabled = True
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock database query
        mock_sync_meta = Mock(spec=SyncMetadata)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_sync_meta
        
        # Execute
        self.engine.enable_auto_sync(workspace, interval)
        
        # Verify
        assert mock_config.auto_sync_interval == interval
        self.mock_session.commit.assert_called()
    
    def test_enable_auto_sync_not_enabled(self):
        """Test enable_auto_sync raises error when sync not enabled."""
        workspace = "test-workspace"
        
        # Mock workspace config with sync disabled
        mock_config = Mock()
        mock_config.sync_enabled = False
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        with pytest.raises(SyncOperationError):
            self.engine.enable_auto_sync(workspace)
    
    def test_disable_auto_sync_success(self):
        """Test successful auto-sync disablement."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock database query
        mock_sync_meta = Mock(spec=SyncMetadata)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_sync_meta
        
        # Execute
        self.engine.disable_auto_sync(workspace)
        
        # Verify
        assert mock_config.auto_sync_interval is None
        self.mock_session.commit.assert_called()
    
    def test_get_sync_status_success(self):
        """Test successful sync status retrieval."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        mock_config.last_sync = datetime.utcnow()
        mock_config.sync_enabled = True
        mock_config.sync_url = "https://example.com"
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock database queries
        mock_sync_meta = Mock(spec=SyncMetadata)
        mock_sync_meta.remote_version = "0.3.0"
        mock_sync_meta.consecutive_failures = 0
        mock_sync_meta.last_error = None
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_sync_meta
        self.mock_session.query.return_value.filter.return_value.count.return_value = 5
        
        # Execute
        with patch("caracal.deployment.sync_engine.get_version_checker") as mock_version:
            mock_version.return_value.get_local_version.return_value = "0.3.0"
            status = self.engine.get_sync_status(workspace)
        
        # Verify
        assert status.workspace == workspace
        assert status.sync_enabled is True
        assert status.pending_operations == 5
    
    def test_resolve_conflicts_operational_transform(self):
        """Test conflict resolution with operational transform."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        mock_config.conflict_strategy = ConflictStrategy.OPERATIONAL_TRANSFORM
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock unresolved conflicts
        mock_conflict = Mock(spec=SyncConflict)
        mock_conflict.conflict_id = uuid4()
        mock_conflict.entity_type = "secret"
        mock_conflict.entity_id = "secret-123"
        mock_conflict.local_version = {"key": "local_value", "field1": "value1"}
        mock_conflict.remote_version = {"key": "remote_value", "field2": "value2"}
        mock_conflict.local_timestamp = datetime.utcnow()
        mock_conflict.remote_timestamp = datetime.utcnow()
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = [mock_conflict]
        
        # Execute
        resolved_count = self.engine.resolve_conflicts(workspace)
        
        # Verify
        assert resolved_count == 1
        self.mock_session.commit.assert_called()
    
    def test_resolve_conflicts_last_write_wins(self):
        """Test conflict resolution with last-write-wins."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        mock_config.conflict_strategy = ConflictStrategy.LAST_WRITE_WINS
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock unresolved conflicts
        mock_conflict = Mock(spec=SyncConflict)
        mock_conflict.conflict_id = uuid4()
        mock_conflict.entity_type = "secret"
        mock_conflict.entity_id = "secret-123"
        mock_conflict.local_version = {"key": "local_value"}
        mock_conflict.remote_version = {"key": "remote_value"}
        mock_conflict.local_timestamp = datetime.utcnow() - timedelta(hours=1)
        mock_conflict.remote_timestamp = datetime.utcnow()
        
        self.mock_session.query.return_value.filter.return_value.all.return_value = [mock_conflict]
        
        # Execute
        resolved_count = self.engine.resolve_conflicts(workspace)
        
        # Verify
        assert resolved_count == 1
        # Remote should win (newer timestamp)
        assert mock_conflict.resolved_version == mock_conflict.remote_version
    
    def test_get_conflict_history_success(self):
        """Test successful conflict history retrieval."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock conflicts
        mock_conflict = Mock(spec=SyncConflict)
        mock_conflict.conflict_id = uuid4()
        mock_conflict.entity_type = "secret"
        mock_conflict.entity_id = "secret-123"
        mock_conflict.local_version = {"key": "local"}
        mock_conflict.remote_version = {"key": "remote"}
        mock_conflict.local_timestamp = datetime.utcnow()
        mock_conflict.remote_timestamp = datetime.utcnow()
        mock_conflict.resolution_strategy = "operational_transform"
        mock_conflict.resolved_at = datetime.utcnow()
        
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_conflict]
        
        # Execute
        conflicts = self.engine.get_conflict_history(workspace)
        
        # Verify
        assert len(conflicts) == 1
        assert conflicts[0].entity_type == "secret"
    
    def test_check_connectivity_success(self):
        """Test successful connectivity check."""
        workspace = "test-workspace"
        
        # Mock workspace config
        mock_config = Mock()
        mock_config.sync_url = "https://example.com"
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Mock HTTP client
        with patch.object(self.engine, "_get_http_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            # Execute
            result = self.engine.check_connectivity(workspace)
            
            # Verify
            assert result is True
    
    def test_check_connectivity_no_url(self):
        """Test connectivity check with no sync URL."""
        workspace = "test-workspace"
        
        # Mock workspace config with no URL
        mock_config = Mock()
        mock_config.sync_url = None
        self.mock_config_manager.get_workspace_config.return_value = mock_config
        
        # Execute
        result = self.engine.check_connectivity(workspace)
        
        # Verify
        assert result is False
    
    def test_get_pending_operations_count(self):
        """Test getting pending operations count."""
        workspace = "test-workspace"
        
        # Mock database query
        self.mock_session.query.return_value.filter.return_value.count.return_value = 10
        
        # Execute
        count = self.engine.get_pending_operations_count(workspace)
        
        # Verify
        assert count == 10
    
    def test_get_failed_operations(self):
        """Test getting failed operations."""
        workspace = "test-workspace"
        
        # Mock failed operation
        mock_op = Mock(spec=SyncOperation)
        mock_op.operation_id = uuid4()
        mock_op.operation_type = "create"
        mock_op.entity_type = "secret"
        mock_op.entity_id = "secret-123"
        mock_op.operation_data = {"key": "value"}
        mock_op.created_at = datetime.utcnow()
        mock_op.retry_count = 3
        mock_op.last_error = "Connection failed"
        
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_op]
        
        # Execute
        operations = self.engine.get_failed_operations(workspace)
        
        # Verify
        assert len(operations) == 1
        assert operations[0].type == "create"
        assert operations[0].retry_count == 3
    
    def test_retry_failed_operation_success(self):
        """Test successful retry of failed operation."""
        workspace = "test-workspace"
        operation_id = str(uuid4())
        
        # Mock failed operation
        mock_op = Mock(spec=SyncOperation)
        mock_op.status = "failed"
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_op
        
        # Execute
        result = self.engine.retry_failed_operation(workspace, operation_id)
        
        # Verify
        assert result is True
        assert mock_op.status == "pending"
        assert mock_op.retry_count == 0
        self.mock_session.commit.assert_called()
    
    def test_retry_failed_operation_not_found(self):
        """Test retry of non-existent operation."""
        workspace = "test-workspace"
        operation_id = str(uuid4())
        
        # Mock no operation found
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = self.engine.retry_failed_operation(workspace, operation_id)
        
        # Verify
        assert result is False
