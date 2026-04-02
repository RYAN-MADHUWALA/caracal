"""
Unit tests for Caracal exceptions module.
"""
import pytest
from caracal import exceptions


@pytest.mark.unit
class TestBaseExceptions:
    """Test base exception classes."""
    
    def test_caracal_error_is_exception(self):
        """Test that CaracalError inherits from Exception."""
        assert issubclass(exceptions.CaracalError, Exception)
    
    def test_caracal_error_can_be_raised(self):
        """Test that CaracalError can be raised and caught."""
        with pytest.raises(exceptions.CaracalError):
            raise exceptions.CaracalError("test error")
    
    def test_caracal_error_message(self):
        """Test that CaracalError preserves error message."""
        msg = "test error message"
        try:
            raise exceptions.CaracalError(msg)
        except exceptions.CaracalError as e:
            assert str(e) == msg


@pytest.mark.unit
class TestIdentityErrors:
    """Test identity-related exceptions."""
    
    def test_identity_error_inherits_from_caracal_error(self):
        """Test IdentityError inheritance."""
        assert issubclass(exceptions.IdentityError, exceptions.CaracalError)
    
    def test_principal_not_found_error(self):
        """Test PrincipalNotFoundError."""
        with pytest.raises(exceptions.PrincipalNotFoundError):
            raise exceptions.PrincipalNotFoundError("principal not found")
    
    def test_duplicate_principal_name_error(self):
        """Test DuplicatePrincipalNameError."""
        with pytest.raises(exceptions.DuplicatePrincipalNameError):
            raise exceptions.DuplicatePrincipalNameError("duplicate name")
    
    def test_invalid_principal_id_error(self):
        """Test InvalidPrincipalIDError."""
        with pytest.raises(exceptions.InvalidPrincipalIDError):
            raise exceptions.InvalidPrincipalIDError("invalid ID")


@pytest.mark.unit
class TestPolicyErrors:
    """Test policy-related exceptions."""
    
    def test_policy_error_inherits_from_caracal_error(self):
        """Test PolicyError inheritance."""
        assert issubclass(exceptions.PolicyError, exceptions.CaracalError)
    
    def test_policy_not_found_error(self):
        """Test PolicyNotFoundError."""
        with pytest.raises(exceptions.PolicyNotFoundError):
            raise exceptions.PolicyNotFoundError("policy not found")
    
    def test_invalid_policy_error(self):
        """Test InvalidPolicyError."""
        with pytest.raises(exceptions.InvalidPolicyError):
            raise exceptions.InvalidPolicyError("invalid policy")
    
    def test_policy_evaluation_error(self):
        """Test PolicyEvaluationError."""
        with pytest.raises(exceptions.PolicyEvaluationError):
            raise exceptions.PolicyEvaluationError("evaluation failed")


@pytest.mark.unit
class TestLedgerErrors:
    """Test ledger-related exceptions."""
    
    def test_ledger_error_inherits_from_caracal_error(self):
        """Test LedgerError inheritance."""
        assert issubclass(exceptions.LedgerError, exceptions.CaracalError)
    
    def test_ledger_write_error(self):
        """Test LedgerWriteError."""
        with pytest.raises(exceptions.LedgerWriteError):
            raise exceptions.LedgerWriteError("write failed")
    
    def test_ledger_read_error(self):
        """Test LedgerReadError."""
        with pytest.raises(exceptions.LedgerReadError):
            raise exceptions.LedgerReadError("read failed")
    
    def test_invalid_ledger_event_error(self):
        """Test InvalidLedgerEventError."""
        with pytest.raises(exceptions.InvalidLedgerEventError):
            raise exceptions.InvalidLedgerEventError("invalid event")


@pytest.mark.unit
class TestMeteringErrors:
    """Test metering-related exceptions."""
    
    def test_metering_error_inherits_from_caracal_error(self):
        """Test MeteringError inheritance."""
        assert issubclass(exceptions.MeteringError, exceptions.CaracalError)
    
    def test_invalid_metering_event_error(self):
        """Test InvalidMeteringEventError."""
        with pytest.raises(exceptions.InvalidMeteringEventError):
            raise exceptions.InvalidMeteringEventError("invalid event")
    
    def test_metering_collection_error(self):
        """Test MeteringCollectionError."""
        with pytest.raises(exceptions.MeteringCollectionError):
            raise exceptions.MeteringCollectionError("collection failed")


@pytest.mark.unit
class TestConfigurationErrors:
    """Test configuration-related exceptions."""
    
    def test_configuration_error_inherits_from_caracal_error(self):
        """Test ConfigurationError inheritance."""
        assert issubclass(exceptions.ConfigurationError, exceptions.CaracalError)
    
    def test_invalid_configuration_error(self):
        """Test InvalidConfigurationError."""
        with pytest.raises(exceptions.InvalidConfigurationError):
            raise exceptions.InvalidConfigurationError("invalid config")
    
    def test_configuration_load_error(self):
        """Test ConfigurationLoadError."""
        with pytest.raises(exceptions.ConfigurationLoadError):
            raise exceptions.ConfigurationLoadError("load failed")


