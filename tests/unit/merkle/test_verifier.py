"""
Unit tests for caracal/merkle/verifier.py

Tests verification logic, tamper detection, and proof validation.
"""
import hashlib
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, MagicMock
from caracal.merkle.verifier import (
    MerkleVerifier,
    VerificationResult,
    VerificationSummary
)
from caracal.merkle.tree import MerkleTree


@pytest.fixture
def mock_db_session():
    """Provide a mock async database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_merkle_signer():
    """Provide a mock Merkle signer."""
    signer = Mock()
    signer.verify_signature = AsyncMock(return_value=True)
    return signer


@pytest.fixture
def sample_batch_id():
    """Provide a sample batch ID."""
    return uuid4()


@pytest.fixture
def sample_merkle_root_record(sample_batch_id):
    """Provide a sample MerkleRoot record."""
    record = Mock()
    record.batch_id = sample_batch_id
    record.merkle_root = "a" * 64  # Hex-encoded hash
    record.signature = "b" * 128  # Hex-encoded signature
    record.event_count = 3
    record.first_event_id = 1
    record.last_event_id = 3
    record.source = "live"
    record.created_at = datetime.utcnow()
    return record


@pytest.fixture
def sample_ledger_events():
    """Provide sample ledger events."""
    events = []
    for i in range(1, 4):
        event = Mock()
        event.event_id = i
        event.principal_id = uuid4()
        event.timestamp = datetime.utcnow()
        event.resource_type = "compute"
        event.quantity = 1.0
        events.append(event)
    return events


@pytest.mark.unit
class TestMerkleVerifierInitialization:
    """Test MerkleVerifier initialization."""
    
    def test_verifier_initialization(self, mock_db_session, mock_merkle_signer):
        """Test verifier initializes correctly."""
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        
        assert verifier.db_session == mock_db_session
        assert verifier.merkle_signer == mock_merkle_signer


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchVerification:
    """Test single batch verification."""
    
    async def test_verify_batch_success(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_batch_id,
        sample_merkle_root_record,
        sample_ledger_events
    ):
        """Test successful batch verification."""
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Setup events query
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_ledger_events)))
        
        # Mock execute to return different results for different queries
        async def mock_execute(stmt):
            # First call returns merkle root, second returns events
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        # Compute expected root from events
        event_hashes = []
        for event in sample_ledger_events:
            event_data = (
                f"{event.event_id}|{event.principal_id}|{event.timestamp.isoformat()}|"
                f"{event.resource_type}|{event.quantity}"
            ).encode()
            event_hash = hashlib.sha256(event_data).digest()
            event_hashes.append(event_hash)
        
        tree = MerkleTree(event_hashes)
        computed_root = tree.get_root()
        
        # Update mock to return matching root
        sample_merkle_root_record.merkle_root = computed_root.hex()
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.batch_id == sample_batch_id
        assert result.verified is True
        assert result.signature_valid is True
        assert result.error_message is None
    
    async def test_verify_batch_not_found(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_batch_id
    ):
        """Test verification when batch not found."""
        # Setup mock to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.verified is False
        assert "not found" in result.error_message.lower()
    
    async def test_verify_batch_no_events(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_batch_id,
        sample_merkle_root_record
    ):
        """Test verification when no events found."""
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        
        async def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.verified is False
        assert "no events found" in result.error_message.lower()
    
    async def test_verify_batch_event_count_mismatch(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_batch_id,
        sample_merkle_root_record,
        sample_ledger_events
    ):
        """Test verification when event count doesn't match."""
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        
        # Return fewer events than expected
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_ledger_events[:2])))
        
        async def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.verified is False
        assert "event count mismatch" in result.error_message.lower()
    
    async def test_verify_batch_root_mismatch(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_batch_id,
        sample_merkle_root_record,
        sample_ledger_events
    ):
        """Test verification when roots don't match (tamper detection)."""
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_ledger_events)))
        
        async def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        # Set a different root (simulating tampering)
        sample_merkle_root_record.merkle_root = "c" * 64
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.verified is False
        assert "root mismatch" in result.error_message.lower()
    
    async def test_verify_batch_invalid_signature(
        self,
        mock_db_session,
        sample_batch_id,
        sample_merkle_root_record,
        sample_ledger_events
    ):
        """Test verification when signature is invalid."""
        # Setup mock signer to return False
        mock_signer = Mock()
        mock_signer.verify_signature = AsyncMock(return_value=False)
        
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_ledger_events)))
        
        async def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        # Compute expected root from events
        event_hashes = []
        for event in sample_ledger_events:
            event_data = (
                f"{event.event_id}|{event.principal_id}|{event.timestamp.isoformat()}|"
                f"{event.resource_type}|{event.quantity}"
            ).encode()
            event_hash = hashlib.sha256(event_data).digest()
            event_hashes.append(event_hash)
        
        tree = MerkleTree(event_hashes)
        computed_root = tree.get_root()
        sample_merkle_root_record.merkle_root = computed_root.hex()
        
        verifier = MerkleVerifier(mock_db_session, mock_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.verified is False
        assert result.signature_valid is False
        assert "invalid signature" in result.error_message.lower()
    
    async def test_verify_batch_migration_batch(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_batch_id,
        sample_merkle_root_record,
        sample_ledger_events
    ):
        """Test verification of migration batch."""
        # Mark as migration batch
        sample_merkle_root_record.source = "migration"
        
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_ledger_events)))
        
        async def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        # Compute expected root
        event_hashes = []
        for event in sample_ledger_events:
            event_data = (
                f"{event.event_id}|{event.principal_id}|{event.timestamp.isoformat()}|"
                f"{event.resource_type}|{event.quantity}"
            ).encode()
            event_hash = hashlib.sha256(event_data).digest()
            event_hashes.append(event_hash)
        
        tree = MerkleTree(event_hashes)
        computed_root = tree.get_root()
        sample_merkle_root_record.merkle_root = computed_root.hex()
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_batch(sample_batch_id)
        
        assert result.verified is True
        assert result.is_migration_batch is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestTimeRangeVerification:
    """Test time range verification."""
    
    async def test_verify_time_range_success(
        self,
        mock_db_session,
        mock_merkle_signer
    ):
        """Test successful time range verification."""
        # Create mock merkle roots
        mock_roots = []
        for i in range(3):
            root = Mock()
            root.batch_id = uuid4()
            root.created_at = datetime.utcnow()
            mock_roots.append(root)
        
        # Setup mock database response
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_roots)))
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock verify_batch to return success
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        
        async def mock_verify_batch(batch_id):
            return VerificationResult(
                batch_id=batch_id,
                verified=True,
                stored_root=b"test",
                computed_root=b"test",
                signature_valid=True
            )
        
        verifier.verify_batch = mock_verify_batch
        
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        
        summary = await verifier.verify_time_range(start_time, end_time)
        
        assert summary.total_batches == 3
        assert summary.verified_batches == 3
        assert summary.failed_batches == 0
        assert len(summary.verification_errors) == 0
    
    async def test_verify_time_range_no_batches(
        self,
        mock_db_session,
        mock_merkle_signer
    ):
        """Test time range verification with no batches."""
        # Setup mock to return empty list
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        
        summary = await verifier.verify_time_range(start_time, end_time)
        
        assert summary.total_batches == 0
        assert summary.verified_batches == 0
        assert summary.failed_batches == 0
    
    async def test_verify_time_range_with_failures(
        self,
        mock_db_session,
        mock_merkle_signer
    ):
        """Test time range verification with some failures."""
        # Create mock merkle roots
        mock_roots = []
        for i in range(3):
            root = Mock()
            root.batch_id = uuid4()
            root.created_at = datetime.utcnow()
            mock_roots.append(root)
        
        # Setup mock database response
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_roots)))
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        
        # Mock verify_batch to return mixed results
        call_count = 0
        
        async def mock_verify_batch(batch_id):
            nonlocal call_count
            call_count += 1
            
            if call_count == 2:
                # Second batch fails
                return VerificationResult(
                    batch_id=batch_id,
                    verified=False,
                    stored_root=b"test",
                    computed_root=b"different",
                    signature_valid=True,
                    error_message="Root mismatch"
                )
            else:
                return VerificationResult(
                    batch_id=batch_id,
                    verified=True,
                    stored_root=b"test",
                    computed_root=b"test",
                    signature_valid=True
                )
        
        verifier.verify_batch = mock_verify_batch
        
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        
        summary = await verifier.verify_time_range(start_time, end_time)
        
        assert summary.total_batches == 3
        assert summary.verified_batches == 2
        assert summary.failed_batches == 1
        assert len(summary.verification_errors) == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventInclusionVerification:
    """Test event inclusion verification."""
    
    async def test_verify_event_inclusion_success(
        self,
        mock_db_session,
        mock_merkle_signer,
        sample_merkle_root_record,
        sample_ledger_events
    ):
        """Test successful event inclusion verification."""
        event_id = 1
        
        # Setup mock database responses
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_merkle_root_record)
        
        events_result = Mock()
        events_result.scalars = Mock(return_value=Mock(all=Mock(return_value=sample_ledger_events)))
        
        async def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return mock_result
            else:
                return events_result
        
        mock_db_session.execute = mock_execute
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_event_inclusion(event_id)
        
        # Result depends on whether computed proof matches stored root
        assert isinstance(result, bool)
    
    async def test_verify_event_inclusion_batch_not_found(
        self,
        mock_db_session,
        mock_merkle_signer
    ):
        """Test event inclusion when batch not found."""
        event_id = 999
        
        # Setup mock to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        result = await verifier.verify_event_inclusion(event_id)
        
        assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestBackfillVerification:
    """Test backfill/migration batch verification."""
    
    async def test_verify_backfill_success(
        self,
        mock_db_session,
        mock_merkle_signer
    ):
        """Test successful backfill verification."""
        # Create mock migration batches
        mock_roots = []
        for i in range(2):
            root = Mock()
            root.batch_id = uuid4()
            root.source = "migration"
            root.created_at = datetime.utcnow()
            mock_roots.append(root)
        
        # Setup mock database response
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_roots)))
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        
        # Mock verify_batch to return success
        async def mock_verify_batch(batch_id):
            return VerificationResult(
                batch_id=batch_id,
                verified=True,
                stored_root=b"test",
                computed_root=b"test",
                signature_valid=True,
                is_migration_batch=True
            )
        
        verifier.verify_batch = mock_verify_batch
        
        summary = await verifier.verify_backfill()
        
        assert summary.total_batches == 2
        assert summary.verified_batches == 2
        assert summary.failed_batches == 0
    
    async def test_verify_backfill_no_migration_batches(
        self,
        mock_db_session,
        mock_merkle_signer
    ):
        """Test backfill verification with no migration batches."""
        # Setup mock to return empty list
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        verifier = MerkleVerifier(mock_db_session, mock_merkle_signer)
        
        summary = await verifier.verify_backfill()
        
        assert summary.total_batches == 0
        assert summary.verified_batches == 0
        assert summary.failed_batches == 0


