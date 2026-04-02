"""
Unit tests for Caracal vault module.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from caracal.core.vault import (
    CaracalVault,
    VaultEntry,
    VaultAuditEvent,
    VaultError,
    GatewayContextRequired,
    SecretNotFound,
    VaultRateLimitExceeded,
    MasterKeyError,
    MasterKeyProvider,
    gateway_context,
    _InMemoryVaultStorage,
)


@pytest.fixture
def mock_storage():
    """Provide a mock vault storage."""
    storage = Mock(spec=_InMemoryVaultStorage)
    storage.save = Mock()
    storage.load = Mock()
    storage.exists = Mock(return_value=False)
    storage.remove = Mock()
    storage.list_names = Mock(return_value=[])
    storage.current_key_version = Mock(return_value=1)
    return storage


@pytest.fixture
def mock_key_provider():
    """Provide a mock master key provider."""
    provider = Mock(spec=MasterKeyProvider)
    provider.derive = Mock(return_value=b"0" * 32)  # 32-byte key
    return provider


@pytest.fixture
def sample_vault_entry():
    """Provide a sample vault entry."""
    return VaultEntry(
        entry_id="entry-123",
        org_id="org-456",
        env_id="env-789",
        secret_name="api-key",
        ciphertext_b64="encrypted_data",
        iv_b64="nonce_data",
        encrypted_dek_b64="encrypted_key",
        dek_iv_b64="key_nonce",
        key_version=1,
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z"
    )


@pytest.mark.unit
class TestVaultEntry:
    """Test VaultEntry dataclass."""
    
    def test_vault_entry_creation(self, sample_vault_entry):
        """Test creating a VaultEntry."""
        assert sample_vault_entry.entry_id == "entry-123"
        assert sample_vault_entry.org_id == "org-456"
        assert sample_vault_entry.env_id == "env-789"
        assert sample_vault_entry.secret_name == "api-key"
        assert sample_vault_entry.key_version == 1


@pytest.mark.unit
class TestVaultAuditEvent:
    """Test VaultAuditEvent dataclass."""
    
    def test_audit_event_creation(self):
        """Test creating a VaultAuditEvent."""
        event = VaultAuditEvent(
            event_id="event-123",
            org_id="org-456",
            env_id="env-789",
            secret_name="api-key",
            operation="create",
            key_version=1,
            actor="gateway",
            timestamp="2024-01-15T10:00:00Z",
            success=True
        )
        
        assert event.event_id == "event-123"
        assert event.operation == "create"
        assert event.success is True
        assert event.error_code is None


@pytest.mark.unit
class TestGatewayContext:
    """Test gateway_context context manager."""
    
    def test_gateway_context_activation(self):
        """Test that gateway context activates correctly."""
        with gateway_context():
            # Inside context, should be active
            from caracal.core.vault import _GATEWAY_CONTEXT_FLAG
            assert getattr(_GATEWAY_CONTEXT_FLAG, "active", False) is True
        
        # Outside context, should be inactive
        assert getattr(_GATEWAY_CONTEXT_FLAG, "active", False) is False
    
    def test_gateway_context_required_without_context(self):
        """Test that operations fail without gateway context."""
        from caracal.core.vault import _assert_gateway_context
        
        with pytest.raises(GatewayContextRequired, match="may only be accessed from within the gateway"):
            _assert_gateway_context()
    
    def test_gateway_context_required_with_context(self):
        """Test that operations succeed with gateway context."""
        from caracal.core.vault import _assert_gateway_context
        
        with gateway_context():
            # Should not raise
            _assert_gateway_context()


@pytest.mark.unit
class TestMasterKeyProvider:
    """Test MasterKeyProvider class."""
    
    def test_master_key_provider_requires_env_var(self):
        """Test that MasterKeyProvider requires CARACAL_VAULT_MEK_SECRET."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(MasterKeyError, match="CARACAL_VAULT_MEK_SECRET is not set"):
                MasterKeyProvider()
    
    def test_master_key_provider_derives_key(self):
        """Test that MasterKeyProvider derives keys correctly."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            provider = MasterKeyProvider()
            key = provider.derive("org-123", "env-456", 1)
            
            assert isinstance(key, bytes)
            assert len(key) == 32  # 256 bits
    
    def test_master_key_provider_deterministic(self):
        """Test that key derivation is deterministic."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            provider = MasterKeyProvider()
            key1 = provider.derive("org-123", "env-456", 1)
            key2 = provider.derive("org-123", "env-456", 1)
            
            assert key1 == key2
    
    def test_master_key_provider_different_versions(self):
        """Test that different versions produce different keys."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            provider = MasterKeyProvider()
            key_v1 = provider.derive("org-123", "env-456", 1)
            key_v2 = provider.derive("org-123", "env-456", 2)
            
            assert key_v1 != key_v2


@pytest.mark.unit
class TestInMemoryVaultStorage:
    """Test _InMemoryVaultStorage class."""
    
    def test_storage_save_and_load(self, sample_vault_entry):
        """Test saving and loading entries."""
        storage = _InMemoryVaultStorage()
        
        storage.save(sample_vault_entry)
        loaded = storage.load(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id,
            sample_vault_entry.secret_name
        )
        
        assert loaded.entry_id == sample_vault_entry.entry_id
        assert loaded.secret_name == sample_vault_entry.secret_name
    
    def test_storage_load_nonexistent(self):
        """Test loading nonexistent entry."""
        storage = _InMemoryVaultStorage()
        
        with pytest.raises(SecretNotFound, match="not found"):
            storage.load("org-123", "env-456", "nonexistent")
    
    def test_storage_exists(self, sample_vault_entry):
        """Test checking if entry exists."""
        storage = _InMemoryVaultStorage()
        
        assert storage.exists(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id,
            sample_vault_entry.secret_name
        ) is False
        
        storage.save(sample_vault_entry)
        
        assert storage.exists(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id,
            sample_vault_entry.secret_name
        ) is True
    
    def test_storage_remove(self, sample_vault_entry):
        """Test removing entries."""
        storage = _InMemoryVaultStorage()
        
        storage.save(sample_vault_entry)
        assert storage.exists(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id,
            sample_vault_entry.secret_name
        ) is True
        
        storage.remove(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id,
            sample_vault_entry.secret_name
        )
        
        assert storage.exists(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id,
            sample_vault_entry.secret_name
        ) is False
    
    def test_storage_list_names(self, sample_vault_entry):
        """Test listing secret names."""
        storage = _InMemoryVaultStorage()
        
        storage.save(sample_vault_entry)
        
        # Create another entry for same org/env
        entry2 = VaultEntry(
            entry_id="entry-456",
            org_id=sample_vault_entry.org_id,
            env_id=sample_vault_entry.env_id,
            secret_name="another-secret",
            ciphertext_b64="data",
            iv_b64="nonce",
            encrypted_dek_b64="key",
            dek_iv_b64="key_nonce",
            key_version=1,
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z"
        )
        storage.save(entry2)
        
        names = storage.list_names(sample_vault_entry.org_id, sample_vault_entry.env_id)
        
        assert len(names) == 2
        assert "api-key" in names
        assert "another-secret" in names
    
    def test_storage_current_key_version(self, sample_vault_entry):
        """Test getting current key version."""
        storage = _InMemoryVaultStorage()
        
        # Default version
        assert storage.current_key_version("org-123", "env-456") == 1
        
        # After saving entry with version 1
        storage.save(sample_vault_entry)
        assert storage.current_key_version(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id
        ) == 1
        
        # After saving entry with version 2
        entry_v2 = VaultEntry(
            entry_id="entry-v2",
            org_id=sample_vault_entry.org_id,
            env_id=sample_vault_entry.env_id,
            secret_name="secret-v2",
            ciphertext_b64="data",
            iv_b64="nonce",
            encrypted_dek_b64="key",
            dek_iv_b64="key_nonce",
            key_version=2,
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z"
        )
        storage.save(entry_v2)
        assert storage.current_key_version(
            sample_vault_entry.org_id,
            sample_vault_entry.env_id
        ) == 2


@pytest.mark.unit
class TestCaracalVault:
    """Test CaracalVault class."""
    
    def test_vault_creation(self):
        """Test creating a CaracalVault."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            assert vault._storage is not None
            assert vault._keys is not None
    
    def test_vault_put_requires_gateway_context(self):
        """Test that put requires gateway context."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with pytest.raises(GatewayContextRequired):
                vault.put("org-123", "env-456", "secret-name", "secret-value")
    
    def test_vault_put_success(self):
        """Test successfully storing a secret."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with gateway_context():
                entry = vault.put("org-123", "env-456", "api-key", "secret-value-123")
                
                assert entry.org_id == "org-123"
                assert entry.env_id == "env-456"
                assert entry.secret_name == "api-key"
                assert entry.key_version == 1
    
    def test_vault_get_requires_gateway_context(self):
        """Test that get requires gateway context."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with pytest.raises(GatewayContextRequired):
                vault.get("org-123", "env-456", "secret-name")
    
    def test_vault_get_success(self):
        """Test successfully retrieving a secret."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with gateway_context():
                # Store secret
                vault.put("org-123", "env-456", "api-key", "secret-value-123")
                
                # Retrieve secret
                value = vault.get("org-123", "env-456", "api-key")
                
                assert value == "secret-value-123"
    
    def test_vault_get_nonexistent(self):
        """Test retrieving nonexistent secret."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with gateway_context():
                with pytest.raises(SecretNotFound):
                    vault.get("org-123", "env-456", "nonexistent")
    
    def test_vault_delete_requires_gateway_context(self):
        """Test that delete requires gateway context."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with pytest.raises(GatewayContextRequired):
                vault.delete("org-123", "env-456", "secret-name")
    
    def test_vault_delete_success(self):
        """Test successfully deleting a secret."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with gateway_context():
                # Store secret
                vault.put("org-123", "env-456", "api-key", "secret-value-123")
                
                # Delete secret
                vault.delete("org-123", "env-456", "api-key")
                
                # Verify deleted
                with pytest.raises(SecretNotFound):
                    vault.get("org-123", "env-456", "api-key")
    
    def test_vault_list_secrets_requires_gateway_context(self):
        """Test that list_secrets requires gateway context."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with pytest.raises(GatewayContextRequired):
                vault.list_secrets("org-123", "env-456")
    
    def test_vault_list_secrets_success(self):
        """Test successfully listing secrets."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with gateway_context():
                # Store multiple secrets
                vault.put("org-123", "env-456", "api-key-1", "value1")
                vault.put("org-123", "env-456", "api-key-2", "value2")
                
                # List secrets
                names = vault.list_secrets("org-123", "env-456")
                
                assert len(names) == 2
                assert "api-key-1" in names
                assert "api-key-2" in names
    
    def test_vault_drain_audit_events(self):
        """Test draining audit events."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            with gateway_context():
                # Perform operations that generate audit events
                vault.put("org-123", "env-456", "api-key", "value")
                vault.get("org-123", "env-456", "api-key")
                
                # Drain events
                events = vault.drain_audit_events()
                
                assert len(events) >= 2
                assert all(isinstance(e, VaultAuditEvent) for e in events)
                
                # Verify events are cleared
                events2 = vault.drain_audit_events()
                assert len(events2) == 0
    
    def test_vault_rate_limiting(self):
        """Test rate limiting enforcement."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            # Create vault with very low rate limit
            vault = CaracalVault(rate_limit=2)
            
            with gateway_context():
                # First two requests should succeed
                vault.put("org-123", "env-456", "key1", "value1")
                vault.put("org-123", "env-456", "key2", "value2")
                
                # Third request should be rate limited
                with pytest.raises(VaultRateLimitExceeded, match="rate limit exceeded"):
                    vault.put("org-123", "env-456", "key3", "value3")
    
    def test_vault_encryption_roundtrip(self):
        """Test that encryption and decryption preserve data."""
        with patch("caracal.core.vault._read_env_or_dotenv", return_value="test_secret_key_12345678901234567890"):
            vault = CaracalVault()
            
            test_values = [
                "simple-value",
                "value with spaces",
                "value-with-special-chars!@#$%",
                "unicode-value-🔐",
                "a" * 1000,  # Long value
            ]
            
            with gateway_context():
                for i, value in enumerate(test_values):
                    name = f"secret-{i}"
                    vault.put("org-123", "env-456", name, value)
                    retrieved = vault.get("org-123", "env-456", name)
                    assert retrieved == value