@pytest.mark.unit
class TestStorageErrors:
    """Test storage-related exceptions."""
    
    def test_storage_error_inherits_from_caracal_error(self):
        """Test StorageError inheritance."""
        assert issubclass(exceptions.StorageError, exceptions.CaracalError)
    
    def test_file_write_error(self):
        """Test FileWriteError."""
        with pytest.raises(exceptions.FileWriteError):
            raise exceptions.FileWriteError("write failed")
    
    def test_file_read_error(self):
        """Test FileReadError."""
        with pytest.raises(exceptions.FileReadError):
            raise exceptions.FileReadError("read failed")
    
    def test_backup_error(self):
        """Test BackupError."""
        with pytest.raises(exceptions.BackupError):
            raise exceptions.BackupError("backup failed")
    
    def test_restore_error(self):
        """Test RestoreError."""
        with pytest.raises(exceptions.RestoreError):
            raise exceptions.RestoreError("restore failed")


@pytest.mark.unit
class TestDelegationTokenErrors:
    """Test delegation token-related exceptions."""
    
    def test_delegation_token_error_inherits_from_caracal_error(self):
        """Test DelegationTokenError inheritance."""
        assert issubclass(exceptions.DelegationTokenError, exceptions.CaracalError)
    
    def test_invalid_delegation_token_error(self):
        """Test InvalidDelegationTokenError."""
        with pytest.raises(exceptions.InvalidDelegationTokenError):
            raise exceptions.InvalidDelegationTokenError("invalid token")
    
    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        with pytest.raises(exceptions.TokenExpiredError):
            raise exceptions.TokenExpiredError("token expired")
    
    def test_token_validation_error(self):
        """Test TokenValidationError."""
        with pytest.raises(exceptions.TokenValidationError):
            raise exceptions.TokenValidationError("validation failed")


@pytest.mark.unit
class TestMerkleErrors:
    """Test Merkle tree-related exceptions."""
    
    def test_merkle_error_inherits_from_caracal_error(self):
        """Test MerkleError inheritance."""
        assert issubclass(exceptions.MerkleError, exceptions.CaracalError)
    
    def test_merkle_verification_error(self):
        """Test MerkleVerificationError."""
        with pytest.raises(exceptions.MerkleVerificationError):
            raise exceptions.MerkleVerificationError("verification failed")
    
    def test_tamper_detected_error(self):
        """Test TamperDetectedError."""
        with pytest.raises(exceptions.TamperDetectedError):
            raise exceptions.TamperDetectedError("tampering detected")
    
    def test_backfill_error(self):
        """Test BackfillError."""
        with pytest.raises(exceptions.BackfillError):
            raise exceptions.BackfillError("backfill failed")


@pytest.mark.unit
class TestAuthorityErrors:
    """Test authority-related exceptions."""
    
    def test_authority_error_inherits_from_caracal_error(self):
        """Test AuthorityError inheritance."""
        assert issubclass(exceptions.AuthorityError, exceptions.CaracalError)
    
    def test_authority_denied_error(self):
        """Test AuthorityDeniedError."""
        with pytest.raises(exceptions.AuthorityDeniedError):
            raise exceptions.AuthorityDeniedError("authority denied")
    
    def test_mandate_not_found_error(self):
        """Test MandateNotFoundError."""
        with pytest.raises(exceptions.MandateNotFoundError):
            raise exceptions.MandateNotFoundError("mandate not found")
    
    def test_mandate_expired_error(self):
        """Test MandateExpiredError."""
        with pytest.raises(exceptions.MandateExpiredError):
            raise exceptions.MandateExpiredError("mandate expired")
    
    def test_mandate_revoked_error(self):
        """Test MandateRevokedError."""
        with pytest.raises(exceptions.MandateRevokedError):
            raise exceptions.MandateRevokedError("mandate revoked")
    
    def test_invalid_mandate_error(self):
        """Test InvalidMandateError."""
        with pytest.raises(exceptions.InvalidMandateError):
            raise exceptions.InvalidMandateError("invalid mandate")
    
    def test_delegation_error(self):
        """Test DelegationError."""
        with pytest.raises(exceptions.DelegationError):
            raise exceptions.DelegationError("delegation failed")
    
    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError."""
        with pytest.raises(exceptions.RateLimitExceededError):
            raise exceptions.RateLimitExceededError("rate limit exceeded")


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test exception hierarchy and catching."""
    
    def test_catch_specific_with_base(self):
        """Test that specific exceptions can be caught with base class."""
        with pytest.raises(exceptions.CaracalError):
            raise exceptions.PolicyNotFoundError("test")
    
    def test_catch_identity_errors_with_identity_error(self):
        """Test catching identity errors with IdentityError base."""
        with pytest.raises(exceptions.IdentityError):
            raise exceptions.PrincipalNotFoundError("test")
    
    def test_catch_policy_errors_with_policy_error(self):
        """Test catching policy errors with PolicyError base."""
        with pytest.raises(exceptions.PolicyError):
            raise exceptions.InvalidPolicyError("test")
    
    def test_catch_authority_errors_with_authority_error(self):
        """Test catching authority errors with AuthorityError base."""
        with pytest.raises(exceptions.AuthorityError):
            raise exceptions.MandateExpiredError("test")