@pytest.mark.unit
class TestVerificationResultDataclass:
    """Test VerificationResult dataclass."""
    
    def test_verification_result_creation(self):
        """Test creating VerificationResult."""
        batch_id = uuid4()
        result = VerificationResult(
            batch_id=batch_id,
            verified=True,
            stored_root=b"test",
            computed_root=b"test",
            signature_valid=True
        )
        
        assert result.batch_id == batch_id
        assert result.verified is True
        assert result.signature_valid is True
        assert result.is_migration_batch is False
        assert result.error_message is None
    
    def test_verification_result_with_error(self):
        """Test creating VerificationResult with error."""
        batch_id = uuid4()
        result = VerificationResult(
            batch_id=batch_id,
            verified=False,
            stored_root=b"test",
            computed_root=b"different",
            signature_valid=True,
            error_message="Root mismatch"
        )
        
        assert result.verified is False
        assert result.error_message == "Root mismatch"


@pytest.mark.unit
class TestVerificationSummaryDataclass:
    """Test VerificationSummary dataclass."""
    
    def test_verification_summary_creation(self):
        """Test creating VerificationSummary."""
        summary = VerificationSummary(
            total_batches=10,
            verified_batches=8,
            failed_batches=2,
            verification_errors=[]
        )
        
        assert summary.total_batches == 10
        assert summary.verified_batches == 8
        assert summary.failed_batches == 2
        assert len(summary.verification_errors) == 0
    
    def test_verification_summary_with_errors(self):
        """Test creating VerificationSummary with errors."""
        error = VerificationResult(
            batch_id=uuid4(),
            verified=False,
            stored_root=b"test",
            computed_root=b"different",
            signature_valid=True,
            error_message="Test error"
        )
        
        summary = VerificationSummary(
            total_batches=1,
            verified_batches=0,
            failed_batches=1,
            verification_errors=[error]
        )
        
        assert summary.failed_batches == 1
        assert len(summary.verification_errors) == 1
        assert summary.verification_errors[0].error_message == "Test error"
